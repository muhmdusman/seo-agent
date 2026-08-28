# 🚀 Deployment Summary

## ✅ What's Been Created

### 1. GitHub Actions Workflows
- `.github/workflows/deploy-backend.yml` - Auto-deploys backend to Elastic Beanstalk on push to `main`
- `.github/workflows/deploy-lambda.yml` - Auto-deploys Lambda function for scheduled reports

### 2. Lambda Function
- `lambda/daily_report_handler.py` - Scheduled daily report generation (not yet created)

### 3. Documentation
- `AWS_DEPLOYMENT_GUIDE.md` - Complete step-by-step deployment guide
- `DEPLOYMENT_SUMMARY.md` - This file

### 4. Git Repository
- ✅ Removed secrets from history (Mistral API key)
- ✅ Removed large deployment artifacts (191MB + 194MB ZIP files)
- ✅ Updated `.gitignore` to prevent future issues
- ✅ Pushed clean code to `scheduler` branch

---

## 📋 Next Steps to Deploy

### Step 1: Create RDS PostgreSQL Database

```bash
# Via AWS Console or CLI
aws rds create-db-instance \
    --db-instance-identifier seo-agent-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 17.2 \
    --master-username postgres \
    --master-user-password YOUR_STRONG_PASSWORD \
    --allocated-storage 20 \
    --db-name app_db \
    --publicly-accessible false
```

**Save these:**
- DB Endpoint: `seo-agent-db.xxxxx.us-east-1.rds.amazonaws.com`
- Password: (save securely)

---

### Step 2: Create Elastic Beanstalk Environment

```bash
cd backend

# Initialize EB
eb init -p python-3.11 seo-agent-backend --region us-east-1

# Generate requirements.txt
pip install uv
uv pip compile pyproject.toml -o requirements.txt

# Create environment with all env variables
eb create seo-agent-production \
    --instance-type t3.small \
    --envvars \
        DATABASE_URL="postgresql+psycopg://postgres:PASSWORD@RDS_ENDPOINT:5432/app_db",\
        REDIS_URL="redis://localhost:6379/0",\
        GOOGLE_CLIENT_ID="your-google-client-id",\
        GOOGLE_CLIENT_SECRET="your-google-client-secret",\
        GOOGLE_REDIRECT_URI="https://api.yourdomain.com/api/v1/auth/google/callback",\
        JWT_SECRET="your-jwt-secret",\
        MISTRAL_API_KEY="your-mistral-key",\
        FRONTEND_URL="https://yourdomain.com"
```

---

### Step 3: Setup GitHub Secrets

Go to **GitHub Repository → Settings → Secrets and variables → Actions**

Add these secrets:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
DATABASE_URL=postgresql://postgres:PASSWORD@RDS_ENDPOINT:5432/app_db
```

**To get AWS credentials:**
1. Go to AWS IAM Console
2. Create new user: `github-actions-deployer`
3. Attach policies: `AWSElasticBeanstalkFullAccess`, `AWSLambdaFullAccess`
4. Create access key → Copy to GitHub Secrets

---

### Step 4: Create Lambda Function for Scheduler

```bash
cd lambda

# Create handler file (we'll do this next)
# Package and deploy
mkdir -p package
pip install psycopg boto3 -t package/
cp daily_report_handler.py package/
cd package
zip -r ../daily_report_function.zip .

# Deploy to AWS
aws lambda create-function \
    --function-name seo-agent-daily-report \
    --runtime python3.11 \
    --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
    --handler daily_report_handler.lambda_handler \
    --zip-file fileb://daily_report_function.zip \
    --timeout 300 \
    --environment Variables="{DATABASE_URL=postgresql://...,API_BASE_URL=https://api.yourdomain.com}"
```

---

### Step 5: Create EventBridge Schedule

```bash
# Create rule for daily 8 AM UTC
aws events put-rule \
    --name seo-agent-daily-report \
    --schedule-expression "cron(0 8 * * ? *)" \
    --state ENABLED

# Add Lambda as target
aws events put-targets \
    --rule seo-agent-daily-report \
    --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:seo-agent-daily-report"

# Grant permission
aws lambda add-permission \
    --function-name seo-agent-daily-report \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com
```

---

### Step 6: Configure Amplify Frontend

1. **Go to AWS Amplify Console**
2. Already connected to your GitHub repo
3. Update build settings to use `amplify.yml` (already exists)
4. Add environment variable:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://your-eb-url.elasticbeanstalk.com/api/v1
   ```
5. Deploy!

---

### Step 7: Update Google OAuth Redirect URIs

In Google Cloud Console → APIs & Credentials → OAuth 2.0 Client IDs:

Add these redirect URIs:
```
https://your-eb-url.elasticbeanstalk.com/api/v1/auth/google/callback
https://yourdomain.com/api/v1/auth/google/callback
```

---

## 🔄 How GitHub Actions Works

### On Every Push to `main`:

1. **Backend Deployment** (if `backend/` files changed):
   - Compiles requirements.txt from pyproject.toml
   - Deploys to Elastic Beanstalk
   - Runs health check

2. **Lambda Deployment** (if `lambda/` files changed):
   - Packages Lambda function with dependencies
   - Updates Lambda function code
   - Verifies deployment

### Manual Triggers:
Both workflows support manual trigger via GitHub Actions UI

---

## 📊 Cost Estimate

| Service | Config | Monthly Cost |
|---------|--------|--------------|
| RDS PostgreSQL | db.t3.micro | ~$15 |
| Elastic Beanstalk | t3.small | ~$15 |
| Lambda | 1000 invokes/day | <$1 |
| EventBridge | 1 rule | Free |
| Amplify | Build + hosting | ~$5 |
| **Total** | | **~$36/month** |

---

## ⚠️ Important Notes

1. **Redis**: Currently configured for local Redis. For production, use **Amazon ElastiCache** or switch to Postgres-based task queue

2. **Celery**: Need to configure Celery on EB using `.ebextensions/03_celery.config` (already in guide)

3. **SSL**: Use AWS Certificate Manager (ACM) for free SSL certificates

4. **Domain**: Point your domain to:
   - Amplify for frontend
   - Elastic Beanstalk for API subdomain

5. **Secrets**: Never commit `.env` or API keys to git!

---

## 🐛 Troubleshooting

### EB deployment fails?
```bash
eb logs
eb ssh
eb status
```

### Lambda not triggering?
```bash
aws logs tail /aws/lambda/seo-agent-daily-report --follow
```

### Database connection fails?
- Check security group rules
- Verify DATABASE_URL format
- Test with: `psql $DATABASE_URL`

---

## 📚 Documentation References

- [Elastic Beanstalk Python Guide](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-apps.html)
- [Lambda with EventBridge](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents.html)
- [GitHub Actions for AWS](https://github.com/aws-actions)
- Full guide: `AWS_DEPLOYMENT_GUIDE.md`

---

**Ready to deploy?** Follow the steps above or refer to the full guide!
