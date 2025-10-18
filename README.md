![header](https://capsule-render.vercel.app/api?type=waving&height=200&color=gradient&text=Serverless%20Fintech%20Ecosystem&fontSize=35&strokeWidth=0&desc=An%20Event-Driven%20Microservice%20Portfolio%20on%20AWS&descAlign=50&descAlignY=62&reversal=false&fontAlign=50&fontAlignY=40)

## 📖 About This Project

This is a portfolio project demonstrating a complete, serverless, and event-driven fintech ecosystem built on Amazon Web Services (AWS).

This is not a single monolith. It is a collection of **decoupled microservices** that communicate asynchronously using **SNS (Simple Notification Service)**. This architecture is designed to be highly scalable, resilient, and maintainable, mirroring modern cloud-native design patterns.

All infrastructure is provisioned and managed using **Terraform**, demonstrating Infrastructure as Code (IaC) best practices.

## ✅ Project Status: In Progress

| Service | Status | Description |
| :--- | :---: | :--- |
| **Digital Wallet API** | ✅ | Core ledger for all services. Manages user balances. |
| **Micro-Loan System** | ✅ | Manages loan applications, approvals, and rejections. |
| **Payment Simulator** | ✅ | Asynchronous, event-driven payment processing saga. |
| **Savings Goal Visualiser** | 🔲 | (Next Up) React frontend for user savings goals. |
| **Debt Repayment Optimiser** | 🔲 | (Future) Algorithmic loan repayment strategies. |

---

## 🏗️ Architecture Overview

The system's core design principle is **event-driven choreography**. Services do not call each other directly. Instead, they publish events to SNS topics, and other services subscribe to the events they care about.

This creates a decoupled system where, for example, the `micro_loan` service can approve a loan without ever knowing *how* the `digital_wallet` service funds it.

### Key Workflows:

**1. Loan Approval Saga:**
1.  **Client** `POST`s to `/loan/{loan_id}/approve`.
2.  **Micro-Loan Service** (Lambda) updates the loan status to "APPROVED".
3.  **Micro-Loan Service** publishes a `LOAN_APPROVED` event to the `loan_events` SNS topic.
4.  **Digital Wallet Service** (Lambda, subscribed to the topic) receives the event, parses the details, and atomically credits the user's wallet.

**2. Payment Processing Saga (Choreography):**
1.  **Client** `POST`s to `/payment`.
2.  **Payment Service** (`request_payment` Lambda) creates a "PENDING" transaction in DynamoDB.
3.  **Payment Service** publishes a `PAYMENT_REQUESTED` event to the `payment_events` SNS topic (with a `MessageAttribute`).
4.  **Digital Wallet Service** (`process_payment_request` Lambda) subscribes to the topic *only for* the `PAYMENT_REQUESTED` event (using an SNS Filter Policy).
5.  **Digital Wallet Service** attempts to debit the wallet:
    * **On Success:** It publishes a `PAYMENT_SUCCESSFUL` event back to the *same* `payment_events` topic.
    * **On Failure (e.g., insufficient funds):** It publishes a `PAYMENT_FAILED` event.
6.  **Payment Service** (`update_transaction_status` Lambda) subscribes to the topic *only for* the `PAYMENT_SUCCESSFUL` or `PAYMENT_FAILED` events (using another SNS Filter Policy).
7.  **Payment Service** receives the result and updates the transaction status from "PENDING" to "SUCCESSFUL" or "FAILED".

---

## 🛠️ Tech Stack

* **Backend:** **Python**
* **Infrastructure as Code:** **Terraform**
* **Serverless Compute:** **AWS Lambda**
* **API:** **AWS API Gateway**
* **Database:** **AWS DynamoDB** (including Global Secondary Indexes - GSIs)
* **Event-Driven Messaging:** **AWS SNS** (with Subscription Filter Policies)
* **Frontend (Future):** **React**, AWS S3, AWS CloudFront

---

## 📂 Project Structure

This repository is structured as a monorepo to manage all microservices and their infrastructure in one place.

```
Serverless-Fintech-Ecosystem/
├── terraform/
│   ├── main.tf             # Root file (shared resources like API Gateway, SNS Topics)
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── digital_wallet/     # IaC for the Wallet service
│       ├── micro_loan/         # IaC for the Loan service
│       └── payment_processor/  # IaC for the Payment service
│
└── src/
    ├── create_wallet/          # Python code for a single Lambda function
    ├── get_wallet/
    ├── apply_for_loan/
    ├── process_loan_approval/  # The SNS subscriber Lambda
    ├── request_payment/
    ├── process_payment_request/
    ├── update_transaction_status/
    └── ... (etc.)
```

---

## 🚀 How to Deploy

### Prerequisites
1.  An [AWS Account](https://aws.amazon.com/)
2.  [AWS CLI](https://aws.amazon.com/cli/) configured (run `aws configure`)
3.  [Terraform](https://www.terraform.io/downloads.html) installed

### Deployment Steps
1.  Clone this repository:
    ```bash
    git clone [https://github.com/KayleeMcLaren/Serverless-Fintech-Ecosystem.git](https://github.com/KayleeMcLaren/Serverless-Fintech-Ecosystem.git)
    cd Serverless-Fintech-Ecosystem
    ```

2.  Navigate to the Terraform directory:
    ```bash
    cd terraform
    ```

3.  Initialize Terraform (this will download the AWS provider and modules):
    ```bash
    terraform init
    ```

4.  Apply the configuration (this will build all the resources on AWS):
    ```bash
    terraform apply
    ```

5.  Type `yes` to approve the plan. Terraform will build everything and output the API Gateway URL.

---

## Endpoints

**Base URL:** (This will be in your `terraform apply` output)

### Digital Wallet Service
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/wallet` | Creates a new wallet with a $0.00 balance. |
| `GET` | `/wallet/{wallet_id}` | Gets the balance and details for a wallet. |
| `POST` | `/wallet/{wallet_id}/credit` | Adds funds to a wallet. |
| `POST` | `/wallet/{wallet_id}/debit` | Removes funds from a wallet (fails on overdraft). |

### Micro-Loan Service
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/loan` | Applies for a new loan (status: "PENDING"). |
| `GET` | `/loan/{loan_id}` | Gets the details and status of a single loan. |
| `GET` | `/loan/by-wallet/{wallet_id}` | Gets all loans associated with a wallet (uses GSI). |
| `POST` | `/loan/{loan_id}/approve` | **Triggers Loan Approval Saga.** |
| `POST` | `/loan/{loan_id}/reject` | Rejects a "PENDING" loan. |

### Payment Processing Service
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/payment` | **Triggers Payment Processing Saga.** (Returns `202 Accepted`) |
| `GET` | `/payment/{transaction_id}` | Checks the status of a payment ("PENDING", "SUCCESSFUL", "FAILED"). |