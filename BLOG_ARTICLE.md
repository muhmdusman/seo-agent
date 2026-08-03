# How I Automated My Weekly SEO Reports with AI and AWS (And Saved 3 Hours Every Week)

## The Annoying Task That Started It All

Every Monday morning, I spent 2-3 hours manually checking Google Search Console, pulling performance data, identifying trends, and writing SEO reports for my websites. It was repetitive, time-consuming, and honestly pretty boring. I'd open Search Console, export data to spreadsheets, compare week-over-week metrics, and try to spot opportunities or issues. By the time I finished, half my morning was gone.

I kept thinking: "There has to be a better way." That's when I decided to build **Search Console Agent** - an AI-powered system that automatically generates SEO insights and emails them to me every morning at 8 AM.

This article walks through how I built it over a weekend using AWS Free Tier services, what I learned, and how you can deploy your own version.

## What Does It Actually Do?

Search Console Agent is a web application that:

1. **Connects to Google Search Console** via OAuth to access your website data
2. **Fetches 30 days of performance metrics** (clicks, impressions, CTR, position)
3. **Analyzes the data using AI** (Mistral AI) to generate actionable insights
4. **Emails daily reports** automatically at 8 AM UTC
5. **Supports multiple websites** - manage all your properties in one place

The best part? Once it's set up, it runs completely on autopilot. I wake up to fresh SEO insights in my inbox every day without lifting a finger.

## The Tech Stack

I built this using a modern, cloud-native stack that runs entirely on AWS Free Tier:

**Frontend:**
- **Next.js 16** with React 19 and TypeScript
- **Tailwind CSS** and Radix UI for the interface
- **Deployed on AWS Amplify** (automatic HTTPS, CI/CD from GitHub)

**Backend:**
- **FastAPI** (Python 3.11) for the REST API
- **SQLAlchemy 2.0** with PostgreSQL for data persistence
- **LangChain** for AI agent orchestration
- **Deployed on AWS Elastic Beanstalk** (managed EC2 instances)

**Database:**
- **AWS RDS PostgreSQL 15.8** (db.t3.micro in Free Tier)

**Automation:**
- **AWS Lambda** for running the daily report generation
- **AWS EventBridge** for scheduling (cron: `0 8 * * ? *`)

**AI & APIs:**
- **Mistral AI** for generating insights and recommendations
- **Google Search Console API** for fetching website performance data

## The Architecture

Here's how all the pieces fit together:

```
User Browser
    ↓
AWS Amplify (HTTPS Frontend)
    ↓
AWS Elastic Beanstalk (Backend API)
    ↓
AWS RDS PostgreSQL (Database)

AWS EventBridge (Trigger: Daily 8 AM UTC)
    ↓
AWS Lambda (Report Generator)
    ↓
Google Search Console API → Mistral AI → SMTP Email
```

The frontend handles user authentication and site selection. The backend API manages OAuth tokens, database operations, and serves the AI analysis. Lambda functions run independently on schedule to generate and send reports.

## How I Built It: The Weekend Timeline

### Saturday Morning: Setting Up Google OAuth

The first challenge was authenticating with Google Search Console. I needed OAuth 2.0 with the `webmasters.readonly` scope.

**Steps:**
1. Created a Google Cloud project
2. Enabled the Search Console API
3. Set up OAuth credentials with authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
4. Added my email as a test user (critical - the app stays in "Testing" mode until verified)

**Gotcha:** The `webmasters.readonly` scope is sensitive, so Google shows an "unverified app" warning. I had to click "Advanced" → "Go to App (unsafe)" during testing. For production, you'd need to submit for OAuth verification.

### Saturday Afternoon: Building the Backend

I created a FastAPI application with four main components:

**1. Authentication System**
- OAuth flow: redirect to Google → receive code → exchange for tokens
- JWT-based sessions stored in PostgreSQL
- Refresh token handling for long-lived access

**2. Database Models**
```python
users 1 ──* oauth_accounts 1 ── 1 oauth_credentials
  └──* sessions
```

**3. Google Search Console Integration**
- Service class wrapping the Search Console API
- Methods to list sites and fetch performance data
- Automatic token refresh when expired

