# Weekend Annoying Task Challenge: Search Console Agent

**Tags:** #productivity #challenge #aws-free-tier #application #ai #seo #automation

## Vision & What the App Does

Every Monday morning, I used to spend 2-3 hours manually checking Google Search Console, pulling performance data, identifying trends, and writing SEO reports for my websites. It was repetitive, time-consuming, and honestly pretty boring. I'd open Search Console, export data to spreadsheets, compare week-over-week metrics, and try to spot opportunities or issues. By the time I finished, half my morning was gone.

That's when I decided to build **Search Console Agent** - an AI-powered system that automatically generates SEO insights and emails them to me every morning at 8 AM UTC. The app connects to Google Search Console, fetches your website's performance data, analyzes it using AI, and sends detailed reports with actionable recommendations straight to your inbox.

**The Problem It Solves:**
Manual SEO reporting is tedious and easy to forget. You need to remember to check Search Console, analyze metrics, spot trends, and document findings. Search Console Agent automates this entire workflow, ensuring you never miss important SEO changes and always have fresh insights waiting in your inbox every morning.

## How the App Works

Search Console Agent is a web application with a simple but powerful workflow:

**1. User Authentication**
You start by visiting the web app and clicking "Connect with Google." This triggers Google OAuth 2.0 authentication, asking permission to access your Search Console data in read-only mode. Once you authorize, the app securely stores your access tokens in a PostgreSQL database.

**2. Site Selection**
After authentication, you see a list of all your verified Search Console properties. You can select which website you want to monitor, and the app remembers your choice for future reports.

**3. Data Collection**
The app fetches the last 30 days of performance metrics from Google Search Console, including:
- Total clicks and impressions
- Average click-through rate (CTR)
- Average search position
- Top performing pages
- Top search queries

**4. AI Analysis**
This is where the magic happens. The app uses Mistral AI (an open-source large language model) to analyze your data. The AI agent:
- Reviews all performance metrics
- Scrapes your top-performing pages to understand content
- Identifies trends, opportunities, and potential issues
- Generates human-readable insights and recommendations

**5. Report Delivery**
Every morning at 8 AM UTC, an automated scheduler triggers the report generation process. The AI creates a fresh analysis and emails it to you via SMTP. You wake up to actionable SEO insights without doing anything.

**6. Multi-Site Support**
If you manage multiple websites, you can add all of them to the app. Each site gets its own automated daily report, keeping all your properties monitored in one place.

The entire process runs on autopilot. Once configured, you never have to manually check Search Console again - the insights come to you.

## How I Built It

I built this over a weekend using modern cloud technologies and AWS services. Here's how it came together:

**Saturday Morning: Google OAuth Setup**
The first step was setting up authentication with Google. I created a Google Cloud project, enabled the Search Console API, and configured OAuth 2.0 credentials. The tricky part was getting the right scope - I needed `webmasters.readonly` to access Search Console data. Since this is a sensitive scope, Google requires the app to be in "Testing" mode with approved test users until it goes through verification. For now, the app works perfectly in testing mode, and I'm planning to submit it for production verification soon.

**Saturday Afternoon: Building the Backend**
I chose FastAPI for the backend because it's fast, modern, and has excellent automatic API documentation. The backend handles:
- OAuth flow management (redirecting to Google, exchanging codes for tokens, refreshing expired tokens)
- Database operations using SQLAlchemy ORM
- API endpoints for fetching sites and triggering analysis
- Integration with Google Search Console API
- AI agent orchestration using LangChain

I structured the database to separate user accounts, OAuth tokens, and sessions. This keeps authentication secure and allows multiple users to connect different Google accounts.

**Saturday Evening: Frontend with Next.js**
For the user interface, I built a clean, responsive web app using Next.js 16 with React and TypeScript. The frontend features:
- Landing page with Google sign-in button
- OAuth callback handler
- Dashboard with site selector dropdown
- Real-time analysis display
- Mobile-responsive design using Tailwind CSS

I used Shadcn/ui components (built on Radix UI) for consistent, accessible UI elements. The design follows modern web standards and works seamlessly on desktop and mobile devices.

**Sunday: AWS Deployment**
This is where everything came together in the cloud:

First, I deployed the database using AWS RDS PostgreSQL. I chose a db.t3.micro instance (covered by AWS Free Tier) with 20GB of storage. The database stores user information, OAuth credentials, and session data securely.

