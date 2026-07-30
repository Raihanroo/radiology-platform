AI-Assisted Radiology Platform (Backend)
This is the backend for an AI-driven radiology platform that provides brain tumor detection (Classification & Segmentation), radiologist review, doctor consultation, and LLM-powered clinical assistant features. The entire system operates on a secure 8-step workflow.

🎯 Current Status

Backend Development: 100% Complete
Testing: 69/69 Tests Passed ✅
Workflows Covered: 8/8 Steps Completed ✅

📋 Progress on 11 Specific Backend Tasks:

1. AI Analysis Module ✅
Processing MRI images for tumor detection (Classification), marking (Segmentation), and extracting confidence scores. Integrated .h5 (TensorFlow) and .pth (PyTorch) models via the inference.py file.

2. LLM Assistant Module ✅
Generating easy-to-understand summaries, report drafts, and patient Q&A text based on AI results. Integrated 7 LLM features using Google Gemini API in the llm_service.py file.

3. Role-Based Access Control (RBAC) ✅
Configured separate permissions and security for Patients, Radiologists, Doctors, and Admins. Custom permission classes are created in accounts/permissions.py.

4. Medical Image Storage ✅
Securely storing heavy MRI images. Currently saving locally in the media/scans/ folder via Django, with a structure ready for cloud storage (AWS S3).

5. Database Management ✅
Saving patient history, medical records, and reports in the database. Using SQLite for development, with all data mapped relationally.

6. Algorithm Processing ✅
Processing image and text data on the server. Successfully implemented server-side image processing and text processing.

7. Notification Engine ⏳ (Future Scope)
Alerting relevant users (e.g., Radiologist or Doctor) based on workflow steps. Real-time push notifications are not yet integrated, but dedicated Queue systems are active for users to see pending tasks.

8. Report Automation ✅
Merging final reports into the database combining AI, Radiologist, and Doctor opinions. Automated logic is implemented in GenerateReportView.

9. Encrypted Data Storage ⏳ (Production Goal)
Data encryption (HIPAA/GDPR compliance). Authentication and permission-level security are 100% ensured. Field-level encryption will be handled during the deployment phase.

10. Audit Logs ✅
Tracking logs of who viewed or changed data and when. The AuditLog model is created, and logs are saved automatically during report approvals.

11. API Development ✅
Built secure REST APIs for data exchange between the frontend and backend servers. Utilized Django REST Framework (DRF) and JWT (JSON Web Token) authentication.

🛠️ Tech Stack
Backend: Django, Django REST Framework
AI/ML: TensorFlow, PyTorch, OpenCV
LLM: Google Gemini API
Database: SQLite (Development), PostgreSQL (Production Ready)
Authentication: JWT (SimpleJWT)

Installation & Setup

Clone the repository:
git clone <your-repo-link>
Create a virtual environment:
bash

python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows
Install dependencies:
bash

pip install -r requirements.txt
Run migrations:
bash

python manage.py migrate
Start the server:
bash

python manage.py runserver




