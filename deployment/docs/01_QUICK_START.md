# ⚡ Quick Start - Deploy in 30 Minutes

Get your Search Console Agent running on AWS with free tier credits!

---

## 🎯 What You'll Deploy

```
Single ECS Fargate Container:
├─ FastAPI Backend (Python 3.11)
├─ Redis Cache (in-memory)
└─ Celery Worker (background tasks)

Cost: $0/month with AWS free tier! 🎉
```

---

## ⏱️ Time Breakdown

- Prerequisites: 5 minutes
- AWS Setup: 10 minutes
- Docker Build: 5 minutes
- Deploy: 5 minutes
- Testing: 5 minutes

**Total: 30 minutes**

---

## 📋 Prerequisites

### 1. AWS Account
- Sign up: https://aws.amazon.com/free/
- Free tier: 12 months of free services

### 2. Install Tools
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version

# Configure
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (us-east-1)
```

### 3. Docker (if not installed)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify
docker --version
```

---

## 🚀 Deployment Steps

### Step 1: Create RDS Database (5 min)

```bash
# Create PostgreSQL database (free tier)
aws rds create-db-instance \
    --db-instance-identifier seo-agent-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 17.2 \
    --master-username postgres \
    --master-user-password "YourStrongPassword123!" \
    --allocated-storage 20 \
    --backup-retention-period 0 \
    --publicly-accessible false \
    --no-multi-az \
    --region us-east-1

# Wait for database to be ready (5 minutes)
aws rds wait db-instance-available --db-instance-identifier seo-agent-db

# Get endpoint
aws rds describe-db-instances \
    --db-instance-identifier seo-agent-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

**Save the endpoint!** Example: `seo-agent-db.xxxxx.us-east-1.rds.amazonaws.com`

---

### Step 2: Run Setup Script (5 min)

```bash
cd deployment/scripts

# Make executable
chmod +x setup-aws.sh

# Run setup (creates ECR, ECS cluster, security groups)
./setup-aws.sh
```

This script creates:
- ✅ ECR repository for Docker images
- ✅ ECS Fargate cluster
- ✅ Security groups (ECS + RDS)
- ✅ IAM roles (task + execution)

---

### Step 3: Build & Push Docker Image (5 min)

```bash
# Update environment variables in deployment/docker/.env.production
# Then run:
chmod +x build-and-push.sh
./build-and-push.sh
```

This script:
- ✅ Builds Docker image with FastAPI + Redis + Celery
- ✅ Tags image
- ✅ Pushes to ECR

---

### Step 4: Deploy to ECS (5 min)

```bash
chmod +x deploy-ecs.sh
./deploy-ecs.sh
```

This script:
- ✅ Creates ECS task definition
- ✅ Creates ECS service with public IP
- ✅ Starts container

---

### Step 5: Get Public IP (1 min)

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
    --cluster seo-agent-cluster \
    --service-name backend-service \
    --query 'taskArns[0]' \
    --output text)

# Get public IP
aws ecs describe-tasks \
    --cluster seo-agent-cluster \
    --tasks $TASK_ARN \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
    --output text | xargs -I {} aws ec2 describe-network-interfaces \
    --network-interface-ids {} \
    --query 'NetworkInterfaces[0].Association.PublicIp' \
    --output text
```

**Save this IP!** Example: `3.80.45.123`

---

### Step 6: Test Backend (2 min)

```bash
# Replace with your IP
export BACKEND_IP="3.80.45.123"

# Health check
curl http://$BACKEND_IP:8000/health

# Should return: {"status":"healthy"}
```

---

### Step 7: Update Frontend (2 min)

1. Go to AWS Amplify Console
2. Select your frontend app
3. Environment variables → Edit
4. Update: `NEXT_PUBLIC_API_BASE_URL=http://3.80.45.123:8000/api/v1`
5. Save and redeploy

---

### Step 8: Setup Daily Scheduler (5 min)

```bash
# Create EventBridge rule (runs daily at 8 AM UTC)
aws events put-rule \
    --name seo-agent-daily-report \
    --schedule-expression "cron(0 8 * * ? *)" \
    --state ENABLED

# Get ECS task definition ARN
TASK_DEF_ARN=$(aws ecs describe-task-definition \
    --task-definition seo-agent-backend \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

# Get subnet ID
SUBNET_ID=$(aws ec2 describe-subnets \
    --query 'Subnets[0].SubnetId' \
    --output text)

# Get security group ID
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=ecs-tasks-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# Add ECS task as target
aws events put-targets \
    --rule seo-agent-daily-report \
    --targets "Id=1,Arn=arn:aws:ecs:us-east-1:$(aws sts get-caller-identity --query Account --output text):cluster/seo-agent-cluster,RoleArn=arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsEventsRole,EcsParameters={TaskDefinitionArn=$TASK_DEF_ARN,TaskCount=1,LaunchType=FARGATE,NetworkConfiguration={awsvpcConfiguration={Subnets=[$SUBNET_ID],SecurityGroups=[$SG_ID],AssignPublicIp=ENABLED}}}"
```

---

## ✅ Verify Deployment

### 1. Backend Health
```bash
curl http://YOUR_IP:8000/health
# Expected: {"status":"healthy"}
```

### 2. Database Connection
```bash
curl http://YOUR_IP:8000/api/v1/health/db
# Expected: {"database":"connected"}
```

### 3. Frontend
- Visit: https://your-app.amplifyapp.com
- Try login with Google
- Test analysis generation

---

## 💰 Current Cost

```
✅ RDS (db.t3.micro)     = $0 (FREE TIER)
✅ ECS Fargate           = $0 (FREE TIER - 20 GB)
✅ Data Transfer         = $0 (FREE TIER - 15 GB)
✅ EventBridge           = $0 (FREE)
✅ Amplify               = $0 (FREE TIER)
─────────────────────────────────────────
Total: $0/month for first year! 🎉
```

---

## 🎉 You're Done!

Your app is now running on AWS with:
- ✅ FastAPI backend on ECS Fargate
- ✅ PostgreSQL on RDS
- ✅ Redis in-memory cache
- ✅ Celery background workers
- ✅ Daily scheduled reports
- ✅ Frontend on Amplify

---

## 🔄 Next Steps

1. **Add Custom Domain** (optional)
   - Route53: $0.50/month
   - Point domain to ECS public IP

2. **Enable HTTPS** (recommended)
   - Application Load Balancer + ACM certificate
   - Cost: +$17/month

3. **Switch to Bedrock** (optional)
   - See: `04_BEDROCK_MIGRATION.md`
   - Better performance, lower cost

4. **Setup Monitoring** (recommended)
   - CloudWatch dashboards (free)
   - Alarms for errors

---

## 🐛 Troubleshooting

**Container won't start?**
```bash
aws logs tail /ecs/seo-agent-backend --follow
```

**Can't connect to backend?**
- Check security group port 8000 is open
- Check public IP is correct

**Database connection failed?**
- Check RDS security group allows ECS
- Verify DATABASE_URL in task definition

**Full troubleshooting:** See `05_TROUBLESHOOTING.md`

---

## 📚 What's Next?

- Read `02_ARCHITECTURE_OPTIONS.md` to understand alternatives
- Read `03_FREE_TIER_SETUP.md` for detailed step-by-step
- Read `04_BEDROCK_MIGRATION.md` to switch AI models

---

**Congratulations! Your app is live on AWS!** 🚀
