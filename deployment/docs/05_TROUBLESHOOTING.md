# 🐛 Troubleshooting Guide

Common issues and solutions for AWS deployment.

---

## 🔍 Quick Diagnostics

### Check Container Status
```bash
aws ecs describe-services \
    --cluster seo-agent-cluster \
    --services backend-service \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

### View Logs
```bash
# Real-time logs
aws logs tail /ecs/seo-agent-backend --follow

# Last 100 lines
aws logs tail /ecs/seo-agent-backend --since 10m
```

### Check Task Health
```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks --cluster seo-agent-cluster --service-name backend-service --query 'taskArns[0]' --output text)

# Describe task
aws ecs describe-tasks --cluster seo-agent-cluster --tasks $TASK_ARN
```

---

## Common Issues

### 1. Container Won't Start

#### Symptom:
- Task starts then immediately stops
- Status shows "STOPPED"

#### Check Logs:
```bash
aws logs tail /ecs/seo-agent-backend --since 30m
```

#### Common Causes:

**A. Missing Environment Variables**
```
Error: KeyError: 'DATABASE_URL'
```
**Solution:** Check task definition has all required env vars

**B. Database Connection Failed**
```
Error: could not connect to server
```
**Solution:** 
- Check RDS security group allows ECS
- Verify DATABASE_URL is correct
- Test connection: `psql $DATABASE_URL`

**C. Redis Failed to Start**
```
Error: redis-server: command not found
```
**Solution:** Rebuild Docker image with Redis installed

**D. Port Already in Use**
```
Error: Address already in use (port 8000)
```
**Solution:** Change port in task definition or kill conflicting process

---

### 2. Can't Connect to Backend

#### Symptom:
- Frontend can't reach backend
- `curl http://PUBLIC_IP:8000` times out

#### Diagnosis:

**A. Check Public IP**
```bash
aws ecs describe-tasks \
    --cluster seo-agent-cluster \
    --tasks $(aws ecs list-tasks --cluster seo-agent-cluster --service-name backend-service --query 'taskArns[0]' --output text) \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
    --output text | xargs -I {} aws ec2 describe-network-interfaces \
    --network-interface-ids {} \
    --query 'NetworkInterfaces[0].Association.PublicIp' \
    --output text
```

**B. Check Security Group**
```bash
# Get security group ID
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=ecs-tasks-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Check rules
aws ec2 describe-security-groups --group-ids $SG_ID
```

**Required Rule:**
- Type: Custom TCP
- Port: 8000
- Source: 0.0.0.0/0 (or your IP)

**Fix:**
```bash
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0
```

**C. Container Not Running**
```bash
# Check running count
aws ecs describe-services \
    --cluster seo-agent-cluster \
    --services backend-service \
    --query 'services[0].runningCount'
```

Should return `1`. If `0`, check logs.

---

### 3. Database Connection Issues

#### Symptom:
```
sqlalchemy.exc.OperationalError: could not connect to server
```

#### Solutions:

**A. Check RDS Security Group**
```bash
# Get RDS security group
RDS_SG=$(aws rds describe-db-instances \
    --db-instance-identifier seo-agent-db \
    --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
    --output text)

# Check rules
aws ec2 describe-security-groups --group-ids $RDS_SG
```

**Required Rule:**
- Type: PostgreSQL
- Port: 5432
- Source: `ecs-tasks-sg` security group

**Fix:**
```bash
ECS_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=ecs-tasks-sg" --query 'SecurityGroups[0].GroupId' --output text)

aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG \
    --protocol tcp \
    --port 5432 \
    --source-group $ECS_SG
```

**B. Check DATABASE_URL Format**

Correct format:
```
postgresql+psycopg://postgres:PASSWORD@ENDPOINT:5432/app_db
```

**NOT:**
```
postgresql://...  ❌ (missing +psycopg)
postgres://...    ❌ (wrong scheme)
```

