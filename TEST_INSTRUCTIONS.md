# 🧪 Testing Instructions - Complete Flow

## Current Status

✅ **Backend Running:** http://localhost:8000
✅ **Frontend Running:** http://localhost:3000
✅ **Email Service:** Working perfectly
✅ **Database:** Connected with 1 user
⚠️  **OAuth Token:** Expired (need to re-authenticate)

---

## 🔐 Step 1: Re-Authenticate with Google (2 minutes)

Your OAuth token expired on July 25, 2026. Let's get a fresh one:

### Instructions:

1. **Open your browser:**
   ```
   http://localhost:3000
   ```

2. **You should see:**
   - Landing page with "Connect with Google" button
   - OR if already logged in, the dashboard

3. **Click "Connect with Google"**
   - This will redirect you to Google's consent screen
   - Approve access to Google Search Console
   - You'll be redirected back to the dashboard

4. **Verify you're logged in:**
   - You should see your verified Google Search Console properties
   - If you don't have any properties, you'll see a message

### Expected Flow:
```
Landing Page → Google OAuth → Consent Screen → Redirect → Dashboard
```

---

## 🧪 Step 2: Run Complete Test (2 minutes)

After re-authenticating, run the comprehensive test:

```bash
cd backend
uv run python test_full_flow.py
```

### What This Test Does:

1. ✅ **Database Check** - Verifies user and OAuth credentials
2. ✅ **Token Validation** - Checks if token is still valid
3. ✅ **Fetch Sites** - Gets your verified sites from Google Search Console
4. ✅ **Generate Report** - Uses AI (Mistral) to analyze your site
5. ✅ **Send Email** - Delivers the report to your inbox

### Expected Output:

```
======================================================================
🚀 SEARCH CONSOLE AGENT - COMPLETE FLOW TEST
======================================================================

📊 Step 1: Fetching user from database...
✅ Found user: mangoapple027@gmail.com
   ✅ Token valid for 0.9 more hours

🔍 Step 2: Fetching sites from Google Search Console...
   ✅ https://example.com (siteOwner)
✅ Found 1 verified site(s)

🤖 Step 3: Generating AI report...
✅ Report generated successfully!

📧 Step 4: Sending email...
✅ Email sent successfully!
   📬 Check your inbox: mangoapple027@gmail.com

🎉 ALL TESTS PASSED!
```

---

## 🐛 Troubleshooting

### Issue: "No verified sites found"

**Solution:** Add a site to Google Search Console

1. Go to: https://search.google.com/search-console
2. Click **Add Property**
3. Choose **URL prefix** or **Domain**
4. Follow verification steps
5. Come back and run test again

### Issue: "Token is expired"

**Solution:** Re-authenticate (Step 1 above)

### Issue: "Failed to generate report"

**Check:**
- Is `MISTRAL_API_KEY` set in `.env`?
- Does your site have data in Search Console?
- Check backend logs for errors

### Issue: "Failed to send email"

**Check:**
- Is `SMTP_PASSWORD` (Gmail App Password) set in `.env`?
- Check backend logs for specific error

---

## 📊 Alternative: Test Scheduler API Directly

If the step-by-step test passes, you can also trigger the scheduler API:

```bash
# Trigger manual scheduler run
curl -X POST http://localhost:8000/api/v1/scheduler/trigger

# Check scheduler status
curl http://localhost:8000/api/v1/scheduler/status

# Test email (sends to admin email)
curl -X POST http://localhost:8000/api/v1/scheduler/test-email
```

---

## 🎯 What Happens in a Successful Test?

1. **Database Query** ✅
   - Finds your user
   - Loads OAuth credentials
   - Validates token expiry

2. **Google Search Console API** ✅
   - Fetches your verified sites
   - Gets last 7 days of performance data
   - Retrieves queries, pages, clicks, impressions

3. **AI Analysis** ✅
   - Sends data to Mistral AI
   - Generates actionable insights
   - Formats as email-friendly report

4. **Email Delivery** ✅
   - Formats report as beautiful HTML
   - Sends via Gmail SMTP
   - You receive it at: amusman9705@gmail.com

---

## ✅ Success Checklist

After testing, you should have:

- [ ] Re-authenticated successfully
- [ ] Test shows valid token
- [ ] Sites fetched from Search Console
- [ ] AI report generated
- [ ] Email received in inbox
- [ ] Email looks good (HTML formatted)
- [ ] Ready to deploy to AWS

---

## 📸 What to Screenshot for Article

For your AWS Builder Center article, screenshot:

1. **Dashboard** showing your verified sites
2. **Email inbox** with the daily report
3. **Email content** showing the AI-generated insights
4. **Test output** showing all steps passing
5. **Scheduler status** API response

---

## 🚀 After All Tests Pass

Congratulations! Your app is working end-to-end. Next steps:

1. **Write Article** - Use `ARTICLE_OUTLINE.md` as template
2. **Deploy to AWS** - Follow `AWS_DEPLOYMENT.md`
3. **Submit Challenge** - Get that AWS Builder Jacket! 🧥

---

## 🆘 Need Help?

**Backend not starting?**
```bash
cd backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend not starting?**
```bash
cd frontend
npm run dev
```

**Database not running?**
```bash
cd backend
docker compose -f db/docker-compose.yaml up -d
```

**Clear and restart everything:**
```bash
# Stop all
pkill -f uvicorn
pkill -f "next dev"

# Start backend
cd backend && uv run uvicorn main:app --reload &

# Start frontend
cd frontend && npm run dev &
```

---

**You're almost there! Just re-authenticate and run the test! 🎉**
