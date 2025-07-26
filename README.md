
# 🧠 Resume Parser & Auth API (FastAPI + MongoDB)

This project is designed to support a **mechanical engineering recruitment system**, particularly for sectors like **automotive, aerospace, and manufacturing**. It uses FastAPI and MongoDB to provide a backend API that handles:

- **Resume parsing** to extract structured engineering profiles
- **Authentication system** for secure access
- Designed to support automated applicant tracking and filtering for technical job roles

---

## ⚙️ Tech Stack

- **Python 3.11+**
- **FastAPI**
- **MongoDB**
- **Uvicorn**
- **Python-dotenv**
- **Pydantic**

---

## 🚀 Features

- 🔐 User authentication and token-based access
- 📄 Resume parsing and data extraction (ideal for filtering Mechanical Engineers)
- 🧠 LLM prompt-based classification logic (for resume intelligence)
- 📦 Modular API routes and clear folder structure
- 🌐 MongoDB-based candidate database

---

## 🧑‍💻 Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd "parser 2"
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

```env
MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net
DATABASE_NAME=resume_parser
SECRET_KEY=your_secret_key
```

---

## ▶️ Run the API

```bash
uvicorn app.main:app --reload
```

Visit:
- http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs

---

---

## 📬 Sample Endpoints

- `POST /auth/register` – Register a recruiter or candidate
- `POST /auth/login` – Authenticate user
- `POST /parser/parse-resume` – Upload and parse resume for roles like "Mechanical Engineer – Automotive Systems"

---

## 🌟 Example Use Case

Veltrix Automotive receives hundreds of resumes for the **Mechanical Engineer – Automotive Systems** role. This API helps them:

- Parse resumes to extract skills like **SolidWorks**, **FEA**, **GD&T**
- Classify experience levels and flag suitable candidates
- Authenticate recruiters to securely manage submissions

---

## 🧑 Author

Developed by **Goutham G**  
📧 Contact:goutham.g1602@gmail.com

---

## 📄 License

MIT License