**4. AI Agent (LangChain + Mistral)**
- Fetches last 30 days of data
- Scrapes top pages for context
- Generates insights using Mistral's `open-mistral-7b` model
- Returns recommendations via Server-Sent Events (SSE)

### Saturday Evening: Frontend with Next.js

The frontend is a clean, modern interface with:
- Landing page with "Connect with Google" button
- OAuth callback handler that stores tokens
- Dashboard with site selector
- Real-time analysis display using SSE

I used Shadcn/ui components (built on Radix) for the UI primitives and Tailwind for styling. The design is mobile-responsive and follows modern web standards.

### Sunday Morning: AWS Deployment

This is where things got interesting. I deployed each component to AWS:

**1. Database (AWS RDS)**
```bash
# Created PostgreSQL instance
Instance class: db.t3.micro (Free Tier)
Storage: 20 GB SSD
Multi-AZ: Disabled (to stay in Free Tier)
Public access: Yes (for development)
```

**2. Backend (AWS Elastic Beanstalk)**
```bash
# Packaged the FastAPI app
cd backend
zip -r app.zip . -x ".venv/*" -x "*.pyc"

# Deployed to Elastic Beanstalk
Platform: Python 3.11 on 64bit Amazon Linux 2023
Instance: t3.micro (Free Tier)
```

I had to create a `Procfile` to tell Elastic Beanstalk how to run the app:
```
web: uvicorn main:app --host 0.0.0.0 --port 8000
```

**3. Frontend (AWS Amplify)**
Connected my GitHub repository, and Amplify automatically:
- Detected Next.js
- Built and deployed on every push to `main`
- Provided HTTPS out of the box
- Set up CI/CD pipeline

**4. Lambda Function (Automated Reports)**
Created a Lambda function that:
- Connects to RDS to fetch user credentials
- Calls Google Search Console API
- Generates AI insights
- Sends email via SMTP

**5. EventBridge Schedule**
Set up a rule to trigger Lambda daily:
```
Cron expression: 0 8 * * ? *
Target: search-console-daily-reports Lambda function
```

### Sunday Afternoon: The Mixed Content Challenge

I hit a major roadblock: **Mixed Content error**.

The frontend was on HTTPS (Amplify), but the backend was on HTTP (Elastic Beanstalk). Browsers block HTTP requests from HTTPS pages for security.

**Solution:** I implemented Next.js rewrites to proxy API calls through the frontend:

```typescript
// next.config.ts
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://backend-url.com/api/v1/:path*',
      },
    ];
  },
};
```

Now the browser sees all requests as HTTPS, while Next.js forwards them to the HTTP backend server-side.

## Key Features That Make It Work

