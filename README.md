# Pharmacy API on Amazon EKS

![AWS](https://img.shields.io/badge/AWS-EKS-orange)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.36-blue)
![Docker](https://img.shields.io/badge/Docker-Hardened-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-green)
![Cognito](https://img.shields.io/badge/Amazon-Cognito-purple)
![CI](https://img.shields.io/badge/GitHub_Actions-CI-success)

A cloud-native FastAPI workload engineered for Amazon EKS with hardened containers, AWS workload identity, real Amazon Cognito JWT authentication, DynamoDB persistence, EventBridge publishing, and automated CI validation.

---

# Architecture

```text
User
  │
  │ Amazon Cognito Access Token
  ▼
FastAPI
  │
  ├── JWT Signature Validation
  ├── Issuer Validation
  ├── Client Validation
  ├── Token Expiration Validation
  └── Cognito Group Mapping
        │
        ├── tenant-tenant-001
        └── role-HospitalAdmin
  │
  ▼
POST /drugs
  │
  ├── tenant_id from authenticated identity
  ├── created_by from Cognito sub
  │
  ├── DynamoDB
  │     └── pharmacy-api-drugs
  │
  └── EventBridge
        └── DrugCreated


Amazon EKS
  │
  └── pharmacy-api Deployment
        │
        ├── FastAPI Pod
        ├── FastAPI Pod
        │
        └── EKS Pod Identity
              └── pharmacy-api-eks-role


Container Delivery

Docker
  │
  ▼
Amazon ECR
  │
  ▼
Immutable SHA256 Image Digest
  │
  ▼
Amazon EKS
```

**AWS Region:** `eu-west-2`

---

# What This Project Demonstrates

The project covers:

- Amazon EKS workload deployment
- Kubernetes 1.36
- hardened non-root containers
- immutable ECR image deployment
- readiness and liveness probes
- EKS Pod Identity
- least-privilege IAM
- Amazon Cognito authentication
- RS256 JWT verification
- Cognito JWKS validation
- issuer validation
- client/audience validation
- access-token enforcement
- tenant-aware identity extraction
- role extraction from Cognito groups
- DynamoDB persistence
- EventBridge event publishing
- automated Python tests
- Kubernetes schema validation
- YAML linting
- GitHub Actions CI

---

# Deployment Evidence

## Amazon EKS Cluster

The managed worker node reached `Ready` state and the EKS Pod Identity Agent was validated during the original EKS deployment phase.

![Amazon EKS cluster ready](docs/eks-cluster-ready.png)

---

## Running Kubernetes Workload

The FastAPI workload was validated with two replicas running on Amazon EKS using an immutable Amazon ECR image digest.

![Pharmacy workload running](docs/pharmacy-workload-running.png)

---

## EKS Pod Identity

The application Pod authenticated through the dedicated:

```text
pharmacy-api-eks-role
```

without storing long-lived AWS credentials inside the workload.

![EKS Pod Identity proof](docs/pod-identity-proof.png)

---

## Application Health

The deployed application returned:

```text
HTTP/1.1 200 OK
```

from:

```text
GET /health
```

![Application health check](docs/health-check.png)

---

# Amazon Cognito Authentication

The application now uses real Amazon Cognito access tokens instead of hard-coded demo claims.

The request path is:

```text
Client
  │
  │ Authorization: Bearer <access-token>
  ▼
FastAPI
  │
  ├── Fetch Cognito JWKS
  ├── Verify RS256 signature
  ├── Verify issuer
  ├── Verify client binding
  ├── Verify expiration
  ├── Verify token_use=access
  │
  └── Extract identity
        │
        ├── sub
        ├── cognito:groups
        ├── tenant
        └── role
```

The application supports generic OIDC configuration while remaining compatible with Amazon Cognito.

Configuration is supplied through:

```text
OIDC_ISSUER
OIDC_CLIENT_ID
OIDC_JWKS_URL
OIDC_TENANT_CLAIM
OIDC_ROLE_CLAIM
```

---

# Cognito Identity Model

For the validated Cognito environment, group membership carries tenant and role information.

Example groups:

```text
tenant-tenant-001
role-HospitalAdmin
```

The API derives:

```text
tenant_id = tenant-001
role      = HospitalAdmin
user_id   = Cognito sub
```

The persistent Cognito subject becomes:

```text
created_by
```

on stored drug records.

---

# Cognito Authentication Evidence

A real Cognito access token was passed to:

```text
GET /auth/me
```

The API validated the token and returned:

```json
{
  "authenticated": true,
  "user_id": "<redacted-cognito-sub>",
  "tenant_id": "tenant-001",
  "role": "HospitalAdmin"
}
```

![Cognito authentication](docs/cognito-authentication.png)

This validates:

```text
Cognito-issued access token
        ↓
JWKS signature verification
        ↓
issuer/client validation
        ↓
tenant + role extraction
        ↓
HTTP 200
```

---

# Authenticated Drug Creation

The protected endpoint:

```text
POST /drugs
```

requires a valid bearer token.

An authenticated Cognito request successfully created a drug record:

```text
Cognito Access Token
        ↓
POST /drugs
        ↓
HTTP 200
        ↓
Drug created successfully
```

![Cognito authenticated drug creation](docs/cognito-drug-create.png)

The API no longer accepts hard-coded identity values.

Instead:

```text
tenant_id
```

comes from the validated identity, while:

```text
created_by
```

comes from the authenticated Cognito subject.

---

# DynamoDB Identity Persistence

The record created through the authenticated API was verified directly in DynamoDB.

The persisted record contained:

```text
drug_name    = Amoxicillin
batch_number = COGNITO-EVIDENCE-001
tenant_id    = tenant-001
created_by   = authenticated Cognito subject
```

![Cognito DynamoDB persistence](docs/cognito-dynamodb-persistence.png)

This demonstrates that authenticated identity context survives the complete application flow:

```text
Cognito
   ↓
JWT
   ↓
FastAPI
   ↓
Drug Service
   ↓
DynamoDB
```

---

# Authentication Behaviour

The API follows a fail-closed security model.

## Missing Bearer Token

```text
POST /drugs
        ↓
401 Unauthorized
```

## Invalid JWT

```text
Invalid signature
Invalid issuer
Wrong client
Expired token
Wrong token type
        ↓
401 Unauthorized
```

## Missing Tenant Identity

```text
Valid JWT
but no tenant identity
        ↓
403 Forbidden
```

## Valid Access Token

```text
Valid Cognito access token
        ↓
Identity extracted
        ↓
Request allowed
```

---

# Authenticated Principal Endpoint

The API includes:

```text
GET /auth/me
```

This endpoint validates authentication without requiring a DynamoDB write.

Example:

```bash
curl \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://127.0.0.1:8000/auth/me
```

Example result:

```json
{
  "authenticated": true,
  "user_id": "<cognito-sub>",
  "tenant_id": "tenant-001",
  "role": "HospitalAdmin"
}
```

---

# Public Health Endpoint

The health endpoint intentionally remains unauthenticated:

```text
GET /health
```

This allows Kubernetes probes and operational health checks to function without application credentials.

Expected response:

```json
{
  "status": "ok"
}
```

---

# Application Flow

Creating a drug now follows:

```text
POST /drugs
    │
    ▼
Bearer Access Token
    │
    ▼
JWT Validation
    │
    ├── Cognito JWKS
    ├── Signature
    ├── Issuer
    ├── Client
    ├── Expiration
    └── Token Type
    │
    ▼
Authenticated Principal
    │
    ├── user_id
    ├── tenant_id
    └── role
    │
    ▼
Drug Service
    │
    ├── Generate Record ID
    ├── Attach tenant_id
    ├── Attach created_by
    ├── Persist to DynamoDB
    └── Publish DrugCreated
    │
    ▼
Amazon EventBridge
```

---

# Example Authenticated Request

```bash
curl -X POST http://127.0.0.1:8000/drugs \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "drug_name": "Amoxicillin",
    "batch_number": "COGNITO-EVIDENCE-001",
    "quantity": 25,
    "reorder_level": 5,
    "expiry_date": "2027-12-31",
    "supplier": "Cognito Test Supplier"
  }'
```

Example response:

```json
{
  "message": "Drug created successfully",
  "data": {
    "drug_name": "Amoxicillin",
    "batch_number": "COGNITO-EVIDENCE-001",
    "quantity": 25,
    "reorder_level": 5,
    "expiry_date": "2027-12-31",
    "supplier": "Cognito Test Supplier",
    "id": "<generated-record-id>",
    "tenant_id": "tenant-001",
    "created_by": "<cognito-sub>"
  }
}
```

---

# Security Engineering

## Container Security

The application container:

- runs as non-root `appuser`
- uses a minimal Python slim base image
- excludes development files with `.dockerignore`
- excludes local virtual environments
- drops all Linux capabilities
- uses `no-new-privileges`
- supports a read-only root filesystem
- limits writable storage to `/tmp`

---

## Kubernetes Security

The Kubernetes workload includes:

- `runAsNonRoot: true`
- fixed non-root UID and GID
- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true`
- all Linux capabilities dropped
- `RuntimeDefault` seccomp profile
- CPU requests
- CPU limits
- memory requests
- memory limits
- readiness probes
- liveness probes
- memory-backed `/tmp`
- rolling updates
- dedicated ServiceAccount
- disabled automatic Kubernetes ServiceAccount token mounting

---

# AWS Workload Identity

The application uses **Amazon EKS Pod Identity** for AWS service access.

This is separate from Cognito end-user authentication.

```text
End User Identity
        ↓
Amazon Cognito
        ↓
JWT
        ↓
FastAPI


Workload Identity
        ↓
EKS Pod Identity
        ↓
IAM Role
        ↓
DynamoDB / EventBridge
```

This separation provides two distinct security boundaries:

```text
Who is the user?
→ Cognito

What AWS services may the workload access?
→ IAM + EKS Pod Identity
```

---

# IAM Permissions

The workload IAM role is restricted to the AWS operations required by the application.

## DynamoDB

```text
dynamodb:GetItem
dynamodb:PutItem
```

Access is restricted to:

```text
pharmacy-api-drugs
```

## EventBridge

```text
events:PutEvents
```

Access is restricted to the required event bus.

No AWS access key or secret key is stored inside the Kubernetes workload.

---

# DynamoDB

Drug records are stored in:

```text
pharmacy-api-drugs
```

The table uses:

```text
Partition Key: id
Type: String
Billing Mode: PAY_PER_REQUEST
```

Records contain authenticated identity context:

```text
id
drug_name
batch_number
quantity
reorder_level
expiry_date
supplier
tenant_id
created_by
```

---

# EventBridge

Successful drug creation publishes:

```text
Source:     pharmacy-api
DetailType: DrugCreated
```

The EventBridge bus is configured using:

```text
EVENT_BUS_NAME
```

instead of being hard-coded in the application.

The service checks:

```text
FailedEntryCount
```

and raises an application error if EventBridge reports failed entries.

---

# Validation

The authentication and application changes are covered by automated tests.

Current test coverage includes:

- valid access token
- expired access token
- ID token rejection
- wrong client rejection
- missing tenant rejection
- authenticated principal creation
- public health endpoint
- missing bearer token
- `/auth/me`
- identity propagation into the service layer
- DynamoDB record creation
- EventBridge success handling
- EventBridge failure handling

Current validated result:

```text
12 tests
OK
```

---

# CI / Validation Evidence

The project was validated with:

```text
Python unit tests
YAML lint
Kubernetes schema validation
Git diff whitespace validation
```

![Cognito CI validation](docs/cognito-ci-validation.png)

Validation result:

```text
Unit tests:
12 tests
OK

YAML:
PASS

Kubernetes:
5 resources valid
0 invalid
0 errors

git diff --check:
PASS
```

---

# Continuous Integration

GitHub Actions runs on:

```text
pull_request
push to main
```

The workflow validates three areas.

## Python Tests

```text
Install dependencies
        ↓
Compile application modules
        ↓
Run unit tests
```

## Container Validation

```text
Build Docker image
        ↓
Verify non-root image user
        ↓
Run hardened container
        │
        ├── Read-only filesystem
        ├── Drop all capabilities
        ├── no-new-privileges
        └── Memory-backed /tmp
        ↓
Verify /health
        ↓
Confirm runtime UID is non-root
```

## Kubernetes Validation

```text
Kubernetes YAML
      │
      ├── yamllint
      │
      └── kubeconform
```

---

# EKS Infrastructure

The repository includes:

```text
eks/cluster.yaml
```

The cluster definition contains:

- cluster name: `pharmacy-eks`
- region: `eu-west-2`
- Kubernetes 1.36
- managed EC2 node group
- `t3.medium` worker
- desired capacity: 1
- minimum capacity: 1
- maximum capacity: 2
- EKS Pod Identity Agent
- project/environment tags

The EKS environment was used during the workload deployment phase and may be removed when not actively being demonstrated to avoid unnecessary AWS cost.

---

# Kubernetes Deployment

Deploy:

```bash
kubectl apply -f k8s/
```

Wait for rollout:

```bash
kubectl rollout status deployment/pharmacy-api
```

Inspect:

```bash
kubectl get deploy,pods,svc -o wide
```

The Kubernetes manifests expect OIDC configuration through the ConfigMap.

Example portable configuration:

```yaml
OIDC_ISSUER: "https://cognito-idp.eu-west-2.amazonaws.com/REPLACE_USER_POOL_ID"
OIDC_CLIENT_ID: "REPLACE_APP_CLIENT_ID"
OIDC_TENANT_CLAIM: "custom:tenant_id"
OIDC_ROLE_CLAIM: "custom:role"
```

Real environment identifiers are intentionally not required in the repository.

---

# Local Authentication Configuration

Example:

```bash
export OIDC_ISSUER="https://cognito-idp.eu-west-2.amazonaws.com/<user-pool-id>"
export OIDC_CLIENT_ID="<app-client-id>"

export AWS_DEFAULT_REGION="eu-west-2"
export TABLE_NAME="pharmacy-api-drugs"
export EVENT_BUS_NAME="default"
```

Start:

```bash
uvicorn app.main:app --reload
```

---

# Health Validation

```bash
curl -i http://127.0.0.1:8000/health
```

Expected:

```text
HTTP/1.1 200 OK
```

---

# Docker

Build:

```bash
docker build -t pharmacy-api .
```

Run:

```bash
docker run \
  --rm \
  --name pharmacy-api \
  --publish 8000:8000 \
  pharmacy-api
```

Hardened runtime:

```bash
docker run \
  --rm \
  --publish 8000:8000 \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  pharmacy-api
```

---

# Amazon ECR

The application image is stored in Amazon ECR.

Kubernetes references an immutable digest:

```text
pharmacy-api@sha256:...
```

instead of a mutable `latest` tag.

This provides deterministic workload deployment.

---

# Repository Structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── app/
│   ├── api/
│   │   └── routes.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   │
│   ├── infra/
│   │   ├── aws_clients.py
│   │   └── dynamodb.py
│   │
│   ├── models/
│   │   └── drug.py
│   │
│   ├── services/
│   │   └── drug_service.py
│   │
│   └── main.py
│
├── docs/
│   ├── cognito-authentication.png
│   ├── cognito-ci-validation.png
│   ├── cognito-drug-create.png
│   ├── cognito-dynamodb-persistence.png
│   ├── dynamodb-persistence.png
│   ├── eks-cluster-ready.png
│   ├── github-actions-ci.png
│   ├── health-check.png
│   ├── pharmacy-workload-running.png
│   └── pod-identity-proof.png
│
├── eks/
│   └── cluster.yaml
│
├── iam/
│   ├── pharmacy-api-policy.json
│   └── pod-identity-trust.json
│
├── k8s/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── ingress.yaml
│   ├── service.yaml
│   └── serviceaccount.yaml
│
├── tests/
│   ├── test_auth.py
│   ├── test_drug_service.py
│   └── test_routes.py
│
├── .dockerignore
├── .gitignore
├── .yamllint.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

# Engineering Skills Demonstrated

## AWS

- Amazon EKS
- Amazon ECR
- Amazon Cognito
- DynamoDB
- EventBridge
- AWS IAM
- EKS Pod Identity
- EC2 managed worker nodes
- Cognito User Pools
- Cognito App Clients
- Cognito Groups
- JWKS-based token validation

## Identity and Security

- OIDC
- JWT
- RS256 signatures
- JWKS
- issuer validation
- client/audience validation
- access-token enforcement
- tenant-aware identity
- role-aware identity
- public vs protected API boundaries
- fail-closed authentication

## Kubernetes

- Deployments
- Services
- ServiceAccounts
- readiness probes
- liveness probes
- rolling updates
- security contexts
- resource requests and limits
- seccomp
- Linux capability reduction
- Kubernetes manifest validation

## Container Engineering

- Docker
- non-root containers
- immutable images
- read-only root filesystems
- Linux capability reduction
- restricted writable filesystem paths
- reduced build contexts

## DevOps

- GitHub Actions
- pull request workflows
- automated Python tests
- container validation
- YAML linting
- kubeconform schema validation
- deployment verification

## Backend Engineering

- Python
- FastAPI
- PyJWT
- boto3
- REST APIs
- DynamoDB
- EventBridge
- authenticated tenant context
- dependency-based FastAPI authentication

---

# Current Limitations

The project intentionally documents remaining production concerns.

Current limitations include:

- tenant separation is encoded through Cognito groups rather than a dedicated identity-management model
- role values are currently application-defined strings
- DynamoDB tenant isolation is application-level rather than enforced through the table key design
- the EventBridge bus currently uses the AWS default event bus
- the ingress manifest requires a compatible ingress controller
- full external production ingress is not currently configured
- Cognito infrastructure is not yet provisioned through Infrastructure as Code
- full application observability has not yet been implemented
- token revocation/session-management workflows are not implemented in the API
- authorization currently validates identity context but does not yet provide fine-grained per-role endpoint permissions

---

# Next Improvements

Potential future iterations include:

- fine-grained role-based endpoint authorization
- Cognito infrastructure through Terraform or CloudFormation
- DynamoDB tenant-aware partition keys
- dedicated EventBridge event bus
- EventBridge retry and DLQ handling
- Kubernetes NetworkPolicies
- PodDisruptionBudget
- Horizontal Pod Autoscaling
- AWS Load Balancer Controller
- Prometheus metrics
- Grafana dashboards
- CloudWatch alarms
- OpenTelemetry tracing
- end-to-end integration tests
- deployment automation
- automated AWS infrastructure provisioning
- SBOM generation
- container image signing
- artifact provenance
- token/session revocation strategy

---

# Completed Roadmap

```text
[Complete] FastAPI application
[Complete] Hardened Docker image
[Complete] Kubernetes deployment
[Complete] Amazon ECR
[Complete] Immutable image digest
[Complete] Amazon EKS deployment
[Complete] EKS Pod Identity
[Complete] Least-privilege IAM
[Complete] DynamoDB persistence
[Complete] EventBridge publishing
[Complete] GitHub Actions CI
[Complete] Kubernetes validation

[Complete] Amazon Cognito User Pool validation
[Complete] Cognito App Client
[Complete] Real Cognito access token
[Complete] JWKS signature validation
[Complete] JWT issuer validation
[Complete] JWT client validation
[Complete] JWT expiration validation
[Complete] Access-token validation
[Complete] Tenant extraction
[Complete] Role extraction
[Complete] Authenticated /auth/me endpoint
[Complete] Protected POST /drugs
[Complete] Authenticated DynamoDB identity persistence
[Complete] EventBridge failure validation
```

---

# Purpose

This repository is an **AWS cloud-native workload engineering and application security case study**.

It demonstrates how a Python API can be:

- containerized securely
- hardened as a non-root workload
- published to Amazon ECR
- deployed using immutable image digests
- operated on Amazon EKS
- granted AWS access using EKS Pod Identity
- authenticated using Amazon Cognito
- protected using real JWT validation
- made tenant-aware through validated identity
- integrated with DynamoDB
- integrated with EventBridge
- validated through automated tests
- checked through CI
- verified against real AWS services

The project focuses on practical Cloud Engineering, Platform Engineering, Kubernetes, AWS workload security, application identity, and cloud-native application delivery.

---

# Author

**Olawale Azeez**

Cloud Engineer | Platform Engineer | AWS Certified Developer – Associate

AWS • Kubernetes • Platform Engineering • Cloud Infrastructure • DevOps • Cloud-Native Application Delivery