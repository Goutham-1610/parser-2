
# 🧠 Resume Parser & Auth API (FastAPI + MongoDB)

This is a FastAPI-based backend service designed to:
- **Parse and extract information from resumes**
- **Provide authentication and user management APIs**
- Use **MongoDB** as the primary database
- Support **modular routing** for scalability

---

## ⚙️ Tech Stack

- **Python 3.11+**
- **FastAPI**
- **MongoDB**
- **Pydantic**
- **Uvicorn** (for ASGI server)
- **Python-dotenv** (for environment variables)

---

## 🚀 Features

- 🔐 **User Authentication** (via JWT or API key)
- 📄 **Resume Parsing** – Uses NLP to extract structured information
- 🧱 Modular design with routers, services, and database layers
- 🔌 MongoDB integration
- 📦 Dependency injection and clean folder structure

---

## 🧑‍💻 Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd "parser 2"
```

### 2. Create Virtual Environment & Activate

```bash
python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

Create a `.env` file in the root folder with the following variables:

```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net
DATABASE_NAME=your_database_name
SECRET_KEY=your_secret_key
```

Replace the values accordingly.

---

## ▶️ Run the API

```bash
uvicorn app.main:app --reload
```

- The server will start at: `http://127.0.0.1:8000`
- Swagger UI (API Docs): `http://127.0.0.1:8000/docs`

---

## 📬 Example Endpoints

> 🧪 Check Swagger docs at `/docs` after running

- `POST /auth/login` – Login with credentials
- `POST /auth/register` – Register a new user
- `POST /parser/parse-resume` – Upload and parse a resume file

---

## 🧪 Testing

To run tests (if implemented):

```bash
pytest
```

---

## 🛠️ To Do (Optional)

- Add error handling and logging
- Add unit tests for endpoints
- Dockerize the application
- Integrate with LLM for smarter resume parsing

---

## 🧑 Author

Developed by **Goutham G**  
📧 Contact: goutham.g1602@gmail.com

---

## 📄 License

This project is licensed under the MIT License.
