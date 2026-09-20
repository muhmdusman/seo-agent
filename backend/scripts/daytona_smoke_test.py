"""Smoke-test the configured Daytona account without uploading repository data."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from daytona import AsyncDaytona, CreateSandboxFromSnapshotParams, DaytonaConfig


async def main() -> None:
    client = AsyncDaytona(
        DaytonaConfig(
            api_key=settings.DAYTONA_API_KEY,
            api_url=settings.DAYTONA_API_URL,
            target=settings.DAYTONA_TARGET.strip() or None,
        )
    )
    sandbox = None
    try:
        sandbox = await client.create(CreateSandboxFromSnapshotParams(
            name=f"{settings.DAYTONA_SANDBOX_NAME_PREFIX}-smoke",
            language="python",
            auto_stop_interval=settings.DAYTONA_SANDBOX_AUTO_STOP_MINUTES,
            auto_archive_interval=settings.DAYTONA_SANDBOX_AUTO_ARCHIVE_MINUTES,
            ephemeral=settings.DAYTONA_SANDBOX_EPHEMERAL,
            labels={"seo-agent-purpose": "smoke-test"},
        ))
        result = await sandbox.process.exec("pwd", timeout=30)
        print("daytona_create=True")
        print(f"exec_exit_code={getattr(result, 'exit_code', None)}")
        print(f"exec_result={str(getattr(result, 'result', '')).strip()}")
    finally:
        if sandbox is not None:
            await client.delete(sandbox, wait=True)
            print("daytona_deleted=True")
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
