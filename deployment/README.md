# 📦 Deployment Guide

Complete AWS deployment setup for Search Console Agent.

---

## 📁 Folder Structure

```
deployment/
├── README.md                          # This file - start here!
│
├── docs/                              # Documentation
│   ├── 01_QUICK_START.md             # Quick start guide
│   ├── 02_ARCHITECTURE_OPTIONS.md    # Compare deployment options
│   ├── 03_FREE_TIER_SETUP.md         # Free tier optimized setup
│   ├── 04_BEDROCK_MIGRATION.md       # Switch from Mistral to Bedrock
│   └── 05_TROUBLESHOOTING.md         # Common issues & solutions
│
├── docker/                            # Docker configurations
│   ├── Dockerfile                     # Main application container
│   ├── Dockerfile.worker              # Celery worker (if separate)
│   ├── supervisord.conf               # Process manager config
│   └── docker-compose.local.yml       # Local development
│
├── ecs/                               # ECS Fargate configurations
│   ├── task-definition.json          # ECS task definition
│   ├── service-definition.json       # ECS service definition
│   └── iam-policies/                  # IAM roles & policies
│       ├── task-role-policy.json
│       ├── execution-role-policy.json
│       └── bedrock-policy.json
│
└── scripts/                           # Deployment scripts
    ├── setup-aws.sh                   # Setup AWS infrastructure
    ├── build-and-push.sh              # Build & push to ECR
    ├── deploy-ecs.sh                  # Deploy to ECS
    └── cleanup.sh                     # Cleanup resources
```

---

## 🚀 Quick Start (5 Steps)

### 1. **Read the Architecture Guide**
```bash
cat deployment/docs/01_QUICK_START.md
```

### 2. **Setup AWS Infrastructure**
```bash
chmod +x deployment/scripts/setup-aws.sh
./deployment/scripts/setup-aws.sh
```

### 3. **Build & Push Docker Image**
```bash
chmod +x deployment/scripts/build-and-push.sh
./deployment/scripts/build-and-push.sh
```

### 4. **Deploy to ECS**
```bash
chmod +x deployment/scripts/deploy-ecs.sh
./deployment/scripts/deploy-ecs.sh
```

### 5. **Update Frontend Environment**
```bash
# Get ECS public IP from AWS Console
# Update Amplify: NEXT_PUBLIC_API_BASE_URL=http://YOUR_IP:8000/api/v1
```

**Done! 🎉**

---

## 📖 Documentation Order

Read these in order:

1. **01_QUICK_START.md** - Start here! 10-minute overview
2. **02_ARCHITECTURE_OPTIONS.md** - Understand deployment choices
3. **03_FREE_TIER_SETUP.md** - Step-by-step deployment ($0 with free tier)
4. **04_BEDROCK_MIGRATION.md** - (Optional) Switch to AWS Bedrock
5. **05_TROUBLESHOOTING.md** - Fix common issues

---

## 💰 Cost Summary

### With AWS Free Tier (First 12 Months):
```
RDS db.t3.micro              = $0 (FREE)
ECS Fargate (0.25/0.5)       = $0 (FREE - 20 GB storage)
Data transfer                = $0 (FREE - 15 GB)
EventBridge                  = $0 (FREE)
Amplify                      = $0 (FREE)
Bedrock Nova Lite            = $1-2/month
────────────────────────────────────
Total                        = $1-2/month 🎉
```