**C. Test Connection from ECS**
```bash
# SSH into ECS task (requires Amazon ECS Exec)
aws ecs execute-command \
    --cluster seo-agent-cluster \
    --task $TASK_ARN \
    --container backend \
    --interactive \
    --command "/bin/bash"

# Then test
psql $DATABASE_URL
```

---

### 4. OAuth Not Working

#### Symptom:
- "Redirect URI mismatch"
- "Origin not allowed"

#### Solution:

**A. Update Google OAuth Redirect URIs**

Go to Google Cloud Console → APIs & Credentials → OAuth 2.0 Client IDs

Add these URIs:
```
http://YOUR_PUBLIC_IP:8000/api/v1/auth/google/callback
http://localhost:8000/api/v1/auth/google/callback  (for local testing)
```

**B. Update CORS in Backend**

File: `backend/main.py`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.amplifyapp.com",
        "http://YOUR_PUBLIC_IP:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**C. Update Frontend API URL**

Amplify → Environment variables:
```
NEXT_PUBLIC_API_BASE_URL=http://YOUR_PUBLIC_IP:8000/api/v1
```

---

### 5. Mistral AI Timeout

#### Symptom:
```
httpx.ReadTimeout: Read timeout after 120 seconds
```

#### Solutions:

**Option A: Increase Timeout (Temporary)**
```python
self.llm = ChatMistralAI(
    timeout=240,  # Increase to 240 seconds
    max_retries=5,
)
```

**Option B: Switch to AWS Bedrock (Recommended)**

See: `04_BEDROCK_MIGRATION.md`

Benefits:
- No timeouts (1-3 second responses)
- Lower cost
- Better reliability

---

### 6. Docker Build Fails

#### Symptom:
```
ERROR: failed to solve: process "/bin/sh -c..." did not complete successfully
```

#### Solutions:

**A. Check Docker Context**
```bash
cd /path/to/Search-console-Agent
docker build -f deployment/docker/Dockerfile .
```

**Note:** Run from project root, not from `deployment/` folder!

**B. Clear Docker Cache**
```bash
docker system prune -a
docker build --no-cache -f deployment/docker/Dockerfile .
```

**C. Check Dependencies**
```bash
# Ensure pyproject.toml exists
ls -la backend/pyproject.toml

# Test locally
cd backend
uv pip compile pyproject.toml
```

---

### 7. ECS Task Keeps Restarting

#### Symptom:
- Task starts, runs for a few seconds, then stops
- Repeats continuously

#### Check Health Check Failure:
```bash
aws logs tail /ecs/seo-agent-backend --since 5m | grep -i health
```

#### Common Causes:

**A. Health Check Failing**
```
Health check failed: curl: (7) Failed to connect
```

**Solution:** 
- Backend not listening on port 8000
- Check logs for startup errors
- Verify uvicorn is running

**B. Out of Memory**
```
Error: killed (OOMKilled)
```

**Solution:** Increase memory in task definition:
```json
{
  "memory": "1024",  // Increase from 512 to 1024
  ...
}
```

**C. Supervisor Not Starting Services**
```bash
# Check supervisor logs
aws logs tail /ecs/seo-agent-backend --since 5m | grep supervisor
```

**Fix:** Check `supervisord.conf` syntax

---

### 8. Celery Worker Not Running

#### Symptom:
- Tasks not processing
- Celery logs missing

#### Diagnosis:
```bash
# Check if Celery process is running
aws logs tail /ecs/seo-agent-backend --since 10m | grep -i celery
```

#### Solutions:

**A. Redis Connection Failed**
```
Error: Can't connect to Redis
```

**Solution:** 
- Redis should start before Celery
- Check supervisor priority settings
- Verify `REDIS_URL=redis://localhost:6379/0`

**B. Celery Import Error**
```
Error: No module named 'core.celery_app'
```

**Solution:**
```bash
# Check working directory in supervisord.conf
[program:celery-worker]
directory=/app  # Must be set!
```

