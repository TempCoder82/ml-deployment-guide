# Azure Container Instances ML Model Deployment Guide

## Deploy Your GPU-Based ML Model on Azure Container Instances

This comprehensive guide walks you through deploying a GPU-accelerated ML model on Microsoft Azure using Container Instances (ACI) and related services.

## Table of Contents

1. [Account Setup & Initial Configuration](#1-account-setup--initial-configuration)
2. [Installing and Configuring Azure CLI](#2-installing-and-configuring-azure-cli)
3. [Resource Groups and Permissions](#3-resource-groups-and-permissions)
4. [Azure Container Registry Setup](#4-azure-container-registry-setup)
5. [Containerization and Image Building](#5-containerization-and-image-building)
6. [Deploying to Container Instances](#6-deploying-to-container-instances)
7. [Networking and Load Balancing](#7-networking-and-load-balancing)
8. [Monitoring with Application Insights](#8-monitoring-with-application-insights)
9. [Scaling and Management](#9-scaling-and-management)
10. [Cost Optimization](#10-cost-optimization)

## 1. Account Setup & Initial Configuration

### Creating Your Azure Account

1. **Navigate to [Azure Portal](https://azure.microsoft.com)**

2. **Start Free Trial**
   - Click "Start free"
   - Sign in with Microsoft account or create new one
   
3. **Free Tier Benefits**
   ```
   ✅ $200 credit for 30 days
   ✅ 12 months of free services including:
      - 750 hours B1S VMs
      - 5GB blob storage
      - 250GB SQL Database
   ✅ Always free services (limited quantities)
   ```

4. **Identity Verification**
   - Phone number verification
   - Credit card required (not charged during trial)

5. **Complete Signup**
   - Agree to terms
   - Create first subscription (auto-created)

### Understanding Azure Hierarchy

```
Management Group
└── Subscription (billing boundary)
    └── Resource Group (logical container)
        └── Resources (ACR, ACI, etc.)
```

### Portal Navigation

1. **Access Portal**: https://portal.azure.com
2. **Key Sections**:
   - Resource Groups: Organize resources
   - Subscriptions: Billing and access
   - Cost Management: Monitor spending
   - All Resources: Global view

## 2. Installing and Configuring Azure CLI

### Installation by Platform

#### macOS
```bash
# Using Homebrew
brew update && brew install azure-cli

# Or direct install
curl -L https://aka.ms/InstallAzureCli | bash
```

#### Linux
```bash
# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# RHEL/CentOS
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
sudo sh -c 'echo -e "[azure-cli]
name=Azure CLI
baseurl=https://packages.microsoft.com/yumrepos/azure-cli
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/azure-cli.repo'
sudo yum install azure-cli
```

#### Windows
```powershell
# Using MSI installer
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'

# Or using Chocolatey
choco install azure-cli

# Or using winget
winget install Microsoft.AzureCLI
```

### Login and Configuration

```bash
# Login to Azure
az login

# This opens browser for authentication
# After login, you'll see your subscriptions

# List subscriptions
az account list --output table

# Set default subscription
az account set --subscription "Your Subscription Name"

# Verify current subscription
az account show --output table

# Configure defaults
az configure --defaults group=ml-deployment-rg location=eastus
```

### Service Principal (for automation)

```bash
# Create service principal
az ad sp create-for-rbac \
  --name ml-deployment-sp \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)

# Save the output - looks like:
{
  "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "displayName": "ml-deployment-sp",
  "password": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}

# Login with service principal
az login --service-principal \
  --username $APP_ID \
  --password $PASSWORD \
  --tenant $TENANT_ID
```

## 3. Resource Groups and Permissions

### Create Resource Group

```bash
# Create resource group
az group create \
  --name ml-deployment-rg \
  --location eastus

# List available locations
az account list-locations \
  --query "[?contains(displayName, 'US')].{Name:name, DisplayName:displayName}" \
  --output table

# GPU-enabled regions for ACI:
# - eastus
# - westus2
# - westeurope
# - northeurope
# - southeastasia
```

### Set Up Managed Identity

```bash
# Create user-assigned managed identity
az identity create \
  --resource-group ml-deployment-rg \
  --name ml-deployment-identity

# Get identity details
IDENTITY_ID=$(az identity show \
  --resource-group ml-deployment-rg \
  --name ml-deployment-identity \
  --query id --output tsv)

IDENTITY_CLIENT_ID=$(az identity show \
  --resource-group ml-deployment-rg \
  --name ml-deployment-identity \
  --query clientId --output tsv)