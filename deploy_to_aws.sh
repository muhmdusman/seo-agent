#!/bin/bash

# Safe AWS Deployment Script for Search Console Agent
# Deploys Lambda + EventBridge while keeping everything else local

set -e  # Exit on error

echo "🚀 Search Console Agent - AWS Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FUNCTION_NAME="search-console-daily-reports"
REGION="us-east-1"
ROLE_NAME="SearchConsoleAgentLambdaRole"
RULE_NAME="daily-seo-reports"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Install: pip install awscli${NC}"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not configured. Run: aws configure${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI configured${NC}"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "   Account ID: $ACCOUNT_ID"

# Load environment variables
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    exit 1
fi

source .env
echo -e "${GREEN}✅ Environment variables loaded${NC}"

# Step 1: Create Lambda package
echo ""
echo "📦 Step 1: Creating Lambda deployment package..."

cd backend

# Clean up
rm -rf lambda_package lambda_function.zip

# Create package directory
mkdir lambda_package

# Copy application code
echo "   Copying application code..."
cp -r agents api core db models schemas services tools lambda_package/
cp lambda_handler.py lambda_package/

# Create requirements.txt if not exists
if [ ! -f "requirements.txt" ]; then
    echo "   Generating requirements.txt..."
    uv pip compile pyproject.toml -o requirements.txt
fi

# Install dependencies
echo "   Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt \
    -t lambda_package/ \
    --platform manylinux2014_x86_64 \
    --python-version 3.11 \
    --implementation cp \
    --only-binary=:all: \
    --upgrade \
    --quiet 2>&1 | grep -v "WARNING" || true

# Fix greenlet specifically if it failed
if [ ! -d "lambda_package/greenlet" ]; then
    echo "   Fixing greenlet dependency..."
    pip install greenlet==3.2.5 \
        -t lambda_package/ \
        --platform manylinux2014_x86_64 \
        --python-version 3.11 \
        --only-binary=:all: \
        --quiet || true
fi

# Create ZIP
echo "   Creating ZIP archive..."
cd lambda_package
zip -r ../lambda_function.zip . -q -x "*.pyc" "*__pycache__*"
cd ..

SIZE=$(ls -lh lambda_function.zip | awk '{print $5}')
echo -e "${GREEN}✅ Lambda package created: lambda_function.zip ($SIZE)${NC}"

cd ..

# Step 2: Create or update IAM role
echo ""
echo "🔐 Step 2: Setting up IAM role..."

if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    echo "   Role $ROLE_NAME already exists"
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
else
    echo "   Creating IAM role..."
    
    # Create trust policy
    cat > /tmp/lambda-trust-policy.json << 'EOF'
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
EOF

    # Create role
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
        --output text &> /dev/null

    # Attach policies
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Wait for role propagation
    echo "   Waiting for role to propagate..."
    sleep 15

    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
fi

echo -e "${GREEN}✅ IAM Role ready${NC}"
echo "   ARN: $ROLE_ARN"

# Step 3: Deploy Lambda function
echo ""
echo "☁️  Step 3: Deploying Lambda function..."

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "   Updating existing function..."
    
    # Update code
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://backend/lambda_function.zip \
        --region $REGION \
        --output text &> /dev/null
    
    # Update configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment Variables="{
            APP_NAME=Search Console Agent,
            DEBUG=false,
            DATABASE_URL=${DATABASE_URL},
            GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},
            GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},
            GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI},
            JWT_SECRET=${JWT_SECRET},
            JWT_ALGORITHM=${JWT_ALGORITHM},
            ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES},
            APP_URL=${APP_URL},
            FRONTEND_URL=${FRONTEND_URL},
            MISTRAL_API_KEY=${MISTRAL_API_KEY},
            REFRESH_TOKEN_EXPIRY_DAYS=${REFRESH_TOKEN_EXPIRY_DAYS},
            SMTP_HOST=${SMTP_HOST},
            SMTP_PORT=${SMTP_PORT},
            SMTP_USERNAME=${SMTP_USERNAME},
            SMTP_PASSWORD=${SMTP_PASSWORD},
            SMTP_FROM_EMAIL=${SMTP_FROM_EMAIL},
            SMTP_FROM_NAME=${SMTP_FROM_NAME},
            SCHEDULER_ENABLED=${SCHEDULER_ENABLED},
            DAILY_REPORT_TIME=${DAILY_REPORT_TIME},
            ADMIN_EMAIL=${ADMIN_EMAIL}
        }" \
        --region $REGION \
        --output text &> /dev/null
    
    echo -e "${GREEN}✅ Lambda function updated${NC}"
