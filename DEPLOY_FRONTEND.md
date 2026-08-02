# 🎨 Frontend Deployment to Vercel

## Quick Deploy (5 minutes)

### Option 1: Vercel CLI (Fastest)

```bash
# Install Vercel CLI
npm i -g vercel

# Go to frontend directory
cd frontend

# Login to Vercel (opens browser)
vercel login

# Deploy
vercel --prod

# Follow prompts:
# Set up and deploy? Yes
# Which scope? Your account
# Link to existing project? No
# What's your project's name? search-console-agent
# In which directory is your code? ./
# Want to modify settings? No

# Done! You'll get a URL like:
# https://search-console-agent.vercel.app
```

---

### Option 2: Vercel Dashboard (Visual)

1. **Push to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Go to Vercel:**
   - Visit: https://vercel.com
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - Framework: Next.js (auto-detected)
   - Root Directory: `frontend`
   - Click "Deploy"

3. **Done!** Get your URL (e.g., `https://search-console-agent.vercel.app`)

---

## ⚙️ Configuration

### Environment Variables

After deployment, add these in Vercel Dashboard:

1. Go to: Project → Settings → Environment Variables

2. Add this variable:
   ```
   Name: NEXT_PUBLIC_API_BASE_URL
   Value: http://localhost:8000/api/v1
   ```
   
   *(We'll update this after deploying backend)*

3. Redeploy for changes to take effect

---

## 🔐 Update Google OAuth

After frontend deployment, update OAuth redirect:

1. **Get your Vercel URL:**
   ```
   https://search-console-agent-xxx.vercel.app
   ```

2. **Update Google Cloud Console:**
   - Go to: https://console.cloud.google.com/apis/credentials
   - Click your OAuth Client ID
   - Add authorized redirect URI:
     ```
     https://your-vercel-url.vercel.app/callback
     ```
   - Save

3. **Update .env:**
   ```env
   FRONTEND_URL="https://your-vercel-url.vercel.app"
   GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"
   ```

---

## 🚀 Backend Options

### Option A: Keep Backend Local (Quick Demo)

**Pros:**
- ✅ Works immediately
- ✅ No backend deployment needed
- ✅ Lambda scheduler still works

**Cons:**
- ❌ Frontend can't connect (CORS issues)
- ❌ Users can't sign up
- ❌ Only works for demo/article

**Best for:** Quick article submission

---

### Option B: Deploy Backend to Render (15 min)

**Render.com** - Free tier, easy deployment

```bash
# 1. Create account at render.com

# 2. New Web Service
#    - Connect GitHub repo
#    - Root Directory: backend
#    - Build Command: pip install -r requirements.txt
#    - Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

# 3. Add environment variables (same as .env)

# 4. Deploy!
```

**Get URL:** `https://search-console-agent.onrender.com`

---

### Option C: Deploy Backend to Railway (Alternative)

**Railway.app** - Also free, modern UI

```bash
# 1. Create account at railway.app

# 2. New Project → Deploy from GitHub
#    - Select repo
#    - Select backend directory
#    - Add environment variables
#    - Deploy

# 3. Get public URL
```

---

## 🔗 Connect Frontend to Backend

### Update Vercel Environment Variable:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-url.com/api/v1
```

### Update Backend CORS:

In `backend/main.py`, the CORS is already set to use `FRONTEND_URL` from `.env`

Update `.env`:
```env
FRONTEND_URL="https://your-vercel-url.vercel.app"
```

Redeploy backend for CORS to work.

---

## ✅ Deployment Checklist

### Frontend (Vercel)
- [ ] Deploy to Vercel
- [ ] Get public URL
- [ ] Update Google OAuth redirect URI
- [ ] Set NEXT_PUBLIC_API_BASE_URL

### Backend (Optional)
- [ ] Deploy to Render/Railway
- [ ] Get public URL
- [ ] Update FRONTEND_URL in .env
- [ ] Redeploy with new CORS settings

### Lambda (Already Done!)
- [x] Lambda deployed
- [x] EventBridge configured
- [x] Daily reports working

---

## 🎯 Quick Path for Article Submission

**Minimum for challenge (works now):**
1. ✅ Lambda + EventBridge (done!)
2. ✅ Deploy frontend to Vercel (5 min)
3. ✅ Take screenshots
4. ✅ Mention backend API in local demo
5. ✅ Submit article!

**Complete for public demo (15 min more):**
1. ✅ Deploy backend to Render
2. ✅ Connect frontend to backend
3. ✅ Update OAuth redirect
4. ✅ Test full signup flow
5. ✅ Live demo ready!

---

## 📸 Screenshots to Take

After deployment:
1. ✅ Lambda function in AWS Console
2. ✅ EventBridge rule enabled
3. ✅ CloudWatch logs
4. ✅ Frontend live on Vercel
5. ✅ Backend live on Render (optional)
6. ✅ Email received

---

## 💡 My Recommendation

**For fastest submission:**

1. **Deploy frontend now (5 min):**
   ```bash
   cd frontend
   vercel --prod
   ```

2. **Take screenshots**

3. **Complete article** with:
   - AWS Lambda (deployed ✅)
   - AWS EventBridge (deployed ✅)
   - Frontend on Vercel
   - Backend kept local (or deploy if time permits)

4. **Submit!**

**You can deploy backend later if needed!**

---

Ready to deploy frontend? Run:
```bash
cd frontend
vercel --prod
```

Or push to GitHub and deploy via Vercel dashboard!
