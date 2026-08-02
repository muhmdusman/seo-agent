# 📅 Daily Scheduler & Email Reports Feature

## Overview

The Search Console Agent now includes an **automated daily scheduler** that generates SEO reports for all user sites and delivers them via email using Web3Forms.

## 🎯 What Problem Does This Solve?

**Annoying Task:** Manually checking Google Search Console every day across multiple websites, analyzing performance changes, and remembering to act on SEO opportunities.

**Solution:** Automated daily emails with AI-generated SEO insights, highlighting immediate opportunities and alerting you to performance drops—all delivered to your inbox at 8 AM UTC every day.

## 🏗️ Architecture

```
┌──────────────────────────┐
│  AWS EventBridge         │  Triggers daily at 8 AM UTC
│  (cron: 0 8 * * ? *)     │
└─────────┬────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│  AWS Lambda Function                             │
│  - Fetches all users from database              │
│  - Retrieves verified sites from Search Console │
│  - Generates reports using DailyAgent + Mistral │
│  - Sends emails via Web3Forms                   │
└─────────┬───────────────────────────────────────┘
          │
          ├──► PostgreSQL (RDS)
          ├──► Google Search Console API
          ├──► Mistral AI LLM
          └──► Web3Forms Email API
```

## ✨ Features

### 1. **Daily Agent** (`agents/daily_agent.py`)
- Generates concise, actionable SEO reports
- Focuses on quick wins and alerts
- Analyzes last 7 days of Search Console data
- Formats reports for email delivery

### 2. **Email Service** (`services/email_service.py`)
- Web3Forms API integration
- Beautiful HTML email templates
- Error notifications to admin
- Delivery tracking and retry logic

### 3. **Scheduler Service** (`services/scheduler_service.py`)
- Orchestrates report generation for all users
- Processes multiple sites per user
- Handles errors gracefully
- Provides detailed statistics

### 4. **API Endpoints** (`api/routes/scheduler.py`)
- `POST /api/v1/scheduler/trigger` - Manual trigger for testing
- `GET /api/v1/scheduler/status` - Check scheduler status
- `POST /api/v1/scheduler/test-email` - Test email delivery

### 5. **Lambda Handler** (`lambda_handler.py`)
- AWS Lambda entry point
- CloudWatch logging integration
- Error handling and reporting

## 📧 Email Report Format

Each daily email includes:

### Performance Snapshot
- Total clicks, impressions, CTR, average position
- Week-over-week changes

### Today's Top Opportunity
- ONE specific action to take today
- Data-backed reasoning
- Quick win potential

### Attention Needed (if any)
- Performance drops
- Technical issues
- Urgent items requiring action

## 🚀 Local Testing

### 1. Test Configuration

```bash
cd backend
python test_scheduler.py
```

This will test:
- ✅ Configuration loading
- ✅ Database connectivity
- ✅ Email service (sends test email)
- ✅ Full scheduler run (optional)

### 2. Test Individual Components

**Test email service only:**
```bash
curl -X POST http://localhost:8000/api/v1/scheduler/test-email
```

**Check scheduler status:**
```bash
curl http://localhost:8000/api/v1/scheduler/status
```

**Manual trigger:**
```bash
curl -X POST http://localhost:8000/api/v1/scheduler/trigger
```

### 3. Run Lambda Handler Locally

```bash
cd backend
python lambda_handler.py
```

## 🔧 Configuration

### Environment Variables

Add to your `.env` file:

```env
# Web3Forms Email Service
WEB3FORMS_ACCESS_KEY="aa8d5796-e26a-43cf-8976-0a468971c727"

# Daily Scheduler Configuration
SCHEDULER_ENABLED=true
DAILY_REPORT_TIME="08:00"
ADMIN_EMAIL="your-email@example.com"
```

### Scheduler Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULER_ENABLED` | `true` | Enable/disable scheduler |
| `DAILY_REPORT_TIME` | `08:00` | Time for daily reports (UTC) |
| `ADMIN_EMAIL` | Required | Admin email for error notifications |
| `WEB3FORMS_ACCESS_KEY` | Required | Web3Forms API key |

## 📊 Report Generation Process

For each user:

1. **Fetch User Sites**
   - Query Google Search Console API
   - Get all verified properties
   - Filter by permission level

2. **Generate Reports**
   - Fetch last 7 days of Search Console data
   - Analyze with Mistral AI
   - Format as actionable insights

3. **Send Emails**
   - Format report as HTML
   - Send via Web3Forms API
   - Track delivery status

4. **Error Handling**
   - Continue on single-site failures
   - Send error notifications to admin
   - Log all failures to CloudWatch

## 🐛 Troubleshooting

### Email Not Received

