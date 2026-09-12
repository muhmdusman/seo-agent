"""Probe the configured LLM provider's rate limits through the Strands SDK.

Calls the model the same way agents/weekly_agent.py does (Strands Agent over
LiteLLMModel, using settings.LLM_MODEL_ID and settings.LLM_API_KEY), so a pass
here means the agent's model path works.

Strands does not surface HTTP response headers, and the headers are where
providers report your actual allowance, so the script also makes one raw
request to read them.

Usage
-----
    cd backend
    uv run python check_rate_limit.py                 # 3 calls, 1s apart
    uv run python check_rate_limit.py -n 10 -d 0      # sustained, no delay
    uv run python check_rate_limit.py --burst         # 5 concurrent calls
    uv run python check_rate_limit.py --model groq/llama-3.3-70b-versatile

Never prints the API key.
"""

from __future__ import annotations

import argparse
import asyncio
import time

import httpx
from strands import Agent
from strands.models.litellm import LiteLLMModel

from core.config import settings


PROMPT = "Reply with exactly one word: ok"

# Where to read rate limit headers, keyed by LiteLLM provider prefix.
PROVIDER_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rule(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def split_model(model_id: str) -> tuple[str, str]:
    """Split a LiteLLM id into (provider, model name).

    Groq model names contain a slash of their own, as in
    groq/openai/gpt-oss-120b, so only the first segment is the provider.
    """
    provider, _, name = model_id.strip().partition("/")
    return provider.lower(), name


def build_agent(model_id: str, api_key: str, max_tokens: int) -> Agent:
    """Construct the agent the same way WeeklyAgent does.

    A fresh Agent per call on purpose. A single Strands Agent rejects
    concurrent invocations, and reusing one across turns makes the provider
    warn that reasoning content cannot be replayed in multi-turn history.
    """
    model = LiteLLMModel(
        model_id=model_id,
        client_args={"api_key": api_key},
        params={
            "temperature": 0,
            # Reasoning models spend part of this budget thinking before they
            # emit any answer, so a small ceiling trips MaxTokensReached
            # rather than returning a short reply.
            "max_tokens": max_tokens,
            "reasoning_effort": "medium",
        },
    )
    return Agent(model=model, tools=[])


def classify(exc: BaseException) -> str:
    """Map an exception to a short, actionable label."""
    name = type(exc).__name__
    text = str(exc)

    if "RateLimit" in name or "429" in text or "rate_limited" in text:
        return "RATE LIMITED (429)"
    if "Authentication" in name or "401" in text:
        return "AUTH FAILED (401) - key rejected"
    if "NotFound" in name or "404" in text or "does not exist" in text:
        return "MODEL NOT FOUND (404) - check the model id"
    if "BadRequest" in name or "400" in text or "422" in text:
        return "BAD REQUEST (400/422) - unsupported param or bad model id"
    if "Timeout" in name:
        return "TIMEOUT"
    return f"OTHER ({name}): {text[:120]}"


# ---------------------------------------------------------------------------
# Raw header probe
# ---------------------------------------------------------------------------

async def read_limit_headers(model_id: str, api_key: str) -> None:
    """Providers report the real allowance in headers, which the SDK hides."""
    rule("1. Reported allowance (raw request, for headers only)")

    provider, name = split_model(model_id)
    endpoint = PROVIDER_ENDPOINTS.get(provider)

    if endpoint is None:
        print(f"  no known REST endpoint for provider {provider!r}; skipping")
        return

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": name,
                    "messages": [{"role": "user", "content": PROMPT}],
                    "max_tokens": 16,
                    "temperature": 0,
                },
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  request failed: {type(exc).__name__}: {exc}")
            return

    print(f"  endpoint: {endpoint}")
    print(f"  status:   {response.status_code}")

    limits = {
        key: value
        for key, value in response.headers.items()
        if "ratelimit" in key.lower() or "retry-after" in key.lower()
    }

    if limits:
        for key, value in sorted(limits.items()):
            print(f"    {key}: {value}")
    else:
        print("    (no rate limit headers returned)")

    if response.status_code >= 400:
        print(f"    body: {response.text[:300]}")

    # A zero ceiling means the workspace is not provisioned at all, which no
    # amount of retrying or key rotation will fix.
    zero = [k for k, v in limits.items() if "limit" in k and v == "0"]
    if zero:
        print(
            "\n  >> Allowance is 0. This is not a burst throttle, so retrying\n"
            "     will not help, and limits are per workspace rather than per\n"
            "     key, so rotating the key changes nothing. Check the\n"
            "     provider's console for tier activation, spending caps, or\n"
            "     failed invoice payments."
        )
    elif response.status_code == 200:
        print("\n  >> Completions are permitted on this workspace.")


