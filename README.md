# Google Antigravity - My AGY Projects

A collection of Python scripts and applications focusing on algorithm implementation, data processing, and simple web application development. This project was developed as part of **Google Antigravity**.

For more information, refer to the [Google Antigravity Codelab](https://codelabs.developers.google.com/getting-started-google-antigravity#10).

---

## 🛠️ Environment & Developer Tools

### 🌐 Environment
- **Antigravity Version**: 1.16.5

### 🏗️ Workspace Configuration
This repository leverages integrated developer tools for consistency and automation:

#### 📜 Workspace Rules
- **Code Generation Guide**: Defines standardized patterns for adding new features without cluttering the main entry point.
- **Code Style Guide**: Mandates PEP 8 compliance and comprehensive documentation through comments.

#### 🔄 Workflows
- **Generate Unit Tests**: A pre-defined automated flow for generating consistent unit tests (`test_*.py`) for all new modules and methods.

#### 🧰 Skills
- **License Header Adder**: Automatically prepends standard corporate license headers to new source files, adapting comment syntax based on the file type.

---

## 🚀 Key Features

### 1. Algorithms & Data Structures
- **Bubble Sort**: An in-place sorting algorithm implemented in `algorithms.py`.
- **Binary Search**: An efficient search algorithm for sorted lists implemented in `algorithms.py`.
- **Unit Tests**: Comprehensive tests for algorithms located in `test_algorithms.py`.

### 2. Flask To-Do Application
- A fully functional web application built with **Flask** for managing tasks.
- **SQLite Integration**: Uses `todos.db` for persistent task storage.
- **CRUD Operations**: Support for adding, editing, and deleting tasks.
- **Dynamic UI**: Uses Jinja2 templates and external CSS for a clean user interface.

### 3. Data Processing Utility
- A modular `data_processor.py` for utility functions like greeting and data initialization.

### 4. Entry Point
- Use `main.py` to quickly showcase algorithm and data processing capabilities.

---

## 🛠️ Project Structure

```text
.
├── algorithms.py          # Algorithm implementations (Sort, Search)
├── app.py                 # Flask web application entry point
├── data_processor.py      # Utility functions for data processing
├── main.py                # Main showcase entry point
├── test_algorithms.py     # Unit tests for core algorithms
├── templates/             # HTML templates for the Flask app
├── static/                # Static assets (CSS, JS)
└── todos.db               # SQLite database for task storage
```

---

## 🚀 Deployment (GitHub & Render)

This project is optimized for deployment on **Render** (as a Web Service) and works seamlessly with **GitHub**.

### 🛠️ Preparing for Render

Render connects directly to your GitHub repository and builds the app automatically.

1. **GitHub Connection**:
   - Push this repository to your GitHub account.
   - Connect your GitHub account to [Render](https://render.com/).

2. **Web Service Configuration**:
   - Select **New +** > **Web Service**.
   - Input your repository URL.
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (This uses the production-grade Gunicorn server).

3. **Database (Persistence)**:
   - By default, SQLite creates `todos.db` in the service's ephemeral storage. For persistence, you should mount a **Disk** in Render or connect to an external PostgreSQL database by setting the `DATABASE_URL` environment variable.

### 📦 Key Files for GitHub/Deployment
- `requirements.txt`: Lists all Python dependencies (`Flask`, `gunicorn`, etc.).
- `.gitignore`: Ensures that local virtual environments and temporary database files aren't tracked.

---

## 🏁 Getting Started

### Prerequisites
- Python 3.x
- Flask (for local development)

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd my-agy-projects
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # .venv\Scripts\activate  # On Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running Locally

- **Development Server**:
  ```bash
  python app.py
  ```
  Then visit `http://127.0.0.1:5000`.

- **Production Simulation (Gunicorn)**:
  ```bash
  gunicorn app:app
  ```

---

## 📝 Rules & Conventions
- All code follows **PEP 8**.
- Environment-aware configurations (e.g., `DB_PATH`) are implemented in `app.py` for cloud flexibility.

---

## 📄 License
© 2026 YOUR_COMPANY_NAME LLC. All rights reserved.
Proprietary and confidential.