1. **Check spam folder** - First report may be flagged
2. **Verify Web3Forms key** - Test with `/scheduler/test-email`
3. **Check Lambda logs** - Look for delivery errors
4. **Verify user email** - Must match OAuth account

### No Reports Generated

1. **Check user has OAuth account** - Run test_scheduler.py
2. **Verify Search Console access** - Check token expiry
3. **Check scheduler enabled** - `SCHEDULER_ENABLED=true`
4. **Review Lambda logs** - Check for execution errors

### Database Connection Issues

1. **Check DATABASE_URL** - Verify RDS endpoint
2. **Security groups** - Allow Lambda → RDS traffic
3. **VPC configuration** - Lambda must be in same VPC
4. **Test connection** - Run test_scheduler.py locally

## 📈 Monitoring

### CloudWatch Metrics

Monitor these key metrics:

- **Lambda Invocations** - Should be 1/day
- **Lambda Duration** - Typically 30-180 seconds
- **Lambda Errors** - Should be 0
- **Email Success Rate** - Track in application logs

### Log Analysis

```bash
# View recent Lambda executions
aws logs tail /aws/lambda/search-console-daily-reports --follow

# Find errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/search-console-daily-reports \
  --filter-pattern "ERROR"

# Count successful reports
aws logs filter-log-events \
  --log-group-name /aws/lambda/search-console-daily-reports \
  --filter-pattern "report sent successfully"
```

## 🔐 Security Considerations

1. **API Keys**
   - Store in AWS Secrets Manager (production)
   - Use environment variables for development
   - Rotate keys regularly

2. **Database Access**
   - Lambda in VPC with RDS
   - Security groups restrict access
   - Use IAM database authentication

3. **Rate Limiting**
   - Respect Google Search Console API limits
   - Implement exponential backoff
   - Process sites in batches if needed

## 🎓 AWS Services Used

This feature demonstrates usage of:

- ✅ **AWS Lambda** - Serverless compute for scheduled tasks
- ✅ **AWS EventBridge** - Cron-based scheduling
- ✅ **AWS RDS** - PostgreSQL database
- ✅ **CloudWatch** - Logging and monitoring
- ✅ **VPC** - Secure networking for Lambda-RDS communication
- ✅ **IAM** - Role-based access control

## 💡 Future Enhancements

1. **User Preferences**
   - Allow users to choose report frequency
   - Customize report time zone
   - Opt-in/opt-out per site

2. **Report History**
   - Store generated reports in database
   - Web UI to view past reports
   - Trend analysis across weeks

3. **Custom Alerts**
   - Set thresholds for notifications
   - Alert on specific query drops
   - Technical SEO issue detection

4. **Report Types**
   - Weekly summary reports
   - Monthly performance reviews
   - Competitor analysis

5. **Multi-Channel Delivery**
   - Slack integration
   - SMS alerts for critical issues
   - In-app notifications

## 📚 Code Structure

```
backend/
├── agents/
│   ├── weekly_agent.py      # Existing comprehensive analysis
│   └── daily_agent.py        # New: Concise daily reports
├── services/
│   ├── email_service.py      # New: Web3Forms integration
│   └── scheduler_service.py  # New: Orchestration logic
├── api/routes/
│   └── scheduler.py          # New: Scheduler endpoints
├── lambda_handler.py         # New: AWS Lambda entry point
├── test_scheduler.py         # New: Testing utilities
└── deploy_lambda.sh          # New: Deployment script
```

## 🎯 Testing Checklist

Before deploying to production:

- [ ] Test email service locally
- [ ] Verify database connectivity
- [ ] Run test_scheduler.py successfully
- [ ] Test Lambda handler locally
- [ ] Deploy to AWS staging environment
- [ ] Test EventBridge trigger
- [ ] Verify CloudWatch logs
- [ ] Confirm email delivery
- [ ] Test error notifications
- [ ] Load test with multiple users

## 📞 Support

For issues or questions:

1. Check CloudWatch logs for Lambda errors
2. Run `test_scheduler.py` to diagnose issues
3. Review `AWS_DEPLOYMENT.md` for setup guidance
4. Open an issue on GitHub

## 🏆 AWS Weekend Challenge

This feature was built for the **AWS Weekend Challenge** to demonstrate:

- **Automation** - Daily scheduled tasks without manual intervention
- **Multi-Service Integration** - Lambda, EventBridge, RDS, CloudWatch
- **Real-World Problem Solving** - Automating annoying SEO monitoring tasks
- **Production-Ready Code** - Error handling, logging, monitoring
- **Scalability** - Handles multiple users and sites efficiently

---

**Built with:** FastAPI, AWS Lambda, Mistral AI, Web3Forms, PostgreSQL
**Deployment:** See `AWS_DEPLOYMENT.md` for complete setup instructions
