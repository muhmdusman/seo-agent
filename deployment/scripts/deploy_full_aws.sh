#!/bin/bash

###############################################################################
# Full AWS Deployment Script
# Deploys Backend (Elastic Beanstalk) + Database (RDS)
# Time: ~45-60 minutes
# Cost: $0 (Free Tier for 12 months)
###############################################################################

set -e

echo "============================================================"
echo "🚀 Full AWS Deployment - Backend + Database"
echo "============================================================"
echo ""
echo "⏱️  Estimated time: 45-60 minutes"
echo "💰 Cost: \$0 (AWS Free Tier)"
echo ""
echo "Services to deploy:"
echo "  1. AWS RDS PostgreSQL (db.t3.micro)"
echo "  2. AWS Elastic Beanstalk (Python 3.11, t3.micro)"
echo "  3. Update Lambda environment"
echo "  4. Update Amplify environment"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

# Variables
REGION="us-east-1"
DB_INSTANCE_ID="search-console-db"
DB_PASSWORD="SearchConsole2024SecurePassword!"
EB_APP_NAME="search-console-api"
EB_ENV_NAME="search-console-prod"
LAMBDA_FUNCTION="search-console-daily-reports"

echo ""
echo "============================================================"
echo "📊 Step 1: Create RDS PostgreSQL Database"
echo "============================================================"
echo ""

# Check if RDS instance already exists
if aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --region $REGION &>/dev/null; then
    echo "✅ RDS instance '$DB_INSTANCE_ID' already exists"
    RDS_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_ID \
        --region $REGION \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)
    echo "📍 Endpoint: $RDS_ENDPOINT"
else
    echo "🔄 Creating RDS PostgreSQL instance (db.t3.micro)..."
    echo "   This will take 5-10 minutes..."
    
    # Get default VPC and security group
    DEFAULT_VPC=$(aws ec2 describe-vpcs --region $REGION --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
    DEFAULT_SG=$(aws ec2 describe-security-groups --region $REGION --filters "Name=vpc-id,Values=$DEFAULT_VPC" "Name=group-name,Values=default" --query 'SecurityGroups[0].GroupId' --output text)
    
    echo "   Using VPC: $DEFAULT_VPC"
    echo "   Using Security Group: $DEFAULT_SG"
    
    # Create RDS instance
    aws rds create-db-instance \
        --db-instance-identifier $DB_INSTANCE_ID \
        --db-instance-class db.t3.micro \
        --engine postgres \
        --engine-version 15.4 \
        --master-username postgres \
        --master-user-password "$DB_PASSWORD" \
        --allocated-storage 20 \
        --vpc-security-group-ids $DEFAULT_SG \
        --publicly-accessible \
        --backup-retention-period 1 \
        --no-multi-az \
        --storage-type gp2 \
        --region $REGION \
        --no-deletion-protection \
        > /dev/null
    
    echo "⏳ Waiting for RDS instance to become available..."
    aws rds wait db-instance-available \
        --db-instance-identifier $DB_INSTANCE_ID \
        --region $REGION
    
    RDS_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_ID \
        --region $REGION \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)
    
    echo "✅ RDS instance created!"
    echo "📍 Endpoint: $RDS_ENDPOINT"
    
    # Update security group to allow PostgreSQL access
    echo "🔓 Opening PostgreSQL port (5432)..."
    aws ec2 authorize-security-group-ingress \
        --group-id $DEFAULT_SG \
        --protocol tcp \
        --port 5432 \
        --cidr 0.0.0.0/0 \
        --region $REGION 2>/dev/null || echo "   (Port already open)"
fi

DATABASE_URL="postgresql+psycopg://postgres:$DB_PASSWORD@$RDS_ENDPOINT:5432/postgres"

echo ""
echo "============================================================"
echo "🗄️  Step 2: Run Database Migrations"
echo "============================================================"
echo ""

cd backend

# Update .env temporarily for migration
echo "🔄 Running Alembic migrations on RDS..."
export DATABASE_URL="$DATABASE_URL"
alembic upgrade head

echo "✅ Database schema created!"

cd ..

echo ""
echo "============================================================"
echo "☁️  Step 3: Deploy Backend to Elastic Beanstalk"
echo "============================================================"
echo ""

