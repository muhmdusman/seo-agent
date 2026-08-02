"""
Test script for the scheduler and email service.
Run this to verify the daily report system works before deploying to AWS.
"""

import asyncio
import sys
from datetime import date

from sqlalchemy import select

from core.config import settings
from db.dbconfig import AsyncSessionLocal
from models.user import User
from models.oauth_account import OAuthAccount
from services.email_service import email_service
from services.scheduler_service import run_daily_reports_job


async def test_email_service():
    """Test that Web3Forms integration works."""
    
    print("\n" + "="*60)
    print("🧪 Testing Email Service")
    print("="*60)
    
    test_report = """
## Test Daily SEO Report

### 📈 Performance Snapshot
- **Total Clicks:** 1,234 (+15% vs last week)
- **Impressions:** 45,678 (+8%)
- **Average CTR:** 2.7% (+0.3%)
- **Average Position:** 12.5 (-1.2 positions better)

### 🎯 Today's Top Opportunity

**Query:** `best seo tools 2026`
- **Current Position:** 5.2
- **Impressions:** 2,450
- **Clicks:** 89
- **CTR:** 3.6%

**Why it matters:** This query is on page 1 with high search volume but below-average CTR for its position.

**Quick action:** Update the meta description to be more compelling and action-oriented. Current title is strong, focus on the snippet.

### ⚠️ Attention Needed

**Page:** `/blog/seo-guide-2025`
- Performance dropped 45% in clicks this week
- Position fell from 3.2 to 8.7 for main query
- Check for new competing content or technical issues

---

*This is a test report to verify email delivery.*
"""
    
    print(f"\n📧 Sending test email to: {settings.ADMIN_EMAIL}")
    print(f"📤 Using Web3Forms API key: {settings.WEB3FORMS_ACCESS_KEY[:20]}...")
    
    try:
        success = await email_service.send_daily_report(
            user_email=settings.ADMIN_EMAIL,
            user_name="Test User",
            site_url="https://example.com",
            report_content=test_report,
            report_date=date.today().strftime("%B %d, %Y"),
        )
        
        if success:
            print("✅ Test email sent successfully!")
            print(f"   Check your inbox at: {settings.ADMIN_EMAIL}")
            return True
        else:
            print("❌ Failed to send test email")
            return False
            
    except Exception as e:
        print(f"❌ Exception during email test: {e}")
        return False


async def test_database_connection():
    """Test database connection and check for users."""
    
    print("\n" + "="*60)
    print("🧪 Testing Database Connection")
    print("="*60)
    
    try:
        async with AsyncSessionLocal() as session:
            # Count users
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            print(f"✅ Database connected successfully")
            print(f"   Found {len(users)} user(s)")
            
            if users:
                print("\n📊 User Details:")
                for user in users:
                    print(f"   - {user.email} (ID: {user.id})")
                    
                    # Check for OAuth accounts
                    oauth_query = select(OAuthAccount).where(
                        OAuthAccount.user_id == user.id
                    )
                    oauth_result = await session.execute(oauth_query)
                    oauth_accounts = oauth_result.scalars().all()
                    
                    if oauth_accounts:
                        print(f"     ✓ OAuth account linked")
                    else:
                        print(f"     ✗ No OAuth account found")
            else:
                print("\n⚠️  No users found in database")
                print("   You'll need to sign in through the frontend first")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_scheduler_service():
    """Test the full scheduler service."""
    
    print("\n" + "="*60)
    print("🧪 Testing Scheduler Service")
    print("="*60)
    
    try:
        async with AsyncSessionLocal() as session:
            print("\n🔄 Running daily reports job...")
            
            stats = await run_daily_reports_job(session)
            
            print("\n📊 Scheduler Run Results:")
            print(f"   Total Users: {stats['total_users']}")
            print(f"   Successful Users: {stats['successful_users']}")
            print(f"   Failed Users: {stats['failed_users']}")
            print(f"   Total Sites: {stats['total_sites']}")
            print(f"   Successful Reports: {stats['successful_reports']}")
            print(f"   Failed Reports: {stats['failed_reports']}")
            
            if stats['errors']:
                print(f"\n⚠️  Errors:")
                for error in stats['errors']:
                    print(f"   - {error}")
            
            if stats['successful_reports'] > 0:
                print("\n✅ Scheduler completed successfully!")
                return True
            elif stats['total_users'] == 0:
                print("\n⚠️  No users to process (expected if no one has signed in yet)")
                return True
            else:
                print("\n❌ Scheduler completed with errors")
                return False
                
    except Exception as e:
        print(f"❌ Scheduler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_config():
    """Test configuration is properly loaded."""
    
    print("\n" + "="*60)
    print("🧪 Testing Configuration")
    print("="*60)
    
    try:
        print(f"\n✅ Configuration loaded:")
        print(f"   App Name: {settings.APP_NAME}")
        print(f"   Database URL: {settings.DATABASE_URL[:40]}...")
        print(f"   Web3Forms Key: {settings.WEB3FORMS_ACCESS_KEY[:20]}...")
        print(f"   Scheduler Enabled: {settings.SCHEDULER_ENABLED}")
        print(f"   Daily Report Time: {settings.DAILY_REPORT_TIME}")
        print(f"   Admin Email: {settings.ADMIN_EMAIL}")
        print(f"   Frontend URL: {settings.FRONTEND_URL}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


async def main():
    """Run all tests."""
    
    print("\n" + "="*60)
    print("🚀 Search Console Agent - Scheduler Test Suite")
    print("="*60)
    
    results = {
        "config": await test_config(),
        "database": await test_database_connection(),
        "email": await test_email_service(),
    }
    
    # Only test scheduler if database has users
    print("\n" + "="*60)
    print("Would you like to test the full scheduler?")
    print("(This will generate and send real reports if users exist)")
    print("="*60)
    response = input("Run scheduler test? (y/n): ").lower().strip()
    
    if response == 'y':
        results["scheduler"] = await test_scheduler_service()
    
    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name.upper()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Ready to deploy to AWS.")
        print("\n📝 Next steps:")
        print("   1. Review AWS_DEPLOYMENT.md for deployment instructions")
        print("   2. Set up AWS RDS PostgreSQL")
        print("   3. Deploy Lambda function")
        print("   4. Create EventBridge schedule")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix issues before deploying.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
