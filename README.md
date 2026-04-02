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

## 🏁 Getting Started

### Prerequisites
- Python 3.x
- Flask

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd my-agy-projects
   ```

2. **Set up a virtual environment (optional but recommended)**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # .venv\Scripts\activate  # On Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install Flask
   ```

### Running the Application

- **To run the To-Do Web App**:
  ```bash
  python app.py
  ```
  Then visit `http://127.0.0.1:5000` in your browser.

- **To run the Algorithm Showcase**:
  ```bash
  python main.py
  ```

- **To run the Unit Tests**:
  ```bash
  python test_algorithms.py
  ```

---

## 📝 Rules & Conventions
- All code follows the **PEP 8** style guide.
- Proprietary notice included in core modules.
- Entry point `main.py` uses modular examples to maintain clean code architecture.

---

## 📄 License
© 2026 YOUR_COMPANY_NAME LLC. All rights reserved.
Proprietary and confidential.
