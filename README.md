# 🚀 KalingaSync AI Enterprise

![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![DynamoDB](https://img.shields.io/badge/Amazon%20DynamoDB-4053D6?style=for-the-badge&logo=Amazon%20DynamoDB&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)

**KalingaSync AI Enterprise** is a highly scalable, fully serverless internal operations and workforce management platform. Engineered natively on the AWS ecosystem, this architecture demonstrates enterprise-grade backend design, emphasizing strict cryptographic access control, decoupled microservices, and real-time AI integration.

🔗 **[[Live Production Gateway](https://main.d1kt3atqogdd7q.amplifyapp.com/)]**

---

### 📸 Application Interface

![Employee Workspace](link-to-your-dashboard-screens<img width="1366" height="768" alt="Screenshot (126)" src="https://github.com/user-attachments/assets/c384abce-08ac-4294-b2f8-c8d4af91b70d" />
hot.png)
![Admin Command Center](link-to-your-adm<img width="1366" height="768" alt="Screenshot (123)" src="https://github.com/user-attachments/assets/456ff56f-2ecd-45fc-a36f-c249b829e150" />
in-screenshot.png)

---

## 🏗️ System Architecture

The application utilizes a purely serverless, event-driven architecture to guarantee zero-maintenance scaling, cost-efficient cloud execution, and high availability.

* **Frontend UI:** Responsive HTML, CSS , and Vanilla JS hosted globally via the AWS Amplify CDN .
* **Authentication Engine:** AWS Cognito integrated with custom Python Lambda triggers for dynamic, enterprise-branded email formatting via Amazon SES [Simple Email Service - a cloud-based email sending service designed to help digital marketers and application developers send notification and transactional emails].
* **API Routing Layer:** AWS API Gateway featuring strict CORS [Cross-Origin Resource Sharing - an HTTP-header based mechanism that allows a server to indicate any origins other than its own from which a browser should permit loading resources] origin enforcement.
* **Compute Microservices:** AWS Lambda (Python 3.12) handling stateless, decoupled execution for Admin provisioning, Employee operations, and Auth events.
* **Data Persistence:** Amazon DynamoDB (NoSQL [Not Only SQL - a database mechanism that provides a mechanism for storage and retrieval of data that is modeled in means other than the tabular relations used in relational databases]) managing distributed state across multiple schema tables (`Users`, `DirectMessages`, `Polls`, `UpdateRequests`, and `Announcements`).
* **Object Storage:** Amazon S3 [Simple Storage Service - an object storage service that offers industry-leading scalability, data availability, security, and performance] for secure profile image asset hosting and rapid retrieval.
* **AI Integration:** Groq API leveraging `llama-3.1-8b-instant` for sub-second, context-aware enterprise assistant responses.

---

## 🔐 Security & Compliance Posture

Security is baked deeply into the infrastructure layer, adhering strictly to the Principle of Least Privilege and enterprise cybersecurity standards.

* **RBAC [Role-Based Access Control - a method of restricting network access based on the roles of individual users within an enterprise]:** Enforced using AWS Cognito User Groups and DynamoDB constraints. Users are assigned `Employee` or `System Administrator` roles, which mathematically dictate their JWT [JSON Web Token - a compact, URL-safe means of representing claims to be transferred between two parties, used here for secure authentication] payload claims.
* **Session Integrity:** Client-side token validation combined with API Gateway HTTP 401 interception to definitively prevent session fixation and unauthenticated data leaks.
* **XSS [Cross-Site Scripting - a security vulnerability where attackers inject malicious scripts into web pages viewed by other users] Mitigation:** A custom global sanitization engine dynamically strips malicious payloads before any DOM [Document Object Model - a programming interface for web documents that represents the page so that programs can change the document structure, style, and content] injection occurs on the client side.
* **Infrastructure Secrets:** Zero credentials exist in the client codebase. All cryptographic keys and routing URLs are injected securely into the Lambda execution context via AWS IAM [Identity and Access Management - a web service that helps you securely control access to AWS resources] Environment Variables.
* **Closed-Loop Notifications:** A bespoke SES pipeline intercepts Cognito triggers to dispatch secure OTP [One-Time Password - an automatically generated numeric or alphanumeric string of characters that authenticates a user for a single transaction or login session] codes and real-time profile mutation alerts.

---

## 🚀 Core Microservices & Features

### 1. Identity & Directory Engine
* **Automated Onboarding:** User-driven registration pipeline requiring manual Admin approval via the Command Center interface.
* **Profile Mutability:** Employees can request profile updates (Role, Department). Changes are held in a DynamoDB quarantine state until cryptographically signed off by an Administrator.
* **Asset Management:** S3 integration allows for seamless, secure profile avatar uploads that instantly propagate across the global directory.

### 2. Internal Communications Protocol
* **Encrypted Direct Messaging:** Master-detail inbox UI for secure, employee-to-employee internal communications.
* **Targeted Broadcasts:** Administrators can deploy global "Super Notes" or targeted private alerts utilizing DynamoDB String Sets to natively prevent duplicate read-receipt acknowledgments.
* **Company Polling Engine:** Real-time enterprise voting mechanics utilizing DynamoDB `ConditionExpression` APIs to mathematically prevent double-voting at the database transaction layer.

### 3. KalingaSync AI Assistant
* Context-aware AI persona utilizing Groq's high-speed inference engine for operational queries.
* Client-side memory management algorithm trims the conversational history to a rolling local window, optimizing API latency and token usage while maintaining seamless conversational flow.

---



### 👨‍💻 Architecture & Engineering
**Priyanshu Patra**
*Specializing in Cloud Infrastructure*
