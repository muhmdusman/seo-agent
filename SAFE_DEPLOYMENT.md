# 🚀 Safe AWS Deployment - Don't Break What's Working!

## ✅ Current Status

**EVERYTHING WORKS LOCALLY:**
- ✅ Backend API
- ✅ Frontend
- ✅ OAuth flow
- ✅ Email delivery
- ✅ Scheduler
- ✅ AI report generation
- ✅ Full end-to-end flow

**AWS Services We'll Use:**
- ✅ AWS Lambda (scheduler execution)
- ✅ AWS EventBridge (daily cron trigger)
- ✅ AWS RDS PostgreSQL (database)
- ✅ AWS Elastic Beanstalk or EC2 (backend API - optional for now)
- ✅ AWS Amplify (frontend - optional for now)

**What We're Keeping:**
- ✅ Mistral AI (works perfectly, no need to change)
- ✅ Gmail SMTP (works perfectly, no need to change)

---

## 🎯 Deployment Strategy: Minimum Viable AWS

We'll deploy in **phases** to minimize risk:

### Phase 1: Lambda + EventBridge Only (Today) ⚡
**Goal:** Get daily scheduler running on AWS
**Risk:** LOW - Lambda is isolated, won't break local setup

### Phase 2: RDS Migration (Later) 🗄️
**Goal:** Move database to AWS RDS
**Risk:** MEDIUM - Keep local backup

### Phase 3: Backend/Frontend (Later) 🌐
**Goal:** Deploy full app to AWS
**Risk:** MEDIUM - Optional for challenge

---

## 📦 Phase 1: Deploy Lambda Function (30 minutes)

This is the **minimum required** to demonstrate AWS usage and keep everything working.

### Step 1.1: Create Lambda Deployment Package

```bash
cd backend

# Create clean directory
rm -rf lambda_package
mkdir lambda_package

# Copy application code
cp -r agents lambda_package/
cp -r api lambda_package/
cp -r core lambda_package/
cp -r db lambda_package/
cp -r models lambda_package/
cp -r schemas lambda_package/
cp -r services lambda_package/
cp -r tools lambda_package/
cp lambda_handler.py lambda_package/

# Install dependencies
pip install -r requirements.txt -t lambda_package/ --platform manylinux2014_x86_64 --only-binary=:all:

# Create ZIP
cd lambda_package
zip -r ../lambda_function.zip . -x "*.pyc" "*__pycache__*"
cd ..

echo "✅ Lambda package created: lambda_function.zip"
ls -lh lambda_function.zip
```

### Step 1.2: Create IAM Role for Lambda

```bash
# Create trust policy
cat > lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name SearchConsoleAgentLambdaRole \
  --assume-role-policy-document file://lambda-trust-policy.json

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name SearchConsoleAgentLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Wait for role to propagate
sleep 10

# Get role ARN (save this!)
aws iam get-role \
  --role-name SearchConsoleAgentLambdaRole \
  --query 'Role.Arn' \
  --output text
```

**Save the Role ARN!** It looks like:
```
arn:aws:iam::123456789012:role/SearchConsoleAgentLambdaRole
```

### Step 1.3: Create Lambda Function

**IMPORTANT:** We'll use your **existing local database** first, so Lambda can access it!

