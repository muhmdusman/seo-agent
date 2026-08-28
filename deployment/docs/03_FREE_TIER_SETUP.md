# 🆓 AWS Free Tier / Low-Cost Architecture

## Your Requirements
- ✅ Personal use (low traffic)
- ✅ AWS Free Tier credits
- ✅ Scheduler runs once daily
- ✅ No load balancer needed
- ✅ Cost optimization priority

---

## 🎯 Optimized Architecture (Minimal Cost)

```
┌─────────────────────────────────────────────────────────────┐
│              Free Tier Optimized Architecture                │
│                                                              │
│  Frontend (Amplify - FREE TIER)                             │
│         ↓                                                    │
│  ┌──────────────────────────────────────────┐              │
│  │   ECS Fargate (Single Task)              │              │
│  │   - FastAPI Backend (Public IP)          │              │
│  │   - Port 8000 exposed                     │              │
│  └──────────────────────────────────────────┘              │
│         ↓                    ↓                               │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │     RDS      │    │    Redis     │                       │
│  │ db.t3.micro  │    │   (Docker)   │ ← Same ECS Task      │
│  │  FREE TIER   │    │   FREE!      │                       │
│  └──────────────┘    └──────────────┘                      │
│         ↓                                                    │
│  ┌──────────────────────────────────────────┐              │
│  │ EventBridge → ECS Task (Run Daily)       │              │
│  │ Daily report - Celery worker runs once   │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 💰 Cost Breakdown (With Free Tier)

### Monthly Costs:

```
✅ AWS Free Tier (12 months):
   - RDS db.t3.micro: 750 hours/month     = $0 (FREE)
   - ECS Fargate: 20 GB storage           = $0 (FREE)
   - Data transfer: 15 GB out             = $0 (FREE)
   
💵 Paid Services:
   - ECS Fargate (0.25 vCPU, 0.5GB RAM):
     24/7 = 720 hours × $0.04048          = ~$29/month
   
   - ElastiCache Redis (SKIP IT!):
     Run Redis in same container          = $0 (FREE!)
   
   - EventBridge scheduler                = $0 (FREE)
   
   - Amplify (already deployed)           = $0 (FREE tier)
   
─────────────────────────────────────────────────
Total Cost = $29/month (or $0 with free tier credits!)
─────────────────────────────────────────────────

💡 With AWS Free Tier Credits = $0/month for first year!
💡 After free tier = $29/month
```

---

## 🔥 Cost Optimization Strategies

### 1. **Skip Load Balancer** (Save $17/month)
- ✅ Assign **public IP** directly to ECS task
- ✅ Access backend via: `http://PUBLIC_IP:8000`
- ✅ Frontend calls backend directly
- ⚠️ IP changes on redeploy (use Route53 or hardcode in env)

### 2. **Run Redis in Same Container** (Save $15/month)
- ✅ Bundle Redis with FastAPI in single Docker image
- ✅ Use docker-compose to start both
- ✅ Perfect for low traffic
- ⚠️ Redis data lost on restart (fine for cache/queue)

### 3. **Skip Celery Worker Service** (Save $29/month)
- ✅ Run Celery worker in same container as FastAPI
- ✅ Use supervisor or run both processes
- ✅ For daily tasks, it's enough
- ⚠️ Less scalable (fine for personal use)

### 4. **Use Smallest ECS Task** (Save $20/month)
- ✅ 0.25 vCPU, 0.5 GB RAM (minimum)
- ✅ Enough for FastAPI + Redis + Celery
- ✅ Upgrade if needed later

### 5. **RDS Free Tier** (Save $15/month first year)
- ✅ db.t3.micro (20GB storage)
- ✅ 750 hours/month free
- ✅ Single-AZ only (no multi-AZ needed)

---

## 🏗️ Final Recommended Architecture

### **Option A: All-in-One Container** (CHEAPEST - $0 with free tier)

```yaml
Single ECS Fargate Task:
  - FastAPI backend (port 8000)
  - Redis (in same container)
  - Celery worker (in same container)
  - Public IP assigned
  
Cost: $29/month (or $0 with free tier)
```

