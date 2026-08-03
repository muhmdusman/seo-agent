# Mixed Content Security Issue - HTTPS Frontend with HTTP Backend

## 🚨 Issue Description

When deploying the Search Console Agent to AWS with:
- **Frontend:** AWS Amplify (HTTPS) - `https://main.d3vozze6u0rukp.amplifyapp.com`
- **Backend:** AWS Elastic Beanstalk (HTTP) - `http://search-console-prod.eba-auaxqesy.us-east-1.elasticbeanstalk.com`

Browsers block HTTP API requests from HTTPS pages due to **Mixed Content** security policy.

### Error Message
```
Mixed Content: The page at 'https://main.d3vozze6u0rukp.amplifyapp.com/dashboard' 
was loaded over HTTPS, but requested an insecure resource 
'http://search-console-prod.eba-auaxqesy.us-east-1.elasticbeanstalk.com/api/v1/auth/me'. 
This request has been blocked; the content must be served over HTTPS.
```

## 🔍 Root Cause

Modern browsers enforce **Mixed Content** security:
- HTTPS pages can only make requests to HTTPS endpoints
- HTTP requests from HTTPS pages are automatically blocked
- This prevents downgrade attacks and man-in-the-middle vulnerabilities

## ✅ Solution: Next.js Server-Side API Proxy

Use Next.js rewrites to proxy API calls through the HTTPS frontend, hiding the HTTP backend from the browser.

### Implementation

**1. Update `frontend/next.config.ts`:**
```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://search-console-prod.eba-auaxqesy.us-east-1.elasticbeanstalk.com/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;
```

**2. Update `frontend/src/lib/config.ts`:**
```typescript
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";
```

**3. Set Amplify Environment Variable:**
```bash
aws amplify update-branch \
  --app-id d3vozze6u0rukp \
  --branch-name main \
  --region us-east-1 \
  --environment-variables NEXT_PUBLIC_API_BASE_URL=/api/v1
```

**4. Deploy:**
```bash
cd frontend
git add next.config.ts src/lib/config.ts
git commit -m "Add Next.js rewrites to fix Mixed Content issue"
git push origin main
```

## 🔧 How It Works

```
Browser Request:
https://main.d3vozze6u0rukp.amplifyapp.com/api/v1/auth/me (HTTPS ✅)
                    ↓
Next.js Server-Side Proxy:
Forwards to → http://search-console-prod.eba-auaxqesy.us-east-1.elasticbeanstalk.com/api/v1/auth/me
                    ↓
Backend Response:
Returns through HTTPS frontend (Browser only sees HTTPS ✅)
```

**Result:** No Mixed Content error, all requests appear to be HTTPS to the browser.

## 🎯 Alternative Solutions

### Option A: Enable HTTPS on Elastic Beanstalk (Recommended for Production)

**Steps:**
1. Request/import SSL certificate in AWS Certificate Manager (ACM)
2. Configure Elastic Beanstalk load balancer for HTTPS listener (port 443)
3. Update CORS in `backend/api/main.py` to allow `https://` origins
4. Update Amplify environment variable to use `https://` URL

**Pros:**
- Proper end-to-end encryption
- No proxy overhead
- Industry best practice

**Cons:**
- Requires SSL certificate setup
- Needs load balancer configuration
- Additional AWS resources

### Option B: Use Same Domain (Subdomain Setup)

**Steps:**
1. Register a custom domain (e.g., `example.com`)
2. Point `app.example.com` → Amplify frontend
3. Point `api.example.com` → Elastic Beanstalk backend
4. Enable HTTPS on both using AWS Certificate Manager
5. Update API_BASE_URL to `https://api.example.com/api/v1`

**Pros:**
- Clean separation
- No proxy needed
- Better for production

**Cons:**
- Requires custom domain purchase
- More DNS configuration
- Higher cost

### Option C: Deploy Both to Amplify (Full Serverless)

**Steps:**
1. Convert backend to serverless functions (AWS Lambda)
2. Deploy both frontend and backend API routes to Amplify
3. Everything under one HTTPS domain

**Pros:**
- Single deployment
- Automatic HTTPS
- Simplified architecture

**Cons:**
- Requires backend rewrite
- Lambda limitations (timeout, cold starts)
- Different deployment model

## 📊 Current Status

- ✅ Next.js rewrites implemented
- ✅ Amplify environment variable updated
- ✅ Frontend uses relative API paths
- 🟡 Backend still on HTTP (works via proxy)
- ❌ End-to-end HTTPS not yet implemented

## 🚀 Recommended Path Forward

For production deployment, implement **Option A (HTTPS on Elastic Beanstalk)**:

1. Generate SSL certificate in ACM
2. Configure EB load balancer
3. Remove Next.js rewrites
4. Update all URLs to HTTPS

The current proxy solution works but adds latency and doesn't provide true end-to-end encryption.

## 🔗 References

- [MDN: Mixed Content](https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content)
- [Next.js Rewrites Documentation](https://nextjs.org/docs/app/api-reference/next-config-js/rewrites)
- [AWS Certificate Manager](https://aws.amazon.com/certificate-manager/)
- [Elastic Beanstalk HTTPS Configuration](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/configuring-https.html)

---

**Last Updated:** August 3, 2026  
**Status:** Workaround implemented, production solution pending
