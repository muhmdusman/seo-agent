#!/bin/bash

# AWS Infrastructure Setup Script
# This script creates all necessary AWS resources for the SEO Agent

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="seo-agent"
CLUSTER_NAME="${PROJECT_NAME}-cluster"
ECR_REPO="${PROJECT_NAME}-backend"
DB_INSTANCE_ID="${PROJECT_NAME}-db"

echo -e "${GREEN}=== AWS Infrastructure Setup ===${NC}"
echo "Region: $AWS_REGION"
echo "Project: $PROJECT_NAME"
echo ""

# Get AWS Account ID
echo -e "${YELLOW}Getting AWS Account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ Account ID: $AWS_ACCOUNT_ID${NC}"
echo ""

# Step 1: Create ECR Repository
echo -e "${YELLOW}Step 1/7: Creating ECR Repository...${NC}"
if aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${GREEN}✓ ECR repository already exists${NC}"
else
    aws ecr create-repository \
        --repository-name $ECR_REPO \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256
    echo -e "${GREEN}✓ ECR repository created${NC}"
fi
echo ""

# Step 2: Create ECS Cluster
echo -e "${YELLOW}Step 2/7: Creating ECS Cluster...${NC}"
if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo -e "${GREEN}✓ ECS cluster already exists${NC}"
else
    aws ecs create-cluster \
        --cluster-name $CLUSTER_NAME \
        --region $AWS_REGION
    echo -e "${GREEN}✓ ECS cluster created${NC}"
fi
echo ""

# Step 3: Create Security Groups
echo -e "${YELLOW}Step 3/7: Creating Security Groups...${NC}"

# Get default VPC
DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION)
echo "Using VPC: $DEFAULT_VPC"

# ECS Security Group
ECS_SG_NAME="ecs-tasks-sg"
if aws ec2 describe-security-groups --filters "Name=group-name,Values=$ECS_SG_NAME" --region $AWS_REGION --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null | grep -q "sg-"; then
    ECS_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$ECS_SG_NAME" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION)
    echo -e "${GREEN}✓ ECS security group already exists: $ECS_SG_ID${NC}"
else
    ECS_SG_ID=$(aws ec2 create-security-group \
        --group-name $ECS_SG_NAME \
        --description "Security group for ECS tasks" \
        --vpc-id $DEFAULT_VPC \
        --region $AWS_REGION \
        --query 'GroupId' \
        --output text)
    
    # Allow HTTP traffic on port 8000
    aws ec2 authorize-security-group-ingress \
        --group-id $ECS_SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region $AWS_REGION
    
    echo -e "${GREEN}✓ ECS security group created: $ECS_SG_ID${NC}"
fi

# RDS Security Group
RDS_SG_NAME="rds-sg"
if aws ec2 describe-security-groups --filters "Name=group-name,Values=$RDS_SG_NAME" --region $AWS_REGION --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null | grep -q "sg-"; then
    RDS_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$RDS_SG_NAME" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION)
    echo -e "${GREEN}✓ RDS security group already exists: $RDS_SG_ID${NC}"
else
    RDS_SG_ID=$(aws ec2 create-security-group \
        --group-name $RDS_SG_NAME \
        --description "Security group for RDS" \
        --vpc-id $DEFAULT_VPC \
        --region $AWS_REGION \
        --query 'GroupId' \
        --output text)
    
    # Allow PostgreSQL from ECS security group
    aws ec2 authorize-security-group-ingress \
        --group-id $RDS_SG_ID \
        --protocol tcp \
        --port 5432 \
        --source-group $ECS_SG_ID \
        --region $AWS_REGION
    
    echo -e "${GREEN}✓ RDS security group created: $RDS_SG_ID${NC}"
fi
echo ""

# Step 4: Create IAM Roles
echo -e "${YELLOW}Step 4/7: Creating IAM Roles...${NC}"

