![header](https://capsule-render.vercel.app/api?type=waving&height=200&color=gradient&text=Serverless%20Fintech%20Ecosystem&fontSize=35&strokeWidth=0&desc=An%20Event-Driven%20Microservice%20Portfolio%20on%20AWS&descAlign=50&descAlignY=62&reversal=false&fontAlign=50&fontAlignY=40)

## 🚀 Live Demo

**[https://d18l23eogq3lrf.cloudfront.net/](https://d18l23eogq3lrf.cloudfront.net/)**

*(This demo environment is deployed from the `main` branch using the `prd` Terraform workspace.)*

---

## ✨ Core Technical Achievements (Production-Grade Features)
This project was developed with a relentless focus on modern, cloud-native engineering practices to demonstrate expertise in highly available, secure, and maintainable systems.

| Category | Achievement | Implementation Details |
| :--- | :---: | :--- |
| **🔒 Security & Auth** | Secured All APIs with Cognito | Every major endpoint (20+ routes) is protected using an AWS Cognito Authorizer to validate JWT tokens, ensuring a production-ready, multi-user system architecture. |
| **🧪 Testing & CI/CD** | Automated Unit Testing | Implemented Pytest and Moto (AWS mocking) unit tests for core financial logic and integrated them into the GitHub Actions CI/CD pipeline to guarantee zero regressions. |
| **📊 Observability** | Structured JSON Logging | Refactored all 20+ Lambda handlers to output queryable JSON logs (instead of plaintext), dramatically improving the efficiency of debugging and monitoring in CloudWatch Log Insights. |
| **🔄 Workflow Mgmt** | Step Function Orchestration | Implemented a reliable, non-blocking user onboarding workflow (KYC/Wallet creation) managed by AWS Step Functions (SFN). |
| **💰 Financial Logic** | Stable Amortization Engine | Replaced brittle simulation logic with a stable mathematical projection engine, accurately calculating interest saved and payoff time for accelerated debt repayment. |

---

## 📖 About This Project

This is a portfolio project demonstrating a complete, **serverless**, and **event-driven fintech ecosystem** built on Amazon Web Services (AWS). It is designed to be highly scalable, resilient, and maintainable, mirroring modern cloud-native design patterns.

All infrastructure is provisioned and managed using **Terraform**, demonstrating **Infrastructure as Code (IaC)** best practices, including **multi-environment workspaces** (`stg` and `prd`).

---

## ✅ Project Status: Complete

| Service | Status | Description |
| :--- | :---: | :--- |
| **Frontend UI (React)** | ✅ | A React SPA that provides a UI for all backend services. |
| **Digital Wallet API** | ✅ | Core ledger service. Manages user balances and all transactions. |
| **Micro-Loan System** | ✅ | Manages loan applications, approvals, rejections, and repayments. |
| **Payment Simulator** | ✅ | Asynchronous, event-driven payment processing saga. |
| **Savings Goal Manager** | ✅ | Manages CRUD for savings goals and handles atomic fund transfers. |
| **Debt Repayment Optimiser** | ✅ | Provides projections for accelerated debt payoff plans. |

---

## 💡 Why I Built This

This project started as a way to deepen my understanding of event-driven architectures and serverless patterns. Working in fintech at AIMLScore, I wanted to build something that would challenge me to implement the production-grade patterns I'd been exposed to:

- **Event choreography** instead of orchestration (letting services communicate asynchronously)
- **Atomic transactions** for financial correctness (all-or-nothing operations)
- **Step Functions** for complex workflows (KYC with human-in-the-loop approval)
- **Comprehensive testing** with mocked AWS services (no actual AWS calls in tests)

Along the way, I learned invaluable lessons about:
- The tradeoffs between different architectural patterns
- How to structure Terraform for multi-environment management
- The importance of observability (structured logging saved me countless debugging hours)
- Why financial systems require different correctness guarantees than typical CRUD apps

This project represents not just what I can build, but how I approach learning: starting with production patterns and building a complete, deployable system.

---

## 🏗️ Architecture Overview

The system's core design principle is **event-driven choreography**. Services do not call each other directly. Instead, they publish events to SNS topics, and other services subscribe to the events they care about. This creates a decoupled system where, for example, the `micro_loan` service can approve a loan without ever knowing *how* the `digital_wallet` service funds it.

### Key Workflows:

**1. 🔒 User Authentication & API Security (Foundation):**
This workflow demonstrates the secure entry point and highlights the serverless automation built into the authentication process.
1. **Client (React)** sends user credentials (email/password) to **AWS Cognito**.
2. **Cognito Trigger:** The **Pre Sign-Up Lambda** (`auto_confirm_user`) immediately intercepts the request and sets autoConfirmUser: True and autoVerifyEmail: True. This step **bypasses the standard email verification process** for a streamlined demo experience.
3. Upon successful login, the **Client** receives a **JWT Token**.
4. The **Client** attaches this token to the Authorization header of all subsequent API requests.
5. **API Gateway** uses a **Cognito Authorizer** to validate the token's signature and expiration before forwarding the request to any downstream Lambda handler.

**2. 📝 User Onboarding & KYC Orchestration (SFN):**
This is a **State Machine** (SFN) workflow, guaranteeing sequential, auditable steps for user approval, including a dedicated path for human intervention.
1. **Client** calls `POST /onboarding/start` (`src/start_onboarding/handler.py`). The Lambda creates a `PENDING_ID_VERIFICATION` record and starts the **Step Function** (SFN).
2. **SFN Task: ID Verification**
   * The SFN executes the `verify_id_mock` Lambda (using the logic in `src/verify_id_mock/handler.py`).
   * The Lambda runs mock logic (checks for `flag@`, `reject`) and returns a simple JSON decision (`{"status": "APPROVED", "message": "..."}`).
3. **SFN Choice State: Based on the output:**
   * If `APPROVED`: Proceeds to the `CreditCheck` task.
   * If `FLAGGED`: Proceeds to the **Human-in-the-Loop** step.
4. **SFN Task: Human-in-the-Loop**
   * The SFN pauses via the `DynamoDB:UpdateItem.waitForTaskToken` integration, which writes the `TaskToken` to the user's record in the `users_table`.
   * The **Admin Tools** calls the `manual_review` API (`src/manual_review_handler/handler.py`). This Lambda retrieves the token and sends a `send_task_success` signal to the SFN to resume the workflow.
5. **SFN Task: Credit Check**
   * The SFN executes the `credit_check_mock` Lambda (using the logic in `src/credit_check_mock/handler.py`), which returns a score and a decision.
6. **SFN Conclusion:** If the credit check is approved, the SFN executes the final `ProvisionAccount` task, which invokes the private `create_wallet` Lambda. The user's final `wallet_id` and `onboarding_status` are set to `APPROVED`.

**3. 💸 Loan Approval Saga:**
1.  **Client** `POST`s to `/loan/{loan_id}/approve`.
2.  **Micro-Loan Service** (`approve_loan` Lambda) updates the loan status to "APPROVED".
3.  **Micro-Loan Service** publishes a `LOAN_APPROVED` event to the `loan_events` SNS topic.
4.  **Digital Wallet Service** (`process_loan_approval` Lambda) receives the event, credits the user's wallet balance, and logs a `LOAN_IN` transaction.

**4. 💳 Payment Processing Saga (Choreography):**
1.  **Client** (`PaymentSimulator.jsx`) `POST`s to `/payment`.
2.  **Payment Service** (`request_payment` Lambda) creates a "PENDING" transaction in its DynamoDB table.
3.  **Payment Service** publishes a `PAYMENT_REQUESTED` event to the `payment_events` SNS topic.
4.  **Digital Wallet Service** (`process_payment_request` Lambda) subscribes to this event.
5.  **Digital Wallet Service** attempts to debit the wallet.
    * **On Success:** It publishes a `PAYMENT_SUCCESSFUL` event back to the *same* `payment_events` topic and logs a `PAYMENT_OUT` transaction.
    * **On Failure (e.g., insufficient funds):** It publishes a `PAYMENT_FAILED` event.
6.  **Payment Service** (`update_transaction_status` Lambda) subscribes to the `_SUCCESSFUL` or `_FAILED` events and updates the transaction status from "PENDING" to "SUCCESSFUL" or "FAILED".

**5. . 📉 Loan Repayment Saga (Choreography):**
*This saga reuses the exact same components as the Payment Saga.*
1.  **Client** (`MicroLoans.jsx`) `POST`s to `/loan/{loan_id}/repay`.
2.  **Micro-Loan Service** (`repay_loan` Lambda) publishes a `LOAN_REPAYMENT_REQUESTED` event to the `payment_events` topic.
3.  **Digital Wallet Service** (`process_payment_request` Lambda) receives this event, debits the wallet, logs a `LOAN_REPAYMENT` transaction, and publishes a `LOAN_REPAYMENT_SUCCESSFUL` event.
4.  **Micro-Loan Service** (`update_loan_repayment_status` Lambda) subscribes to this result, receives it, and updates the `remaining_balance` on the loan in the `loans_table`.

**6. 🎯 Atomic Savings Goal Transaction:**
1.  **Client** (`SavingsGoals.jsx`) `POST`s to `/savings-goal/{id}/add`.
2.  **Savings Goal Service** (`add_to_savings_goal` Lambda) performs an atomic **DynamoDB Transaction** (`TransactWriteItems`) to simultaneously:
    * **Debit** the main `wallets_table` (with a condition check for sufficient funds).
    * **Credit** the `current_amount` on the `savings_goals_table`.
3.  The Lambda then logs a `SAVINGS_ADD` transaction to the `transaction-logs` table.

---

## 🛠️ Tech Stack

### Backend & DevOps
* **Infrastructure as Code:** **Terraform** (with `stg` & `prd` Workspaces)
* **Authentication:** AWS Cognito (User Pool, JWT Authorizers)
* **Serverless Compute:** **AWS Lambda** (Python 3.12)
* **API:** **AWS API Gateway** (REST API)
* **Database:** **AWS DynamoDB** (including Global Secondary Indexes - GSIs)
* **Workflow:** AWS Step Functions (SFN)
* **Event-Driven Messaging:** **AWS SNS** (with Subscription Filter Policies)

### Frontend
* **Framework:** **React** (with React Hooks & Context API)
* **Hosting:** **AWS S3** (Static Website Hosting) 
* **CDN & Delivery:** **AWS CloudFront** (with OAC)
* **UI/Styling:** **Tailwind CSS**
* **Notifications:** **React Hot Toast**

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
│ │ └── ... (All React components updated for Authorization)
│ │ ├── contexts/
│ │ │ └── WalletContext.jsx (Manages Cognito Session)
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
    VITE_API_URL="https://your-prd-api-url-from-step-4/v1"
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

## 🧪 Detailed Testing & Code Quality

Code quality is enforced via a GitHub Actions pipeline that executes unit tests and validates all Infrastructure as Code (IaC) before deployment.

### 1. CI/CD Pipeline (`.github/workflows/ci.yml`)
The pipeline validates code quality on every push and pull request. It runs unit tests first, then validates Terraform configuration. 
**Note:** This is a validation pipeline; actual deployment is done manually via Terraform workspaces as described in the deployment section.

```yaml
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
    
    # Set the working directory to the 'src' folder
    defaults:
      run:
        working-directory: ./src

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          # We also need boto3, which is available in the Lambda runtime
          pip install boto3

      - name: Run tests
        run: |
          python3 -m pytest tests/

  validate-terraform:
    name: Validate Terraform
    runs-on: ubuntu-latest
    needs: test-lambda
    
    # Set the working directory to the 'terraform' folder
    defaults:
      run:
        working-directory: ./terraform
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform init -backend=false

      - name: Terraform Validate
        run: terraform validate
```
###  2. Unit Test Examples (Pytest + Moto)
Unit tests mock AWS services like DynamoDB and SNS to ensure core business logic is executed reliably without external network dependencies.

**A. Atomic Savings Transaction** (`tests/test_add_to_savings_goal.py`)
This test verifies the critical TransactWriteItems operation is atomic (debit wallet, credit goal) and correctly fails when funds are insufficient.

```
# Mocks: DynamoDB

def test_add_to_savings_goal_success(mock_db):
    # ARRANGE: Wallet balance: $100.00, Goal balance: $50.00
    wallets_table = mock_db.Table('test-wallets')
    savings_table = mock_db.Table('test-savings-goals')
    wallets_table.put_item(Item={'wallet_id': 'w_123', 'balance': Decimal('100.00')})
    savings_table.put_item(Item={'goal_id': 'g_123', 'wallet_id': 'w_123', 'current_amount': Decimal('50.00'), ...})
    
    # ACT: Attempt to move $25.50
    response = add_to_savings_goal(event, {})

    # ASSERT:
    assert response['statusCode'] == 200
    # Wallet balance is $74.50 (100.00 - 25.50)
    assert wallets_table.get_item(Key={'wallet_id': 'w_123'})['Item']['balance'] == Decimal('74.50') 
    # Goal balance is $75.50 (50.00 + 25.50)
    assert savings_table.get_item(Key={'goal_id': 'g_123'})['Item']['current_amount'] == Decimal('75.50')

def test_add_to_savings_goal_insufficient_funds(mock_db):
    # ARRANGE: Wallet balance: $10.00 (less than the $25.00 requested)
    wallets_table.put_item(Item={'wallet_id': 'w_123', 'balance': Decimal('10.00')})
    
    # ACT: Attempt to move $25.00
    response = add_to_savings_goal(event, {})
    
    # ASSERT: 
    assert response['statusCode'] == 400
    # Balance must remain unchanged
    assert wallets_table.get_item(Key={'wallet_id': 'w_123'})['Item']['balance'] == Decimal('10.00')

```
**B. Event-Driven Payment Logic** (`tests/test_process_payment_request.py`)
This test validates the Lambda's ability to handle different event types (`PAYMENT_REQUESTED` vs `LOAN_REPAYMENT_REQUESTED`) and correctly debit the wallet.
```
# Mocks: DynamoDB, SNS

def test_payment_success(mock_aws_clients, mock_sns_event):
    # ARRANGE: Wallet balance: $100.00. Event requests $40.00 payment.
    dynamodb, sns = mock_aws_clients
    wallets_table = dynamodb.Table('test-wallets')
    wallets_table.put_item(Item={'wallet_id': 'w_123', 'balance': Decimal('100.00')})
    event = mock_sns_event('PAYMENT_REQUESTED', {'wallet_id': 'w_123', 'amount': Decimal('40.00'), ...})

    # ACT: Process the event
    response = process_payment_request(event, {})

    # ASSERT: 
    assert response['statusCode'] == 200
    # Wallet debited successfully
    assert wallets_table.get_item(Key={'wallet_id': 'w_123'})['Item']['balance'] == Decimal('60.00')
    # Transaction is logged
    assert len(dynamodb.Table('test-transaction-logs').scan()['Items']) == 1


def test_payment_insufficient_funds(mock_aws_clients, mock_sns_event):
    # ARRANGE: Wallet balance: $10.00. Event requests $40.00 payment.
    dynamodb, sns = mock_aws_clients
    wallets_table = dynamodb.Table('test-wallets')
    wallets_table.put_item(Item={'wallet_id': 'w_123', 'balance': Decimal('10.00')})
    event = mock_sns_event('PAYMENT_REQUESTED', {'wallet_id': 'w_123', 'amount': Decimal('40.00'), ...})

    # ACT: Process the event (should fail conditional check)
    response = process_payment_request(event, {})

    # ASSERT:
    assert response['statusCode'] == 200 # Lambda runs successfully
    # Wallet balance is NOT debited
    assert wallets_table.get_item(Key={'wallet_id': 'w_123'})['Item']['balance'] == Decimal('10.00')
    # No log is created
    assert len(dynamodb.Table('test-transaction-logs').scan()['Items']) == 0
```

---

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
| `POST`| `/debt-optimiser` | Calculates accelerated debt payoff projections based on minimum payments and weighted average amortization formulas. |

---