Next, I packaged the FastAPI backend and deployed it to AWS Elastic Beanstalk. I selected the Python 3.11 platform running on Amazon Linux 2023 with a t3.micro instance (also Free Tier eligible). Elastic Beanstalk automatically handles load balancing, health monitoring, and auto-scaling.

For the frontend, I connected my GitHub repository to AWS Amplify. Amplify detected the Next.js project automatically and set up continuous deployment. Every time I push code to the main branch, Amplify builds and deploys the new version. It also provides HTTPS out of the box, which is essential for security.

The most exciting part was setting up automated reports. I created an AWS Lambda function that contains the report generation logic. This function connects to the RDS database to fetch user credentials, calls the Google Search Console API, runs the AI analysis, and sends emails via SMTP. To trigger this function daily, I configured AWS EventBridge with a cron expression set to 8 AM UTC every day.

**The Challenge: Mixed Content Security**
I hit one major technical challenge: the frontend was served over HTTPS (Amplify), but the backend was on HTTP (Elastic Beanstalk). Modern browsers block HTTP requests from HTTPS pages for security reasons - this is called Mixed Content blocking.

My solution was to implement Next.js rewrites, which act as a server-side proxy. When the browser makes a request to the frontend's API path, Next.js forwards it to the backend HTTP URL server-side. The browser only sees HTTPS requests, so there's no security warning. This was a clever workaround that kept me in the AWS Free Tier while maintaining security.

## AWS Services Used / Architecture Overview

The app runs entirely on AWS using six core services:

**AWS Amplify** hosts the frontend web application. It provides automatic builds from GitHub, HTTPS certificates, and global CDN distribution. Every time I push code, Amplify rebuilds and deploys the new version in minutes.

**AWS Elastic Beanstalk** runs the backend API. It manages the Python application server, handles load balancing, and provides health monitoring. I deployed a FastAPI application using Uvicorn as the ASGI server.

**AWS RDS PostgreSQL** is the database layer. It stores user accounts, OAuth credentials from Google, and session information. The db.t3.micro instance provides reliable storage with automated backups.

**AWS Lambda** executes the report generation function. This serverless function runs only when triggered, making it cost-effective. It fetches data from Search Console, calls the AI model, and sends emails.

**AWS EventBridge** schedules the daily reports. I configured a rule with a cron expression that triggers the Lambda function every day at 8 AM UTC. EventBridge is reliable and requires no server management.

**AWS CloudWatch** collects logs from all services. I can monitor API requests, debug errors, and track Lambda executions. This was crucial for troubleshooting during deployment.

**Architecture Flow:**

When a user visits the app, their browser connects to AWS Amplify (frontend). Clicking "Connect with Google" sends a request through Next.js rewrites to Elastic Beanstalk (backend). The backend redirects to Google's OAuth consent screen. After the user authorizes, Google sends an authorization code back to the backend callback URL. The backend exchanges this code for access and refresh tokens, stores them in RDS, and redirects the user back to the frontend dashboard.

Once authenticated, the user selects a website. The frontend fetches the list of Search Console properties from the backend, which calls Google's API using the stored tokens. The user can manually trigger an analysis or wait for the automated daily report.

Every day at 8 AM UTC, EventBridge triggers the Lambda function. Lambda connects to RDS to get user credentials, fetches Search Console data for the last 30 days, passes it to the Mistral AI model for analysis, and sends the generated report via email. The entire process happens automatically without any manual intervention.

This architecture is scalable, cost-effective (runs on AWS Free Tier), and reliable. Each service has a specific purpose, and they work together seamlessly.

## What I Learned

Building this project taught me several valuable lessons about cloud architecture and AI integration:

**AWS Free Tier is Powerful:** I was amazed that I could run a full production-grade application completely free for the first year. Amplify, Elastic Beanstalk (t3.micro), RDS (db.t3.micro), Lambda, and EventBridge all fit within Free Tier limits. After the first year, the estimated cost is only around fifteen to twenty dollars per month.

**Serverless Isn't Always the Best Choice:** I initially considered building the entire backend as Lambda functions, but I chose Elastic Beanstalk instead. For complex APIs with multiple dependencies and long-running AI calls, a traditional server approach was simpler to develop and debug. Lambda is perfect for the scheduled reports, but the main API works better on Elastic Beanstalk.

**OAuth is Complex but Essential:** Setting up Google OAuth taught me about authorization flows, token management, and security best practices. I learned about access tokens (short-lived), refresh tokens (long-lived), and how to handle token expiration gracefully. The OAuth consent screen warnings for unverified apps are intimidating, but they're necessary for user security.

