#!/bin/bash

# Lambda Deployment via S3 (for large packages)
set -e

echo "🚀 Search Console Agent - Lambda Deployment via S3"
echo "=================================================="

FUNCTION_NAME="search-console-daily-reports"
REGION="us-east-1"
ROLE_NAME="SearchConsoleAgentLambdaRole"
BUCKET_NAME="search-console-lambda-${RANDOM}"

# Check AWS CLI
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS Account: $ACCOUNT_ID"

# Load .env
source .env

echo ""
echo "📦 Step 1: Using existing Lambda package..."
cd backend

if [ ! -f "lambda_function.zip" ]; then
    echo "❌ lambda_function.zip not found! Run the other script first."
    exit 1
fi

SIZE=$(ls -lh lambda_function.zip | awk '{print $5}')
echo "✅ Package ready: lambda_function.zip ($SIZE)"

cd ..

echo ""
echo "☁️  Step 2: Creating S3 bucket for deployment..."

if aws s3 ls "s3://${BUCKET_NAME}" 2>/dev/null; then
    echo "   Bucket exists"
else
    aws s3 mb "s3://${BUCKET_NAME}" --region $REGION
    echo "✅ Bucket created: ${BUCKET_NAME}"
fi

echo ""
echo "📤 Step 3: Uploading package to S3..."

aws s3 cp backend/lambda_function.zip "s3://${BUCKET_NAME}/lambda_function.zip"
echo "✅ Package uploaded"

echo ""
echo "☁️  Step 4: Creating Lambda function from S3..."

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_handler.lambda_handler \
    --code S3Bucket=${BUCKET_NAME},S3Key=lambda_function.zip \
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
    --output json

echo "✅ Lambda function created!"

echo ""
echo "🧪 Step 5: Testing Lambda..."

sleep 5

aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --region $REGION \
    response.json

echo ""
echo "Response:"
cat response.json | python -m json.tool || cat response.json

echo ""
echo "⏰ Step 6: Setting up EventBridge..."

RULE_NAME="daily-seo-reports"
FUNCTION_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "cron(0 8 * * ? *)" \
    --region $REGION \
    --output text &> /dev/null

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
echo "🧹 Cleanup: Deleting S3 bucket..."
aws s3 rb "s3://${BUCKET_NAME}" --force

echo ""
echo "=================================================="
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "=================================================="
echo ""
echo "🔗 Lambda Function:"
echo "   https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/$FUNCTION_NAME"
echo ""
echo "📧 Check your email: $ADMIN_EMAIL"
