# ⚡ Agentic CI/CD Algorithmic Reviewer

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Microframework-lightgrey)
![Gemini API](https://img.shields.io/badge/AI-Gemini_2.5_Flash-orange)
![GitHub Webhooks](https://img.shields.io/badge/CI%2FCD-GitHub_Webhooks-black)

## 📌 Overview
The **Agentic CI/CD Algorithmic Reviewer** is an event-driven microservice designed to integrate directly into GitHub repository workflows. Unlike standard static analysis tools (like SonarQube or ESLint) that check for syntax and basic bugs, this agent autonomously evaluates Pull Requests specifically for **Data Structures and Algorithms (DSA) inefficiencies**. 

When a developer opens a PR, the system analyzes the Git diff and suggests optimal architectural refactors (e.g., transforming an $O(n^2)$ nested loop into an $O(n)$ hash map lookup), directly injecting structured markdown feedback and performance metrics into the PR comments.

## 🏗️ System Architecture
1. **Event Trigger:** GitHub fires a secure Webhook payload (`pull_request` event) when a PR is opened or synchronized.
2. **Security Layer:** The Flask backend intercepts the payload and verifies the `X-Hub-Signature-256` HMAC hash to prevent unauthorized spoofing.
3. **Data Extraction:** The system queries the GitHub REST API to extract the exact code diff.
4. **Agentic Inference:** The diff is processed via prompt-chaining using the Google Gemini 2.5 Flash API, enforcing strict JSON schema outputs.
5. **Automated Feedback:** The agent calculates cyclomatic complexity and estimated operations saved, posting a formatted markdown table directly back to the GitHub PR.

## ✨ Core Features
* **Algorithmic Optimization:** Identifies sub-optimal Big-O time and space complexities.
* **Idempotent Webhook Processing:** Safely handles duplicate GitHub delivery events.
* **Cryptographic Security:** Payload verification using SHA-256 HMAC signatures.
* **Custom Telemetry:** Tracks agent execution latency and calculates real-world computational savings.

  <img width="1129" height="820" alt="Screenshot 2026-03-01 134116" src="https://github.com/user-attachments/assets/8baef79f-d0ac-43ad-8f77-62598df28558" />


## 🚀 Getting Started

### Prerequisites
* Python 3.9+
* A GitHub Personal Access Token (PAT) with `repo` permissions.
* A Google Gemini API Key.
* [ngrok](https://ngrok.com/) (for local webhook testing).

### Installation
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Rishabh-raj-kumar/ci_cd_pipeline.git](https://github.com/Rishabh-raj-kumar/ci_cd_pipeline.git)
   cd ci_cd_pipeline
