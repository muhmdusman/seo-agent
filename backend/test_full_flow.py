"""
Complete end-to-end test of the Search Console Agent scheduler.
Tests the full flow: Database → Google Search Console → AI Analysis → Email Delivery
"""

import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.config import settings
from db.dbconfig import AsyncSessionLocal
from models.user import User
from models.oauth_account import OAuthAccount
from models.oauth_credential import OAuthCredential
from services.search_console_service import SearchConsoleService
from agents.daily_agent import DailyAgent
from services.email_service import email_service


async def test_full_flow():
    """Test the complete scheduler flow."""
    
    print("\n" + "="*70)
    print("🧪 TESTING COMPLETE SCHEDULER FLOW")
    print("="*70)
    
    async with AsyncSessionLocal() as session:
        
        # Step 1: Get user with credentials
        print("\n📊 Step 1: Fetching user from database...")
        
        query = (
            select(User)
            .join(OAuthAccount, User.id == OAuthAccount.user_id)
            .join(OAuthCredential, OAuthAccount.id == OAuthCredential.oauth_account_id)
            .options(
                selectinload(User.oauth_accounts).selectinload(OAuthAccount.credentials)
            )
            .where(OAuthCredential.access_token.isnot(None))
        )
        
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ No user with OAuth credentials found!")
            print("\n💡 To fix this:")
            print("   1. Visit: http://localhost:3000")
            print("   2. Click 'Connect with Google'")
            print("   3. Authorize the app")
            print("   4. Come back and run this test again")
            return False
        
        print(f"✅ Found user: {user.email}")
        
        # Get OAuth credentials
        oauth_account = user.oauth_accounts[0] if user.oauth_accounts else None
        if not oauth_account or not oauth_account.credentials:
            print("❌ User has no OAuth credentials!")
            return False
        
        credentials = oauth_account.credentials
        print(f"   Token expires: {credentials.expires_at}")
        
        # Check if token is expired
        now = datetime.now(timezone.utc)
        if credentials.expires_at < now:
            print("⚠️  Token is expired!")
            print("   Please re-authenticate at: http://localhost:3000")
            print("   Then run this test again.")
            return False
        
        time_left = (credentials.expires_at - now).total_seconds() / 3600
        print(f"   ✅ Token valid for {time_left:.1f} more hours")
        
        # Step 2: Fetch sites from Google Search Console
        print("\n🔍 Step 2: Fetching sites from Google Search Console...")
        
        search_console = SearchConsoleService()
        
        try:
            sites_data = await search_console.list_sites(credentials.access_token)
            sites = []
            
            for entry in sites_data.get("siteEntry", []):
                permission = entry.get("permissionLevel", "")
                site_url = entry.get("siteUrl", "")
                if permission in ["siteOwner", "siteFullUser"] and site_url:
                    sites.append(site_url)
                    print(f"   ✅ {site_url} ({permission})")
            
            if not sites:
                print("❌ No verified sites found in Google Search Console!")
                print("\n💡 To add sites:")
                print("   1. Visit: https://search.google.com/search-console")
                print("   2. Add and verify a property")
                print("   3. Come back and run this test again")
                return False
            
            print(f"\n✅ Found {len(sites)} verified site(s)")
            
        except Exception as e:
            print(f"❌ Failed to fetch sites: {e}")
            print("\n💡 This might mean:")
            print("   - Token expired (re-authenticate)")
            print("   - No sites in Search Console")
            print("   - API rate limit reached")
            return False
        
        # Step 3: Generate AI report for first site
        print(f"\n🤖 Step 3: Generating AI report for {sites[0]}...")
        
        daily_agent = DailyAgent(session)
        
        try:
            report = await daily_agent.generate_report(
                user_id=str(user.id),
                site_url=sites[0]
            )
            
            print("✅ Report generated successfully!")
            print(f"\n📄 Report Preview (first 500 chars):")
            print("-" * 70)
            print(report[:500] + "..." if len(report) > 500 else report)
            print("-" * 70)
            
        except Exception as e:
            print(f"❌ Failed to generate report: {e}")
            print("\n💡 Check:")
            print("   - MISTRAL_API_KEY is set correctly")
            print("   - Site has data in Search Console")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 4: Send email
        print(f"\n📧 Step 4: Sending email to {user.email}...")
        
        try:
            success = await email_service.send_daily_report(
                user_email=user.email,
                user_name=user.username or user.email.split('@')[0],
                site_url=sites[0],
                report_content=report,
                report_date=datetime.now().strftime("%B %d, %Y")
            )
            
            if success:
                print("✅ Email sent successfully!")
                print(f"   📬 Check your inbox: {user.email}")
                return True
            else:
                print("❌ Failed to send email")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_scheduler_trigger():
    """Test the scheduler API endpoint."""
    
    print("\n" + "="*70)
    print("🧪 TESTING SCHEDULER API ENDPOINT")
    print("="*70)
    
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            print("\n🔄 Triggering scheduler via API...")
            
            response = await client.post(
                "http://localhost:8000/api/v1/scheduler/trigger",
                timeout=300.0  # 5 minutes timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Scheduler executed successfully!")
                print(f"\n📊 Statistics:")
                stats = result.get("statistics", {})
                print(f"   Total Users: {stats.get('total_users', 0)}")
                print(f"   Successful Users: {stats.get('successful_users', 0)}")
                print(f"   Total Sites: {stats.get('total_sites', 0)}")
                print(f"   Successful Reports: {stats.get('successful_reports', 0)}")
                print(f"   Failed Reports: {stats.get('failed_reports', 0)}")
                
                if stats.get('errors'):
                    print(f"\n⚠️  Errors:")
                    for error in stats['errors']:
                        print(f"   - {error}")
                
                return stats.get('successful_reports', 0) > 0
            else:
                print(f"❌ Scheduler failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to trigger scheduler: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    
    print("\n" + "="*70)
    print("🚀 SEARCH CONSOLE AGENT - COMPLETE FLOW TEST")
    print("="*70)
    print(f"\n⚙️  Configuration:")
    print(f"   Backend: http://localhost:8000")
    print(f"   Frontend: http://localhost:3000")
    print(f"   Admin Email: {settings.ADMIN_EMAIL}")
    print(f"   Scheduler Enabled: {settings.SCHEDULER_ENABLED}")
    
    # Test 1: Full flow step-by-step
    print("\n" + "="*70)
    print("TEST 1: Step-by-Step Flow")
    print("="*70)
    
    flow_success = await test_full_flow()
    
    # Test 2: Scheduler API endpoint
    if flow_success:
        print("\n" + "="*70)
        print("TEST 2: Scheduler API Endpoint")
        print("="*70)
        
        api_success = await test_scheduler_trigger()
    else:
        print("\n⏭️  Skipping API test (flow test failed)")
        api_success = False
    
    # Summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    
    print(f"\n{'✅' if flow_success else '❌'} Step-by-Step Flow Test")
    print(f"{'✅' if api_success else '❌'} Scheduler API Test")
    
    if flow_success and api_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n📝 Next Steps:")
        print("   1. ✅ Local testing complete")
        print("   2. 📝 Write your AWS Builder Center article")
        print("   3. ☁️  Deploy to AWS (see AWS_DEPLOYMENT.md)")
        print("   4. 🏆 Submit for AWS Builder Jacket")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        
        if not flow_success:
            print("\n💡 Common issues:")
            print("   - Token expired → Re-authenticate at http://localhost:3000")
            print("   - No sites → Add site to Google Search Console")
            print("   - API key → Check MISTRAL_API_KEY in .env")
        
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