**Dockerfile structure:**
```dockerfile
FROM python:3.11-slim

# Install Redis
RUN apt-get update && apt-get install -y redis-server

# Copy app
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

# Start script runs all services
CMD ["./start-all.sh"]
```

**start-all.sh:**
```bash
#!/bin/bash
redis-server --daemonize yes
celery -A core.celery_app worker --loglevel=info &
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### **Option B: Two Containers** (BETTER SEPARATION - $58/month)

```yaml
ECS Task 1: FastAPI + Redis
  - 0.25 vCPU, 0.5 GB RAM
  - Public IP
  - Cost: $29/month

ECS Task 2: Celery Worker
  - 0.25 vCPU, 0.5 GB RAM
  - No public IP
  - Cost: $29/month
  
Total: $58/month (or $29 with free tier for 1 task)
```

---

## 🎯 My Recommendation for Your Use Case

### **Go with Option A: All-in-One Container**

**Why?**
1. ✅ **$0 with AWS free tier credits**
2. ✅ **$29/month after free tier** (vs $60+ for separated)
3. ✅ **Perfect for personal use / low traffic**
4. ✅ **One container = simple deployment**
5. ✅ **No load balancer needed**
6. ✅ **Redis included (no ElastiCache cost)**
7. ✅ **GitHub Actions still works**

**Trade-offs:**
- ⚠️ All services in one container (less scalable)
- ⚠️ Redis data lost on restart (fine for cache/queue)
- ⚠️ IP changes on redeploy (use env variable in frontend)

**For your use case (personal use, daily scheduler), this is PERFECT!**

---

## 📦 Implementation Plan

### Phase 1: Create Dockerfile (All-in-One)

**File: `Dockerfile`**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install uv && uv pip install --system -r pyproject.toml

# Copy application
COPY backend/ .

# Create supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port
EXPOSE 8000

# Run supervisor (manages all services)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

**File: `supervisord.conf`**
```ini
[supervisord]
nodaemon=true
user=root

[program:redis]
command=redis-server --bind 0.0.0.0 --port 6379
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:celery]
command=celery -A core.celery_app worker --loglevel=info
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:fastapi]
command=uvicorn main:app --host 0.0.0.0 --port 8000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

---

### Phase 2: AWS Setup

#### 1. Create RDS (Free Tier)
```bash
aws rds create-db-instance \
    --db-instance-identifier seo-agent-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 17.2 \
    --master-username postgres \
    --master-user-password YOUR_PASSWORD \
    --allocated-storage 20 \
    --backup-retention-period 0 \
    --publicly-accessible false \
    --no-multi-az
```

**Save:** Endpoint URL

#### 2. Create ECR Repository
```bash
aws ecr create-repository \
    --repository-name seo-agent-backend \
    --region us-east-1
```

#### 3. Build & Push Docker Image
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Build
docker build -t seo-agent-backend .

# Tag
docker tag seo-agent-backend:latest \
YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/seo-agent-backend:latest

# Push
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/seo-agent-backend:latest
```

#### 4. Create ECS Cluster
```bash
aws ecs create-cluster \
    --cluster-name seo-agent-cluster \
    --region us-east-1
