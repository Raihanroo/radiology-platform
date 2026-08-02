AI-Assisted Radiology Platform

![alt text](image.png)


This is a full-stack AI-driven radiology platform that provides brain tumor detection (Classification and Segmentation), radiologist review, doctor consultation, and LLM-powered clinical assistant features. The entire system operates on a secure 8-step workflow, bridging the gap between medical imaging and artificial intelligence.

Progress on 11 Specific Backend Tasks

AI Analysis Module (Completed)Processing MRI images for tumor detection (Classification), marking (Segmentation), and extracting confidence scores. Integrated .h5 (TensorFlow) and .pth (PyTorch) models via the inference.py file. Includes automatic .tif to .png conversion for web compatibility.

LLM Assistant Module (Completed)Generating easy-to-understand summaries, report drafts, and patient Q&A text based on AI results. Integrated 7 LLM features using the Google Gemini API in the llm_service.py file.

Role-Based Access Control (Completed)Configured separate permissions and security for Patients, Radiologists, Doctors, and Admins. Custom permission classes are created in accounts/permissions.py.

Medical Image Storage (Completed)Securely storing heavy MRI images. Currently saving locally in the media/scans/ folder via Django, with a structure ready for cloud storage (AWS S3).

Database Management (Completed)Saving patient history, medical records, and reports in the database. Using SQLite for development, with all data mapped relationally. PostgreSQL ready for production.

Algorithm Processing (Completed)Processing image and text data on the server. Successfully implemented server-side image processing (OpenCV, Pillow) and text processing for AI inference.

Notification Engine (Future Scope)Alerting relevant users (e.g., Radiologist or Doctor) based on workflow steps. Real-time push notifications are not yet integrated, but dedicated Queue systems are active for users to see pending tasks.
Report Automation (Completed)Merging final reports into the database combining AI, Radiologist, and Doctor opinions. Automated logic is implemented in GenerateReportView.

Encrypted Data Storage (Production Goal)Data encryption (HIPAA/GDPR compliance). Authentication and permission-level security are 100% ensured. Field-level encryption will be handled during the deployment phase.

Audit Logs (Completed)Tracking logs of who viewed or changed data and when. The AuditLog model is created, and logs are saved automatically during report approvals. Accessible via the Admin Dashboard.

API Development (Completed)Built secure REST APIs for data exchange between the frontend and backend servers. Utilized Django REST Framework (DRF) and JWT (JSON Web Token) authentication.


Frontend Features

Role-based Dashboards for Admin, Patient, Radiologist, and Doctor.
patient Profile 
1.[alt text](image-1.png) 2.![alt text](image-2.png)

Radiologist profile: 
1. ![alt text](image-3.png) 2. ![alt text](image-4.png)

Doctor profile:
1. ![alt text](image-5.png) 2. ![alt text](image-6.png)

Admin Profile:
1.![alt text](image-7.png) 2 ![alt text](image-8.png) 3.![alt text](image-9.png) 4.![alt text](image-10.png)
5.![alt text](image-11.png)

AI Segmentation Visualization in review and report modals.

AI Draft Generation button for doctors to auto-generate report summaries.
PDF Report Download with dynamic Watermark and professional formatting.
Patient AI Chatbot for medical Q&A based on their specific approved report.
User Management system for Admins to activate/deactivate users.

Tech Stack

Backend: Django, Django REST Framework, SimpleJWT
Frontend: React.js, Vite, Tailwind CSS, Axios, React Router
AI/ML: TensorFlow, PyTorch, OpenCV, Pillow
LLM: Google Gemini API (OpenAI-compatible integration)
Database: SQLite (Development), PostgreSQL (Production Ready)
Installation and Setup


Installation and Setup

Clone the repository:
git clone <your-repo-link>cd radiology-platform
Backend Setup (Django):
bash

python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows

pip install -r requirements.txt

# Create a .env file and add your SECRET_KEY, GEMINI_API_KEY, and DB credentials

python manage.py migrate
python manage.py runserver
Frontend Setup (React):
bash

cd frontend
npm install
npm run dev
Access the application:
Open your browser and navigate to http://localhost:5173/ for the frontend. The backend API will be running at http://127.0.0.1:8000/.
text

