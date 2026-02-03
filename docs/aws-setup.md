# AWS Infrastructure Setup for Canada.ca Chat Agent
# =================================================
#
# This guide helps you set up Aurora PostgreSQL and ElastiCache Redis on AWS.
# Estimated monthly cost: ~$55-75/month (can be reduced by stopping when not in use)

## Quick Setup via AWS Console

### Step 1: Create VPC (if you don't have one)
# Use the AWS VPC Wizard to create a VPC with public and private subnets

### Step 2: Create Aurora PostgreSQL Serverless v2

1. Go to AWS RDS Console > Create database
2. Choose "Amazon Aurora"
3. Edition: "Amazon Aurora PostgreSQL-Compatible Edition"
4. Engine version: PostgreSQL 15.x or later
5. Templates: "Dev/Test" (for cost savings)
6. DB cluster identifier: `canadaca-db`
7. Master username: `postgres`
8. Master password: (save this securely)
9. Instance configuration:
   - Choose "Serverless v2"
   - Minimum ACUs: 0.5 (cheapest)
   - Maximum ACUs: 4 (adjust based on needs)
10. Connectivity:
    - VPC: Select your VPC
    - Public access: Yes (for development) or No (for production)
    - Security group: Create new, allow port 5432
11. Database name: `canadaca`
12. Click "Create database"

After creation, connect and run:
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Step 3: Create ElastiCache Redis

1. Go to AWS ElastiCache Console > Create cluster
2. Choose "Redis OSS"
3. Cluster mode: Disabled (simpler for development)
4. Name: `canadaca-cache`
5. Node type: `cache.t3.micro` (~$12/month)
6. Number of replicas: 0 (for development)
7. Subnet group: Create new in your VPC
8. Security group: Create new, allow port 6379
9. Click "Create"

### Step 4: Configure Security Groups

Aurora Security Group:
- Inbound: Port 5432 from your IP (dev) or ElastiCache security group

ElastiCache Security Group:
- Inbound: Port 6379 from Aurora security group

### Step 5: Update Your .env File

```bash
# Get your Aurora endpoint from RDS Console
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@your-cluster.cluster-xxxxx.ca-central-1.rds.amazonaws.com:5432/canadaca

# Get your ElastiCache endpoint from ElastiCache Console
REDIS_URL=redis://your-cluster.xxxxx.cache.amazonaws.com:6379
```

### Step 6: Initialize the Database

```bash
# Run from your local machine (if Aurora is publicly accessible)
# Or from an EC2 instance in the same VPC

uv run python scripts/init_db.py
```

---

## Cost Optimization Tips

1. **Stop Aurora when not in use**: Aurora Serverless v2 can be paused
2. **Use smaller ACUs**: Start with 0.5 ACU minimum
3. **Consider Reserved Capacity**: For production, reserve 1 year for 30-40% savings
4. **Use t3.micro for ElastiCache**: Cheapest option at ~$12/month

## Estimated Monthly Costs (ca-central-1)

| Service | Configuration | Cost |
|---------|--------------|------|
| Aurora Serverless v2 | 0.5-4 ACU | ~$43-150/month |
| ElastiCache Redis | cache.t3.micro | ~$12/month |
| **Total** | | **~$55-65/month** |

## Alternative: Even Cheaper Option

If you want the absolute cheapest:
- **RDS PostgreSQL db.t3.micro** (~$15/month) instead of Aurora
- **Skip Redis** (optional for development)

This would bring costs to ~$15-30/month.
