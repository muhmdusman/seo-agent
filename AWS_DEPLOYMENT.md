  # AWS Deployment Guide - Search Console Agent

Complete guide to deploy the Search Console Agent with automated daily SEO reports on AWS.

## 🏗️ Architecture Overview

```
┌─────────────────────┐
│  AWS EventBridge    │ ──(Daily 8AM UTC)──┐
│  (Cron Scheduler)   │                    │
└─────────────────────┘                    ▼
                                   ┌───────────────────┐
┌─────────────────────┐            │   AWS Lambda      │
│   Web3Forms API     │◄───────────│  Daily Reports    │
│   (Email Delivery)  │            └─────────┬─────────┘
└─────────────────────┘                      │
                                            │
                                            ▼
                                   ┌────────────────────┐
                                   │   AWS RDS          │
                                   │   PostgreSQL       │
                                   └────────────────────┘
                                            ▲
                                            │
┌─────────────────────┐            ┌───────┴────────┐
│   Users / Browsers  │◄───────────│  FastAPI       │
└─────────────────────┘            │  Backend       │
                                   │  (EC2/EB)      │
                                   └────────────────┘
                                            ▲
                                            │
                                   ┌────────┴────────┐
                                   │  Next.js        │
                                   │  Frontend       │
                                   │  (Amplify/S3)   │
                                   └─────────────────┘
```

## 📋 Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Python 3.11+
- Docker (for local testing)
- Google Cloud OAuth credentials
- Web3Forms API key: `aa8d5796-e26a-43cf-8976-0a468971c727`

## 🚀 Step-by-Step Deployment

### Step 1: Set Up AWS RDS PostgreSQL

1. **Create RDS Instance:**
   ```bash
   aws rds create-db-instance \
     --db-instance-identifier search-console-db \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --engine-version 17.2 \
     --master-username postgres \
     --master-user-password YOUR_STRONG_PASSWORD \
     --allocated-storage 20 \
     --backup-retention-period 7 \
     --publicly-accessible \
     --vpc-security-group-ids sg-YOUR_SECURITY_GROUP \
     --region us-east-1
   ```

2. **Configure Security Group:**
   - Allow inbound PostgreSQL (port 5432) from Lambda and EC2
   - Add your IP for database migrations

3. **Get Database Endpoint:**
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier search-console-db \
     --query 'DBInstances[0].Endpoint.Address' \
     --output text
   ```

4. **Update DATABASE_URL:**
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/app_db
   ```

5. **Run Migrations:**
   ```bash
   cd backend
   uv run alembic upgrade head
   ```

### Step 2: Create IAM Role for Lambda

1. **Create Trust Policy (`lambda-trust-policy.json`):**
   ```json
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
   ```

2. **Create IAM Role:**
   ```bash
   aws iam create-role \
     --role-name search-console-lambda-role \
     --assume-role-policy-document file://lambda-trust-policy.json
   ```

3. **Attach Policies:**
   ```bash
   # Basic Lambda execution
   aws iam attach-role-policy \
     --role-name search-console-lambda-role \
     --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
   
   # VPC access (if RDS is in VPC)
   aws iam attach-role-policy \
     --role-name search-console-lambda-role \
     --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
   ```

4. **Get Role ARN:**
   ```bash
   aws iam get-role \
     --role-name search-console-lambda-role \
     --query 'Role.Arn' \
     --output text
   ```

### Step 3: Deploy Lambda Function

1. **Generate requirements.txt:**
   ```bash
   cd backend
   uv pip compile pyproject.toml -o requirements.txt
   ```

2. **Create Lambda Layer (for dependencies):**
   ```bash
   mkdir -p lambda-layer/python
   pip install -r requirements.txt -t lambda-layer/python/
   cd lambda-layer
   zip -r ../lambda-layer.zip python/
   cd ..
   
   aws lambda publish-layer-version \
     --layer-name search-console-dependencies \
     --description "Dependencies for Search Console Agent" \
     --zip-file fileb://lambda-layer.zip \
     --compatible-runtimes python3.11 \
     --region us-east-1
   ```

3. **Package Application Code:**
   ```bash
   cd backend
   zip -r lambda-code.zip \
     lambda_handler.py \
     agents/ \
     api/ \
     core/ \
     db/ \
     models/ \
     schemas/ \
     services/ \
     tools/ \
     -x "**/__pycache__/*" "**/*.pyc"
   ```

4. **Create Lambda Function:**
   ```bash
   aws lambda create-function \
     --function-name search-console-daily-reports \
     --runtime python3.11 \
     --role arn:aws:iam::YOUR_ACCOUNT_ID:role/search-console-lambda-role \
     --handler lambda_handler.lambda_handler \
     --zip-file fileb://lambda-code.zip \
     --timeout 900 \
     --memory-size 512 \
     --region us-east-1 \
     --layers arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:layer:search-console-dependencies:1
   ```

5. **Set Environment Variables:**
   ```bash
   aws lambda update-function-configuration \
     --function-name search-console-daily-reports \
     --environment Variables="{
       APP_NAME=Search Console Agent,
       DEBUG=false,
       DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@RDS_ENDPOINT:5432/app_db,
       GOOGLE_CLIENT_ID=YOUR_CLIENT_ID,
       GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET,
       GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback,
       JWT_SECRET=YOUR_JWT_SECRET,
       JWT_ALGORITHM=HS256,
       ACCESS_TOKEN_EXPIRE_MINUTES=60,
       APP_URL=https://your-domain.com,
       FRONTEND_URL=https://your-frontend.com,
       MISTRAL_API_KEY=YOUR_MISTRAL_KEY,
       REFRESH_TOKEN_EXPIRY_DAYS=7,
       WEB3FORMS_ACCESS_KEY=aa8d5796-e26a-43cf-8976-0a468971c727,
       SCHEDULER_ENABLED=true,
       DAILY_REPORT_TIME=08:00,
       ADMIN_EMAIL=admin@yourdomain.com
     }" \
     --region us-east-1
   ```

