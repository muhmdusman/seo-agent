# 🚀 Deploy Frontend to AWS Amplify - Step by Step

## ✅ Prerequisites Done
- [x] Code pushed to GitHub: https://github.com/muhmdusman/seo-agent
- [x] `amplify.yml` created and pushed
- [x] Lambda + EventBridge deployed

---

## 📝 Deployment Steps (5 minutes)

### Step 1: Open AWS Amplify Console

Click this link (it will auto-select region us-east-1):
```
https://console.aws.amazon.com/amplify/home?region=us-east-1
```

---

### Step 2: Create New App

1. Click **"Create new app"** (orange button)
2. Select **"Host web app"**
3. Choose **"GitHub"** as the source

---

### Step 3: Authorize GitHub

1. Click **"Authorize AWS Amplify"**
2. GitHub will open in a new tab
3. Click **"Authorize aws-amplify"**
4. Enter your GitHub password if prompted
5. Window closes automatically

---

### Step 4: Select Repository

1. **Repository:** Select `muhmdusman/seo-agent`
2. **Branch:** Select `main`
3. Click **"Next"**

---

### Step 5: Configure Build Settings

**App name:** `search-console-agent`

**Build settings:** Amplify will auto-detect the `amplify.yml` file ✅

**Root directory:** Leave empty (or set to `frontend` if asked)

**Environment variables:** Click "Advanced settings" and add:

```
Key: NEXT_PUBLIC_API_BASE_URL
Value: http://localhost:8000/api/v1
```

*(We'll update this later if you deploy backend)*

Click **"Next"**

---

### Step 6: Review and Deploy

1. Review all settings
2. Click **"Save and deploy"**
3. ☕ Wait 3-5 minutes for build

---

### Step 7: Get Your URL

After deployment completes:

1. You'll see a URL like: `https://main.d1a2b3c4d5e6f7.amplifyapp.com`
2. **Copy this URL** - you'll need it!
3. Click the URL to test your frontend

---

### Step 8: Update Google OAuth

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click your OAuth 2.0 Client ID
3. Under **"Authorized redirect URIs"**, add:
   ```
   https://your-amplify-url.amplifyapp.com/callback
   ```
   *(Replace with your actual Amplify URL)*
4. Click **"Save"**

---

### Step 9: Update .env and Redeploy Lambda

Update your local `.env`:

```env
FRONTEND_URL="https://your-amplify-url.amplifyapp.com"
```

Redeploy Lambda with new frontend URL:

```bash
./deploy_via_s3.sh
```

---

## ✅ Verification Checklist

After deployment:

- [ ] Amplify build succeeded (green checkmark)
- [ ] Frontend URL loads
- [ ] Landing page displays correctly
- [ ] "Connect with Google" button visible
- [ ] OAuth redirect added to Google Console
- [ ] Lambda updated with new FRONTEND_URL

---

## 🎯 Current Architecture

```
┌──────────────────────────────────┐
│  Users / Browsers                │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  AWS Amplify (Frontend)          │  ✅ DEPLOYED
│  https://xxx.amplifyapp.com      │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  Backend API                     │  (Local for now)
│  localhost:8000                  │
└──────────────────────────────────┘

       ⏰ Daily 8 AM UTC
             │
             ▼
┌──────────────────────────────────┐
│  AWS EventBridge                 │  ✅ DEPLOYED
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  AWS Lambda                      │  ✅ DEPLOYED
│  Daily Report Generator          │
└──────────────────────────────────┘
```

---

## 📊 AWS Services Now Using

1. ✅ **AWS Lambda** - Daily report generation
2. ✅ **AWS EventBridge** - Cron scheduling
3. ✅ **AWS CloudWatch** - Logging & monitoring
4. ✅ **AWS Amplify** - Frontend hosting + CI/CD

**That's 4 AWS services!** 🎉

---

## 🎨 Custom Domain (Optional)

If you want a custom domain like `seo-agent.yourdomain.com`:

1. Go to Amplify Console → **Domain management**
2. Click **"Add domain"**
3. Enter your domain
4. Follow DNS configuration steps
5. Update Google OAuth with custom domain

---

## 🐛 Troubleshooting

### Build Fails

**Check build logs:**
1. Amplify Console → Your app
2. Click on the failed build
3. Expand "Frontend" section
4. Read error messages

**Common fixes:**
- Node version issues → Add to `amplify.yml`: `preBuild: - nvm use 20`
- Dependency issues → Use `npm ci --legacy-peer-deps`

### Frontend Loads But Can't Connect

**Expected!** Backend is still running locally.

**Options:**
1. Keep it local (mention in article as demo limitation)
2. Deploy backend to Render/Railway (see DEPLOY_FRONTEND.md)

### OAuth Redirect Fails

**Make sure:**
- Amplify URL added to Google Console
- URL is exact (including `https://`)
- Callback path is `/callback`

---

## 📸 Screenshots to Take

For your article:

1. ✅ Amplify Console - Successful deployment
2. ✅ Amplify URL - Frontend live
3. ✅ Lambda Console - Function active
4. ✅ EventBridge Console - Rule enabled
5. ✅ CloudWatch Logs - Successful execution
6. ✅ Email - Daily report received

---

## 🎉 After Amplify Deployment

You'll have:
- ✅ **Public frontend** - Anyone can visit
- ✅ **Automated backend** - Lambda running daily
- ✅ **Full AWS stack** - 4 AWS services
- ✅ **Ready for article** - Screenshots + live demo

---

## 📝 For Your Article

> "The application is deployed entirely on AWS infrastructure:
>
> - **AWS Amplify** hosts the Next.js frontend with automatic CI/CD from GitHub. Every push to the main branch triggers an automatic build and deployment.
> 
> - **AWS Lambda** executes the daily report generation, processing all users and their Google Search Console sites, generating AI-powered insights, and delivering reports via email.
> 
> - **AWS EventBridge** triggers the Lambda function daily at 8 AM UTC with a cron expression.
> 
> - **AWS CloudWatch** provides comprehensive logging, monitoring, and metrics for the entire automated workflow.
> 
> Users access the public Amplify URL, authenticate with Google OAuth, and automatically receive daily SEO reports to their inbox every morning."

---

## 🚀 Ready?

Go to: https://console.aws.amazon.com/amplify/home?region=us-east-1

Click "Create new app" and follow the steps above!

**Estimated time: 5 minutes** ⏱️

---

**Let's deploy and win that AWS Builder Jacket! 🧥**
