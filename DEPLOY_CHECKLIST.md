# ✅ AWS Deployment Checklist

## 🎯 Pre-Deployment Verification

### Everything Working Locally?
- [x] Backend API running
- [x] Frontend running
- [x] Database connected
- [x] OAuth working
- [x] Email service working
- [x] Scheduler tested
- [x] Full flow tested
- [x] Email received successfully

**Status: ✅ EVERYTHING WORKS!**

---

## 🔧 AWS Prerequisites

### 1. AWS CLI Setup
```bash
# Check if AWS CLI is installed
aws --version

# If not installed:
pip install awscli

# Configure AWS CLI
aws configure
# Enter: Access Key ID
# Enter: Secret Access Key
# Enter: Region (us-east-1)
# Enter: Output format (json)
```

### 2. Test AWS Access
```bash
# Should show your account info
aws sts get-caller-identity

# Should list S3 buckets (or empty array)
aws s3 ls
```

### 3. Required Permissions

Your AWS user needs these permissions:
- ✅ Lambda: Full access (create, update, invoke)
- ✅ IAM: Create roles and policies
- ✅ EventBridge: Create and manage rules
- ✅ CloudWatch: View logs

**Simplest approach:** Attach `AdministratorAccess` policy (for testing)

---

## 📦 Deployment Options

### Option 1: Automated Script (Recommended) ⚡

**One-command deployment:**
```bash
./deploy_to_aws.sh
```

**What it does:**
1. ✅ Creates Lambda deployment package
2. ✅ Sets up IAM role
3. ✅ Deploys Lambda function
4. ✅ Configures environment variables
5. ✅ Tests the function
6. ✅ Creates EventBridge daily schedule
7. ✅ Links everything together

**Time:** ~5 minutes

**Pros:**
- Fast and automatic
- Handles all steps
- Tests deployment
- Idempotent (safe to run multiple times)

**Cons:**
- Less control
- Need to debug script if errors

---

### Option 2: Manual Deployment (More Control) 🎯

Follow `SAFE_DEPLOYMENT.md` step-by-step.

**Time:** ~30 minutes

**Pros:**
- Full control
- Understand each step
- Easy to troubleshoot

**Cons:**
- More steps
- More time
- Potential for human error

---

## 🚀 Quick Start: Automated Deployment

### Step 1: Verify Prerequisites

```bash
# Check everything
aws --version                  # Should show version
aws sts get-caller-identity    # Should show your account
cat .env | grep SMTP_PASSWORD  # Should show your app password
```

### Step 2: Run Deployment Script

```bash
# Make executable (if not already)
chmod +x deploy_to_aws.sh

# Deploy!
./deploy_to_aws.sh
```

### Step 3: Watch Output

You'll see:
```
🚀 Search Console Agent - AWS Deployment
==========================================

📋 Checking prerequisites...
✅ AWS CLI configured
   Account ID: 123456789012

📦 Step 1: Creating Lambda deployment package...
   Copying application code...
   Installing dependencies...
   Creating ZIP archive...
✅ Lambda package created: lambda_function.zip (45M)

🔐 Step 2: Setting up IAM role...
✅ IAM Role ready

☁️  Step 3: Deploying Lambda function...
✅ Lambda function created

🧪 Step 4: Testing Lambda function...
✅ Lambda test successful!
   Check your email: amusman9705@gmail.com

⏰ Step 5: Setting up EventBridge schedule...
✅ EventBridge rule configured
   Schedule: Daily at 8:00 AM UTC

🎉 DEPLOYMENT SUCCESSFUL!
```

### Step 4: Verify Email

Check your inbox (amusman9705@gmail.com) - you should receive a test report!

### Step 5: Check AWS Console

- **Lambda:** https://console.aws.amazon.com/lambda/home?region=us-east-1
- **EventBridge:** https://console.aws.amazon.com/events/home?region=us-east-1
- **CloudWatch:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1

---

## 🧪 Post-Deployment Testing

### Test 1: Manual Lambda Invoke

```bash
aws lambda invoke \
  --function-name search-console-daily-reports \
  --region us-east-1 \
  output.json

cat output.json | python -m json.tool
```

**Expected:** Email sent successfully

### Test 2: Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/search-console-daily-reports \
  --follow \
  --region us-east-1
```

**Expected:** See execution logs, no errors

### Test 3: Verify EventBridge

```bash
aws events describe-rule \
  --name daily-seo-reports \
  --region us-east-1
```

**Expected:** Rule enabled, schedule set to `cron(0 8 * * ? *)`

### Test 4: List Targets

```bash
aws events list-targets-by-rule \
  --rule daily-seo-reports \
  --region us-east-1