# Install EB CLI if not already installed
if ! command -v eb &> /dev/null; then
    echo "📦 Installing AWS Elastic Beanstalk CLI..."
    pip install awsebcli --quiet
fi

cd backend

# Initialize EB if not already done
if [ ! -d ".elasticbeanstalk" ]; then
    echo "🔄 Initializing Elastic Beanstalk..."
    eb init -p python-3.11 $EB_APP_NAME --region $REGION
fi

# Create .ebextensions for configuration
mkdir -p .ebextensions
cat > .ebextensions/python.config << EOF
option_settings:
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: "/var/app/current:$PYTHONPATH"
  aws:elasticbeanstalk:container:python:
    WSGIPath: api.main:app
EOF

# Create Procfile for running the app
cat > Procfile << EOF
web: uvicorn api.main:app --host 0.0.0.0 --port 8000
EOF

# Check if environment exists
if aws elasticbeanstalk describe-environments --application-name $EB_APP_NAME --environment-names $EB_ENV_NAME --region $REGION &>/dev/null; then
    echo "✅ Elastic Beanstalk environment '$EB_ENV_NAME' already exists"
    echo "🔄 Deploying latest code..."
    eb deploy $EB_ENV_NAME
else
    echo "🔄 Creating Elastic Beanstalk environment (t3.micro)..."
    echo "   This will take 5-10 minutes..."
    eb create $EB_ENV_NAME \
        --instance-type t3.micro \
        --single \
        --region $REGION
fi

echo "⏳ Waiting for environment to be ready..."
aws elasticbeanstalk wait environment-updated \
    --application-name $EB_APP_NAME \
    --environment-names $EB_ENV_NAME \
    --region $REGION

# Get EB URL
EB_URL=$(aws elasticbeanstalk describe-environments \
    --application-name $EB_APP_NAME \
    --environment-names $EB_ENV_NAME \
    --region $REGION \
    --query 'Environments[0].CNAME' \
    --output text)

echo "✅ Backend deployed!"
echo "🔗 URL: http://$EB_URL"

# Set environment variables
echo "🔧 Configuring environment variables..."

# Read from .env file
if [ -f "../.env" ]; then
    eb setenv \
        DATABASE_URL="$DATABASE_URL" \
        GOOGLE_CLIENT_ID="$(grep GOOGLE_CLIENT_ID ../.env | cut -d '=' -f2)" \
        GOOGLE_CLIENT_SECRET="$(grep GOOGLE_CLIENT_SECRET ../.env | cut -d '=' -f2)" \
        JWT_SECRET="$(grep JWT_SECRET ../.env | cut -d '=' -f2)" \
        MISTRAL_API_KEY="$(grep MISTRAL_API_KEY ../.env | cut -d '=' -f2)" \
        SMTP_HOST="$(grep SMTP_HOST ../.env | cut -d '=' -f2)" \
        SMTP_PORT="$(grep SMTP_PORT ../.env | cut -d '=' -f2)" \
        SMTP_USERNAME="$(grep SMTP_USERNAME ../.env | cut -d '=' -f2)" \
        SMTP_PASSWORD="$(grep SMTP_PASSWORD ../.env | cut -d '=' -f2)" \
        SMTP_FROM_EMAIL="$(grep SMTP_FROM_EMAIL ../.env | cut -d '=' -f2)" \
        SMTP_FROM_NAME="$(grep SMTP_FROM_NAME ../.env | cut -d '=' -f2)" \
        FRONTEND_URL="https://main.d3vozze6u0rukp.amplifyapp.com" \
        GOOGLE_REDIRECT_URI="http://$EB_URL/api/v1/auth/google/callback"
fi

cd ..

echo ""
echo "============================================================"
echo "🔄 Step 4: Update Lambda Function"
echo "============================================================"
echo ""