else
    echo "   Creating new function..."
    
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb://backend/lambda_function.zip \
        --timeout 900 \
        --memory-size 1024 \
        --region $REGION \
        --environment Variables="{
            APP_NAME=Search Console Agent,
            DEBUG=false,
            DATABASE_URL=${DATABASE_URL},
            GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},
            GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},
            GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI},
            JWT_SECRET=${JWT_SECRET},
            JWT_ALGORITHM=${JWT_ALGORITHM},
            ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES},
            APP_URL=${APP_URL},
            FRONTEND_URL=${FRONTEND_URL},
            MISTRAL_API_KEY=${MISTRAL_API_KEY},
            REFRESH_TOKEN_EXPIRY_DAYS=${REFRESH_TOKEN_EXPIRY_DAYS},
            SMTP_HOST=${SMTP_HOST},
            SMTP_PORT=${SMTP_PORT},
            SMTP_USERNAME=${SMTP_USERNAME},
            SMTP_PASSWORD=${SMTP_PASSWORD},
            SMTP_FROM_EMAIL=${SMTP_FROM_EMAIL},
            SMTP_FROM_NAME=${SMTP_FROM_NAME},
            SCHEDULER_ENABLED=${SCHEDULER_ENABLED},
            DAILY_REPORT_TIME=${DAILY_REPORT_TIME},
            ADMIN_EMAIL=${ADMIN_EMAIL}
        }" \
        --output text &> /dev/null
    
    echo -e "${GREEN}✅ Lambda function created${NC}"
fi

FUNCTION_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"
echo "   ARN: $FUNCTION_ARN"

# Step 4: Test Lambda function
echo ""
echo "🧪 Step 4: Testing Lambda function..."

aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --region $REGION \
    /tmp/lambda_response.json \
    --output text &> /dev/null

if [ $? -eq 0 ]; then
    RESULT=$(cat /tmp/lambda_response.json | python -m json.tool)
    
    if echo "$RESULT" | grep -q '"success": true'; then
        echo -e "${GREEN}✅ Lambda test successful!${NC}"
        echo "   Check your email: $ADMIN_EMAIL"
    else
        echo -e "${YELLOW}⚠️  Lambda executed but check logs for errors${NC}"
        echo "$RESULT"
    fi
else
    echo -e "${RED}❌ Lambda test failed${NC}"
    cat /tmp/lambda_response.json
fi

# Step 5: Create EventBridge rule
echo ""
echo "⏰ Step 5: Setting up EventBridge schedule..."

if aws events describe-rule --name $RULE_NAME --region $REGION &> /dev/null; then
    echo "   Rule $RULE_NAME already exists"
else
    echo "   Creating EventBridge rule..."
    
    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "cron(0 8 * * ? *)" \
        --description "Trigger daily SEO reports at 8 AM UTC" \
        --region $REGION \
        --output text &> /dev/null
fi

# Add Lambda permission
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/${RULE_NAME} \
    --region $REGION \
    --output text &> /dev/null 2>&1 || true

# Set Lambda as target
aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id"="1","Arn"="${FUNCTION_ARN}" \
    --region $REGION \
    --output text &> /dev/null

echo -e "${GREEN}✅ EventBridge rule configured${NC}"
echo "   Schedule: Daily at 8:00 AM UTC"

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 DEPLOYMENT SUCCESSFUL!${NC}"
echo "=========================================="
echo ""
echo "📊 What was deployed:"
echo "   ✅ Lambda function: $FUNCTION_NAME"
echo "   ✅ EventBridge rule: $RULE_NAME"
echo "   ✅ Daily schedule: 8:00 AM UTC"
echo ""
echo "🔗 AWS Console Links:"
echo "   Lambda: https://console.aws.amazon.com/lambda/home?region=${REGION}#/functions/${FUNCTION_NAME}"
echo "   EventBridge: https://console.aws.amazon.com/events/home?region=${REGION}#/rules/${RULE_NAME}"
echo "   CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=${REGION}#logsV2:log-groups/log-group/\$252Faws\$252Flambda\$252F${FUNCTION_NAME}"
echo ""
echo "🧪 Test Commands:"
echo "   # Manual trigger:"
echo "   aws lambda invoke --function-name $FUNCTION_NAME --region $REGION output.json && cat output.json"
echo ""
echo "   # View logs:"
echo "   aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"
echo ""
echo "📧 Next daily report: Tomorrow at 8:00 AM UTC"
echo "   Email will be sent to: $ADMIN_EMAIL"
echo ""
echo -e "${GREEN}✅ Ready to submit AWS Builder Challenge!${NC}"
