![header](https://capsule-render.vercel.app/api?type=waving&height=200&color=gradient&text=Serverless%20Fintech%20Ecosystem&fontSize=35&strokeWidth=0&desc=An%20Event-Driven%20Microservice%20Portfolio%20on%20AWS&descAlign=50&descAlignY=62&reversal=false&fontAlign=50&fontAlignY=40)

## 🚀 Live Demo

**[https://d2pymqjbz2xiof.cloudfront.net/](https://d2pymqjbz2xiof.cloudfront.net/)**

*(This demo environment is deployed from the `main` branch using the `prd` Terraform workspace.)*

---![header](https://capsule-render.vercel.app/api?type=waving&height=200&color=gradient&text=Serverless%20Fintech%20Ecosystem&fontSize=35&strokeWidth=0&desc=An%20Event-Driven%20Microservice%20Portfolio%20on%20AWS&descAlign=50&descAlignY=62&reversal=false&fontAlign=50&fontAlignY=40)

## 🚀 Live Demo

**[https://d2pymqjbz2xiof.cloudfront.net/](https://d2pymqjbz2xiof.cloudfront.net/)**

*(This demo environment is deployed from the `main` branch using the `prd` Terraform workspace.)*

---

## 📖 About This Project

This is a portfolio project demonstrating a complete, serverless, and event-driven fintech ecosystem built on Amazon Web Services (AWS). This includes a complete **React frontend** (hosted on S3/CloudFront) and a decoupled backend built from **five distinct microservices**.

This is not a single monolith. It is a collection of services that communicate asynchronously using **SNS (Simple Notification Service)**. This architecture is designed to be highly scalable, resilient, and maintainable, mirroring modern cloud-native design patterns.

All infrastructure is provisioned and managed using **Terraform**, demonstrating Infrastructure as Code (IaC) best practices, including **multi-environment workspaces** (`stg` and `prd`).

## ✅ Project Status: Complete

|| Service | Status | Description |
| :--- | :---: | :--- |
| **Frontend UI (React)** | ✅ | A React SPA that provides a UI for all backend services. |
| **Digital Wallet API** | ✅ | Core ledger service. Manages user balances and all transactions. |
| **Micro-Loan System** | ✅ | Manages loan applications, approvals, rejections, and repayments. |
| **Payment Simulator** | ✅ | Asynchronous, event-driven payment processing saga. |
| **Savings Goal Manager** | ✅ | Manages CRUD for savings goals and handles atomic fund transfers. |
| **Debt Repayment Optimiser** | ✅ | Algorithmic calculator for "Avalanche" vs. "Snowball" payoff plans. |

---

## 🏗️ Architecture Overview

The system's core design principle is **event-driven choreography**. Services do not call each other directly. Instead, they publish events to SNS topics, and other services subscribe to the events they care about. This creates a decoupled system where, for example, the `micro_loan` service can approve a loan without ever knowing *how* the `digital_wallet` service funds it.

### Key Workflows:

**1. Loan Approval Saga:**
1.  **Client** (`MicroLoans.jsx`) `POST`s to `/loan/{loan_id}/approve`.
2.  **Micro-Loan Service** (`approve_loan` Lambda) updates the loan status to "APPROVED".
3.  **Micro-Loan Service** publishes a `LOAN_APPROVED` event to the `loan_events` SNS topic.
4.  **Digital Wallet Service** (`process_loan_approval` Lambda) receives the event, credits the user's wallet balance, and logs a `LOAN_IN` transaction.

**2. Payment Processing Saga (Choreography):**
1.  **Client** (`PaymentSimulator.jsx`) `POST`s to `/payment`.
2.  **Payment Service** (`request_payment` Lambda) creates a "PENDING" transaction in its DynamoDB table.
3.  **Payment Service** publishes a `PAYMENT_REQUESTED` event to the `payment_events` SNS topic.
4.  **Digital Wallet Service** (`process_payment_request` Lambda) subscribes to this event.
5.  **Digital Wallet Service** attempts to debit the wallet.
    * **On Success:** It publishes a `PAYMENT_SUCCESSFUL` event back to the *same* `payment_events` topic and logs a `PAYMENT_OUT` transaction.
    * **On Failure (e.g., insufficient funds):** It publishes a `PAYMENT_FAILED` event.
6.  **Payment Service** (`update_transaction_status` Lambda) subscribes to the `_SUCCESSFUL` or `_FAILED` events and updates the transaction status from "PENDING" to "SUCCESSFUL" or "FAILED".

**3. Loan Repayment Saga (Choreography):**
*This saga reuses the exact same components as the Payment Saga.*
1.  **Client** (`MicroLoans.jsx`) `POST`s to `/loan/{loan_id}/repay`.
2.  **Micro-Loan Service** (`repay_loan` Lambda) publishes a `LOAN_REPAYMENT_REQUESTED` event to the `payment_events` topic.
3.  **Digital Wallet Service** (`process_payment_request` Lambda) receives this event, debits the wallet, logs a `LOAN_REPAYMENT` transaction, and publishes a `LOAN_REPAYMENT_SUCCESSFUL` event.
4.  **Micro-Loan Service** (`update_loan_repayment_status` Lambda) subscribes to this result, receives it, and updates the `remaining_balance` on the loan in the `loans_table`.

**4. Atomic Savings Goal Transaction:**
1.  **Client** (`SavingsGoals.jsx`) `POST`s to `/savings-goal/{id}/add`.
2.  **Savings Goal Service** (`add_to_savings_goal` Lambda) performs an atomic **DynamoDB Transaction** (`TransactWriteItems`) to simultaneously:
    * **Debit** the main `wallets_table` (with a condition check for sufficient funds).
    * **Credit** the `current_amount` on the `savings_goals_table`.
3.  The Lambda then logs a `SAVINGS_ADD` transaction to the `transaction-logs` table.

---

## 🛠️ Tech Stack

### Backend & DevOps
* **Infrastructure as Code:** **Terraform** (with `stg` & `prd` Workspaces)
* **Serverless Compute:** **AWS Lambda** (Python 3.12)
* **API:** **AWS API Gateway** (REST API)
* **Database:** **AWS DynamoDB** (including Global Secondary Indexes - GSIs)
* **Event-Driven Messaging:** **AWS SNS** (with Subscription Filter Policies)

### Frontend
* **Framework:** **React** (with React Hooks & Context API)
* **Hosting:** **AWS S3** (Static Website Hosting)
* **CDN & Delivery:** **AWS CloudFront** (with OAC)
* **UI/Styling:** **Tailwind CSS**
* **Data Visualization:** **Recharts**
* **Notifications:** **React Hot Toast**

---

## 🔒 Security Note

This project is currently configured for demo purposes. In a real-world production environment, all API Gateway endpoints would be secured. The recommended next step is to implement an **AWS Cognito User Pool** to manage user sign-up/sign-in and use a **Cognito Authorizer** on API Gateway to validate JWT tokens on all incoming requests.

---

## 📂 Project Structure

This repository is a monorepo managing all services and infrastructure.

```
Serverless-Fintech-Ecosystem/ 
├── frontend/ 
│ ├── src/ 
│ │ ├── Dashboard.jsx 
│ │ ├── Wallet.jsx 
│ │ ├── MicroLoans.jsx 
│ │ ├── SavingsGoals.jsx 
│ │ ├── PaymentSimulator.jsx 
│ │ ├── DebtOptimiser.jsx 
│ │ ├── ConfirmModal.jsx 
│ │ ├── Spinner.jsx 
│ │ └── ...
│ │ ├── contexts/
│ │ │ └── WalletContext.jsx
│ │ ├── App.jsx
│ │ └── main.jsx
│ ├── .env.production
│ └── .env.staging
├── terraform/
│ ├── main.tf # Root file (shared resources: API Gateway, SNS, DynamoDB tables)
│ ├── variables.tf
│ ├── outputs.tf
│ ├── prd.tfvars.json # Production variables (e.g., CloudFront URL)
│ ├── stg.tfvars.json # Staging variables (e.g., localhost)
│ └── modules/
│ │ ├── digital_wallet/ # IaC for Wallet service
│ │ ├── micro_loan/ # IaC for Loan service
│ │ ├── payment_processor/ # IaC for Payment service
│ │ ├── savings_goal/ # IaC for Savings service
│ │ ├── debt_optimiser/ # IaC for Optimiser service
└── src/
| ├── create_wallet/ # Python code for a single Lambda function
| ├── get_wallet/
| ├── credit_wallet/
| ├── debit_wallet/
| ├── get_wallet_transactions/
| ├── apply_for_loan/
| ├──  ... (and 20+ other Lambda function folders) ...
```

---

## 🚀 How to Deploy

This project uses **Terraform Workspaces** to manage separate `stg` (staging) and `prd` (production) environments.

### Prerequisites
1.  An [AWS Account](https://aws.amazon.com/)
2.  [AWS CLI](https://aws.amazon.com/cli/) configured (run `aws configure`)
3.  [Terraform](https://www.terraform.io/downloads.html) installed
4.  [Node.js](https://nodejs.org/en) (v18+) and `npm` installed
5.  A `git` client

### Part 1: Deploy Backend (Staging)

This workflow is for development.
1.  `git clone https://github.com/KayleeMcLaren/Serverless-Fintech-Ecosystem.git`
2.  `cd Serverless-Fintech-Ecosystem/terraform`
3.  `terraform init`
4.  `terraform workspace new stg` (or `terraform workspace select stg` if it exists)
5.  `terraform apply -var-file="stg.tfvars.json"`
    * This will build all `stg` resources (e.g., `fintech-ecosystem-stg-api`) and configure CORS for `http://localhost:5173`.
6.  Note the `api_endpoint_url` from the output.

### Part 2: Run Frontend (Staging)
1.  `cd ../frontend`
2.  Create a file named `.env.development` and add the `stg` API URL:
    ```
    VITE_API_URL="https-your-stg-api-url-from-step-6/v1"
    ```
3.  `npm install`
4.  `npm run dev`
    * Your app is now running at `http://localhost:5173` and connected to your live `stg` backend.

### Part 3: Deploy Backend (Production/Demo)
1.  `cd terraform`
2.  `terraform workspace select prd`
3.  `terraform apply -var-file="prd.tfvars.json"`
    * This first `apply` uses `frontend_cors_origin = "*"` to build all `prd` resources.
4.  Note the `cloudfront_domain_name` (e.g., `https://d123.cloudfront.net`) and `api_endpoint_url` from the outputs.
5.  **Edit `terraform/prd.tfvars.json`** and set the `frontend_cors_origin` to your CloudFront URL:
    ```json
    { "frontend_cors_origin": "[https://d123.cloudfront.net](https://d123.cloudfront.net)" }
    ```
6.  `terraform apply -var-file="prd.tfvars.json"`
    * Run `apply` a second time. This updates all 20 Lambdas and API Gateway integrations with the correct, secure CORS origin.

### Part 4: Deploy Frontend (Production/Demo)
1.  `cd ../frontend`
2.  Create a file named `.env.production` and add the `prd` API URL:
    ```
    VITE_API_URL="httpshttps://your-prd-api-url-from-step-4/v1"
    ```
3.  `npm install`
4.  `npm run build`
5.  Note your `prd` S3 bucket name from the Terraform output (e.g., `fintech-ecosystem-prd-frontend-bucket-...`).
6.  Sync the build to S3:
    ```bash
    aws s3 sync ./dist/ s3://YOUR-PRD-BUCKET-NAME --delete
    ```
7.  In the **AWS CloudFront Console**, find your `prd` distribution, go to the "Invalidations" tab, and create a new invalidation for `/*`.

---

## 🧪 Testing

Testing an event-driven system involves two main types of tests:

### 1. Unit Tests (with `pytest` and `moto`)
Unit tests are used to test a single Lambda function's logic in isolation. We use `pytest` for the test framework and `moto` to mock all AWS services (DynamoDB, SNS).

**To run tests:**
1.  Install dependencies: `pip install pytest moto[dynamodb,sns]`
2.  Navigate to the `src` directory: `cd src`
3.  Run `pytest`: `pytest`

**Example (`src/tests/test_create_wallet.py`):**
```python
import pytest
import boto3
from moto import mock_dynamodb
from create_wallet.handler import create_wallet
import os
import json

@pytest.fixture
def mock_env(monkeypatch):
    """Mocks environment variables."""
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-wallets")
    monkeypatch.setenv("TRANSACTIONS_LOG_TABLE_NAME", "test-logs")
    monkeypatch.setenv("CORS_ORIGIN", "*")

@pytest.fixture
def mock_db(mock_env):
    """Mocks DynamoDB."""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        # Create the wallets table
        dynamodb.create_table(
            TableName="test-wallets",
            KeySchema=[{'AttributeName': 'wallet_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'wallet_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        # Create the logs table
        dynamodb.create_table(
            TableName="test-logs",
            KeySchema=[{'AttributeName': 'transaction_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'transaction_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        yield dynamodb

def test_create_wallet_success(mock_db):
    """Tests successful wallet creation."""
    event = {"httpMethod": "POST", "body": "{}"}
    context = {}
    
    response = create_wallet(event, context)
    
    assert response['statusCode'] == 201
    body = json.loads(response['body'])
    assert 'wallet' in body
    assert 'wallet_id' in body['wallet']

    # Verify item was created in the mock DB
    table = mock_db.Table("test-wallets")
    item = table.get_item(Key={'wallet_id': body['wallet']['wallet_id']})
    assert item['Item']['balance'] == 0
```

### 2. Integration Tests
Integration tests check the flow between services. A simple way to test this is:

1. Deploy the stack to the `stg` workspace.

2. Manually (or via an AWS CLI script) publish a test `LOAN_APPROVED` event to the `fintech-ecosystem-stg-loan-events` SNS topic.

3. Wait ~5 seconds.

4. Manually (or via script) query the `fintech-ecosystem-stg-wallets` table to assert that the correct wallet's balance was increased.

## 🔄 CI/CD Pipeline
A basic CI/CD pipeline is defined in .github/workflows/ci.yml. This GitHub Actions workflow triggers on every push to main or dev and:

1. Sets up Python.

2. Installs Python dependencies (e.g., pytest, moto).

3. **Runs Unit Tests** with pytest.

4. Sets up Terraform.

5. **Validates Terraform** with terraform init and terraform validate.

Example (.github/workflows/ci.yml):
```
name: CI Pipeline

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main ]

jobs:
  test-lambda:
    name: Run Lambda Unit Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          # Create/use a requirements.txt in your src folder for libraries like boto3
          # pip install -r src/requirements.txt
          pip install pytest moto[dynamodb,sns]
      - name: Run tests
        run: |
          cd src
          pytest

  validate-terraform:
    name: Validate Terraform
    runs-on: ubuntu-latest
    needs: test-lambda # Run after tests pass
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3
      - name: Terraform Init
        run: |
          cd terraform
          terraform init -backend=false # Don't need state for validation
      - name: Terraform Validate
        run: |
          cd terraform
          terraform validate
```

## 🗺️ API Endpoints
**Base URL:** (From terraform apply output, e.g., .../v1)

### Digital Wallet Service (/wallet)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/wallet` | Creates a new wallet with a $0.00 balance. |
| `GET` | `/wallet/{wallet_id}` | Gets wallet balance and details. |
| `POST` | `/wallet/{wallet_id}/credit` | Adds funds to a wallet. |
| `POST` | `/wallet/{wallet_id}/debit` | Removes funds from a wallet (fails on overdraft). |
| `GET` | `/wallet/{wallet_id}/transactions` | Gets the wallet's transaction history. |

### Micro-Loan Service (/loan)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/loan` | Applies for a new loan (status: "PENDING"). |
| `GET` | `/loan/{loan_id}` | Gets the details and status of a single loan. |
| `GET` | `/loan/by-wallet/{wallet_id}` | Gets all loans associated with a wallet (uses GSI). |
| `POST` | `/loan/{loan_id}/approve` | **(Admin) Triggers Loan Approval Saga.** |
| `POST` | `/loan/{loan_id}/reject` | **(Admin)** Rejects a pending loan.. |
| `POST` | `/loan/{loan_id}/repay` | **Triggers Loan Repayment Saga.** |

### Payment Processing Service (/payment)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/payment` | **Triggers Payment Processing Saga.** (Returns `202 Accepted`) |
| `GET` | `/payment/{transaction_id}` | Checks the status of a payment ("PENDING", "SUCCESSFUL", "FAILED"). |
| `GET` | `/payment/by-wallet/{wallet_id}` | Gets all payment transactions for a wallet. |

### Savings Goal Service (/savings-goal)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST`| `/savings-goal` | Creates a new savings goal. |
| `GET` | `/savings-goal/by-wallet/{wallet_id}` | Gets all savings goals for a wallet. |
| `DELETE` | `/savings-goal/{goal_id}` | Deletes a savings goal. |
| `POST`| `/savings-goal/{goal_id}/add` | Atomically transfers funds from wallet to goal. |
| `GET` | `/savings-goal/{goal_id}/transactions` | Gets the contribution history for a goal. |
| `POST`| `/savings-goal/{goal_id}/redeem` | Redeems a completed goal, transferring funds to wallet. |

### Debt Optimiser Service (/debt-optimiser)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST`| `/debt-optimiser` | Calculates Avalanche vs. Snowball loan repayment plans. |

## 📖 About This Project

This is a portfolio project demonstrating a complete, serverless, and event-driven fintech ecosystem built on Amazon Web Services (AWS). This includes a complete **React frontend** (hosted on S3/CloudFront) and a decoupled backend built from **five distinct microservices**.

This is not a single monolith. It is a collection of services that communicate asynchronously using **SNS (Simple Notification Service)**. This architecture is designed to be highly scalable, resilient, and maintainable, mirroring modern cloud-native design patterns.

All infrastructure is provisioned and managed using **Terraform**, demonstrating Infrastructure as Code (IaC) best practices, including **multi-environment workspaces** (`stg` and `prd`).

## ✅ Project Status: Complete

|| Service | Status | Description |
| :--- | :---: | :--- |
| **Frontend UI (React)** | ✅ | A React SPA that provides a UI for all backend services. |
| **Digital Wallet API** | ✅ | Core ledger service. Manages user balances and all transactions. |
| **Micro-Loan System** | ✅ | Manages loan applications, approvals, rejections, and repayments. |
| **Payment Simulator** | ✅ | Asynchronous, event-driven payment processing saga. |
| **Savings Goal Manager** | ✅ | Manages CRUD for savings goals and handles atomic fund transfers. |
| **Debt Repayment Optimiser** | ✅ | Algorithmic calculator for "Avalanche" vs. "Snowball" payoff plans. |

---

## 🏗️ Architecture Overview

The system's core design principle is **event-driven choreography**. Services do not call each other directly. Instead, they publish events to SNS topics, and other services subscribe to the events they care about. This creates a decoupled system where, for example, the `micro_loan` service can approve a loan without ever knowing *how* the `digital_wallet` service funds it.

### Key Workflows:

**1. Loan Approval Saga:**
1.  **Client** (`MicroLoans.jsx`) `POST`s to `/loan/{loan_id}/approve`.
2.  **Micro-Loan Service** (`approve_loan` Lambda) updates the loan status to "APPROVED".
3.  **Micro-Loan Service** publishes a `LOAN_APPROVED` event to the `loan_events` SNS topic.
4.  **Digital Wallet Service** (`process_loan_approval` Lambda) receives the event, credits the user's wallet balance, and logs a `LOAN_IN` transaction.

**2. Payment Processing Saga (Choreography):**
1.  **Client** (`PaymentSimulator.jsx`) `POST`s to `/payment`.
2.  **Payment Service** (`request_payment` Lambda) creates a "PENDING" transaction in its DynamoDB table.
3.  **Payment Service** publishes a `PAYMENT_REQUESTED` event to the `payment_events` SNS topic.
4.  **Digital Wallet Service** (`process_payment_request` Lambda) subscribes to this event.
5.  **Digital Wallet Service** attempts to debit the wallet.
    * **On Success:** It publishes a `PAYMENT_SUCCESSFUL` event back to the *same* `payment_events` topic and logs a `PAYMENT_OUT` transaction.
    * **On Failure (e.g., insufficient funds):** It publishes a `PAYMENT_FAILED` event.
6.  **Payment Service** (`update_transaction_status` Lambda) subscribes to the `_SUCCESSFUL` or `_FAILED` events and updates the transaction status from "PENDING" to "SUCCESSFUL" or "FAILED".

**3. Loan Repayment Saga (Choreography):**
*This saga reuses the exact same components as the Payment Saga.*
1.  **Client** (`MicroLoans.jsx`) `POST`s to `/loan/{loan_id}/repay`.
2.  **Micro-Loan Service** (`repay_loan` Lambda) publishes a `LOAN_REPAYMENT_REQUESTED` event to the `payment_events` topic.
3.  **Digital Wallet Service** (`process_payment_request` Lambda) receives this event, debits the wallet, logs a `LOAN_REPAYMENT` transaction, and publishes a `LOAN_REPAYMENT_SUCCESSFUL` event.
4.  **Micro-Loan Service** (`update_loan_repayment_status` Lambda) subscribes to this result, receives it, and updates the `remaining_balance` on the loan in the `loans_table`.

**4. Atomic Savings Goal Transaction:**
1.  **Client** (`SavingsGoals.jsx`) `POST`s to `/savings-goal/{id}/add`.
2.  **Savings Goal Service** (`add_to_savings_goal` Lambda) performs an atomic **DynamoDB Transaction** (`TransactWriteItems`) to simultaneously:
    * **Debit** the main `wallets_table` (with a condition check for sufficient funds).
    * **Credit** the `current_amount` on the `savings_goals_table`.
3.  The Lambda then logs a `SAVINGS_ADD` transaction to the `transaction-logs` table.

---

## 🛠️ Tech Stack

### Backend & DevOps
* **Infrastructure as Code:** **Terraform** (with `stg` & `prd` Workspaces)
* **Serverless Compute:** **AWS Lambda** (Python 3.12)
* **API:** **AWS API Gateway** (REST API)
* **Database:** **AWS DynamoDB** (including Global Secondary Indexes - GSIs)
* **Event-Driven Messaging:** **AWS SNS** (with Subscription Filter Policies)

### Frontend
* **Framework:** **React** (with React Hooks & Context API)
* **Hosting:** **AWS S3** (Static Website Hosting)
* **CDN & Delivery:** **AWS CloudFront** (with OAC)
* **UI/Styling:** **Tailwind CSS**
* **Data Visualization:** **Recharts**
* **Notifications:** **React Hot Toast**

---

## 🔒 Security Note

This project is currently configured for demo purposes. In a real-world production environment, all API Gateway endpoints would be secured. The recommended next step is to implement an **AWS Cognito User Pool** to manage user sign-up/sign-in and use a **Cognito Authorizer** on API Gateway to validate JWT tokens on all incoming requests.

---

## 📂 Project Structure

This repository is a monorepo managing all services and infrastructure.

```
Serverless-Fintech-Ecosystem/ 
├── frontend/ 
│ ├── src/ 
│ │ ├── Dashboard.jsx 
│ │ ├── Wallet.jsx 
│ │ ├── MicroLoans.jsx 
│ │ ├── SavingsGoals.jsx 
│ │ ├── PaymentSimulator.jsx 
│ │ ├── DebtOptimiser.jsx 
│ │ ├── ConfirmModal.jsx 
│ │ ├── Spinner.jsx 
│ │ └── ...
│ │ ├── contexts/
│ │ │ └── WalletContext.jsx
│ │ ├── App.jsx
│ │ └── main.jsx
│ ├── .env.production
│ └── .env.staging
├── terraform/
│ ├── main.tf # Root file (shared resources: API Gateway, SNS, DynamoDB tables)
│ ├── variables.tf
│ ├── outputs.tf
│ ├── prd.tfvars.json # Production variables (e.g., CloudFront URL)
│ ├── stg.tfvars.json # Staging variables (e.g., localhost)
│ └── modules/
│ │ ├── digital_wallet/ # IaC for Wallet service
│ │ ├── micro_loan/ # IaC for Loan service
│ │ ├── payment_processor/ # IaC for Payment service
│ │ ├── savings_goal/ # IaC for Savings service
│ │ ├── debt_optimiser/ # IaC for Optimiser service
└── src/
| ├── create_wallet/ # Python code for a single Lambda function
| ├── get_wallet/
| ├── credit_wallet/
| ├── debit_wallet/
| ├── get_wallet_transactions/
| ├── apply_for_loan/
| ├──  ... (and 20+ other Lambda function folders) ...
```

---

## 🚀 How to Deploy

This project uses **Terraform Workspaces** to manage separate `stg` (staging) and `prd` (production) environments.

### Prerequisites
1.  An [AWS Account](https://aws.amazon.com/)
2.  [AWS CLI](https://aws.amazon.com/cli/) configured (run `aws configure`)
3.  [Terraform](https://www.terraform.io/downloads.html) installed
4.  [Node.js](https://nodejs.org/en) (v18+) and `npm` installed
5.  A `git` client

### Part 1: Deploy Backend (Staging)

This workflow is for development.
1.  `git clone https://github.com/KayleeMcLaren/Serverless-Fintech-Ecosystem.git`
2.  `cd Serverless-Fintech-Ecosystem/terraform`
3.  `terraform init`
4.  `terraform workspace new stg` (or `terraform workspace select stg` if it exists)
5.  `terraform apply -var-file="stg.tfvars.json"`
    * This will build all `stg` resources (e.g., `fintech-ecosystem-stg-api`) and configure CORS for `http://localhost:5173`.
6.  Note the `api_endpoint_url` from the output.

### Part 2: Run Frontend (Staging)
1.  `cd ../frontend`
2.  Create a file named `.env.development` and add the `stg` API URL:
    ```
    VITE_API_URL="https-your-stg-api-url-from-step-6/v1"
    ```
3.  `npm install`
4.  `npm run dev`
    * Your app is now running at `http://localhost:5173` and connected to your live `stg` backend.

### Part 3: Deploy Backend (Production/Demo)
1.  `cd terraform`
2.  `terraform workspace select prd`
3.  `terraform apply -var-file="prd.tfvars.json"`
    * This first `apply` uses `frontend_cors_origin = "*"` to build all `prd` resources.
4.  Note the `cloudfront_domain_name` (e.g., `https://d123.cloudfront.net`) and `api_endpoint_url` from the outputs.
5.  **Edit `terraform/prd.tfvars.json`** and set the `frontend_cors_origin` to your CloudFront URL:
    ```json
    { "frontend_cors_origin": "[https://d123.cloudfront.net](https://d123.cloudfront.net)" }
    ```
6.  `terraform apply -var-file="prd.tfvars.json"`
    * Run `apply` a second time. This updates all 20 Lambdas and API Gateway integrations with the correct, secure CORS origin.

### Part 4: Deploy Frontend (Production/Demo)
1.  `cd ../frontend`
2.  Create a file named `.env.production` and add the `prd` API URL:
    ```
    VITE_API_URL="httpshttps://your-prd-api-url-from-step-4/v1"
    ```
3.  `npm install`
4.  `npm run build`
5.  Note your `prd` S3 bucket name from the Terraform output (e.g., `fintech-ecosystem-prd-frontend-bucket-...`).
6.  Sync the build to S3:
    ```bash
    aws s3 sync ./dist/ s3://YOUR-PRD-BUCKET-NAME --delete
    ```
7.  In the **AWS CloudFront Console**, find your `prd` distribution, go to the "Invalidations" tab, and create a new invalidation for `/*`.

---

## 🧪 Testing

Testing an event-driven system involves two main types of tests:

### 1. Unit Tests (with `pytest` and `moto`)
Unit tests are used to test a single Lambda function's logic in isolation. We use `pytest` for the test framework and `moto` to mock all AWS services (DynamoDB, SNS).

**To run tests:**
1.  Install dependencies: `pip install pytest moto[dynamodb,sns]`
2.  Navigate to the `src` directory: `cd src`
3.  Run `pytest`: `pytest`

**Example (`src/tests/test_create_wallet.py`):**
```python
import pytest
import boto3
from moto import mock_dynamodb
from create_wallet.handler import create_wallet
import os
import json

@pytest.fixture
def mock_env(monkeypatch):
    """Mocks environment variables."""
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-wallets")
    monkeypatch.setenv("TRANSACTIONS_LOG_TABLE_NAME", "test-logs")
    monkeypatch.setenv("CORS_ORIGIN", "*")

@pytest.fixture
def mock_db(mock_env):
    """Mocks DynamoDB."""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        # Create the wallets table
        dynamodb.create_table(
            TableName="test-wallets",
            KeySchema=[{'AttributeName': 'wallet_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'wallet_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        # Create the logs table
        dynamodb.create_table(
            TableName="test-logs",
            KeySchema=[{'AttributeName': 'transaction_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'transaction_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        yield dynamodb

def test_create_wallet_success(mock_db):
    """Tests successful wallet creation."""
    event = {"httpMethod": "POST", "body": "{}"}
    context = {}
    
    response = create_wallet(event, context)
    
    assert response['statusCode'] == 201
    body = json.loads(response['body'])
    assert 'wallet' in body
    assert 'wallet_id' in body['wallet']

    # Verify item was created in the mock DB
    table = mock_db.Table("test-wallets")
    item = table.get_item(Key={'wallet_id': body['wallet']['wallet_id']})
    assert item['Item']['balance'] == 0
```

### 2. Integration Tests
Integration tests check the flow between services. A simple way to test this is:

1. Deploy the stack to the `stg` workspace.

2. Manually (or via an AWS CLI script) publish a test `LOAN_APPROVED` event to the `fintech-ecosystem-stg-loan-events` SNS topic.

3. Wait ~5 seconds.

4. Manually (or via script) query the `fintech-ecosystem-stg-wallets` table to assert that the correct wallet's balance was increased.

## 🔄 CI/CD Pipeline
A basic CI/CD pipeline is defined in .github/workflows/ci.yml. This GitHub Actions workflow triggers on every push to main or dev and:

1. Sets up Python.

2. Installs Python dependencies (e.g., pytest, moto).

3. **Runs Unit Tests** with pytest.

4. Sets up Terraform.

5. **Validates Terraform** with terraform init and terraform validate.

Example (.github/workflows/ci.yml):
```
name: CI Pipeline

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main ]

jobs:
  test-lambda:
    name: Run Lambda Unit Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          # Create/use a requirements.txt in your src folder for libraries like boto3
          # pip install -r src/requirements.txt
          pip install pytest moto[dynamodb,sns]
      - name: Run tests
        run: |
          cd src
          pytest

  validate-terraform:
    name: Validate Terraform
    runs-on: ubuntu-latest
    needs: test-lambda # Run after tests pass
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3
      - name: Terraform Init
        run: |
          cd terraform
          terraform init -backend=false # Don't need state for validation
      - name: Terraform Validate
        run: |
          cd terraform
          terraform validate
```

## 🗺️ API Endpoints
**Base URL:** (From terraform apply output, e.g., .../v1)

### Digital Wallet Service (/wallet)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/wallet` | Creates a new wallet with a $0.00 balance. |
| `GET` | `/wallet/{wallet_id}` | Gets wallet balance and details. |
| `POST` | `/wallet/{wallet_id}/credit` | Adds funds to a wallet. |
| `POST` | `/wallet/{wallet_id}/debit` | Removes funds from a wallet (fails on overdraft). |
| `GET` | `/wallet/{wallet_id}/transactions` | Gets the wallet's transaction history. |

### Micro-Loan Service (/loan)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/loan` | Applies for a new loan (status: "PENDING"). |
| `GET` | `/loan/{loan_id}` | Gets the details and status of a single loan. |
| `GET` | `/loan/by-wallet/{wallet_id}` | Gets all loans associated with a wallet (uses GSI). |
| `POST` | `/loan/{loan_id}/approve` | **(Admin) Triggers Loan Approval Saga.** |
| `POST` | `/loan/{loan_id}/reject` | **(Admin)** Rejects a pending loan.. |
| `POST` | `/loan/{loan_id}/repay` | **Triggers Loan Repayment Saga.** |

### Payment Processing Service (/payment)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/payment` | **Triggers Payment Processing Saga.** (Returns `202 Accepted`) |
| `GET` | `/payment/{transaction_id}` | Checks the status of a payment ("PENDING", "SUCCESSFUL", "FAILED"). |
| `GET` | `/payment/by-wallet/{wallet_id}` | Gets all payment transactions for a wallet. |

### Savings Goal Service (/savings-goal)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST`| `/savings-goal` | Creates a new savings goal. |
| `GET` | `/savings-goal/by-wallet/{wallet_id}` | Gets all savings goals for a wallet. |
| `DELETE` | `/savings-goal/{goal_id}` | Deletes a savings goal. |
| `POST`| `/savings-goal/{goal_id}/add` | Atomically transfers funds from wallet to goal. |
| `GET` | `/savings-goal/{goal_id}/transactions` | Gets the contribution history for a goal. |
| `POST`| `/savings-goal/{goal_id}/redeem` | Redeems a completed goal, transferring funds to wallet. |

### Debt Optimiser Service (/debt-optimiser)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST`| `/debt-optimiser` | Calculates Avalanche vs. Snowball loan repayment plans. |