```

#### 5. Create Task Definition

**File: `ecs-task-definition.json`**
```json
{
  "family": "seo-agent-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/seo-agent-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://postgres:PASSWORD@RDS_ENDPOINT:5432/app_db"},
        {"name": "REDIS_URL", "value": "redis://localhost:6379/0"},
        {"name": "GOOGLE_CLIENT_ID", "value": "your-client-id"},
        {"name": "GOOGLE_CLIENT_SECRET", "value": "your-client-secret"},
        {"name": "JWT_SECRET", "value": "your-jwt-secret"},
        {"name": "MISTRAL_API_KEY", "value": "your-mistral-key"},
        {"name": "FRONTEND_URL", "value": "https://your-amplify-url.amplifyapp.com"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/seo-agent-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register it:
```bash
aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition.json
```

#### 6. Create ECS Service (with Public IP)
```bash
aws ecs create-service \
    --cluster seo-agent-cluster \
    --service-name backend-service \
    --task-definition seo-agent-backend \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}"
```

**Important:** 
- Replace `subnet-xxxxx` with your VPC subnet
- Replace `sg-xxxxx` with security group (allow port 8000)
- `assignPublicIp=ENABLED` gives you a public IP!

#### 7. Get Public IP
```bash
aws ecs list-tasks --cluster seo-agent-cluster --service-name backend-service
aws ecs describe-tasks --cluster seo-agent-cluster --tasks TASK_ARN
```

Look for `publicIp` in the output!

---

### Phase 3: Setup Scheduler (Daily Reports)

#### Create EventBridge Rule
```bash
# Create rule (runs daily at 8 AM UTC)
aws events put-rule \
    --name seo-agent-daily-report \
    --schedule-expression "cron(0 8 * * ? *)" \
    --state ENABLED

# Add ECS task as target
aws events put-targets \
    --rule seo-agent-daily-report \
    --targets '[
      {
        "Id": "1",
        "Arn": "arn:aws:ecs:us-east-1:ACCOUNT:cluster/seo-agent-cluster",
        "RoleArn": "arn:aws:iam::ACCOUNT:role/ecsEventsRole",
        "EcsParameters": {
          "TaskDefinitionArn": "arn:aws:ecs:us-east-1:ACCOUNT:task-definition/seo-agent-backend",
          "TaskCount": 1,
          "LaunchType": "FARGATE",
          "NetworkConfiguration": {
            "awsvpcConfiguration": {
              "Subnets": ["subnet-xxxxx"],
              "SecurityGroups": ["sg-xxxxx"],
              "AssignPublicIp": "ENABLED"
            }
          }
        }
      }
    ]'
```

---

### Phase 4: GitHub Actions

**File: `.github/workflows/deploy-ecs.yml`**
```yaml
name: Deploy to ECS Fargate

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: seo-agent-backend
  ECS_CLUSTER: seo-agent-cluster
  ECS_SERVICE: backend-service
  ECS_TASK_DEFINITION: seo-agent-backend

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build, tag, and push image to Amazon ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
      
      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --force-new-deployment
```

---

### Phase 5: Update Frontend

In Amplify environment variables, set:
```
NEXT_PUBLIC_API_BASE_URL=http://YOUR_PUBLIC_IP:8000/api/v1
```

**Note:** IP changes on redeploy. Solutions:
1. Use AWS Route53 to map domain to IP (costs $0.50/month)
2. Use Elastic IP (free if attached, $0.005/hour if not)
3. Update manually after redeploy (free, simple for personal use)

---

## 🎉 Total Setup Time

1. Create RDS: 10 minutes
2. Create Dockerfile: 15 minutes
3. Setup ECS: 20 minutes
4. GitHub Actions: 10 minutes
5. Scheduler: 10 minutes

**Total: ~65 minutes**

---

## 📊 Cost Summary (Final)

### With AWS Free Tier (First 12 Months):
```
RDS db.t3.micro              = $0 (FREE)
ECS Fargate (0.25/0.5)       = $0 (20 GB storage free)
Data transfer (15 GB)        = $0 (FREE)
EventBridge                  = $0 (FREE)
Amplify                      = $0 (FREE)
────────────────────────────────────
Total                        = $0/month 🎉
```

### After Free Tier:
```
RDS db.t3.micro              = $15
ECS Fargate                  = $29
Data transfer                = $2
────────────────────────────────────
Total                        = $46/month
```

**vs Original Architecture with Load Balancer:**
- Original: $64-72/month
- Optimized: $29-46/month
- **Savings: $25-35/month (35-54% cheaper!)**

---

## ✅ Checklist

- [ ] Create RDS PostgreSQL (db.t3.micro, free tier)
- [ ] Create ECR repository
- [ ] Create Dockerfile with supervisor (Redis + Celery + FastAPI)
- [ ] Build and push Docker image
- [ ] Create ECS cluster
- [ ] Create task definition
- [ ] Create ECS service with public IP
- [ ] Get public IP and save it
- [ ] Create EventBridge rule for daily scheduler
- [ ] Setup GitHub Actions workflow
- [ ] Update Amplify environment variables
- [ ] Test deployment!

---

**Ready to implement? This is the cheapest, simplest setup for your use case!**
