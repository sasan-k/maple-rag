# Azure Infrastructure Setup for Canada.ca Chat Agent
# ===================================================
#
# This guide helps you set up Azure Database for PostgreSQL and Azure Cache for Redis.
# Estimated monthly cost: ~$30-50/month (cheaper than AWS!)

## Quick Comparison: Azure vs AWS

| Component | Azure | AWS |
|-----------|-------|-----|
| PostgreSQL | Flexible Server B1ms (~$12/mo) | Aurora Serverless (~$43/mo) |
| Redis | Cache for Redis C0 (~$16/mo) | ElastiCache t3.micro (~$12/mo) |
| LLM | Azure OpenAI | Bedrock |
| **Total** | **~$28-40/month** | ~$55-65/month |

---

## Step 1: Create Azure Database for PostgreSQL

### Via Azure Portal

1. Go to Azure Portal > Create a resource > Azure Database for PostgreSQL
2. Choose **Flexible Server**
3. Configure:
   - Subscription: Your subscription
   - Resource group: Create new `canadaca-rg`
   - Server name: `canadaca-db`
   - Region: **Canada Central**
   - PostgreSQL version: **16**
   - Workload type: **Development** (cheapest)
   - Compute + storage:
     - Compute tier: **Burstable**
     - Compute size: **B1ms** (~$12/month)
     - Storage: 32 GB
4. Authentication:
   - Admin username: `postgres`
   - Password: (save securely)
5. Networking:
   - Allow public access
   - Add your current client IP
6. Click **Review + create**

### Via Azure CLI

```bash
# Login to Azure
az login

# Create resource group
az group create --name canadaca-rg --location canadacentral

# Create PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group canadaca-rg \
  --name canadaca-db \
  --location canadacentral \
  --admin-user postgres \
  --admin-password YOUR_SECURE_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --public-access 0.0.0.0

# Create the database
az postgres flexible-server db create \
  --resource-group canadaca-rg \
  --server-name canadaca-db \
  --database-name canadaca

# Enable pgvector extension
az postgres flexible-server parameter set \
  --resource-group canadaca-rg \
  --server-name canadaca-db \
  --name azure.extensions \
  --value vector
```

### Enable pgvector Extension

Connect to your database and run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Step 2: Create Azure Cache for Redis

### Via Azure Portal

1. Go to Azure Portal > Create a resource > Azure Cache for Redis
2. Configure:
   - Subscription: Your subscription
   - Resource group: `canadaca-rg`
   - DNS name: `canadaca-cache`
   - Location: **Canada Central**
   - Cache type: **Basic C0** (~$16/month)
3. Click **Review + create**

### Via Azure CLI

```bash
az redis create \
  --resource-group canadaca-rg \
  --name canadaca-cache \
  --location canadacentral \
  --sku Basic \
  --vm-size c0
```

---

## Step 3: (Optional) Create Azure OpenAI Resource

If you want to use Azure OpenAI instead of AWS Bedrock:

1. Go to Azure Portal > Create a resource > Azure OpenAI
2. Configure:
   - Resource group: `canadaca-rg`
   - Region: **Canada East** (Azure OpenAI available here)
   - Name: `canadaca-openai`
   - Pricing tier: Standard S0
3. After creation, deploy models:
   - Go to Azure OpenAI Studio
   - Deploy: `gpt-4o` (chat) and `text-embedding-ada-002` (embeddings)

---

## Step 4: Update Your .env File

```bash
# ================
# Azure PostgreSQL
# ================
# Format: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@canadaca-db.postgres.database.azure.com:5432/canadaca?sslmode=require

# ================
# Azure Redis
# ================
# Get the access key from Azure Portal > canadaca-cache > Access keys
REDIS_URL=rediss://:YOUR_ACCESS_KEY@canadaca-cache.redis.cache.windows.net:6380

# ================
# Azure OpenAI (if using instead of AWS Bedrock)
# ================
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://canadaca-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-02-01
```

---

## Step 5: Initialize the Database

```bash
uv run python scripts/init_db.py
```

---

## Cost Comparison

| Service | Azure | AWS |
|---------|-------|-----|
| PostgreSQL | B1ms: ~$12/mo | Aurora: ~$43/mo |
| Redis | C0: ~$16/mo | t3.micro: ~$12/mo |
| **Infrastructure Total** | **~$28/mo** | ~$55/mo |

**Azure is ~50% cheaper for the base infrastructure!**

---

## Hybrid Option: Azure + AWS Bedrock

You can use:
- **Azure PostgreSQL + Redis** (cheaper infrastructure)
- **AWS Bedrock** (for LLM - already configured)

This gives you the best of both worlds:
- Cheaper database costs on Azure
- More LLM model choices on AWS Bedrock

```bash
# .env for hybrid setup
DATABASE_URL=postgresql+asyncpg://...@canadaca-db.postgres.database.azure.com:5432/canadaca
REDIS_URL=rediss://:...@canadaca-cache.redis.cache.windows.net:6380
LLM_PROVIDER=aws_bedrock  # Keep using AWS Bedrock for LLMs
AWS_REGION=ca-central-1
```

---

## Security Best Practices

1. **Use Private Endpoints** in production (no public access)
2. **Enable SSL** for all connections
3. **Use Managed Identity** instead of passwords where possible
4. **Configure firewall rules** to allow only necessary IPs
