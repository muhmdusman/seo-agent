# 🚀 Quick Start - Deploy in 30 Minutes

Complete guide to get your Search Console Agent with daily email reports running on AWS.

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Google Cloud OAuth credentials
- [ ] Web3Forms API key: `aa8d5796-e26a-43cf-8976-0a468971c727`
- [ ] Python 3.11+ installed locally
- [ ] Git repository cloned

## 🎯 30-Minute Deployment Path

### Step 1: Local Setup (5 min)

```bash
# Clone and enter directory
cd /path/to/Search-console-Agent

# Install dependencies
cd backend
uv sync

# Create symlink for .env
ln -sfn ../.env .env

# Start local database
docker compose -f db/docker-compose.yaml up -d

# Run migrations
uv run alembic upgrade head
```

### Step 2: Test Locally (5 min)

```bash
# Start backend
uv run uvicorn main:app --reload

# In another terminal, test scheduler
uv run python test_scheduler.py
```

Visit http://localhost:8000/docs to verify API is running.

### Step 3: AWS RDS Setup (10 min)

```bash
# Create RDS instance (use AWS Console for faster setup)
# Or use CLI:
aws rds create-db-instance \
  --db-instance-identifier search-console-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password YOUR_STRONG_PASSWORD \
  --allocated-storage 20

# Get endpoint
aws rds describe-db-instances \
  --db-instance-identifier search-console-db \
  --query 'DBInstances[0].Endpoint.Address'

# Update .env with RDS endpoint
# DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@RDS_ENDPOINT:5432/app_db

# Run migrations on RDS
uv run alembic upgrade head
```

### Step 4: Lambda Deployment (10 min)

```bash
# Create IAM role (or use AWS Console)
aws iam create-role \
  --role-name search-console-lambda-role \
  --assume-role-policy-document file://lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name search-console-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Package and deploy
cd backend
./deploy_lambda.sh

# Or manually:
zip -r lambda.zip lambda_handler.py agents/ services/ models/ core/ db/ tools/ api/ schemas/

aws lambda create-function \
  --function-name search-console-daily-reports \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/search-console-lambda-role \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 900 \
  --memory-size 512

# Set environment variables (use AWS Console - easier)
```

### Step 5: EventBridge Setup (5 min)

```bash
# Create daily trigger
aws events put-rule \
  --name daily-seo-reports \
  --schedule-expression "cron(0 8 * * ? *)"

# Add Lambda permission
aws lambda add-permission \
  --function-name search-console-daily-reports \
  --statement-id AllowEventBridge \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com

# Set target
aws events put-targets \
  --rule daily-seo-reports \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:search-console-daily-reports"
```

## ✅ Verification Steps

### Test Lambda Function
```bash
aws lambda invoke \
  --function-name search-console-daily-reports \
  response.json

cat response.json
```

### Test Email Service
```bash
curl -X POST https://your-api.com/api/v1/scheduler/test-email
```

### Check CloudWatch Logs
```bash
aws logs tail /aws/lambda/search-console-daily-reports --follow
```

## 🔥 Common Issues & Fixes

### Lambda Can't Connect to RDS
**Solution:** Add Lambda to same VPC as RDS, update security groups

```bash
# Update Lambda VPC config
aws lambda update-function-configuration \
  --function-name search-console-daily-reports \
  --vpc-config SubnetIds=subnet-xxx,SecurityGroupIds=sg-xxx
```

### Email Not Sending
**Solution:** Verify Web3Forms key, check Lambda logs

```bash
# Check logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/search-console-daily-reports \
  --filter-pattern "email"
```

### Lambda Timeout
**Solution:** Increase timeout to 15 minutes

```bash
aws lambda update-function-configuration \
  --function-name search-console-daily-reports \
  --timeout 900
```

## 📱 Environment Variables (Lambda)

Set these in AWS Lambda Console → Configuration → Environment Variables:

```env
APP_NAME=Search Console Agent
DEBUG=false
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@RDS_ENDPOINT/app_db
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_URL=https://your-api.com
FRONTEND_URL=https://your-frontend.com
MISTRAL_API_KEY=your-mistral-key
REFRESH_TOKEN_EXPIRY_DAYS=7
WEB3FORMS_ACCESS_KEY=aa8d5796-e26a-43cf-8976-0a468971c727
SCHEDULER_ENABLED=true
DAILY_REPORT_TIME=08:00
ADMIN_EMAIL=your-email@example.com
```

## 🎯 Frontend Deployment (Optional)

### Using AWS Amplify

1. Go to AWS Amplify Console
2. Connect GitHub repository
3. Select `frontend` directory
4. Set build settings:
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - cd frontend
           - npm install
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: frontend/.next
       files:
         - '**/*'
   ```
5. Set environment variable:
   - `NEXT_PUBLIC_API_BASE_URL`: Your backend URL
6. Deploy!

## 📊 Monitoring Dashboard

### CloudWatch Metrics to Monitor
- Lambda Invocations (should be 1/day)
- Lambda Duration (typical: 30-180s)
- Lambda Errors (should be 0)
- RDS CPU/Memory (should be low)

### Set Up Alarms
```bash
# Email on Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name search-console-lambda-errors \
  --alarm-description "Alert on Lambda execution errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 3600 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

## 💰 Cost Breakdown

| Service | Free Tier | After Free Tier |
|---------|-----------|-----------------|
| Lambda | 1M requests/month | $0.20/1M requests |
| RDS t3.micro | 750 hrs/month (12mo) | ~$13/month |
| EventBridge | Always free | Always free |
| CloudWatch | 5GB logs/month | $0.50/GB |
| **Total** | **$0/month (year 1)** | **~$14/month** |

## 🎓 Testing Checklist

- [ ] Lambda function executes without errors
- [ ] Test email received successfully
- [ ] CloudWatch logs show execution
- [ ] EventBridge rule is enabled
- [ ] Manual trigger works via API
- [ ] Database connection established
- [ ] OAuth flow works end-to-end
- [ ] Daily email arrives at 8 AM UTC

## 📚 Full Documentation

- **Complete Setup:** [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)
- **Feature Details:** [SCHEDULER_FEATURE.md](SCHEDULER_FEATURE.md)
- **Article Draft:** [ARTICLE_OUTLINE.md](ARTICLE_OUTLINE.md)
- **Implementation:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## 🆘 Getting Help

1. Check CloudWatch logs first
2. Run `test_scheduler.py` locally to isolate issues
3. Review AWS_DEPLOYMENT.md troubleshooting section
4. Check GitHub issues

## 🎉 Success Criteria

You're done when:
- ✅ Lambda executes daily without errors
- ✅ You receive daily SEO report emails
- ✅ CloudWatch shows successful invocations
- ✅ No errors in logs for 3 days
- ✅ Frontend is accessible and OAuth works

---

**Time to deploy and win that AWS Builder Jacket! 🧥**

*Need help? Check the full deployment guide: [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)*