echo "🔧 Updating Lambda environment variables..."
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION \
    --environment "Variables={
        DATABASE_URL=$DATABASE_URL,
        GOOGLE_CLIENT_ID=$(grep GOOGLE_CLIENT_ID .env | cut -d '=' -f2 | tr -d '"'),
        GOOGLE_CLIENT_SECRET=$(grep GOOGLE_CLIENT_SECRET .env | cut -d '=' -f2 | tr -d '"'),
        JWT_SECRET=$(grep JWT_SECRET .env | cut -d '=' -f2 | tr -d '"'),
        MISTRAL_API_KEY=$(grep MISTRAL_API_KEY .env | cut -d '=' -f2 | tr -d '"'),
        SMTP_HOST=$(grep SMTP_HOST .env | cut -d '=' -f2 | tr -d '"'),
        SMTP_PORT=$(grep SMTP_PORT .env | cut -d '=' -f2 | tr -d '"'),
        SMTP_USERNAME=$(grep SMTP_USERNAME .env | cut -d '=' -f2 | tr -d '"'),
        SMTP_PASSWORD=$(grep SMTP_PASSWORD .env | cut -d '=' -f2 | tr -d '"'),
        SMTP_FROM_EMAIL=$(grep SMTP_FROM_EMAIL .env | cut -d '=' -f2 | tr -d '"'),
        SMTP_FROM_NAME=$(grep SMTP_FROM_NAME .env | cut -d '=' -f2 | tr -d '"'),
        ADMIN_EMAIL=$(grep ADMIN_EMAIL .env | cut -d '=' -f2 | tr -d '"'),
        FRONTEND_URL=https://main.d3vozze6u0rukp.amplifyapp.com
    }" \
    --region $REGION \
    > /dev/null

echo "✅ Lambda updated with RDS database URL!"

echo ""
echo "============================================================"
echo "🎨 Step 5: Update Amplify Frontend"
echo "============================================================"
echo ""

echo "📝 Update Amplify environment variable manually:"
echo ""
echo "   Go to: https://console.aws.amazon.com/amplify/home?region=us-east-1#/d3vozze6u0rukp"
echo "   → Environment variables"
echo "   → Edit: NEXT_PUBLIC_API_BASE_URL"
echo "   → Set to: http://$EB_URL/api/v1"
echo "   → Save"
echo "   → Redeploy"
echo ""

echo "============================================================"
echo "🎉 Deployment Complete!"
echo "============================================================"
echo ""
echo "📊 Deployment Summary:"
echo ""
echo "✅ Database:"
echo "   RDS PostgreSQL: $RDS_ENDPOINT"
echo "   Connection: $DATABASE_URL"
echo ""
echo "✅ Backend API:"
echo "   URL: http://$EB_URL"
echo "   Health Check: http://$EB_URL/health"
echo ""
echo "✅ Lambda:"
echo "   Function: $LAMBDA_FUNCTION"
echo "   Status: Updated with RDS connection"
echo ""
echo "✅ Frontend:"
echo "   URL: https://main.d3vozze6u0rukp.amplifyapp.com"
echo "   Action Required: Update NEXT_PUBLIC_API_BASE_URL"
echo ""
echo "============================================================"
echo "📋 Next Steps:"
echo "============================================================"
echo ""
echo "1. Update Amplify environment variable (see above)"
echo "2. Update Google OAuth Console:"
echo "   Add redirect URI: http://$EB_URL/api/v1/auth/google/callback"
echo ""
echo "3. Test the application:"
echo "   - Visit: https://main.d3vozze6u0rukp.amplifyapp.com"
echo "   - Click 'Connect with Google'"
echo "   - Authenticate and connect sites"
echo ""
echo "4. Test Lambda manually:"
echo "   aws lambda invoke --function-name $LAMBDA_FUNCTION --region $REGION response.json"
echo ""
echo "============================================================"
echo "💰 Monthly Cost Estimate:"
echo "============================================================"
echo ""
echo "   RDS db.t3.micro:        \$0 (Free Tier - 750 hrs/month)"
echo "   EC2 t3.micro (EB):      \$0 (Free Tier - 750 hrs/month)"
echo "   Lambda:                 \$0 (Free Tier - 1M requests/month)"
echo "   Amplify:                \$0 (Free Tier - 1000 build min/month)"
echo "   Data Transfer:          \$0 (Free Tier - 100GB/month)"
echo "   ─────────────────────────────────────────────"
echo "   Total:                  \$0/month (for first 12 months!)"
echo ""
echo "🎉 Everything is deployed on AWS Free Tier!"
echo "============================================================"
