# 🚀 Option 2: Deploy Database to AWS RDS

## ⚡ Quick AWS RDS Setup (30 minutes)

### Step 1: Create RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier search-console-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password YourSecurePassword123! \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxx \
  --publicly-accessible \
  --backup-retention-period 0 \
  --no-multi-az \
  --region us-east-1
```

**Wait 5-10 minutes for database to be available**

---

### Step 2: Get RDS Endpoint

```bash
aws rds describe-db-instances \
  --db-instance-identifier search-console-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

**Output:** `search-console-db.xxxxx.us-east-1.rds.amazonaws.com`

---

### Step 3: Update Security Group

Allow Lambda and your local machine to connect:

1. Get RDS security group ID
2. Add inbound rule:
   - Type: PostgreSQL
   - Port: 5432
   - Source: 0.0.0.0/0 (for demo) or your IP + Lambda VPC

---

### Step 4: Migrate Your Data

Update local `.env`:
```env
RDS_DATABASE_URL="postgresql+psycopg://postgres:YourSecurePassword123!@search-console-db.xxxxx.us-east-1.rds.amazonaws.com:5432/postgres"
```

Run migration:
```bash
cd backend

# Export local data
python -c "
from db.dbconfig import SessionLocal
from models.user import User
from models.oauth_account import OAuthAccount
import json

db = SessionLocal()
users = db.query(User).all()
accounts = db.query(OAuthAccount).all()

data = {
    'users': [{'id': u.id, 'email': u.email, 'full_name': u.full_name} for u in users],
    'accounts': [{'user_id': a.user_id, 'access_token': a.access_token, 'refresh_token': a.refresh_token} for a in accounts]
}

with open('data_export.json', 'w') as f:
    json.dump(data, f)
print('Data exported!')
"

# Connect to RDS and import
DATABASE_URL=$RDS_DATABASE_URL alembic upgrade head

# Import data to RDS
# (Manual step: re-authenticate via frontend to save to RDS)
```

---

### Step 5: Update Lambda Environment

```bash
aws lambda update-function-configuration \
  --function-name search-console-daily-reports \
  --environment "Variables={DATABASE_URL=postgresql+psycopg://postgres:YourSecurePassword123!@search-console-db.xxxxx.us-east-1.rds.amazonaws.com:5432/postgres,...}" \
  --region us-east-1
```

---

### Step 6: Test Lambda with RDS

Invoke Lambda manually:
```bash
aws lambda invoke \
  --function-name search-console-daily-reports \
  --region us-east-1 \
  response.json

cat response.json
```

---

## ✅ After RDS Setup:

- ✅ Lambda can connect to database
- ✅ Daily reports will work automatically
- ❌ Backend API still local (new users can't sign up)

**Cost:** ~$15-20/month (Free Tier: 750 hours/month for 12 months)

---

## ⚠️ For Weekend Challenge:

**This might be overkill!** Option 1 (demo with screenshots) is sufficient for the challenge.

**If you have time and want a fully working demo:** Do Option 3 (deploy backend too).