**AI Agents Need Good Tools:** The quality of AI-generated insights depends heavily on the tools you provide. I used LangChain to give the AI agent two tools: one for fetching Search Console data and another for scraping webpage content. The better the tools, the better the AI's recommendations.

**Architecture Matters for Security:** The Mixed Content issue taught me to plan security from the start. HTTPS isn't just a nice-to-have - it's required by modern browsers. Understanding how to proxy requests or enable HTTPS on all services is crucial for production deployments.

**Database Design Impacts Everything:** Separating OAuth credentials from user sessions was a smart decision. It allows users to connect multiple Google accounts and makes token refresh logic cleaner. Good data modeling at the start saves headaches later.

**Automation Compounds Value:** The three hours I spent every week on manual reports adds up to over 150 hours per year. Automating this task not only saves time but also ensures consistency. I never forget to check Search Console now because the insights arrive automatically.

## Current Status & Testing

The app is currently running in **testing mode** as required by Google OAuth verification. This means it works perfectly, but only for approved test users. I'm planning to submit the app for Google's verification process to make it publicly available soon.

**Want to test it yourself?**

You have two options:

**Option 1: Try the Live Demo**
Visit the deployed app at: https://main.d3vozze6u0rukp.amplifyapp.com/

Since it's in testing mode, you'll need to be added as a test user. Drop your email address in the comments, and I'll add you to the test user list. You'll see an "unverified app" warning from Google - just click "Advanced" and "Continue" to proceed. Your data is completely safe and read-only.

**Option 2: Run It Locally**
Clone the repository from GitHub: https://github.com/muhmdusman/seo-agent

The README has complete setup instructions for running the app locally. You'll need to create your own Google Cloud project and OAuth credentials, but you'll have full control over the environment.

For local testing, you can configure the email delivery to use your own SMTP server or a service like SendGrid. The AI analysis works with any Mistral API key (they offer a free tier).

## What's Next

I'm actively working on several improvements:

**Production Verification:** Submitting the app to Google for OAuth verification so anyone can use it without being a test user.

**Weekly Trend Analysis:** Comparing current performance to previous weeks to identify significant changes and trends.

**Keyword Opportunity Detection:** Finding search queries where you rank on page 2 (positions 11-20) - these are low-hanging fruit for optimization.

**Custom Report Templates:** Allowing users to choose what metrics and insights they want in their reports.

**Slack and Discord Notifications:** Sending alerts directly to your team's communication channels instead of just email.

**Performance Alerts:** Immediate notifications when traffic drops significantly or ranking changes dramatically.

## Results and Impact

The impact has been immediate and significant:

**Before Search Console Agent:**
- 3 hours per week manually checking and analyzing data
- Often forgot to check, missing important changes
- Reactive approach - noticed issues days or weeks late

**After Search Console Agent:**
- Zero hours spent on manual checks
- Daily insights delivered automatically
- Proactive alerts catch issues immediately

In just the first week, the AI spotted two opportunities I would have missed:
1. A blog post ranking at position 8 with low CTR - I optimized the title and meta description, and it's now getting 40% more clicks
2. A declining keyword that needed fresh content - I updated the article, and rankings recovered within days

The time savings alone justify the effort, but the proactive insights are the real value. I'm catching SEO opportunities and problems before they impact traffic significantly.

## Link to App or Repo

**Live Demo:** https://main.d3vozze6u0rukp.amplifyapp.com/  
**Source Code:** https://github.com/muhmdusman/seo-agent  
**Documentation:** Full deployment guides and API docs in the repository

The repository includes:
- Complete source code for frontend and backend
- AWS deployment instructions
- Local development setup guide
- Database migration scripts
- Environment configuration templates

Everything you need to deploy your own instance is included. The app is released under the MIT License, so you're free to use, modify, and deploy it however you'd like.

## Final Thoughts

Building Search Console Agent was the perfect weekend project - practical, challenging, and immediately useful. It solved a real problem in my workflow and taught me valuable lessons about AWS, AI integration, and OAuth flows.

The best part is that it runs entirely on AWS Free Tier, so you can build your own without worrying about costs for the first year. After that, it costs less than a couple of coffee trips per month.

If you manage any websites, I highly recommend automating your SEO monitoring. The time savings compound quickly, you'll catch issues faster, and you'll never miss important changes again.

**Drop your email in the comments if you want to be added as a test user, and I'll send you an invite!**

What annoying task could you automate this weekend?
