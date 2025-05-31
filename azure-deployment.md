# Azure Container Instances (ACI) ML Model Deployment Guide

*This guide is intended for readers who have never deployed an ML model before. It provides detailed, step-by-step instructions to deploy a GPU-accelerated machine learning (ML) model using Microsoft Azure Container Instances (ACI).*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Prerequisites](#2-prerequisites)
3. [Overview of the Deployment Process](#3-overview-of-the-deployment-process)
4. [Step 1: Set Up an Azure Account and Environment](#4-step-1-set-up-an-azure-account-and-environment)
5. [Step 2: Install and Configure Azure CLI](#5-step-2-install-and-configure-azure-cli)
6. [Step 3: Create a Resource Group and Required Permissions](#6-step-3-create-a-resource-group-and-required-permissions)
7. [Step 4: Develop and Containerize Your ML Model](#7-step-4-develop-and-containerize-your-ml-model)

   1. [4.1: Develop a Sample ML Model API](#71-develop-a-sample-ml-model-api)
   2. [4.2: Write a Dockerfile](#72-write-a-dockerfile)
   3. [4.3: Build and Test Your Docker Image Locally](#73-build-and-test-your-docker-image-locally)
8. [Step 5: Push Docker Image to Azure Container Registry](#8-step-5-push-docker-image-to-azure-container-registry)

   1. [5.1: Create an Azure Container Registry (ACR)](#81-create-an-azure-container-registry-acr)
   2. [5.2: Log In to ACR and Push the Image](#82-log-in-to-acr-and-push-the-image)
9. [Step 6: Deploy to Azure Container Instances (ACI)](#9-step-6-deploy-to-azure-container-instances-aci)

   1. [6.1: Choose a GPU-Enabled Region](#91-choose-a-gpu-enabled-region)
   2. [6.2: Deploy ACI with GPU Resources](#92-deploy-aci-with-gpu-resources)
   3. [6.3: Verify and Test the Deployment](#93-verify-and-test-the-deployment)
10. [Step 7: Networking, Load Balancing, and Custom Domain](#10-step-7-networking-load-balancing-and-custom-domain)

    1. [7.1: Configure Container Ports and Public IP](#101-configure-container-ports-and-public-ip)
    2. [7.2: (Optional) Use Azure Application Gateway or Load Balancer](#102-optional-use-azure-application-gateway-or-load-balancer)
    3. [7.3: (Optional) Map a Custom Domain](#103-optional-map-a-custom-domain)
11. [Step 8: Monitoring and Logging](#11-step-8-monitoring-and-logging)

    1. [8.1: Enable Azure Monitor](#111-enable-azure-monitor)
    2. [8.2: Configure Application Insights](#112-configure-application-insights)
    3. [8.3: Review Logs and Metrics](#113-review-logs-and-metrics)
12. [Step 9: Scaling and Maintenance](#12-step-9-scaling-and-maintenance)

    1. [9.1: Manual Scaling](#121-manual-scaling)
    2. [9.2: Auto-Scaling Considerations](#122-auto-scaling-considerations)
    3. [9.3: Updating the Container Image](#123-updating-the-container-image)
13. [Step 10: Cost Optimization and Best Practices](#13-step-10-cost-optimization-and-best-practices)
14. [Troubleshooting Common Issues](#14-troubleshooting-common-issues)

---

## 1. Introduction

Deploying a machine learning model into production involves packaging your trained model and serving it so that other services or users can send requests and receive predictions. Microsoft Azure Container Instances (ACI) offers a straightforward way to run Docker containers in the cloud without managing the underlying virtual machines. In this guide, you will learn how to:

* Develop a simple ML model API that serves predictions.
* Containerize your ML application with Docker.
* Push the container to Azure Container Registry (ACR).
* Deploy the container in Azure Container Instances using GPU resources.
* Configure networking, monitoring, and scaling for your ML service.

By the end of this guide, you will have a fully functional, GPU-enabled ML service running in Azure, accessible via a REST API. This guide assumes no prior knowledge of Azure or containerization.

---

## 2. Prerequisites

Before starting, ensure you have the following:

1. **Azure Account:** If you don’t have one, go to [Azure Portal](https://azure.microsoft.com) and sign up for a free account. The free tier provides \$200 credit for 30 days, along with some always-free services.
2. **Basic Command Line Knowledge:** Comfort with running commands in a terminal (macOS Terminal, Windows PowerShell, or Linux shell).
3. **Python 3.x Installed Locally:** Used to build and test your ML model API. You can download Python from [python.org](https://www.python.org/downloads/).
4. **Docker Installed Locally:** To containerize your application, install Docker Desktop (macOS/Windows) or Docker Engine (Linux). Follow instructions at [Docker Installation Guide](https://docs.docker.com/get-docker/).
5. **Basic Git Knowledge (Optional):** If you want to store your code in a Git repository.

---

## 3. Overview of the Deployment Process

1. **Set Up Azure Environment**

   * Create an Azure account and install Azure CLI.
   * Create a resource group and service principal (optional for automation).
2. **Develop and Containerize ML Model**

   * Write a simple ML model served via a REST API (e.g., using Flask or FastAPI).
   * Create a Dockerfile to package the application, including the model and its dependencies.
3. **Push Docker Image to ACR**

   * Create an Azure Container Registry (ACR).
   * Tag and push your local Docker image to ACR.
4. **Deploy to ACI**

   * Choose a GPU-enabled Azure region.
   * Deploy the container to ACI, specifying GPU SKU if needed.
   * Obtain a public endpoint and test the model API.
5. **Configure Networking and Monitoring**

   * Expose ports, optionally set up load balancing or custom domains.
   * Enable Azure Monitor and Application Insights to track logs and metrics.
6. **Scaling and Maintenance**

   * Understand how to scale ACI containers.
   * Update your container when the model or code changes.
7. **Cost Optimization**

   * Monitor usage and spending.
   * Use budgets and cost alerts.

---

## 4. Step 1: Set Up an Azure Account and Environment

### 4.1 Create an Azure Account

1. **Visit Azure Portal**: Open your browser and go to [https://azure.microsoft.com](https://azure.microsoft.com).
2. **Start Free Trial**: Click "Start free" to create a new account. You will need to provide a Microsoft account (or create one), a phone number for identity verification, and a credit card (for identity purposes; you won’t be charged during the trial unless you upgrade).
3. **Activate Your Subscription**: After verification, you’ll receive \$200 credit valid for 30 days. You can also access 12 months of free services and some always-free services.

### 4.2 Understand Azure Terminology

* **Azure Subscription**: A billing entity. All Azure resources you create are billed under a subscription.
* **Resource Group**: A logical container for related Azure resources (e.g., compute instances, storage accounts, container registries). It helps organize and manage resources collectively.
* **Azure Region**: A geographical location where Azure data centers are available (e.g., East US, West Europe, Southeast Asia).
* **Resource**: An individual Azure service you create (e.g., Azure Container Registry, Azure Container Instance).

---

## 5. Step 2: Install and Configure Azure CLI

Azure CLI is a command-line tool to interact with Azure resources. We will use it extensively for creating and managing resources.

### 5.1 Install Azure CLI

#### macOS (Homebrew)

```bash
brew update && brew install azure-cli
```

Or, use the direct install script:

```bash
curl -L https://aka.ms/InstallAzureCli | bash
```

#### Linux (Ubuntu/Debian)

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

#### Windows (PowerShell)

Using MSI installer:

```powershell
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'
```

Or using Chocolatey:

```powershell
choco install azure-cli
```

### 5.2 Log In to Azure

After installation, open a terminal or PowerShell and run:

```bash
az login
```

* A browser window will open prompting you to sign in to your Azure account.
* After successful login, the CLI will list available subscriptions associated with your account.

### 5.3 Set Default Subscription and Defaults

If you have multiple subscriptions, pick the one to use:

```bash
# List subscriptions
az account list --output table

# Set the default subscription (replace "<SUBSCRIPTION_NAME>")
az account set --subscription "<SUBSCRIPTION_NAME>"

# Verify current subscription
az account show --output table
```

Configure some defaults to avoid repeating parameters:

```bash
az configure --defaults group=ml-deployment-rg location=eastus
```

* `group=ml-deployment-rg`: Default Resource Group.
* `location=eastus`: Default Azure region.

### 5.4 (Optional) Create a Service Principal for Automation

A Service Principal (SP) is an identity used by applications or automation tools to access Azure resources. Creating an SP allows deployments via scripts without using your personal Azure credentials.

```bash
# Create service principal with Contributor role for the subscription (replace placeholders if needed)
az ad sp create-for-rbac \
  --name ml-deployment-sp \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)
```

The output will look like:

```json
{
  "appId": "<APP_ID>",
  "displayName": "ml-deployment-sp",
  "password": "<PASSWORD>",
  "tenant": "<TENANT_ID>"
}
```

Store these values securely. To log in using SP:

```bash
az login --service-principal \
  --username $APP_ID \
  --password $PASSWORD \
  --tenant $TENANT_ID
```

---

## 6. Step 3: Create a Resource Group and Required Permissions

A Resource Group logically groups your Azure resources. Create a dedicated resource group for your ML deployment.

### 6.1 Create a Resource Group

```bash
az group create \
  --name ml-deployment-rg \
  --location eastus
```

* `ml-deployment-rg`: Name of the Resource Group. You can choose any name, but keep it simple.
* `eastus`: Azure region. Choose a region that supports GPU-enabled instances (e.g., eastus, westeurope, southeastasia).

### 6.2 List Available Regions for GPU-Enabled Container Instances

Not all regions offer GPU-enabled ACI. To find supported regions:

```bash
# List popular US regions. You can explore similarly for other regions.
az account list-locations --query "[?contains(name, 'eastus') || contains(name, 'westeurope') || contains(name, 'southeastasia')].{Name:name, DisplayName:displayName}" --output table
```

Common GPU-enabled regions:

* East US (`eastus`)
* West US 2 (`westus2`)
* West Europe (`westeurope`)
* North Europe (`northeurope`)
* Southeast Asia (`southeastasia`)

> **Note:** Azure occasionally updates supported SKUs per region. Refer to [Azure Container Instances Regions](https://docs.microsoft.com/azure/container-instances/container-instances-quotas) for the latest information.

### 6.3 Set Up Permissions (Managed Identity or Service Principal)

If you plan for automation or CI/CD, assign permissions to a Service Principal or User-Assigned Managed Identity. For manual deployments, your logged-in user will suffice.

#### Create a User-Assigned Managed Identity

A managed identity can be used by ACI to pull from a private container registry or access other resources. This is optional for a simple tutorial.

```bash
# Create managed identity in the resource group
az identity create \
  --resource-group ml-deployment-rg \
  --name ml-deployment-identity

# Capture identity details for later use
IDENTITY_ID=$(az identity show --resource-group ml-deployment-rg --name ml-deployment-identity --query id --output tsv)
IDENTITY_CLIENT_ID=$(az identity show --resource-group ml-deployment-rg --name ml-deployment-identity --query clientId --output tsv)
```

You can assign this identity roles (e.g., ACR Pull) if needed.

---

## 7. Step 4: Develop and Containerize Your ML Model

In this section, we will build a simple machine learning model (e.g., a classifier or regression) and expose it via a REST API. We will then write a `Dockerfile` to containerize the application.

> **Why an API?**: Packaging your model behind an API (e.g., HTTP endpoint) allows any client (such as a web app or another service) to send data and receive model predictions.

### 7.1 Develop a Sample ML Model API

We will use Python and Flask (a minimal web framework) to build a simple API that loads a pre-trained model and returns predictions. For illustration, assume you already have a trained model saved as `model.joblib`. If not, we will include code to train a very basic model.

#### 7.1.1 Create a Project Directory

On your local machine, create a directory for this project:

```bash
mkdir ml-aci-demo
cd ml-aci-demo
```

#### 7.1.2 Set Up a Python Virtual Environment

Creating a virtual environment ensures isolated dependencies:

```bash
python3 -m venv venv
# Activate the venv
# macOS/Linux:
source venv/bin/activate
# Windows (PowerShell):
# .\venv\Scripts\Activate.ps1
```

Install required Python packages:

```bash
pip install flask scikit-learn joblib pandas
```

* **flask**: Lightweight web framework.
* **scikit-learn**: For simple ML models (e.g., logistic regression).
* **joblib**: To serialize (save/load) model files.
* **pandas**: (Optional) For data handling.

#### 7.1.3 (Optional) Train a Simple Model

If you don’t already have a trained model, you can quickly train one. For example, a logistic regression on the Iris dataset.

Create a file named `train_model.py` with the following content:

```python
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
import joblib
import os

# Load Iris dataset
iris = load_iris()
X, y = iris.data, iris.target

# Train a simple logistic regression model
model = LogisticRegression(max_iter=200)
model.fit(X, y)

# Ensure models directory exists
os.makedirs('models', exist_ok=True)

# Save the model
model_path = os.path.join('models', 'iris_model.joblib')
joblib.dump(model, model_path)
print(f"Model saved to {model_path}")
```

Run the training script:

```bash
python train_model.py
```

This creates a `models/iris_model.joblib` file.

#### 7.1.4 Create the Flask App

Create a file named `app.py`:

```python
from flask import Flask, request, jsonify
import joblib
import numpy as np
import os

app = Flask(__name__)

# Load the trained model on startup
MODEL_PATH = os.path.join('models', 'iris_model.joblib')
model = joblib.load(MODEL_PATH)

@app.route('/')
def home():
    return "Welcome to the Iris Classification API!" , 200

@app.route('/predict', methods=['POST'])
def predict():
    """
    Expects a JSON payload: {"data": [[5.1, 3.5, 1.4, 0.2], ...]}
    Returns predicted class indices.
    """
    try:
        data = request.get_json()
        features = np.array(data['data'])  # Expecting list of lists
        preds = model.predict(features).tolist()
        return jsonify({'predictions': preds}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Listen on all interfaces (0.0.0.0) so Docker can map ports
    app.run(host='0.0.0.0', port=5000)
```

Explanation:

* On startup, the Flask app loads the pre-trained model from `models/iris_model.joblib`.
* The `/predict` endpoint expects a JSON payload with a key `data`, containing an array of feature vectors. It returns predictions as JSON.

#### 7.1.5 Test the API Locally

Ensure you are in the `ml-aci-demo` directory and your virtual environment is activated.

```bash
python app.py
```

In another terminal, test using `curl`:

```bash
curl -X POST http://127.0.0.1:5000/predict \
     -H "Content-Type: application/json" \
     -d '{"data": [[5.1, 3.5, 1.4, 0.2]]}'
```

Expected response:

```json
{
  "predictions": [0]
}
```

* Class index `0` corresponds to the Iris-Setosa class.

Stop the Flask server (Ctrl+C).

> **Note:** If you have a different ML model (e.g., TensorFlow, PyTorch), the approach is similar: write a script that loads the model and exposes an inference endpoint.

---

### 7.2 Write a Dockerfile

Next, we will create a Dockerfile to build a container image containing our Flask app and trained model.

Create a file named `Dockerfile` (no file extension) in the `ml-aci-demo` directory:

```dockerfile
# Use official Python image with slim-buster variant for smaller size
FROM python:3.9-slim-buster

# Set environment variables to avoid Python buffering and disable .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy source code
COPY app.py /app/
COPY train_model.py /app/
COPY models/ /app/models/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install flask scikit-learn joblib pandas

# Expose port 5000 for the Flask app
EXPOSE 5000

# Default command to run the Flask app
CMD ["python", "app.py"]
```

Explanation:

1. **Base Image:** `python:3.9-slim-buster` – a lightweight Python image.
2. **Environment Variables:** Disable writing `.pyc` files and enable unbuffered logs.
3. **Work Directory:** `/app` inside the container.
4. **Copy Files:** Copy the Python scripts (`app.py`, `train_model.py`) and `models/` directory into `/app` in the container.
5. **Install Dependencies:** Run `pip install` to install necessary Python packages.
6. **Expose Port:** Inform Docker that the container listens on port 5000.
7. **CMD:** Default command to start the Flask app when the container runs.

> **Tip:** For production, consider using a production-ready server like Gunicorn instead of the Flask development server. However, for demonstration and simplicity, Flask’s built-in server is acceptable.

---

### 7.3 Build and Test Your Docker Image Locally

1. **Build the Docker image**

   From the `ml-aci-demo` directory, run:

   ```bash
   ```

docker build -t ml-aci-demo\:latest .

````

   - `-t ml-aci-demo:latest`: Tags the image as `ml-aci-demo` with tag `latest`.

2. **Run the Docker container locally**

   ```bash
docker run -d --name ml-aci-demo-container -p 5000:5000 ml-aci-demo:latest
````

* `-d`: Run container in detached mode.
* `--name ml-aci-demo-container`: Give the running container a name.
* `-p 5000:5000`: Map host port 5000 to container port 5000.

3. **Test the API from the host**

   ```bash
   ```

curl -X POST [http://localhost:5000/predict](http://localhost:5000/predict)&#x20;
-H "Content-Type: application/json"&#x20;
-d '{"data": \[\[6.2, 2.8, 4.8, 1.8]]}'

````

   Expected response:

   ```json
   {"predictions": [2]}
````

* Class index `2` corresponds to Iris-Virginica.

4. **View Container Logs**

   ```bash
   ```

docker logs ml-aci-demo-container

````

   You should see startup logs from the Flask app.

5. **Stop and Remove the Local Container**

   ```bash
docker stop ml-aci-demo-container
docker rm ml-aci-demo-container
````

If the local tests succeed, you are now ready to push the Docker image to Azure Container Registry.

---

## 8. Step 5: Push Docker Image to Azure Container Registry (ACR)

Azure Container Registry (ACR) is a private Docker registry for storing container images. We will create an ACR instance, log in, and push our image.

### 8.1 Create an Azure Container Registry (ACR)

1. **Choose a Unique ACR Name**

   The ACR name must be globally unique across Azure (e.g., `mlaci12345acr`).

2. **Create the ACR**

   ```bash
   ```

az acr create&#x20;
\--resource-group ml-deployment-rg&#x20;
\--name \<ACR\_NAME>&#x20;
\--sku Basic&#x20;
\--location eastus

````

   - Replace `<ACR_NAME>` with your unique ACR name (only lowercase letters and numbers allowed, between 5 and 50 characters).
   - `--sku Basic`: An entry-level SKU sufficient for most demos. Other options include `Standard` or `Premium`.

3. **Verify ACR Creation**

   ```bash
az acr show --resource-group ml-deployment-rg --name <ACR_NAME> --output table
````

You should see details of the newly created ACR.

### 8.2 Log In to ACR and Push the Image

1. **Log in to ACR**

   ```bash
   ```

az acr login --name \<ACR\_NAME>

````

   This command configures your local Docker client to push and pull images from ACR.

2. **Tag the Local Image for ACR**

   Docker images pushed to ACR must be tagged with the registry’s login server, which is in the format `<ACR_NAME>.azurecr.io`.

   ```bash
# Retrieve the ACR login server
echo $(az acr show --name <ACR_NAME> --query loginServer --output tsv)

# Tag the local image
docker tag ml-aci-demo:latest <ACR_NAME>.azurecr.io/ml-aci-demo:latest
````

* The new tag follows: `<ACR_LOGIN_SERVER>/ml-aci-demo:latest`.

3. **Push the Image to ACR**

   ```bash
   ```

docker push \<ACR\_NAME>.azurecr.io/ml-aci-demo\:latest

````

   - This uploads your Docker image to ACR. It may take a few minutes, depending on image size.

4. **Verify Image in ACR**

   ```bash
az acr repository list --name <ACR_NAME> --output table
````

You should see your `ml-aci-demo` repository listed.

---

## 9. Step 6: Deploy to Azure Container Instances (ACI)

Now that your container image is in ACR, you can deploy it to ACI. If you need GPU resources (e.g., for inference with large neural networks), ensure you choose a GPU-enabled SKU.

### 9.1 Choose a GPU-Enabled Region

Ensure your Resource Group resides in a GPU-supported region. Reviewing Step 6.2, common GPU-enabled regions include `eastus`, `westus2`, `westeurope`, `northeurope`, and `southeastasia`.

If you used `eastus` for your Resource Group (as in our commands), you can deploy GPU-enabled containers there.

### 9.2 Deploy ACI with GPU Resources

ACI allows you to specify the CPU, memory, and GPU count. Azure supports NVIDIA GPUs (e.g., `K80`, `P100`) in ACI.

1. **Set Variables for Reuse**

   ```bash
   RESOURCE_GROUP="ml-deployment-rg"
   ACI_NAME="ml-aci-instance"
   ACR_NAME="<ACR_NAME>"
   ACI_LOCATION="eastus"  # must match or be compatible with your RG's region
   IMAGE_NAME="${ACR_NAME}.azurecr.io/ml-aci-demo:latest"
   GPU_SKU="K80"  # or P100, V100 depending on availability in your region
   GPU_COUNT=1
   CPU_CORES=4
   MEMORY_GB=16

   # Retrieve ACR credentials (username/password) for ACI to pull private image
   ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
   ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)
   ```

2. **Deploy the ACI Instance**

   ```bash
   az container create \
     --resource-group $RESOURCE_GROUP \
     --name $ACI_NAME \
     --image $IMAGE_NAME \
     --cpu $CPU_CORES \
     --memory $MEMORY_GB \
     --gpu $GPU_COUNT \
     --gpu-sku $GPU_SKU \
     --registry-login-server "${ACR_NAME}.azurecr.io" \
     --registry-username $ACR_USERNAME \
     --registry-password $ACR_PASSWORD \
     --ports 5000 \
     --dns-name-label $ACI_NAME \
     --location $ACI_LOCATION \
     --environment-variables \
         MODEL_PATH="/app/models/iris_model.joblib" \
         OTHER_ENV_VAR="value"
   ```

   Explanation of arguments:

   * `--Image`: The ACR-hosted Docker image.
   * `--cpu`, `--memory`: CPU cores and memory to allocate.
   * `--gpu`, `--gpu-sku`: Number of GPUs and the GPU SKU.
   * `--registry-login-server`, `--registry-username`, `--registry-password`: Credentials for pulling from private ACR.
   * `--ports 5000`: Expose port 5000 (Flask default).
   * `--dns-name-label`: A unique DNS label (e.g., `ml-aci-instance`). The FQDN becomes `${ACI_NAME}.${ACI_LOCATION}.azurecontainer.io`.
   * `--environment-variables`: Pass environment variables to the container (optional).

3. **Verify Deployment Status**

   ```bash
   az container show \
     --resource-group $RESOURCE_GROUP \
     --name $ACI_NAME \
     --query "{ FQDN:ipAddress.fqdn, State:instanceView.state }" \
     --output table
   ```

   You should see the FQDN (e.g., `ml-aci-instance.eastus.azurecontainer.io`) and the state `Running` when deployment succeeds.

### 9.3 Verify and Test the Deployment

1. **Test the API Endpoint**

   Use `curl` or a web browser to test:

   ```bash
   curl -X POST http://<ACI_FQDN>:5000/predict \
        -H "Content-Type: application/json" \
        -d '{"data": [[5.9, 3.0, 5.1, 1.8]]}'
   ```

   Replace `<ACI_FQDN>` with the FQDN from the previous command (e.g., `ml-aci-instance.eastus.azurecontainer.io`).

   You should receive a JSON response similar to:

   ```json
   {"predictions": [2]}
   ```

2. **Check Container Logs in Azure**

   ```bash
   az container logs \
     --resource-group $RESOURCE_GROUP \
     --name $ACI_NAME \
     --follow
   ```

   This streams the container’s stdout/stderr logs, useful for debugging startup errors or runtime issues.

---

## 10. Step 7: Networking, Load Balancing, and Custom Domain

### 10.1 Configure Container Ports and Public IP

By default, ACI assigns a dynamic public IP or DNS name to your container instance via the `--dns-name-label`. That endpoint resolves to an IP reachable over the internet.

* URL format: `http://<DNS_NAME>.<REGION>.azurecontainer.io:5000/`
* You can omit the port if you configure your container to run on port 80 instead of 5000. To do so, modify the `Flask` app to listen on port 80 and change `EXPOSE 5000` to `EXPOSE 80` in the Dockerfile.

### 10.2 (Optional) Use Azure Application Gateway or Load Balancer

For production scenarios, you might want to:

* Terminate SSL/TLS (HTTPS) at a gateway.
* Use a load balancer for multiple ACI instances.

Azure Application Gateway (Layer 7) can provide:

* SSL offloading.
* Path-based routing.
* Web Application Firewall (WAF).

**Basic Application Gateway Setup (Outline):**

1. Create a Virtual Network (VNet) and subnet for the gateway.
2. Create a Public IP for the gateway.
3. Create the Application Gateway resource, specifying frontend IP, backend ACI IP, and health probes.
4. Configure listeners (ports 80/443) and rules to route traffic to your ACI instance.

For detailed steps, refer to [Azure Application Gateway Documentation](https://docs.microsoft.com/azure/application-gateway/overview).

### 10.3 (Optional) Map a Custom Domain

If you own a domain (e.g., `mydomain.com`), you can map a subdomain (e.g., `api.mydomain.com`) to your ACI’s DNS name:

1. In your DNS provider’s management console, create a CNAME record:

   * Host/Alias: `api` (for `api.mydomain.com`)
   * Points to: `<ACI_DNS_NAME>.<REGION>.azurecontainer.io`
2. (Optional) Add a wildcard `A` record or use Azure DNS for advanced control.
3. For HTTPS, obtain an SSL/TLS certificate and configure it on an Application Gateway or Azure Front Door.

---

## 11. Step 8: Monitoring and Logging

Monitoring and logging are crucial for understanding performance, diagnosing errors, and maintaining your service.

### 11.1 Enable Azure Monitor for Container Instances

Azure Monitor provides metrics and logs for ACI:

```bash
# Enable diagnostic settings to send logs to a Log Analytics workspace
# Step 1: Create or identify a Log Analytics Workspace
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name ml-aci-workspace

# Capture workspace ID
WORKSPACE_ID=$(az monitor log-analytics workspace show --resource-group $RESOURCE_GROUP --workspace-name ml-aci-workspace --query id --output tsv)

# Step 2: Configure diagnostic settings for ACI
ez monitor diagnostic-settings create \
  --resource /subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerInstance/containerGroups/$ACI_NAME \
  --workspace $WORKSPACE_ID \
  --name "aci-diagnostics" \
  --logs '[{"category": "ContainerInstanceLogs", "enabled": true}, {"category": "ContainerInstanceMetrics", "enabled": true}]'
```

* This sends both logs (stdout/stderr, container events) and metrics (CPU, memory, GPU utilization) to the Log Analytics workspace.

### 11.2 Configure Application Insights (Optional)

If you want more granular telemetry from your Flask application (e.g., request rates, response times, exceptions), integrate [Azure Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview) into your code.

1. **Create an Application Insights Resource**

   ```bash
   az monitor app-insights component create \
     --app ml-api-insights \
     --location eastus \
     --resource-group $RESOURCE_GROUP \
     --application-type web

   APP_INSIGHTS_KEY=$(az monitor app-insights component show --app ml-api-insights --resource-group $RESOURCE_GROUP --query instrumentationKey --output tsv)
   ```

2. **Instrument Your Flask App**

   Install the Azure Monitor SDK:

   ```bash
   pip install opencensus-ext-azure
   ```

   Update `app.py` to include Application Insights:

   ```python
   from opencensus.ext.azure.log_exporter import AzureLogHandler
   from opencensus.ext.azure.trace_exporter import AzureExporter
   from opencensus.trace.samplers import ProbabilitySampler
   from opencensus.trace.tracer import Tracer
   import logging

   # --- Existing imports ---
   from flask import Flask, request, jsonify
   import joblib
   import numpy as np
   import os

   app = Flask(__name__)

   # Configure Application Insights
   INSTRUMENTATION_KEY = os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')
   if INSTRUMENTATION_KEY:
       # Set up logging to send logs to Application Insights
       logger = logging.getLogger(__name__)
       logger.addHandler(AzureLogHandler(connection_string=f"InstrumentationKey={INSTRUMENTATION_KEY}"))
       
       # Set up tracing for web requests
       tracer = Tracer(
           exporter=AzureExporter(connection_string=f"InstrumentationKey={INSTRUMENTATION_KEY}"),
           sampler=ProbabilitySampler(1.0)
       )

   # Load model...
   MODEL_PATH = os.path.join('models', 'iris_model.joblib')
   model = joblib.load(MODEL_PATH)

   @app.route('/')
   def home():
       return "Welcome to the Iris Classification API!", 200

   @app.route('/predict', methods=['POST'])
   def predict():
       try:
           data = request.get_json()
           features = np.array(data['data'])
           preds = model.predict(features).tolist()
           return jsonify({'predictions': preds}), 200
       except Exception as e:
           logger.error(f"Error in /predict: {str(e)}") if INSTRUMENTATION_KEY else None
           return jsonify({'error': str(e)}), 400

   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5000)
   ```

3. **Pass APPINSIGHTS\_INSTRUMENTATIONKEY to ACI**

   When deploying ACI, include the environment variable:

   ```bash
   az container update \
     --resource-group $RESOURCE_GROUP \
     --name $ACI_NAME \
     --set environmentVariables.APPINSIGHTS_INSTRUMENTATIONKEY="$APP_INSIGHTS_KEY"
   ```

4. **View Telemetry in Azure Portal**

   In the Azure Portal, navigate to your Application Insights resource (`ml-api-insights`) to view live metrics, request rates, dependencies, and exceptions.

### 11.3 Review Logs and Metrics

* **Log Analytics**: Run queries in Log Analytics Workspace to filter container logs, errors, and metrics. Example Kusto query:

  ```kusto
  ContainerInstanceLog_CL
  | where TimeGenerated > ago(1h)
  | where ContainerName_s == "ml-aci-instance"
  | project TimeGenerated, Log_s, Level_s
  ```

* **Metrics**: In Azure Portal, under your ACI resource, click "Metrics" to visualize CPU, memory, and GPU utilization over time.

* **Application Insights**: Track request count, response time, failure rate, and custom events.

---

## 12. Step 9: Scaling and Maintenance

Azure Container Instances offer simplicity but limited built-in scaling. For large-scale, consider Azure Kubernetes Service (AKS). However, you can still manually scale ACI by creating multiple instances behind a load balancer or by scripting new deployments.

### 12.1 Manual Scaling

To handle more concurrent requests, deploy additional ACI instances and distribute traffic:

1. **Deploy Another ACI Instance**

   Choose a different `--dns-name-label` (e.g., `ml-aci-instance-2`):

   ```bash
   az container create \
     --resource-group $RESOURCE_GROUP \
     --name ml-aci-instance-2 \
     --image $IMAGE_NAME \
     --cpu $CPU_CORES \
     --memory $MEMORY_GB \
     --gpu $GPU_COUNT \
     --gpu-sku $GPU_SKU \
     --registry-login-server "${ACR_NAME}.azurecr.io" \
     --registry-username $ACR_USERNAME \
     --registry-password $ACR_PASSWORD \
     --ports 5000 \
     --dns-name-label ml-aci-instance-2 \
     --location $ACI_LOCATION
   ```

2. **Use a Load Balancer or Application Gateway**

   * Create an Azure Load Balancer and add both ACI public IPs as backend pool members.
   * Configure health probes on port 5000 and a load-balancing rule.
   * Alternatively, use an Application Gateway as discussed earlier.

> **Note:** Manual scaling can become complex. For auto-scaling or more advanced orchestration, consider AKS.

### 12.2 Auto-Scaling Considerations

ACI does not natively support auto-scaling. To achieve auto-scaling:

* Use Azure Logic Apps, Azure Functions, or Azure Automation scripts to monitor metrics (e.g., CPU, queue length) and programmatically create or delete ACI instances.
* Use Azure Container Instances Virtual Node in AKS to achieve a serverless Kubernetes-like environment that can burst into ACI.

### 12.3 Updating the Container Image (Rolling Updates)

When you update your ML model or code, you need to rebuild the container, push it to ACR, and then update the ACI deployment.

1. **Modify Code or Model**

   * Update `app.py`, retrain the model (if needed), or add new dependencies.
   * Update/Create new `model.joblib` in `models/` directory.

2. **Rebuild and Tag the Image**

   ```bash
   docker build -t ml-aci-demo:v2 .
   docker tag ml-aci-demo:v2 <ACR_NAME>.azurecr.io/ml-aci-demo:v2
   docker push <ACR_NAME>.azurecr.io/ml-aci-demo:v2
   ```

3. **Update ACI to Use the New Image**

   ```bash
   az container update \
     --resource-group $RESOURCE_GROUP \
     --name $ACI_NAME \
     --image <ACR_NAME>.azurecr.io/ml-aci-demo:v2
   ```

   ACI will pull the new image and restart the container. Ensure minimal downtime by testing in a staging instance before updating production.

---

## 13. Step 10: Cost Optimization and Best Practices

Running GPU-enabled containers can be costly. Follow these best practices to optimize costs:

1. **Right-Size Resources**

   * Only request the number of GPUs, CPU cores, and memory you need for inference. Over-provisioning leads to unnecessary costs.

2. **Turn Off or Delete Idle Containers**

   * If your service is not needed 24/7, consider scheduling it to shut down during off-hours using Azure Automation or Azure Functions.

3. **Monitor Costs with Azure Cost Management**

   * In Azure Portal, navigate to Cost Management + Billing.
   * Create budgets and set alerts (e.g., alert me when my spend reaches 50% of my \$200 credit).

4. **Use Low-Priority or Spot Instances for Non-Critical Workloads**

   * ACI does not support Spot SKUs, but if you move to AKS, you can leverage spot node pools for cost savings.

5. **Leverage Azure Reserved Instances**

   * For long-term, predictable workloads, consider Azure Reserved Instances (e.g., 1-year or 3-year commitment with discounts).

6. **Use Application Insights Sampling**

   * Configure sampling to reduce the volume of telemetry data collected by Application Insights, lowering costs.

7. **Periodic Clean-Up of Unused Resources**

   * Delete old container images from ACR: `az acr repository delete --name <ACR_NAME> --repository ml-aci-demo --yes`
   * Remove stale ACI instances: `az container delete --resource-group $RESOURCE_GROUP --name <ACI_NAME> --yes`

---

## 14. Troubleshooting Common Issues

1. **ACI Deployment Fails**

   * Check if your region supports GPU SKUs: `az aks get-versions --location <region>` (for ACI, refer to ACI docs).
   * Review container logs: `az container logs --resource-group $RESOURCE_GROUP --name $ACI_NAME`.
   * Ensure ACR credentials (username/password) are correct.

2. **IMAGE\_PULL\_ERROR**

   * Confirm the image tag exists in ACR: `az acr repository show-tags --name <ACR_NAME> --repository ml-aci-demo`.
   * Ensure ACI has permission to pull from ACR (correct credentials).

3. **API Returns 404 or 500**

   * Verify Flask app is listening on the correct port (5000 by default).
   * Confirm `CMD ["python", "app.py"]` in Dockerfile is correct.
   * Check if any required environment variables are missing.

4. **High Latency or Timeout**

   * GPU cold start can take longer; consider warming up the container (e.g., send a small request on startup).
   * Monitor CPU, memory, and GPU metrics to ensure resource utilization is adequate.

5. **Out of Memory (OOM) Errors**

   * Increase memory allocation in ACI: `--memory <size>`.
   * Optimize model size (e.g., quantize, compress) or use a smaller base image.

6. **Authentication Errors with ACR**

   * Regenerate ACR credentials: `az acr credential renew --name <ACR_NAME> --password-name password`. Then update ACI credentials or re-login.

---

## Appendix and References

* **Azure Container Instances Documentation**: [https://docs.microsoft.com/azure/container-instances/overview](https://docs.microsoft.com/azure/container-instances/overview)
* **Azure Container Registry Documentation**: [https://docs.microsoft.com/azure/container-registry/](https://docs.microsoft.com/azure/container-registry/)
* **Azure CLI Reference**: [https://docs.microsoft.com/cli/azure/](https://docs.microsoft.com/cli/azure/)
* **Flask Documentation**: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
* **Scikit-learn Documentation**: [https://scikit-learn.org/](https://scikit-learn.org/)
* **Docker Documentation**: [https://docs.docker.com/](https://docs.docker.com/)

---

**Congratulations!** You now have a detailed understanding of how to deploy a GPU-based ML model on Azure Container Instances, from start to finish. This guide assumed no prior deployment experience and explained each step clearly. Feel free to adapt and extend this guide for your specific ML use cases.
[← Back to Main Guide](./README.md) | [GCP Guide →](./gcp-deployment.md)