# ---------------------------------------------------------------------------
# Strands calls
# ---------------------------------------------------------------------------

async def one_call(agent: Agent, label: str) -> tuple[bool, float, str]:
    started = time.monotonic()
    try:
        result = await agent.invoke_async(PROMPT)
        elapsed = time.monotonic() - started
        reply = str(result).strip().replace("\n", " ")[:60]
        print(f"  {label}  OK      {elapsed:6.2f}s  reply={reply!r}")
        return True, elapsed, "ok"
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - started
        reason = classify(exc)
        print(f"  {label}  FAILED  {elapsed:6.2f}s  {reason}")
        return False, elapsed, reason


async def sequential(
    model_id: str, api_key: str, count: int, delay: float, max_tokens: int
) -> list[tuple[bool, float, str]]:
    rule(f"2. Sequential calls through Strands ({count} requests, {delay}s apart)")

    results = []

    for index in range(1, count + 1):
        agent = build_agent(model_id, api_key, max_tokens)
        results.append(await one_call(agent, f"[{index}/{count}]"))
        if index < count and delay > 0:
            await asyncio.sleep(delay)

    return results


async def burst(
    model_id: str, api_key: str, count: int, max_tokens: int
) -> list[tuple[bool, float, str]]:
    rule(f"3. Concurrent burst ({count} simultaneous requests)")
    print("  Reveals a requests-per-second ceiling that sequential calls miss.\n")

    # One Agent each: Strands raises ConcurrencyException if a single Agent
    # instance is invoked more than once at a time.
    return list(
        await asyncio.gather(
            *(
                one_call(build_agent(model_id, api_key, max_tokens), f"[burst {i}]")
                for i in range(1, count + 1)
            )
        )
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> int:
    model_id = (args.model or settings.LLM_MODEL_ID).strip()
    provider, name = split_model(model_id)

    api_key = (
        settings.MISTRAL_API_KEY if provider == "mistral" else settings.GROQ_API_KEY
    ).strip()

    rule(f"Rate limit check via Strands SDK ({provider})")

    if not api_key:
        print(f"  No API key for provider {provider!r}. Set it in backend/.env.")
        return 1

    print(f"  provider:    {provider}")
    print(f"  model:       {name}")
    print(f"  model id:    {model_id}")
    print(f"  key present: yes (length {len(api_key)})")

    if model_id != model_id.strip() or "\n" in model_id:
        print("  WARNING: model id contains whitespace or newlines")

    await read_limit_headers(model_id, api_key)

    results = await sequential(
        model_id, api_key, args.requests, args.delay, args.max_tokens
    )

    if args.burst:
        results += await burst(model_id, api_key, args.burst_size, args.max_tokens)

    # -- summary ------------------------------------------------------------
    rule("Summary")

    passed = sum(1 for ok, _, _ in results if ok)
    failed = len(results) - passed
    print(f"  succeeded: {passed}/{len(results)}")
    print(f"  failed:    {failed}/{len(results)}")

    if failed:
        reasons: dict[str, int] = {}
        for ok, _, reason in results:
            if not ok:
                reasons[reason] = reasons.get(reason, 0) + 1
        print("\n  failure breakdown:")
        for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"    {count:3d}  {reason}")

    if passed:
        latencies = [t for ok, t, _ in results if ok]
        print(
            f"\n  latency: min {min(latencies):.2f}s  "
            f"avg {sum(latencies) / len(latencies):.2f}s  "
            f"max {max(latencies):.2f}s"
        )

    if passed == len(results):
        print("\n  All calls succeeded. The agent's model path is healthy.")
        return 0

    if passed == 0:
        print("\n  Every call failed. See the breakdown above.")
        return 1

    print("\n  Partial success, which points at a per-minute or per-second")
    print("  ceiling rather than a hard block. Retry with backoff would help.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check LLM provider rate limits via the Strands SDK.",
    )
    parser.add_argument(
        "--model", default=None,
        help="override the model id (default: settings.LLM_MODEL_ID)",
    )
    parser.add_argument(
        "-n", "--requests", type=int, default=3,
        help="number of sequential calls (default: 3)",
    )
    parser.add_argument(
        "-d", "--delay", type=float, default=1.0,
        help="seconds between sequential calls (default: 1.0)",
    )
    parser.add_argument(
        "--burst", action="store_true",
        help="also fire a concurrent burst",
    )
    parser.add_argument(
        "--burst-size", type=int, default=5,
        help="requests in the burst (default: 5)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=512,
        help=(
            "completion budget per call (default: 512). Reasoning models spend "
            "part of this thinking, so very low values fail with "
            "MaxTokensReached rather than returning a short reply."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(parse_args())))