```

**Expected:** Lambda function listed as target

---

## 📊 What Gets Deployed?

### AWS Resources Created:

1. **Lambda Function**
   - Name: `search-console-daily-reports`
   - Runtime: Python 3.11
   - Memory: 1024 MB
   - Timeout: 15 minutes
   - Environment: All your .env variables

2. **IAM Role**
   - Name: `SearchConsoleAgentLambdaRole`
   - Permissions: Lambda execution + CloudWatch logs

3. **EventBridge Rule**
   - Name: `daily-seo-reports`
   - Schedule: `cron(0 8 * * ? *)`
   - Target: Lambda function

4. **CloudWatch Log Group**
   - Auto-created: `/aws/lambda/search-console-daily-reports`
   - Retention: Forever (you can change this)

### What Stays Local:

- ✅ PostgreSQL database
- ✅ Backend API (for on-demand reports)
- ✅ Frontend (for user interaction)

**Why?** Keep risk low, deploy what's needed for the challenge.

---

## 💰 Cost Estimate

### Free Tier (First 12 months):
- Lambda: 1M requests/month free
- EventBridge: Always free
- CloudWatch: 5GB logs/month free

**Your usage:**
- Lambda: ~30 invocations/month (once per day)
- CloudWatch: ~50MB logs/month

**Cost: $0.00/month** ✅

### After Free Tier:
- Lambda: $0.20/1M requests = ~$0.01/month
- CloudWatch: $0.50/GB = ~$0.03/month

**Total: ~$0.04/month** (basically free!)

---

## 🐛 Common Issues & Fixes

### Issue: "Access Denied" when deploying

**Solution:**
```bash
# Check your AWS credentials
aws sts get-caller-identity

# If wrong account, reconfigure
aws configure
```

### Issue: Lambda package too large

**Solution:**
```bash
# The script handles this, but if manual:
# Use Lambda Layers for dependencies
mkdir python
pip install -r requirements.txt -t python/
zip -r layer.zip python/

aws lambda publish-layer-version \
  --layer-name search-console-deps \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11
```

### Issue: Lambda can't connect to database

**Expected!** Your local database isn't publicly accessible.

**Quick fix for testing:**
```bash
# Option A: Use ngrok (recommended for testing)
ngrok tcp 5433

# Use the ngrok URL in Lambda DATABASE_URL
# Update via AWS Console or CLI
```

**Proper fix:** Deploy RDS (Phase 2) - not required for challenge

### Issue: Lambda timeout

**Solution:**
```bash
aws lambda update-function-configuration \
  --function-name search-console-daily-reports \
  --timeout 900
```

### Issue: Environment variables not set

**Solution:**
```bash
# Check variables
aws lambda get-function-configuration \
  --function-name search-console-daily-reports \
  --query Environment

# Update if needed - the script handles this
```

---

## 📝 For Your Article

After deployment, you can say:

### Architecture

> "The application runs on **AWS Lambda**, triggered daily by **AWS EventBridge** at 8 AM UTC. The Lambda function connects to the database, fetches user sites from Google Search Console API, generates AI-powered insights using Mistral, and delivers reports via email. **CloudWatch** provides comprehensive logging and monitoring."

### AWS Services

✅ **AWS Lambda** - Serverless compute for scheduled report generation
✅ **AWS EventBridge** - Cron-based scheduling (daily at 8 AM UTC)
✅ **CloudWatch** - Logging, monitoring, and metrics

### Deployment

> "Deployment is automated via a bash script that packages the application, creates necessary IAM roles, deploys the Lambda function with all environment variables, and configures EventBridge to trigger daily. The entire deployment takes ~5 minutes."

---

## 🎯 Success Criteria

After deployment:
- ✅ Lambda function in AWS Console
- ✅ EventBridge rule enabled
- ✅ Email received from Lambda test
- ✅ CloudWatch logs visible
- ✅ No errors in logs
- ✅ Ready for daily execution

---

## 📸 Screenshots for Article

Take these screenshots:

1. **AWS Lambda Console** - Your function
2. **EventBridge Rule** - Daily schedule
3. **CloudWatch Logs** - Successful execution
4. **Email Inbox** - Report received
5. **Lambda Test Result** - Success response

---

## 🎉 Ready to Deploy?

### Final Check:
- [ ] AWS CLI configured
- [ ] All local tests passing
- [ ] .env file complete
- [ ] Email service working

### Deploy:
```bash
./deploy_to_aws.sh
```

### After Deployment:
- [ ] Lambda test successful
- [ ] Email received
- [ ] CloudWatch logs visible
- [ ] EventBridge rule enabled
- [ ] Screenshots taken

### Submit:
- [ ] Complete article with screenshots
- [ ] Publish on AWS Builder Center
- [ ] Win AWS Builder Jacket! 🧥

---

**Let's deploy and win that jacket! 🚀**
