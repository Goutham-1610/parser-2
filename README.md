
# 🧠 Resume Parser & Auth API (FastAPI + MongoDB)

This project is a backend API built with FastAPI and MongoDB to support **automated resume parsing, user authentication**, and **role-based candidate filtering**. It is suitable for recruitment systems across all domains such as IT, healthcare, engineering, finance, etc.

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

- 🔐 Secure user authentication with token-based access
- 📄 Resume parsing and structured data extraction
- 🧠 LLM-based classification support for job roles (optional)
- 📦 Modular, clean, and scalable API architecture
- 🌐 MongoDB integration for candidate database storage
- 📊 Easily extendable for different domains (IT, finance, healthcare, etc.)

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
venv\Scripts\activate     # Windows
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

Access API:
- Base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

---

## 📬 Sample Endpoints

- `POST /auth/register` – Register a recruiter or candidate
- `POST /auth/login` – Authenticate user
- `POST /parser/parse-resume` – Upload and parse resumes (for any domain)

---

## 🌟 Example Use Cases

This API can be integrated into:

- A **job portal** to automate candidate screening  
- An **HR tool** for sorting resumes by role/domain  
- A **university portal** to process student resumes for placement  
- A **staffing agency** to quickly match candidates to job descriptions

---

## 🧑 Author

Developed by **Goutham G**  
📧 Contact: goutham.g1602@gmail.com

---

## 📄 License

MIT License