# ECS Task Execution Role
EXECUTION_ROLE_NAME="ecsTaskExecutionRole"
if aws iam get-role --role-name $EXECUTION_ROLE_NAME >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Execution role already exists${NC}"
else
    aws iam create-role \
        --role-name $EXECUTION_ROLE_NAME \
        --assume-role-policy-document '{
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
          }]
        }'
    
    aws iam attach-role-policy \
        --role-name $EXECUTION_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    
    echo -e "${GREEN}✓ Execution role created${NC}"
fi

# ECS Task Role
TASK_ROLE_NAME="ecsTaskRole"
if aws iam get-role --role-name $TASK_ROLE_NAME >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Task role already exists${NC}"
else
    aws iam create-role \
        --role-name $TASK_ROLE_NAME \
        --assume-role-policy-document '{
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
          }]
        }'
    
    echo -e "${GREEN}✓ Task role created${NC}"
fi

# ECS Events Role (for EventBridge)
EVENTS_ROLE_NAME="ecsEventsRole"
if aws iam get-role --role-name $EVENTS_ROLE_NAME >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Events role already exists${NC}"
else
    aws iam create-role \
        --role-name $EVENTS_ROLE_NAME \
        --assume-role-policy-document '{
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "events.amazonaws.com"},
            "Action": "sts:AssumeRole"
          }]
        }'
    
    aws iam attach-role-policy \
        --role-name $EVENTS_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceEventsRole
    
    echo -e "${GREEN}✓ Events role created${NC}"
fi
echo ""

# Step 5: Create CloudWatch Log Group
echo -e "${YELLOW}Step 5/7: Creating CloudWatch Log Group...${NC}"
if aws logs describe-log-groups --log-group-name-prefix "/ecs/$PROJECT_NAME-backend" --region $AWS_REGION --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q "/ecs/$PROJECT_NAME-backend"; then
    echo -e "${GREEN}✓ Log group already exists${NC}"
else
    aws logs create-log-group \
        --log-group-name "/ecs/$PROJECT_NAME-backend" \
        --region $AWS_REGION
    echo -e "${GREEN}✓ Log group created${NC}"
fi
echo ""

# Step 6: Output Configuration
echo -e "${YELLOW}Step 6/7: Saving Configuration...${NC}"
cat > deployment/config.env << EOF
# Auto-generated AWS Configuration
# Generated on: $(date)

AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
PROJECT_NAME=$PROJECT_NAME
CLUSTER_NAME=$CLUSTER_NAME
ECR_REPO=$ECR_REPO
ECS_SG_ID=$ECS_SG_ID
RDS_SG_ID=$RDS_SG_ID
DEFAULT_VPC=$DEFAULT_VPC

# ECR Repository URI
ECR_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO

# IAM Role ARNs
EXECUTION_ROLE_ARN=arn:aws:iam::$AWS_ACCOUNT_ID:role/$EXECUTION_ROLE_NAME
TASK_ROLE_ARN=arn:aws:iam::$AWS_ACCOUNT_ID:role/$TASK_ROLE_NAME
EVENTS_ROLE_ARN=arn:aws:iam::$AWS_ACCOUNT_ID:role/$EVENTS_ROLE_NAME
EOF
echo -e "${GREEN}✓ Configuration saved to deployment/config.env${NC}"
echo ""

# Step 7: Summary
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo ""
echo "Resources Created:"
echo "  ✓ ECR Repository: $ECR_REPO"
echo "  ✓ ECS Cluster: $CLUSTER_NAME"
echo "  ✓ Security Groups: $ECS_SG_ID, $RDS_SG_ID"
echo "  ✓ IAM Roles: Created"
echo "  ✓ CloudWatch Logs: /ecs/$PROJECT_NAME-backend"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Create RDS database (if not done)"
echo "  2. Run: ./build-and-push.sh"
echo "  3. Run: ./deploy-ecs.sh"
echo ""
echo -e "${GREEN}Configuration saved in: deployment/config.env${NC}"