---

### 9. EventBridge Scheduler Not Running

#### Symptom:
- Daily reports not generated
- No scheduled tasks

#### Check Rule:
```bash
aws events describe-rule --name seo-agent-daily-report
```

#### Check Targets:
```bash
aws events list-targets-by-rule --rule seo-agent-daily-report
```

#### Solutions:

**A. Rule Disabled**
```bash
aws events enable-rule --name seo-agent-daily-report
```

**B. Missing IAM Permissions**
```bash
# Check events role
aws iam get-role --role-name ecsEventsRole

# Attach policy if missing
aws iam attach-role-policy \
    --role-name ecsEventsRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceEventsRole
```

**C. Test Manually**
```bash
# Trigger rule manually
aws events put-events \
    --entries '[{"Source":"manual","DetailType":"test","Detail":"{}"}]'
```

---

### 10. High AWS Costs

#### Symptom:
- Bill higher than expected

#### Check Costs:
```bash
# Get current month costs
aws ce get-cost-and-usage \
    --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=SERVICE
```

#### Common Causes:

**A. Load Balancer Running**
- Cost: $17/month
- **Solution:** Remove if not needed (use public IP)

**B. Multiple ECS Tasks**
```bash
# Check running tasks
aws ecs list-tasks --cluster seo-agent-cluster
```

**Solution:** Should be only 1 task. Stop extras:
```bash
aws ecs stop-task --cluster seo-agent-cluster --task TASK_ARN
```

**C. RDS Not on Free Tier**
```bash
# Check instance class
aws rds describe-db-instances \
    --db-instance-identifier seo-agent-db \
    --query 'DBInstances[0].DBInstanceClass'
```

**Should be:** `db.t3.micro` or `db.t4g.micro`

---

## 🔧 Useful Commands

### Container Management
```bash
# Force new deployment
aws ecs update-service \
    --cluster seo-agent-cluster \
    --service backend-service \
    --force-new-deployment

# Scale up/down
aws ecs update-service \
    --cluster seo-agent-cluster \
    --service backend-service \
    --desired-count 2

# Stop service
aws ecs update-service \
    --cluster seo-agent-cluster \
    --service backend-service \
    --desired-count 0
```

### Logs
```bash
# Stream logs
aws logs tail /ecs/seo-agent-backend --follow --format short

# Search logs
aws logs filter-log-events \
    --log-group-name /ecs/seo-agent-backend \
    --filter-pattern "ERROR"

# Get specific time range
aws logs tail /ecs/seo-agent-backend \
    --since 2024-01-15T10:00:00 \
    --until 2024-01-15T11:00:00
```

### Database
```bash
# Connect to RDS
psql "postgresql://postgres:PASSWORD@ENDPOINT:5432/app_db"

# Run migrations
aws ecs run-task \
    --cluster seo-agent-cluster \
    --task-definition seo-agent-backend \
    --overrides '{"containerOverrides":[{"name":"backend","command":["alembic","upgrade","head"]}]}'
```

---

## 🆘 Still Having Issues?

### 1. Check CloudWatch Logs
All errors are logged here. Look for:
- Stack traces
- Connection errors
- Configuration issues

### 2. Enable Debug Mode
Add to task definition:
```json
{
  "name": "LOG_LEVEL",
  "value": "DEBUG"
}
```

### 3. Test Locally First
```bash
cd backend
docker build -f ../deployment/docker/Dockerfile -t test .
docker run -p 8000:8000 --env-file .env test
curl http://localhost:8000/health
```

### 4. Review Security Groups
Most connection issues are security group misconfigurations.

### 5. Check AWS Service Health
https://status.aws.amazon.com/

---

## 📚 Additional Resources

- [ECS Troubleshooting](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/troubleshooting.html)
- [RDS Connectivity](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Troubleshooting.html)
- [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)

---

**Need more help? Check the AWS documentation or reach out to AWS Support.**