### 1. Secure OAuth Flow
Instead of cookies (which don't work cross-domain), I store tokens in localStorage:
```typescript
localStorage.setItem('access_token', token);
localStorage.setItem('refresh_token', refreshToken);
```

Then send them in headers:
```typescript
const token = localStorage.getItem('access_token');
headers: { Authorization: `Bearer ${token}` }
```

### 2. AI-Powered Insights
The agent uses LangChain to orchestrate:
```python
tools = [
    SearchConsoleTool(),      # Fetch metrics
    WebScraperTool(),         # Get page content
]

agent = create_react_agent(llm, tools, prompt)
result = agent.invoke({"input": "Analyze SEO performance..."})
```

Mistral AI generates actionable recommendations like:
- "Your blog post on X saw a 45% CTR increase - consider creating similar content"
- "Position dropped for 'keyword Y' - check for new competitors"
- "Top page has slow load time - optimize images"

### 3. Real-Time Streaming with SSE
The frontend displays analysis progress in real-time:
```typescript
const eventSource = new EventSource('/api/v1/agent/weekly');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.message); // "Fetching data...", "Analyzing...", etc.
};
```

### 4. Multi-Site Support
Users can:
- Link multiple Google Search Console properties
- Switch between sites instantly
- Get separate reports for each property

## AWS Services Breakdown

Here's how I used AWS Free Tier to keep costs at $0:

| Service | Usage | Free Tier Limit | Monthly Cost |
|---------|-------|----------------|--------------|
| **Amplify** | Frontend hosting | 1000 build minutes | $0 |
| **Elastic Beanstalk** | Backend API (t3.micro) | 750 hours | $0 |
| **RDS PostgreSQL** | Database (db.t3.micro) | 750 hours | $0 |
| **Lambda** | Daily reports | 1M requests | $0 |
| **EventBridge** | Scheduling | Unlimited rules | $0 |
| **CloudWatch** | Logs | 5 GB | $0 |

**Total: $0/month for the first year!**

After the Free Tier expires, estimated cost is ~$15-20/month (mostly RDS and Elastic Beanstalk).

## Challenges and Solutions

### Challenge 1: OAuth Token Storage
**Problem:** Cookies don't work cross-domain (Amplify vs Elastic Beanstalk)  
**Solution:** Store tokens in localStorage, send via Authorization header

### Challenge 2: Mixed Content Security
**Problem:** HTTPS frontend can't call HTTP backend  
**Solution:** Next.js rewrites to proxy requests server-side

### Challenge 3: Google OAuth "Unverified App" Warning
**Problem:** Sensitive scopes require app verification  
**Solution:** Added test users, clicked "Advanced" → "Continue anyway"

### Challenge 4: Lambda Database Connectivity
**Problem:** Lambda couldn't reach RDS in private subnet  
**Solution:** Made RDS publicly accessible with security group rules (dev only - use VPC in production)

### Challenge 5: Alembic Migrations in Production
**Problem:** Running migrations on deployed database  
**Solution:** SSH into Elastic Beanstalk instance, ran `alembic upgrade head`

## What I Learned

1. **AWS Free Tier is powerful** - You can build production-grade apps without spending a dime
2. **Serverless isn't always the answer** - Elastic Beanstalk was easier than Lambda for a complex API
3. **OAuth is tricky** - Test with your own account first, expect warnings with sensitive scopes
4. **HTTPS matters** - Mixed Content policies are strict, plan your architecture accordingly
5. **AI agents need good tools** - The quality of LangChain tools directly impacts AI output

## Results and Impact

Before Search Console Agent:
- **3 hours/week** manually checking Search Console
- **Reactive** - noticed issues days late
- **Inconsistent** - sometimes forgot to check

After Search Console Agent:
- **0 hours/week** - fully automated
- **Proactive** - alerts in my inbox every morning
- **Consistent** - never miss a day

I've already spotted two major opportunities:
1. A blog post ranking #8 that needs better CTR optimization
2. A declining keyword that needed fresh content

The time savings alone pay for the effort, but the proactive insights are the real win.

## Try It Yourself

The complete source code is on GitHub: [https://github.com/muhmdusman/seo-agent](https://github.com/muhmdusman/seo-agent)

**Live Demo:** [https://main.d3vozze6u0rukp.amplifyapp.com/](https://main.d3vozze6u0rukp.amplifyapp.com/)

To deploy your own:

1. Clone the repository
2. Set up Google OAuth credentials
3. Get a Mistral API key (free tier available)
4. Deploy to AWS using the deployment guides in the repo
5. Configure your SMTP settings for email delivery

The README has step-by-step instructions for local development and AWS deployment.

## What's Next?

I'm planning to add:
- **Weekly trend analysis** - Compare performance week-over-week
- **Keyword opportunity detection** - Find keywords close to page 1
- **Competitor monitoring** - Track when competitors outrank you
- **Slack/Discord notifications** - Get alerts where you work
- **Custom report templates** - Tailor insights to your needs

## Final Thoughts

Building Search Console Agent was a perfect weekend project - practical, challenging, and immediately useful. It solved a real problem in my workflow and taught me a ton about AWS, AI agents, and OAuth flows.

The best part? It runs on AWS Free Tier, so you can build your own without worrying about costs.

If you manage any websites, I highly recommend building something like this. The time savings compound quickly, and you'll learn valuable skills along the way.

**What annoying task could you automate this weekend?**

---

**Tags:** #challenge #productivity #aws-free-tier #application #ai #seo #automation #serverless #nextjs #python

**Live App:** https://main.d3vozze6u0rukp.amplifyapp.com/  
**Source Code:** https://github.com/muhmdusman/seo-agent  
**Author:** Muhammad Usman ([@muhmdusman](https://github.com/muhmdusman))