### After Free Tier:
```
RDS db.t3.micro              = $15
ECS Fargate                  = $29
Data transfer                = $2
Bedrock Nova Lite            = $1-2
────────────────────────────────────
Total                        = $47-49/month
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              AWS Free Tier Architecture                  │
│                                                          │
│  Frontend (Amplify - Already Deployed)                  │
│         ↓                                                │
│  ┌──────────────────────────────────────┐              │
│  │   ECS Fargate (Single Container)     │              │
│  │   Public IP: http://X.X.X.X:8000     │              │
│  │                                       │              │
│  │   ├─ FastAPI Backend                 │              │
│  │   ├─ Redis Cache                     │              │
│  │   └─ Celery Worker                   │              │
│  └──────────────────────────────────────┘              │
│         ↓                    ↓                           │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │     RDS      │    │   Bedrock    │                  │
│  │ PostgreSQL   │    │  Nova Lite   │                  │
│  │  FREE TIER   │    │  $1-2/month  │                  │
│  └──────────────┘    └──────────────┘                  │
│         ↓                                                │
│  ┌──────────────────────────────────────┐              │
│  │ EventBridge → ECS Task (Daily)       │              │
│  │ Scheduled Reports (8 AM UTC)         │              │
│  └──────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Deployment Checklist

### Prerequisites
- [ ] AWS Account with free tier credits
- [ ] AWS CLI installed: `aws --version`
- [ ] Docker installed: `docker --version`
- [ ] GitHub Actions secrets configured

### AWS Infrastructure
- [ ] RDS PostgreSQL created (db.t3.micro)
- [ ] ECR repository created
- [ ] ECS cluster created
- [ ] Security groups configured
- [ ] IAM roles created (task + execution roles)

### Docker & ECS
- [ ] Dockerfile created
- [ ] Docker image built locally
- [ ] Image pushed to ECR
- [ ] ECS task definition registered
- [ ] ECS service created with public IP

### Scheduler
- [ ] EventBridge rule created (daily cron)
- [ ] ECS scheduled task configured
- [ ] IAM permissions for EventBridge

### Frontend
- [ ] Amplify environment variable updated
- [ ] Frontend redeployed

### Testing
- [ ] Backend health check: `http://PUBLIC_IP:8000/health`
- [ ] OAuth login works
- [ ] Analysis generation works
- [ ] Daily scheduler runs

---

## 🔧 Useful Commands

### Docker
```bash
# Build image
docker build -t seo-agent-backend -f deployment/docker/Dockerfile .

# Run locally
docker run -p 8000:8000 --env-file .env seo-agent-backend

# Test locally
curl http://localhost:8000/health
```

### AWS ECR
```bash
# Login
aws ecr get-login-password --region us-east-1 | \
docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Push
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/seo-agent-backend:latest
```

### ECS
```bash
# Deploy
aws ecs update-service --cluster seo-agent-cluster --service backend-service --force-new-deployment

# Check status
aws ecs describe-services --cluster seo-agent-cluster --services backend-service

# View logs
aws logs tail /ecs/seo-agent-backend --follow
```

### RDS
```bash
# Connect
psql postgresql://postgres:PASSWORD@RDS_ENDPOINT:5432/app_db

# Check connections
psql -c "SELECT * FROM pg_stat_activity;"
```

---

## 🐛 Troubleshooting

### Issue: Container won't start
```bash
# Check logs
aws logs tail /ecs/seo-agent-backend --follow

# Common causes:
# - Missing environment variables
# - Database connection failed
# - Port already in use
```

### Issue: Can't connect to backend
```bash
# Check security group
# - Port 8000 must be open
# - Source: 0.0.0.0/0 (or your IP)

# Check public IP
aws ecs describe-tasks --cluster seo-agent-cluster --tasks TASK_ARN
```

### Issue: Database connection failed
```bash
# Check security group
# - RDS security group must allow ECS security group
# - Port 5432 inbound from ECS

# Test connection
psql "postgresql://postgres:PASSWORD@RDS_ENDPOINT:5432/app_db"
```

**Full troubleshooting guide:** `docs/05_TROUBLESHOOTING.md`

---

## 📚 Additional Resources

- [AWS Free Tier](https://aws.amazon.com/free/)
- [ECS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [GitHub Actions for AWS](https://github.com/aws-actions)

---

## 🆘 Need Help?

1. Check `docs/05_TROUBLESHOOTING.md`
2. Check CloudWatch logs
3. Review ECS task events
4. Check security group rules

---

**Ready to deploy? Start with `docs/01_QUICK_START.md`!** 🚀