### Step 4: Create EventBridge Schedule

1. **Create EventBridge Rule:**
   ```bash
   aws events put-rule \
     --name daily-seo-reports \
     --schedule-expression "cron(0 8 * * ? *)" \
     --description "Trigger daily SEO report generation at 8 AM UTC" \
     --region us-east-1
   ```

2. **Add Lambda Permission:**
   ```bash
   aws lambda add-permission \
     --function-name search-console-daily-reports \
     --statement-id AllowEventBridgeInvoke \
     --action lambda:InvokeFunction \
     --principal events.amazonaws.com \
     --source-arn arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/daily-seo-reports \
     --region us-east-1
   ```

3. **Set Target:**
   ```bash
   aws events put-targets \
     --rule daily-seo-reports \
     --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:search-console-daily-reports" \
     --region us-east-1
   ```

### Step 5: Deploy Backend API

#### Option A: AWS Elastic Beanstalk (Recommended)

1. **Install EB CLI:**
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB:**
   ```bash
   cd backend
   eb init -p python-3.11 search-console-agent --region us-east-1
   ```

3. **Create Environment:**
   ```bash
   eb create search-console-prod \
     --database.engine postgres \
     --database.size 5 \
     --database.instance db.t3.micro
   ```

4. **Configure Environment Variables:**
   ```bash
   eb setenv \
     APP_NAME="Search Console Agent" \
     DATABASE_URL="postgresql+psycopg://..." \
     GOOGLE_CLIENT_ID="..." \
     # ... (all env vars)
   ```

5. **Deploy:**
   ```bash
   eb deploy
   ```

#### Option B: AWS EC2 with Docker

1. **Launch EC2 Instance** (t2.micro for Free Tier)
2. **Install Docker & Docker Compose**
3. **Clone repo and configure .env**
4. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

### Step 6: Deploy Frontend

#### Using AWS Amplify

1. **Connect GitHub Repository:**
   - Go to AWS Amplify Console
   - Connect your GitHub repo
   - Select the `frontend` directory

2. **Configure Build Settings:**
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
     cache:
       paths:
         - frontend/node_modules/**/*
   ```

3. **Set Environment Variables:**
   - `NEXT_PUBLIC_API_BASE_URL`: Your backend URL

4. **Deploy:**
   - Amplify auto-deploys on push to main

## 🧪 Testing

### Test Email Service

```bash
# Local test
curl -X POST http://localhost:8000/api/v1/scheduler/test-email

# Production test
curl -X POST https://your-api.com/api/v1/scheduler/test-email
```

### Manual Trigger Daily Reports

```bash
# Local
curl -X POST http://localhost:8000/api/v1/scheduler/trigger

# Production
curl -X POST https://your-api.com/api/v1/scheduler/trigger
```

### Test Lambda Function

```bash
aws lambda invoke \
  --function-name search-console-daily-reports \
  --region us-east-1 \
  output.json

cat output.json
```

## 📊 Monitoring

### CloudWatch Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/search-console-daily-reports --follow

# View recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/search-console-daily-reports \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics

- Lambda invocations
- Lambda errors
- Lambda duration
- RDS connections
- Custom metrics (report success rate)

## 💰 Cost Estimation (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| AWS Lambda | 30 invocations/month, 5 min avg | ~$0.00 (Free Tier) |
| AWS RDS (t3.micro) | 720 hours/month | ~$13.00 |
| AWS Elastic Beanstalk | t2.micro, 720 hours | ~$8.50 |
| AWS Amplify | Hosting | ~$0.15/GB |
| Data Transfer | 10GB/month | ~$0.90 |
| **Total** | | **~$22.55/month** |

**Free Tier eligible for 12 months:** ~$0/month

## 🔒 Security Best Practices

1. **Secrets Management:**
   ```bash
   # Store sensitive variables in AWS Secrets Manager
   aws secretsmanager create-secret \
     --name search-console/database \
     --secret-string '{"url":"postgresql://..."}'
   ```

2. **VPC Configuration:**
   - Place RDS in private subnet
   - Lambda in VPC with NAT gateway for internet access

3. **IAM Least Privilege:**
   - Only grant necessary permissions
   - Use separate roles for Lambda, EC2, and RDS

4. **Encryption:**
   - Enable RDS encryption at rest
   - Use SSL/TLS for database connections
   - Enable S3 encryption for artifacts

## 🐛 Troubleshooting

### Lambda Timeout
- Increase timeout in Lambda configuration
- Optimize database queries
- Process sites in batches

### Database Connection Issues
- Check security group rules
- Verify VPC configuration
- Test connection from Lambda

### Email Not Sending
- Verify Web3Forms API key
- Check Lambda logs for errors
- Test with `/scheduler/test-email` endpoint

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS RDS Documentation](https://docs.aws.amazon.com/rds/)
- [AWS EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [Web3Forms API Documentation](https://web3forms.com/docs)

## 🎯 Next Steps

1. Set up monitoring and alerting
2. Add user preferences for report frequency
3. Implement report history tracking
4. Add support for weekly/monthly reports
5. Create admin dashboard for scheduler management

---

Built for the AWS Weekend Challenge 🏆