```bash
# Get your public IP (Lambda will connect to your local database via this)
MY_IP=$(curl -s ifconfig.me)
echo "Your public IP: $MY_IP"

# Create Lambda function
aws lambda create-function \
  --function-name search-console-daily-reports \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/SearchConsoleAgentLambdaRole \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 900 \
  --memory-size 1024 \
  --region us-east-1 \
  --environment Variables="{
    APP_NAME=Search Console Agent,
    DEBUG=false,
    DATABASE_URL=postgresql+psycopg://postgres:postgres@${MY_IP}:5433/app_db,
    GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},
    GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},
    GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI},
    JWT_SECRET=${JWT_SECRET},
    JWT_ALGORITHM=HS256,
    ACCESS_TOKEN_EXPIRE_MINUTES=60,
    APP_URL=${APP_URL},
    FRONTEND_URL=${FRONTEND_URL},
    MISTRAL_API_KEY=${MISTRAL_API_KEY},
    REFRESH_TOKEN_EXPIRY_DAYS=7,
    SMTP_HOST=smtp.gmail.com,
    SMTP_PORT=587,
    SMTP_USERNAME=${SMTP_USERNAME},
    SMTP_PASSWORD=${SMTP_PASSWORD},
    SMTP_FROM_EMAIL=${SMTP_FROM_EMAIL},
    SMTP_FROM_NAME=Search Console Agent,
    SCHEDULER_ENABLED=true,
    DAILY_REPORT_TIME=08:00,
    ADMIN_EMAIL=${ADMIN_EMAIL}
  }"
```

**Note:** Replace `YOUR_ACCOUNT_ID` and environment variables with actual values from your `.env`

### Step 1.4: Allow Lambda to Access Your Local Database

**Option A: Open Port (Quick but insecure - for testing only)**
```bash
# Allow Lambda to connect to your local PostgreSQL
sudo ufw allow 5433/tcp
```

**Option B: Use ngrok (Better for testing)**
```bash
# Install ngrok
snap install ngrok

# Create tunnel
ngrok tcp 5433

# Use the ngrok URL in Lambda DATABASE_URL
# Format: postgresql+psycopg://postgres:postgres@0.tcp.ngrok.io:12345/app_db
```

### Step 1.5: Test Lambda Function

```bash
# Manual invoke
aws lambda invoke \
  --function-name search-console-daily-reports \
  --region us-east-1 \
  response.json

# Check response
cat response.json | python -m json.tool

# Check logs
aws logs tail /aws/lambda/search-console-daily-reports --follow --region us-east-1
```

**Expected:** Email sent to your inbox!

### Step 1.6: Create EventBridge Schedule

```bash
# Create daily trigger at 8 AM UTC
aws events put-rule \
  --name daily-seo-reports \
  --schedule-expression "cron(0 8 * * ? *)" \
  --description "Daily SEO report generation" \
  --region us-east-1

# Add Lambda permission
aws lambda add-permission \
  --function-name search-console-daily-reports \
  --statement-id AllowEventBridge \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/daily-seo-reports \
  --region us-east-1

# Set Lambda as target
aws events put-targets \
  --rule daily-seo-reports \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:search-console-daily-reports" \
  --region us-east-1

# Verify
aws events describe-rule --name daily-seo-reports --region us-east-1
```

**That's it for Phase 1!** ✅

---

## 🧪 Test Lambda + EventBridge

### Manual Test
```bash
# Trigger Lambda manually
aws lambda invoke \
  --function-name search-console-daily-reports \
  --region us-east-1 \
  output.json

cat output.json
```

### Check CloudWatch Logs
```bash
# View logs
aws logs tail /aws/lambda/search-console-daily-reports \
  --follow \
  --region us-east-1

# Or in AWS Console:
# https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
```

### Verify EventBridge
```bash
# Check rule is enabled
aws events list-rules --region us-east-1 | grep daily-seo-reports

# Check targets
aws events list-targets-by-rule --rule daily-seo-reports --region us-east-1
```

---

## 📊 What You've Accomplished (Phase 1)

✅ **AWS Lambda Function** - Runs your scheduler code
✅ **AWS EventBridge** - Triggers Lambda daily at 8 AM UTC
✅ **CloudWatch Logs** - Monitors execution
✅ **Automated Daily Reports** - Working on AWS!

**AWS Services Used:**
- AWS Lambda (compute)
- AWS EventBridge (scheduling)
- CloudWatch (logging)

**What's Still Local (and that's OK):**
- Database (PostgreSQL)
- Backend API (for on-demand reports)
- Frontend (for user interaction)

---

## 📝 For Your Article

You can now say:

> "The daily report scheduler runs on **AWS Lambda**, triggered by **AWS EventBridge** every morning at 8 AM UTC. Lambda executes the report generation for all users and delivers insights via email. **CloudWatch** provides monitoring and logging for the automated workflow."

**AWS Services Demonstrated:**
1. ✅ AWS Lambda - Serverless compute
2. ✅ AWS EventBridge - Event scheduling
3. ✅ CloudWatch - Monitoring & logs

**This satisfies the challenge requirements!** 🎉

---

## 🚫 What We're NOT Doing (Yet)

### Phase 2: RDS Migration (Optional)
- Move PostgreSQL to AWS RDS
- Update Lambda to use RDS
- Configure VPC for Lambda

### Phase 3: Full Deployment (Optional)
- Deploy backend to Elastic Beanstalk
- Deploy frontend to Amplify
- Update OAuth redirect URIs

**Why skip for now?**
- Phase 1 demonstrates AWS usage ✅
- Local setup works perfectly ✅
- Reduced risk of breaking things ✅
- Can deploy Phase 2-3 after winning jacket 😉

---

## 🎯 Deployment Checklist

### Before Deployment
- [x] Everything working locally
- [x] Email service tested
- [x] Full flow tested
- [ ] AWS CLI configured (`aws configure`)
- [ ] AWS account has permissions

### Phase 1 Deployment
- [ ] Create IAM role
- [ ] Package Lambda function
- [ ] Deploy Lambda
- [ ] Configure environment variables
- [ ] Test Lambda manually
- [ ] Create EventBridge rule
- [ ] Test daily trigger
- [ ] Verify CloudWatch logs

### After Deployment
- [ ] Lambda executes without errors
- [ ] Email received successfully
- [ ] CloudWatch shows logs
- [ ] EventBridge rule enabled
- [ ] Take screenshots for article

---

## 🆘 Troubleshooting

### Lambda Timeout
**Solution:** Increase timeout to 900 seconds (15 minutes)
```bash
aws lambda update-function-configuration \
  --function-name search-console-daily-reports \
  --timeout 900
```

### Can't Connect to Database
**Solution:** Check firewall, use ngrok, or deploy RDS

### Package Too Large
**Solution:** Use Lambda Layers for dependencies
```bash
# Create layer for dependencies
mkdir python
pip install -r requirements.txt -t python/
zip -r layer.zip python/

aws lambda publish-layer-version \
  --layer-name search-console-deps \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11
```

### Environment Variables Missing
**Solution:** Use Systems Manager Parameter Store
```bash
# Store secrets
aws ssm put-parameter \
  --name /search-console/smtp-password \
  --value "your-password" \
  --type SecureString

# Update Lambda to read from SSM
```

---

## 💰 Cost (Phase 1 Only)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 30 invocations/month, ~2 min each | $0.00 (Free Tier) |
| EventBridge | 1 rule | $0.00 (Free) |
| CloudWatch | Logs | $0.00 (5GB free) |
| **Total** | | **$0.00/month** |

**With Free Tier: Completely free for first 12 months!**

---

## 🎉 Success Criteria

After Phase 1:
- ✅ Lambda function deployed
- ✅ EventBridge triggering daily
- ✅ Receiving automated emails
- ✅ CloudWatch logging working
- ✅ AWS services demonstrated
- ✅ Challenge requirements met

**Ready to submit article and win jacket!** 🧥

---

## 📚 Next Steps After Deployment

1. **Screenshot Everything**
   - Lambda function in console
   - EventBridge rule
   - CloudWatch logs
   - Email received

2. **Complete Article**
   - Add screenshots to `ARTICLE_OUTLINE.md`
   - Describe deployment process
   - Add architecture diagram

3. **Submit Challenge**
   - Publish on AWS Builder Center
   - Submit before deadline
   - Win AWS Builder Jacket! 🏆

4. **Optional: Deploy Phase 2-3**
   - RDS for production database
   - Elastic Beanstalk for backend
   - Amplify for frontend

---

**Let's deploy Phase 1 and get that jacket! 🚀**
