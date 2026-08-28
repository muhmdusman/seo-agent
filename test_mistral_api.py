#!/usr/bin/env python3
"""
Test script to verify Mistral API key and diagnose timeout issues.
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

print("=" * 80)
print("MISTRAL API KEY VERIFICATION TEST")
print("=" * 80)
print()

# Check if API key exists
if not MISTRAL_API_KEY:
    print("❌ ERROR: MISTRAL_API_KEY not found in environment!")
    print("   Make sure .env file exists and contains MISTRAL_API_KEY")
    sys.exit(1)

print(f"✅ API Key found: {MISTRAL_API_KEY[:10]}...{MISTRAL_API_KEY[-5:]}")
print()

# Test different configurations
async def test_mistral(model_name, timeout, max_retries):
    """Test Mistral API with specific configuration."""
    print(f"\n{'─' * 80}")
    print(f"Testing: {model_name}")
    print(f"Timeout: {timeout}s | Max Retries: {max_retries}")
    print(f"{'─' * 80}")
    
    try:
        llm = ChatMistralAI(
            model_name=model_name,
            api_key=MISTRAL_API_KEY,
            temperature=0,
            timeout=timeout,
            max_retries=max_retries,
        )
        
        # Simple test prompt
        test_prompt = "Say 'Hello, I am working!' in one sentence."
        
        print(f"📤 Sending test prompt: '{test_prompt}'")
        start_time = time.time()
        
        response = await llm.ainvoke(test_prompt)
        
        elapsed = time.time() - start_time
        
        print(f"✅ SUCCESS!")
        print(f"⏱️  Response time: {elapsed:.2f} seconds")
        print(f"📥 Response: {response.content}")
        return True, elapsed
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ FAILED after {elapsed:.2f} seconds")
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        return False, elapsed


async def main():
    """Run all tests."""
    
    print("\n" + "=" * 80)
    print("TEST 1: Quick Response Test (mistral-small)")
    print("=" * 80)
    
    success1, time1 = await test_mistral(
        model_name="mistral-small-latest",
        timeout=60,
        max_retries=2,
    )
    
    if not success1:
        print("\n⚠️  Simple test failed! API key might be invalid or expired.")
        print("   Please check your Mistral API key at: https://console.mistral.ai/")
        return
    
    print("\n" + "=" * 80)
    print("TEST 2: Medium Model Test")
    print("=" * 80)
    
    success2, time2 = await test_mistral(
        model_name="mistral-medium-latest",
        timeout=60,
        max_retries=2,
    )
    
    print("\n" + "=" * 80)
    print("TEST 3: Large Model Test (Current Setup)")
    print("=" * 80)
    
    success3, time3 = await test_mistral(
        model_name="mistral-large-latest",
        timeout=120,
        max_retries=3,
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    print("Model Comparison:")
    print(f"  mistral-small-latest:  {'✅ PASS' if success1 else '❌ FAIL'} ({time1:.2f}s)")
    print(f"  mistral-medium-latest: {'✅ PASS' if success2 else '❌ FAIL'} ({time2:.2f}s)")
    print(f"  mistral-large-latest:  {'✅ PASS' if success3 else '❌ FAIL'} ({time3:.2f}s)")
    print()
    
    if success1:
        print("✅ Mistral API Key is VALID and working!")
        print()
        
        if not success3:
            print("⚠️  ISSUE IDENTIFIED:")
            print("   - mistral-large-latest is timing out or too slow")
            print("   - mistral-small/medium work fine")
            print()
            print("💡 RECOMMENDATION:")
            print("   Switch to mistral-medium-latest for faster responses")
            print("   (Update backend/agents/weekly_agent.py)")
        else:
            print("✅ All models work! The timeout issue might be:")
            print("   - Large prompts (too much Search Console data)")
            print("   - Network latency to Mistral servers")
            print("   - Server load during peak times")
            print()
            print("💡 RECOMMENDATIONS:")
            print("   1. Use mistral-medium-latest (faster, still good quality)")
            print("   2. Reduce prompt size (limit to top 50 queries/pages)")
            print("   3. Switch to OpenAI or Anthropic (more reliable)")
    else:
        print("❌ Mistral API Key appears to be INVALID or EXPIRED")
        print()
        print("🔧 NEXT STEPS:")
        print("   1. Check your API key at: https://console.mistral.ai/")
        print("   2. Generate a new API key if needed")
        print("   3. Update .env file with new key")
        print("   4. Or switch to OpenAI/Anthropic (simpler, more reliable)")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
