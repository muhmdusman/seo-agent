# 🚀 Deploy Frontend to AWS Amplify

## Why Amplify for This Challenge?

✅ **All-AWS Solution:**
- AWS Lambda (scheduler) ✓
- AWS EventBridge (cron) ✓  
- AWS CloudWatch (logs) ✓
- **AWS Amplify (frontend)** ← Add this!

✅ **Article-friendly:** "Fully deployed on AWS infrastructure"

---

## 📋 Prerequisites

1. ✅ GitHub account
2. ✅ Your code in a GitHub repository
3. ✅ AWS Console access

---

## 🎯 Quick Deployment (10 minutes)

### Step 1: Push Code to GitHub

If not already on GitHub:

```bash
cd /home/muhmdusman/Desktop/seo-bot/Search-console-Agent

# Initialize git if needed
git init
git add .
git commit -m "Ready for AWS deployment"

# Create GitHub repo (via browser or CLI)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/Search-console-Agent.git
git branch -M main
git push -u origin main
```

---

### Step 2: Deploy to AWS Amplify

#### Via AWS Console (Easiest):

1. **Open AWS Amplify Console:**
   ```
   https://console.aws.amazon.com/amplify/home?region=us-east-1
   ```

2. **Click "New app" → "Host web app"**

3. **Connect to GitHub:**
   - Click "GitHub"
   - Click "Authorize AWS Amplify"
   - Select your repository: `Search-console-Agent`
   - Branch: `main`
   - Click "Next"

4. **Configure build settings:**
   
   Amplify will auto-detect Next.js. Update the build settings:

   **App name:** `search-console-agent`
   
   **Build and test settings:**
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - cd frontend
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: frontend/.next
       files:
         - '**/*'
     cache:
       paths:
         - frontend/node_modules/**/*
   ```

   **Important:** Set **Root directory** to: `frontend`

5. **Advanced settings:**
   
   Add environment variable:
   ```
   Key: NEXT_PUBLIC_API_BASE_URL
   Value: http://localhost:8000/api/v1
   ```
   
   *(We'll update this later if deploying backend)*

6. **Click "Next" → "Save and deploy"**

7. **Wait for deployment** (~3-5 minutes)

8. **Get your URL:**
   ```
   https://main.d1234abcd.amplifyapp.com
   ```

---

### Step 3: Update OAuth Redirect

1. **Copy your Amplify URL** (from step 8)

2. **Update Google Cloud Console:**
   - Go to: https://console.cloud.google.com/apis/credentials
   - Click your OAuth 2.0 Client ID
   - Under "Authorized redirect URIs", add:
     ```
     https://your-amplify-url.amplifyapp.com/callback
     ```
   - Click "Save"

3. **Update your `.env` file:**
   ```env
   FRONTEND_URL="https://your-amplify-url.amplifyapp.com"
   ```

---

## ⚙️ Alternative: Deploy via AWS CLI

If you prefer CLI:

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Configure
amplify configure

# Initialize
cd frontend
amplify init
# Follow prompts

# Add hosting
amplify add hosting
# Select: Hosting with Amplify Console

# Publish
amplify publish
```

---

## 🔧 Build Configuration Issues?

If Amplify fails to build, update `amplify.yml`:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci --legacy-peer-deps
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: frontend/.next
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
```

Add this file to your repo:
```bash
# Create amplify.yml in project root
cat > amplify.yml << 'EOF'
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: frontend/.next
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
EOF

git add amplify.yml
git commit -m "Add Amplify build config"
git push
```

---

## 🎨 Custom Domain (Optional)

1. Go to Amplify Console → Domain Management
2. Add custom domain
3. Follow DNS configuration steps
4. Update OAuth redirect with custom domain

---

## 📊 What You Get with Amplify

✅ **Automatic deployments** - Push to GitHub, auto-deploy
✅ **HTTPS by default** - SSL certificate included
✅ **CDN** - CloudFront distribution for fast loading
✅ **Branch deployments** - Deploy dev/staging branches
✅ **Build logs** - Debug failed deployments
✅ **Free tier** - 1000 build minutes + 15GB served/month

---

## 🎯 Current Architecture (After Amplify Deploy)

```
┌─────────────────────────────────────────┐
│         User's Browser                  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      AWS Amplify (Frontend)             │
│      Next.js Dashboard                  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      Backend API (Local)                │
│      FastAPI on localhost:8000          │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      PostgreSQL (Local)                 │
└─────────────────────────────────────────┘

           ⏰ Daily 8 AM UTC
             │
             ▼
┌─────────────────────────────────────────┐
│      AWS EventBridge                    │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      AWS Lambda                         │
│      Daily Report Generator             │
└────────────┬────────────────────────────┘
             │
             ├──► PostgreSQL (Local)
             ├──► Google Search Console API
             ├──► Mistral AI
             └──► Gmail SMTP
```

---

## 📝 For Your Article

After Amplify deployment, you can say:

> "The application is deployed entirely on AWS:
> - **AWS Amplify** hosts the Next.js frontend with automatic CI/CD from GitHub
> - **AWS Lambda** executes the daily report generation
> - **AWS EventBridge** triggers Lambda at 8 AM UTC daily
> - **AWS CloudWatch** provides comprehensive logging and monitoring
> 
> Users access the public Amplify URL, authenticate with Google OAuth, and receive automated daily SEO reports via email."

**AWS Services Used:**
1. ✅ AWS Amplify (frontend hosting + CI/CD)
2. ✅ AWS Lambda (report generation)
3. ✅ AWS EventBridge (scheduling)
4. ✅ CloudWatch (monitoring)

---

## 🚨 Common Issues

### Build fails with "command not found: npm"
**Solution:** Amplify uses Node 18 by default. Add to build settings:
```yaml
phases:
  preBuild:
    commands:
      - nvm use 20
      - cd frontend
      - npm ci
```

### CORS errors
**Solution:** Backend CORS needs to allow Amplify URL. Update backend/.env:
```env
FRONTEND_URL="https://your-amplify-url.amplifyapp.com"
```

### OAuth redirect fails
**Solution:** Make sure you added the Amplify URL to Google Cloud Console

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Amplify app created
- [ ] Build successful
- [ ] Amplify URL obtained
- [ ] Google OAuth updated
- [ ] Environment variables set
- [ ] Frontend loads correctly

---

## 🎉 After Deployment

1. ✅ Visit your Amplify URL
2. ✅ Test the landing page
3. ✅ Click "Connect with Google" (may need backend deployed)
4. ✅ Take screenshots
5. ✅ Update article with live URL
6. ✅ Submit challenge!

---

## 💡 Quick Commands

```bash
# Check Amplify app status
aws amplify list-apps --region us-east-1

# Get app details
aws amplify get-app --app-id YOUR_APP_ID --region us-east-1

# Trigger new deployment
git commit --allow-empty -m "Trigger deployment"
git push
```

---

## 🎯 Recommended: Deploy in This Order

1. ✅ **Lambda + EventBridge** (Done!)
2. ✅ **Amplify (Frontend)** (Do this now!)
3. ⏳ **Backend** (Optional - Render/Railway)

**You can submit with just #1 and #2!** Backend can stay local for demo purposes.

---

Ready to deploy? Go to:
👉 https://console.aws.amazon.com/amplify/home?region=us-east-1

Click "New app" → "Host web app" → Follow steps above! 🚀
