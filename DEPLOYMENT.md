# 🚀 Deployment Guide

**Quick Link:** All deployment files are in the [`deployment/`](./deployment/) folder.

---

## 📁 What's Inside

```
deployment/
├── README.md                     # Start here!
├── docs/                         # Complete documentation
│   ├── 00_DEPLOYMENT_SUMMARY.md  # Overview
│   ├── 01_QUICK_START.md        # 30-minute setup guide
│   ├── 02_ARCHITECTURE_OPTIONS.md # Compare deployment options
│   ├── 03_FREE_TIER_SETUP.md    # Detailed step-by-step
│   ├── 04_BEDROCK_MIGRATION.md  # Switch to AWS Bedrock
│   └── 05_TROUBLESHOOTING.md    # Fix common issues
├── docker/                       # Docker configurations
│   ├── Dockerfile                # Production container
│   ├── supervisord.conf          # Process manager
│   └── .env.production.example   # Environment template
├── ecs/                          # AWS ECS configurations
│   └── task-definition.json      # ECS Fargate task
└── scripts/                      # Automation scripts
    └── setup-aws.sh              # Setup AWS infrastructure
```

---

## ⚡ Quick Start

### 1. Read the Guide
```bash
cat deployment/README.md
```

### 2. Setup AWS (10 minutes)
```bash
cd deployment/scripts
chmod +x setup-aws.sh
./setup-aws.sh
```

### 3. Build & Deploy
Follow the instructions in [`deployment/docs/01_QUICK_START.md`](./deployment/docs/01_QUICK_START.md)

---

## 🏗️ Architecture

**All-in-One Container (Optimized for Free Tier)**

```
ECS Fargate (Single Container):
├─ FastAPI Backend (port 8000)
├─ Redis Cache (in-memory)
└─ Celery Worker (background tasks)
     ↓
RDS PostgreSQL (db.t3.micro - FREE)
     ↓
AWS Bedrock (optional - $1-2/month)

Cost: $0/month with free tier! 🎉
After: $29-49/month
```

---

## 💰 Cost Breakdown

### With AWS Free Tier (First 12 Months):
- RDS db.t3.micro: **$0** (FREE)
- ECS Fargate: **$0** (FREE - 20 GB storage)
- Data transfer: **$0** (FREE - 15 GB)
- Bedrock Nova Lite: **$1-2/month**
- **Total: $1-2/month** 🎉

### After Free Tier:
- RDS: $15/month
- ECS Fargate: $29/month
- Bedrock: $1-2/month
- **Total: $45-46/month**

---

## 📖 Documentation

Read in this order:

1. **[Quick Start](./deployment/docs/01_QUICK_START.md)** - Deploy in 30 minutes
2. **[Architecture Options](./deployment/docs/02_ARCHITECTURE_OPTIONS.md)** - Understand choices
3. **[Free Tier Setup](./deployment/docs/03_FREE_TIER_SETUP.md)** - Detailed guide
4. **[Bedrock Migration](./deployment/docs/04_BEDROCK_MIGRATION.md)** - Switch AI models
5. **[Troubleshooting](./deployment/docs/05_TROUBLESHOOTING.md)** - Fix issues

---

## ✅ What You Get

- ✅ **FastAPI Backend** - Running 24/7 on ECS Fargate
- ✅ **PostgreSQL Database** - RDS with automatic backups
- ✅ **Redis Cache** - In-memory, no extra cost
- ✅ **Celery Workers** - Background task processing
- ✅ **Daily Scheduler** - EventBridge cron for reports
- ✅ **GitHub Actions** - Auto-deploy on push
- ✅ **CloudWatch Logs** - Monitoring & debugging
- ✅ **Free Tier Optimized** - $0/month for first year!

---

## 🎯 Key Features

### 1. No Load Balancer Needed
- Direct public IP access
- **Saves $17/month**

### 2. Redis in Container
- No ElastiCache needed
- **Saves $15/month**

### 3. All-in-One Container
- FastAPI + Redis + Celery
- **Saves $29/month**

### 4. AWS Bedrock Ready
- Switch from Mistral in 5 minutes
- No more timeout issues
- Better performance

---

## 🚀 Getting Started

```bash
# 1. Clone and navigate
cd deployment/scripts

# 2. Setup AWS infrastructure
chmod +x setup-aws.sh
./setup-aws.sh

# 3. Follow the Quick Start guide
cat ../docs/01_QUICK_START.md
```

---

## 🆘 Need Help?

- **Issues?** → [`deployment/docs/05_TROUBLESHOOTING.md`](./deployment/docs/05_TROUBLESHOOTING.md)
- **Questions?** → Check the documentation in [`deployment/docs/`](./deployment/docs/)
- **Errors?** → Check CloudWatch Logs

---

## 📚 Additional Resources

- [AWS Free Tier](https://aws.amazon.com/free/)
- [ECS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [RDS Pricing](https://aws.amazon.com/rds/postgresql/pricing/)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)

---

**Ready to deploy?** Start with [`deployment/README.md`](./deployment/README.md)! 🚀
