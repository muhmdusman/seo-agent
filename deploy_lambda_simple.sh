#!/bin/bash

# Simplified Lambda Deployment - Uses Lambda Layers for Dependencies
# This avoids dependency compatibility issues

set -e

echo "🚀 Search Console Agent - Simple Lambda Deployment"
echo "=================================================="
echo ""

# Configuration
FUNCTION_NAME="search-console-daily-reports"
REGION="us-east-1"
ROLE_NAME="SearchConsoleAgentLambdaRole"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install: pip install awscli"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Run: aws configure"
    exit 1
fi

echo "✅ AWS CLI configured"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "   Account ID: $ACCOUNT_ID"

# Load environment variables
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

source .env
echo "✅ Environment variables loaded"

echo ""
echo "📦 Step 1: Creating Lambda deployment package (code only)..."

cd backend

# Clean up
rm -rf lambda_code_only lambda_code.zip

# Create directory for code only (no dependencies)
mkdir lambda_code_only

# Copy application code
echo "   Copying application code..."
cp -r agents api core db models schemas services tools lambda_code_only/
cp lambda_handler.py lambda_code_only/

# Create ZIP (small - no dependencies)
cd lambda_code_only
zip -r ../lambda_code.zip . -q
cd ..

SIZE=$(ls -lh lambda_code.zip | awk '{print $5}')
echo "✅ Lambda code package created: lambda_code.zip ($SIZE)"

cd ..

echo ""
echo "🔐 Step 2: Setting up IAM role..."

if aws iam get-role --role-name $ROLE_NAME &> /dev/null 2>&1; then
    echo "   Role already exists"
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
else
    echo "   Creating IAM role..."
    
    cat > /tmp/lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
        --output text &> /dev/null

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    echo "   Waiting for role to propagate..."
    sleep 15

    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
fi

echo "✅ IAM Role ready"

echo ""
echo "☁️  Step 3: Deploying Lambda function..."

LAYER_ARN="arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-SQLAlchemy:19"

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null 2>&1; then
    echo "   Updating existing function..."
    
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://backend/lambda_code.zip \
        --region $REGION \
        --output text &> /dev/null
    
    sleep 3
    
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout 900 \
        --memory-size 1024 \
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
    
    echo "✅ Lambda function updated"
else
    echo "   Creating new function..."
    
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb://backend/lambda_code.zip \
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
    
    echo "✅ Lambda function created"
fi

echo ""
echo "⚠️  IMPORTANT: Installing dependencies in Lambda Console"
echo ""
echo "Since dependencies have compatibility issues, you have 2 options:"
echo ""
echo "Option 1: Use AWS Console to add a Layer (Recommended)"
echo "   1. Go to: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/$FUNCTION_NAME"
echo "   2. Scroll to 'Layers' section"
echo "   3. Click 'Add a layer'"
echo "   4. Choose 'Specify an ARN'"
echo "   5. Enter: arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-requests:11"
echo "   6. Add another layer for SQLAlchemy if needed"
echo ""
echo "Option 2: Upload dependencies separately (Advanced)"
echo "   See: LAMBDA_LAYERS.md for instructions"
echo ""
echo "For now, let's test if basic imports work..."

echo ""
echo "🧪 Step 4: Testing Lambda function (may fail due to missing deps)..."

aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --region $REGION \
    /tmp/lambda_response.json \
    --log-type Tail \
    --query 'LogResult' \
    --output text 2>/dev/null | base64 -d || true

if [ -f /tmp/lambda_response.json ]; then
    RESULT=$(cat /tmp/lambda_response.json 2>/dev/null || echo "{}")
    if echo "$RESULT" | grep -q "success"; then
        echo "✅ Lambda test successful!"
    else
        echo "⚠️  Lambda may need dependencies installed"
        echo "   Response: $RESULT"
    fi
fi

echo ""
echo "⏰ Step 5: Setting up EventBridge..."

RULE_NAME="daily-seo-reports"
FUNCTION_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

if aws events describe-rule --name $RULE_NAME --region $REGION &> /dev/null 2>&1; then
    echo "   Rule already exists"
else
    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "cron(0 8 * * ? *)" \
        --region $REGION \
        --output text &> /dev/null
fi

aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/${RULE_NAME} \
    --region $REGION \
    --output text &> /dev/null 2>&1 || true

aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id"="1","Arn"="${FUNCTION_ARN}" \
    --region $REGION \
    --output text &> /dev/null

echo "✅ EventBridge configured"

echo ""
echo "=================================================="
echo "🎉 DEPLOYMENT COMPLETE (with notes)"
echo "=================================================="
echo ""
echo "✅ Lambda function deployed: $FUNCTION_NAME"
echo "✅ EventBridge rule created: $RULE_NAME"
echo ""
echo "⚠️  NEXT STEP: Add dependencies via Lambda Console"
echo "   Follow Option 1 above to add Lambda Layers"
echo ""
echo "🔗 AWS Console:"
echo "   https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/$FUNCTION_NAME"
echo ""
echo "After adding layers, test again:"
echo "   aws lambda invoke --function-name $FUNCTION_NAME --region us-east-1 out.json && cat out.json"
