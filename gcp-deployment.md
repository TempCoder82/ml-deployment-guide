# Google Cloud Platform (GCP) ML Model Deployment Guide

## Deploy Your GPU-Based ML Model on Cloud Run in 30 Minutes

This guide takes you from zero GCP experience to a fully deployed, scalable ML model endpoint using Cloud Run with GPU support.

## Table of Contents

1. [Account Setup & Initial Configuration](#1-account-setup--initial-configuration)
2. [Installing and Configuring GCloud CLI](#2-installing-and-configuring-gcloud-cli)
3. [Setting Up Permissions & Service Accounts](#3-setting-up-permissions--service-accounts)
4. [Containerization Options](#4-containerization-options)
5. [Building and Pushing Your Container](#5-building-and-pushing-your-container)
6. [Deploying to Cloud Run](#6-deploying-to-cloud-run)
7. [Testing Your Endpoint](#7-testing-your-endpoint)
8. [Monitoring & Scaling](#8-monitoring--scaling)
9. [Cost Optimization](#9-cost-optimization)
10. [Troubleshooting](#10-troubleshooting)

## 1. Account Setup & Initial Configuration

### Creating Your GCP Account

1. **Navigate to [Google Cloud Console](https://console.cloud.google.com)**
   
2. **Sign in or Create a Google Account**
   - Use existing Google account or create new one
   - You'll get $300 free credits valid for 90 days

3. **Accept Terms and Set Up Billing**
   ```
   ⚠️ Don't worry! You won't be charged unless you:
   - Manually upgrade to a paid account
   - Exceed the free tier limits after upgrading
   ```

4. **Create Your First Project**
   - Click "Select a project" → "New Project"
   - Project name: `ml-model-deployment`
   - Note your Project ID (looks like: `ml-model-deployment-123456`)

### Enabling Required APIs

In the Cloud Console, enable these APIs:

```bash
# Option 1: Via Console UI
# Go to "APIs & Services" → "Enable APIs and Services"
# Search and enable each:
- Cloud Run API
- Container Registry API (or Artifact Registry API)
- Cloud Build API
- Compute Engine API (for GPU)

# Option 2: Via Command Line (after installing gcloud)
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable compute.googleapis.com
```

## 2. Installing and Configuring GCloud CLI

### Installation by Platform

#### macOS
```bash
# Using Homebrew
brew install google-cloud-sdk

# Or download directly
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

#### Linux
```bash
# Add Cloud SDK repo
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -

# Install
sudo apt-get update && sudo apt-get install google-cloud-cli
```

#### Windows
```powershell
# Download installer from:
# https://cloud.google.com/sdk/docs/install#windows

# Or use PowerShell
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe
```

### Initial Configuration

```bash
# Initialize gcloud
gcloud init

# Follow prompts:
# 1. Choose "Create a new configuration" 
# 2. Configuration name: "ml-deployment"
# 3. Choose your Google account
# 4. Select your project: ml-model-deployment
# 5. Choose default region: us-central1 (has GPU support)

# Verify configuration
gcloud config list
```

## 3. Setting Up Permissions & Service Accounts

### Understanding GCP IAM

GCP uses Identity and Access Management (IAM) to control who can do what. For deployment, we need:

1. **Your User Account**: Has owner permissions (created with project)
2. **Service Account**: For automated deployments and Cloud Run

### Creating a Service Account

```bash
# Create service account
gcloud iam service-accounts create ml-model-sa \
    --display-name="ML Model Service Account" \
    --description="Service account for ML model deployment"

# Grant necessary roles
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="ml-model-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run Invoker (to call the service)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker"

# Storage permissions (for Container Registry)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectViewer"

# Create and download key (for local development)
gcloud iam service-accounts keys create ~/ml-model-key.json \
    --iam-account=$SA_EMAIL

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=~/ml-model-key.json
```

## 4. Containerization Options

### Option A: Local Docker Build (Recommended for Development)

#### Installing Docker
```bash
# macOS
brew install docker

# Linux
sudo apt-get update
sudo apt-get install docker.io
sudo usermod -aG docker $USER  # Add yourself to docker group
newgrp docker  # Activate group membership

# Windows
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
```

#### Creating an Optimized Dockerfile

```dockerfile
# Dockerfile
# Use NVIDIA CUDA base image for GPU support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Cloud Run expects PORT environment variable
ENV PORT 8080

# Run the application
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### Multi-Stage Build for Smaller Images

```dockerfile
# Dockerfile.multistage
# Stage 1: Build environment
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04 AS builder

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Stage 2: Runtime environment
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

# Copy application
COPY . .

EXPOSE 8080
ENV PORT 8080

CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Option B: Cloud Build (Recommended for Production)

Create a `cloudbuild.yaml` file:

```yaml
# cloudbuild.yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ml-model:$COMMIT_SHA', '.']
  
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ml-model:$COMMIT_SHA']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'ml-model-service'
      - '--image=gcr.io/$PROJECT_ID/ml-model:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=8Gi'
      - '--cpu=4'
      - '--gpu=1'
      - '--gpu-type=nvidia-tesla-t4'

# Optional: Configure timeout
timeout: 1200s

# Optional: Use Artifact Registry instead of Container Registry
# images: ['us-central1-docker.pkg.dev/$PROJECT_ID/ml-models/ml-model:$COMMIT_SHA']
```

## 5. Building and Pushing Your Container

### Using Local Docker Build

```bash
# Set project ID
PROJECT_ID=$(gcloud config get-value project)

# Configure Docker for GCR
gcloud auth configure-docker

# Build your image
docker build -t gcr.io/$PROJECT_ID/ml-model:latest .

# Test locally (optional)
docker run -p 8080:8080 gcr.io/$PROJECT_ID/ml-model:latest

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/ml-model:latest
```

### Using Cloud Build

```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml .

# Or without cloudbuild.yaml
gcloud builds submit --tag gcr.io/$PROJECT_ID/ml-model:latest .
```

### Using Artifact Registry (Newer, Recommended)

```bash
# Create repository
gcloud artifacts repositories create ml-models \
    --repository-format=docker \
    --location=us-central1 \
    --description="ML model images"

# Configure Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/ml-models/ml-model:latest .
docker push us-central1-docker.pkg.dev/$PROJECT_ID/ml-models/ml-model:latest
```

## 6. Deploying to Cloud Run

### Basic Deployment

```bash
# Deploy with GPU support
gcloud run deploy ml-model-service \
    --image gcr.io/$PROJECT_ID/ml-model:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 8Gi \
    --cpu 4 \
    --gpu 1 \
    --gpu-type nvidia-tesla-t4 \
    --max-instances 10 \
    --min-instances 0 \
    --timeout 300
```

### Advanced Configuration

```bash
# With environment variables
gcloud run deploy ml-model-service \
    --image gcr.io/$PROJECT_ID/ml-model:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 16Gi \
    --cpu 8 \
    --gpu 1 \
    --gpu-type nvidia-tesla-t4 \
    --max-instances 10 \
    --min-instances 1 \
    --timeout 300 \
    --set-env-vars="MODEL_PATH=/models/my_model.pth" \
    --set-env-vars="BATCH_SIZE=32" \
    --set-env-vars="USE_CUDA=true"
```

### Using a Service YAML

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: ml-model-service
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/gpu: "1"
        run.googleapis.com/gpu-type: nvidia-tesla-t4
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containerConcurrency: 1
      timeoutSeconds: 300
      containers:
      - image: gcr.io/PROJECT_ID/ml-model:latest
        resources:
          limits:
            cpu: "8"
            memory: "16Gi"
        env:
        - name: MODEL_PATH
          value: "/models/my_model.pth"
        - name: USE_CUDA
          value: "true"
```

Deploy with:
```bash
gcloud run services replace service.yaml --region us-central1
```

## 7. Testing Your Endpoint

### Get Your Service URL

```bash
# Get service details
gcloud run services describe ml-model-service --region us-central1

# Get just the URL
SERVICE_URL=$(gcloud run services describe ml-model-service \
    --region us-central1 \
    --format 'value(status.url)')

echo "Your service URL: $SERVICE_URL"
```

### Test with cURL

```bash
# Health check
curl $SERVICE_URL/health

# Make a prediction
curl -X POST $SERVICE_URL/predict \
    -H "Content-Type: application/json" \
    -d '{"input": "your input data here"}'
```

### Test with Python

```python
import requests
import json

# Get service URL
service_url = "https://ml-model-service-xxxxx-uc.a.run.app"

# Health check
response = requests.get(f"{service_url}/health")
print(response.json())

# Make prediction
data = {"input": "your input data"}
response = requests.post(f"{service_url}/predict", json=data)
print(response.json())
```

## 8. Monitoring & Scaling

### View Logs

```bash
# Stream logs
gcloud logging read "resource.type=cloud_run_revision \
    AND resource.labels.service_name=ml-model-service" \
    --limit 50 \
    --format json

# Or use the Console
# Go to Cloud Run → ml-model-service → Logs
```

### Set Up Monitoring

```bash
# Create an alert policy for high latency
gcloud alpha monitoring policies create \
    --notification-channels=YOUR_CHANNEL_ID \
    --display-name="High Latency Alert" \
    --condition="
      {
        'displayName': 'Request latency',
        'conditionThreshold': {
          'filter': 'resource.type=\"cloud_run_revision\" 
                     AND metric.type=\"run.googleapis.com/request_latencies\"',
          'comparison': 'COMPARISON_GT',
          'thresholdValue': 5000,
          'duration': '60s'
        }
      }"
```

### Auto-scaling Configuration

```bash
# Update scaling settings
gcloud run services update ml-model-service \
    --region us-central1 \
    --min-instances 1 \
    --max-instances 100 \
    --concurrency 1 \
    --cpu-throttling \
    --update-annotations autoscaling.knative.dev/target=70
```

## 9. Cost Optimization

### Estimate Costs

```python
# cost_calculator.py
def calculate_cloud_run_gpu_cost(
    requests_per_month=10000,
    avg_request_duration_seconds=2,
    gpu_type="tesla-t4",
    region="us-central1"
):
    # Pricing as of 2024 (check current prices)
    gpu_prices = {
        "tesla-t4": 0.25,  # per GPU-hour
    }
    
    # Calculate GPU hours
    gpu_hours = (requests_per_month * avg_request_duration_seconds) / 3600
    
    # Calculate cost
    gpu_cost = gpu_hours * gpu_prices[gpu_type]
    
    # Add CPU/Memory costs (simplified)
    compute_cost = gpu_hours * 0.10  # Approximate
    
    total_cost = gpu_cost + compute_cost
    
    print(f"Estimated monthly cost: ${total_cost:.2f}")
    print(f"GPU hours: {gpu_hours:.2f}")
    print(f"Cost per request: ${total_cost/requests_per_month:.4f}")
    
calculate_cloud_run_gpu_cost()
```

### Cost Saving Tips

1. **Use Minimum Instances Wisely**
   ```bash
   # Set to 0 for true serverless (with cold starts)
   gcloud run services update ml-model-service --min-instances 0
   ```

2. **Optimize Request Concurrency**
   ```bash
   # If your model can handle multiple requests
   gcloud run services update ml-model-service --concurrency 10
   ```

3. **Use Spot/Preemptible GPUs** (when available)
   ```bash
   # Add annotation for spot instances
   --update-annotations run.googleapis.com/gpu-class=spot
   ```

## 10. Troubleshooting

### Common Issues and Solutions

#### 1. "Container failed to start"
```bash
# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Common fixes:
# - Ensure PORT environment variable is set
# - Check if all dependencies are installed
# - Verify CUDA compatibility
```

#### 2. "GPU not available"
```python
# Add to your app startup
import torch
if torch.cuda.is_available():
    print(f"GPU available: {torch.cuda.get_device_name(0)}")
else:
    print("WARNING: GPU not available, using CPU")
```

#### 3. "Out of memory"
```bash
# Increase memory allocation
gcloud run services update ml-model-service --memory 32Gi
```

#### 4. "Cold start too slow"
```bash
# Keep minimum instances warm
gcloud run services update ml-model-service --min-instances 1

# Or implement model preloading
```

### Performance Optimization

```python
# app.py - Optimized FastAPI app
from fastapi import FastAPI
import torch
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
model = None
executor = ThreadPoolExecutor(max_workers=1)

@app.on_event("startup")
async def load_model():
    global model
    # Load model in background
    loop = asyncio.get_event_loop()
    model = await loop.run_in_executor(
        executor, 
        torch.load, 
        "model.pth"
    )
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    print("Model loaded successfully")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available()
    }

@app.post("/predict")
async def predict(data: dict):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        run_inference,
        model,
        data
    )
    return {"prediction": result}

def run_inference(model, data):
    with torch.no_grad():
        # Your inference logic here
        return model(data)
```

## Next Steps

1. **Set up CI/CD**: Automate deployments with Cloud Build triggers
2. **Add authentication**: Remove `--allow-unauthenticated` for production
3. **Implement monitoring**: Set up dashboards and alerts
4. **Optimize costs**: Fine-tune scaling parameters

## Useful Commands Reference

```bash
# View all services
gcloud run services list

# View service details
gcloud run services describe ml-model-service --region us-central1

# Delete service
gcloud run services delete ml-model-service --region us-central1

# View container images
gcloud container images list

# Delete old images
gcloud container images delete gcr.io/$PROJECT_ID/ml-model:tag

# Check quotas
gcloud compute project-info describe --project=$PROJECT_ID

# View billing
gcloud billing accounts list
```

---

Congratulations! You've successfully deployed your ML model to GCP Cloud Run with GPU support. Your model is now accessible via a scalable, secure API endpoint.

[← Back to Main Guide](./README.md) | [AWS Fargate Guide →](./aws-fargate-deployment.md)
