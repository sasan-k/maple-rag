# Infrastructure as Code (IaC) Migration Plan

## Objective
Migrate all manual cloud resource provisioning (currently Azure-focused) to a unified Infrastructure as Code solution using Terraform. This will ensure reproducibility, version control, and multi-cloud compatibility (Azure & AWS).

## Core Standard
- **Tool:** Terraform
- **State Management:** Remote state (Azure Storage Account or Terraform Cloud) to allow team collaboration.
- **Directory Structure:**
  ```text
  terraform/
  ├── modules/
  │   ├── azure/         # Azure-specific modules
  │   │   ├── acr/
  │   │   ├── container_apps/
  │   │   └── networking/
  │   └── aws/           # AWS-specific modules (for Bedrock, future needs)
  ├── environments/
  │   ├── dev/
  │   │   ├── main.tf
  │   │   └── terraform.tfvars
  │   └── prod/
  │       ├── main.tf
  │       └── terraform.tfvars
  └── README.md
  ```

## Tasks

### 1. Azure Resources (Priority)
- [ ] **Resource Group**: Import existing `canadaca-rg`.
- [ ] **Container Registry**: Import `canadacaregistry`.
- [ ] **Identity**: Define the User Assigned Identities and Federated Credentials (OIDC) via `azuread` provider.
- [ ] **Container Apps environment**: Define the environment, Log Analytics workspace, and VNET settings.
- [ ] **Container Apps**: Define the Web App and Job (Scraper) resources with secrets injection.
- [ ] **PostgreSQL**: Provision Azure Database for PostgreSQL (Flexible Server).
- [ ] **Redis**: Provision Azure Cache for Redis.

### 2. AWS Resources (Secondary)
- [ ] **IAM**: Define usage roles for Bedrock access.
- [ ] **Bedrock**: Configure model access and permissions (if applicable via IaC).

### 3. CI/CD Integration
- [ ] Create a GitHub Action `terraform.yml` to run `terraform plan` on PRs and `terraform apply` on merge to main.

## Initial Setup
1. Create `terraform/` folder in root.
2. Initialize `main.tf` with Azure provider.
3. Use `terraform import` to bring existing manually created resources under management.
