# AWS Fargate ML Model Deployment Guide

## Deploy Your GPU-Based ML Model on AWS ECS with Fargate

This comprehensive guide walks you through deploying a GPU-accelerated ML model on AWS using ECS (Elastic Container Service) with Fargate compute.

## Table of Contents

1. [Account Setup & Initial Configuration](#1-account-setup--initial-configuration)
2. [Installing and Configuring AWS CLI](#2-installing-and-configuring-aws-cli)
3. [IAM Roles and Permissions Setup](#3-iam-roles-and-permissions-setup)
4. [Container Registry (ECR) Setup](#4-container-registry-ecr-setup)
5. [Containerization and Image Building](#5-containerization-and-image-building)
6. [ECS Cluster and Task Definition](#6-ecs-cluster-and-task-definition)
7. [Service Deployment with Fargate](#7-service-deployment-with-fargate)
8. [Load Balancer and Networking](#8-load-balancer-and-networking)
9. [Testing and Monitoring](#9-testing-and-monitoring)
10. [Auto-scaling and Cost Optimization](#10-auto-scaling-and-cost-optimization)

## 1. Account Setup & Initial Configuration

### Creating Your AWS Account

1. **Navigate to [AWS Console](https://aws.amazon.com)**

2. **Create a New Account**
   - Click "Create an AWS Account"
   - Provide email, password, and account name
   - Choose "Personal" or "Professional" account type

3. **Billing Information**
   ```
   ⚠️ AWS Free Tier includes:
   - 750 hours of t2.micro EC2 instances
   - 5 GB of ECR storage
   - Limited Fargate compute hours
   - Valid for 12 months
   ```

4. **Identity Verification**
   - Phone verification required
   - Credit card for billing (won't charge within free tier)

5. **Choose Support Plan**
   - Select "Basic Plan" (free)

### Initial Security Setup

```bash
# IMPORTANT: Enable MFA on root account
# Go to IAM → Security credentials → MFA
# Use virtual MFA device (Google Authenticator, etc.)
```

### Create IAM User for CLI Access

1. **Navigate to IAM Console**
   ```
   Services → IAM → Users → Add User
   ```

2. **Create User**
   - Username: `ml-deploy-user`
   - Access type: ✅ Programmatic access
   - Permissions: `AdministratorAccess` (we'll restrict later)

3. **Save Credentials**
   ```
   ⚠️ Save these securely - shown only once!
   Access Key ID: AKIAIOSFODNN7EXAMPLE
   Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   ```

## 2. Installing and Configuring AWS CLI

### Installation by Platform

#### macOS
```bash
# Using Homebrew
brew install awscli

# Or using pip
pip3 install awscli --upgrade --user

# Or download directly
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

#### Linux
```bash
# Using package manager (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install awscli

# Or download directly
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

#### Windows
```powershell
# Download MSI installer
# https://awscli.amazonaws.com/AWSCLIV2.msi

# Or using chocolatey
choco install awscli

# Or using pip
pip install awscli
```

### Configure AWS CLI

```bash
# Configure with your credentials
aws configure

# Enter when prompted:
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json

# Verify configuration
aws sts get-caller-identity
```

### Setting Up Multiple Profiles (Optional)

```bash
# Add a named profile
aws configure --profile ml-deployment

# Use specific profile
export AWS_PROFILE=ml-deployment
# or
aws s3 ls --profile ml-deployment
```

## 3. IAM Roles and Permissions Setup

### Understanding AWS IAM for ECS

We need several IAM roles:
1. **Task Execution Role**: Allows ECS to pull images and write logs
2. **Task Role**: Permissions for your container to access AWS services
3. **Service Role**: Allows ECS to manage load balancers

### Create Task Execution Role

```bash
# Create trust policy file
cat > ecs-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-trust-policy.json

# Attach managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### Create Task Role (for your application)

```bash
# Create application role
aws iam create-role \
  --role-name ml-model-task-role \
  --assume-role-policy-document file://ecs-trust-policy.json

# Create custom policy for S3 access (if needed)
cat > ml-model-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-ml-models-bucket/*",
        "arn:aws:s3:::your-ml-models-bucket"
      ]
    }
  ]
}
EOF

# Create and attach policy
aws iam create-policy \
  --policy-name ml-model-policy \
  --policy-document file://ml-model-policy.json

aws iam attach-role-policy \
  --role-name ml-model-task-role \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/ml-model-policy
```

## 4. Container Registry (ECR) Setup

### Create ECR Repository

```bash
# Create repository
aws ecr create-repository \
  --repository-name ml-model \
  --image-scanning-configuration scanOnPush=true \
  --region us-east-1

# Get repository URI
export ECR_URI=$(aws ecr describe-repositories \
  --repository-names ml-model \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR URI: $ECR_URI"
```

### Configure Docker for ECR

```bash
# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URI

# Alternative for older Docker versions
$(aws ecr get-login --no-include-email --region us-east-1)
```

## 5. Containerization and Image Building

### GPU-Optimized Dockerfile for AWS

```dockerfile
# Dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI (for S3 model downloads if needed)
RUN pip3 install awscli

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# ECS uses dynamic port mapping
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Build and Push to ECR

```bash
# Build image
docker build -t ml-model:latest .

# Tag for ECR
docker tag ml-model:latest $ECR_URI:latest

# Push to ECR
docker push $ECR_URI:latest

# Tag with version
docker tag ml-model:latest $ECR_URI:v1.0.0
docker push $ECR_URI:v1.0.0
```

### Automated Build with CodeBuild (Optional)

```yaml
# buildspec.yml
version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
      - IMAGE_TAG=${CODEBUILD_RESOLVED_SOURCE_VERSION:=latest}
  
  build:
    commands:
      - echo Build started on `date`
      - docker build -t $ECR_REPOSITORY_URI:latest .
      - docker tag $ECR_REPOSITORY_URI:latest $ECR_REPOSITORY_URI:$IMAGE_TAG
  
  post_build:
    commands:
      - echo Build completed on `date`
      - docker push $ECR_REPOSITORY_URI:latest
      - docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
```

## 6. ECS Cluster and Task Definition

### Create ECS Cluster

```bash
# Create cluster
aws ecs create-cluster \
  --cluster-name ml-model-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1 \
    capacityProvider=FARGATE_SPOT,weight=4
```

### Create Task Definition

```json
{
  "family": "ml-model-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "4096",
  "memory": "30720",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ml-model-task-role",
  "containerDefinitions": [
    {
      "name": "ml-model",
      "image": "YOUR_ECR_URI:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "resourceRequirements": [
        {
          "type": "GPU",
          "value": "1"
        }
      ],
      "environment": [
        {
          "name": "USE_GPU",
          "value": "true"
        },
        {
          "name": "MODEL_PATH",
          "value": "/models/model.pth"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ml-model",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "runtimePlatform": {
    "operatingSystemFamily": "LINUX",
    "cpuArchitecture": "X86_64"
  }
}
```

Register the task definition:

```bash
# Save above JSON as task-definition.json
# Replace YOUR_ACCOUNT and YOUR_ECR_URI

# Create CloudWatch log group
aws logs create-log-group --log-group-name /ecs/ml-model

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

## 7. Service Deployment with Fargate

### Create VPC and Networking (if needed)

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ml-model-vpc}]'

# Get VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ml-model-vpc" --query 'Vpcs[0].VpcId' --output text)

# Create subnets
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create Internet Gateway
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=ml-model-igw}]'
IGW_ID=$(aws ec2 describe-internet-gateways --filters "Name=tag:Name,Values=ml-model-igw" --query 'InternetGateways[0].InternetGatewayId' --output text)

# Attach to VPC
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
```

### Create Application Load Balancer

```bash
# Create security group for ALB
aws ec2 create-security-group \
  --group-name ml-model-alb-sg \
  --description "Security group for ML model ALB" \
  --vpc-id $VPC_ID

ALB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=ml-model-alb-sg" --query 'SecurityGroups[0].GroupId' --output text)

# Allow HTTP traffic
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Create ALB
aws elbv2 create-load-balancer \
  --name ml-model-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups $ALB_SG_ID \
  --scheme internet-facing \
  --type application
```

### Create ECS Service

```bash
# Create service
aws ecs create-service \
  --cluster ml-model-cluster \
  --service-name ml-model-service \
  --task-definition ml-model-task:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxxxx,subnet-yyyyy],
    securityGroups=[$TASK_SG_ID],
    assignPublicIp=ENABLED
  }" \
  --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=ml-model,containerPort=8080" \
  --health-check-grace-period-seconds 60
```

### Service Definition with Auto-scaling

```json
{
  "serviceName": "ml-model-service",
  "taskDefinition": "ml-model-task",
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:...",
      "containerName": "ml-model",
      "containerPort": 8080
    }
  ],
  "desiredCount": 2,
  "launchType": "FARGATE",
  "platformVersion": "LATEST",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxxxx", "subnet-yyyyy"],
      "securityGroups": ["sg-xxxxx"],
      "assignPublicIp": "ENABLED"
    }
  },
  "deploymentConfiguration": {
    "minimumHealthyPercent": 100,
    "maximumPercent": 200
  },
  "capacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE",
      "weight": 1,
      "base": 1
    },
    {
      "capacityProvider": "FARGATE_SPOT",
      "weight": 3
    }
  ]
}
```

## 8. Load Balancer and Networking

### Complete ALB Setup

```bash
# Create target group
aws elbv2 create-target-group \
  --name ml-model-targets \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-enabled \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
```

### Configure HTTPS (Production)

```bash
# Request certificate from ACM
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS

# After validation, create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=$CERT_ARN \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
```

## 9. Testing and Monitoring

### Get Endpoint URL

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names ml-model-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "Your endpoint: http://$ALB_DNS"
```

### Test Your Deployment

```bash
# Health check
curl http://$ALB_DNS/health

# Test prediction endpoint
curl -X POST http://$ALB_DNS/predict \
  -H "Content-Type: application/json" \
  -d '{"input": "test data"}'
```

### Monitor with CloudWatch

```bash
# View logs
aws logs tail /ecs/ml-model --follow

# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name ml-model-dashboard \
  --dashboard-body file://dashboard.json
```

Dashboard configuration:
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ECS", "CPUUtilization", "ServiceName", "ml-model-service", "ClusterName", "ml-model-cluster"],
          [".", "MemoryUtilization", ".", ".", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ECS Service Metrics"
      }
    }
  ]
}
```

### Set Up Alarms

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name ml-model-high-cpu \
  --alarm-description "Alarm when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ServiceName,Value=ml-model-service Name=ClusterName,Value=ml-model-cluster
```

## 10. Auto-scaling and Cost Optimization

### Configure Auto-scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/ml-model-cluster/ml-model-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --policy-name ml-model-cpu-scaling \
  --service-namespace ecs \
  --resource-id service/ml-model-cluster/ml-model-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

### Cost Optimization Strategies

#### 1. Use Fargate Spot
```bash
# Update service to use more Spot instances
aws ecs update-service \
  --cluster ml-model-cluster \
  --service ml-model-service \
  --capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1,base=1 \
    capacityProvider=FARGATE_SPOT,weight=4
```

#### 2. Schedule-based Scaling
```bash
# Scale down during off-hours
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/ml-model-cluster/ml-model-service \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name scale-down-night \
  --schedule "cron(0 22 * * ? *)" \
  --scalable-target-action MinCapacity=0,MaxCapacity=1

# Scale up during business hours
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/ml-model-cluster/ml-model-service \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name scale-up-morning \
  --schedule "cron(0 8 * * ? *)" \
  --scalable-target-action MinCapacity=2,MaxCapacity=10
```

#### 3. Cost Calculator

```python
# fargate_cost_calculator.py
def calculate_fargate_cost(
    vcpu=4,  # 4 vCPU
    memory=30,  # 30 GB
    gpu_count=1,
    hours_per_month=730,
    spot_percentage=0.7
):
    # Fargate pricing (check current rates)
    vcpu_price = 0.04048  # per vCPU-hour
    memory_price = 0.004445  # per GB-hour
    gpu_price = 0.7  # per GPU-hour (estimate)
    
    # Calculate base costs
    cpu_cost = vcpu * vcpu_price * hours_per_month
    memory_cost = memory * memory_price * hours_per_month
    gpu_cost = gpu_count * gpu_price * hours_per_month
    
    # Apply Spot discount (typically 70% off)
    spot_discount = 0.3
    spot_hours = hours_per_month * spot_percentage
    on_demand_hours = hours_per_month * (1 - spot_percentage)
    
    total_cost = (cpu_cost + memory_cost + gpu_cost) * (
        (on_demand_hours / hours_per_month) + 
        (spot_hours / hours_per_month * spot_discount)
    )
    
    print(f"Monthly Fargate Cost Estimate:")
    print(f"On-Demand Hours: {on_demand_hours:.0f}")
    print(f"Spot Hours: {spot_hours:.0f}")
    print(f"Total Cost: ${total_cost:.2f}")
    print(f"Per-hour Cost: ${total_cost/hours_per_month:.3f}")
    
calculate_fargate_cost()
```

## Troubleshooting

### Common Issues

#### 1. Task Fails to Start
```bash
# Check task stopped reason
aws ecs describe-tasks \
  --cluster ml-model-cluster \
  --tasks $(aws ecs list-tasks --cluster ml-model-cluster --service-name ml-model-service --query 'taskArns[0]' --output text)

# Common fixes:
# - Check execution role permissions
# - Verify image exists in ECR
# - Check CloudWatch logs
```

#### 2. Health Checks Failing
```bash
# Update health check settings
aws elbv2 modify-target-group \
  --target-group-arn $TARGET_GROUP_ARN \
  --health-check-interval-seconds 60 \
  --health-check-timeout-seconds 30 \
  --healthy-threshold-count 2
```

#### 3. Out of Memory
```bash
# Update task definition with more memory
# Edit task-definition.json to increase memory
aws ecs register-task-definition --cli-input-json file://task-definition-updated.json

# Update service
aws ecs update-service \
  --cluster ml-model-cluster \
  --service ml-model-service \
  --task-definition ml-model-task:2
```

## Clean Up Resources

```bash
# Delete in reverse order to avoid dependencies

# 1. Delete service
aws ecs update-service \
  --cluster ml-model-cluster \
  --service ml-model-service \
  --desired-count 0

aws ecs delete-service \
  --cluster ml-model-cluster \
  --service ml-model-service

# 2. Delete ALB
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# 3. Delete target group
aws elbv2 delete-target-group --target-group-arn $TARGET_GROUP_ARN

# 4. Delete cluster
aws ecs delete-cluster --cluster ml-model-cluster

# 5. Delete ECR repository
aws ecr delete-repository \
  --repository-name ml-model \
  --force

# 6. Delete CloudWatch logs
aws logs delete-log-group --log-group-name /ecs/ml-model
```

## Production Checklist

- [ ] Enable container insights for detailed monitoring
- [ ] Set up centralized logging with CloudWatch or ELK
- [ ] Implement circuit breakers in your application
- [ ] Use secrets manager for sensitive data
- [ ] Enable AWS WAF on your ALB
- [ ] Set up backup and disaster recovery
- [ ] Configure cross-region replication for ECR
- [ ] Implement blue-green deployments
- [ ] Set up cost alerts and budgets
- [ ] Regular security audits with AWS Security Hub

---

Congratulations! You've successfully deployed your ML model to AWS Fargate with GPU support. Your model is now running in a scalable, managed container environment.

[← Back to Main Guide](./README.md) | [Azure Guide →](./azure-deployment.md)