#!/bin/bash

# AWS Lambda Deployment Script for Daily SEO Reports
# This script packages and deploys the Lambda function to AWS

set -e

echo "🚀 Deploying Search Console Agent Daily Reports to AWS Lambda"

# Configuration
FUNCTION_NAME="search-console-agent-daily-reports"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_handler.lambda_handler"
TIMEOUT=900  # 15 minutes
MEMORY=512   # MB

# Create deployment package directory
echo "📦 Creating deployment package..."
rm -rf lambda_package
mkdir -p lambda_package

# Install dependencies to package directory
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t lambda_package/ --quiet

# Copy application code
echo "📋 Copying application code..."
cp -r agents lambda_package/
cp -r api lambda_package/
cp -r core lambda_package/
cp -r db lambda_package/
cp -r models lambda_package/
cp -r schemas lambda_package/
cp -r services lambda_package/
cp -r tools lambda_package/
cp lambda_handler.py lambda_package/

# Create ZIP file
echo "🗜️  Creating ZIP archive..."
cd lambda_package
zip -r ../lambda_deployment.zip . -q
cd ..

echo "✅ Deployment package created: lambda_deployment.zip"

# Check if function exists
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null; then
    echo "📝 Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://lambda_deployment.zip \
        --region "$REGION"
else
    echo "🆕 Creating new Lambda function..."
    echo "⚠️  Make sure to:"
    echo "   1. Create an IAM role with Lambda execution permissions"
    echo "   2. Set environment variables in AWS Lambda console"
    echo "   3. Configure VPC access if RDS is in private subnet"
    
    # You'll need to create the function manually or provide IAM role ARN
    echo ""
    echo "To create the function, run:"
    echo "aws lambda create-function \\"
    echo "  --function-name $FUNCTION_NAME \\"
    echo "  --runtime $RUNTIME \\"
    echo "  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \\"
    echo "  --handler $HANDLER \\"
    echo "  --zip-file fileb://lambda_deployment.zip \\"
    echo "  --timeout $TIMEOUT \\"
    echo "  --memory-size $MEMORY \\"
    echo "  --region $REGION"
fi

# Clean up
echo "🧹 Cleaning up..."
rm -rf lambda_package

echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set environment variables in AWS Lambda console"
echo "2. Create EventBridge rule to trigger daily at 8 AM UTC:"
echo "   cron(0 8 * * ? *)"
echo "3. Test the function with a test event"
echo ""
echo "🔗 AWS Lambda Console:"
echo "https://console.aws.amazon.com/lambda/home?region=$REGION#/functions/$FUNCTION_NAME"
