import os
import sys

# Immediate version check to see what environment we are in
print(f"DEBUG: STARTUP INITIATED")
print(f"DEBUG: PYTHON VERSION: {sys.version}")
sys.stdout.flush()

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Force flush prints for Render diagnostics
def log(msg):
    print(msg)
    sys.stdout.flush()

# Configure Database
# Render uses postgres://, but SQLAlchemy 1.4+ requires postgresql://
db_url = os.environ.get('DATABASE_URL', 'sqlite:///todos.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable engine-level logging for Render debugging if needed
# app.config['SQLALCHEMY_ECHO'] = True 

db = SQLAlchemy(app)

# Todo Model
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Todo {self.task}>'

# Initialize database
def init_db():
    log(f"--- DATABASE INITIALIZATION ---")
    log(f"Using URI: {db_url.split('@')[-1] if '@' in db_url else db_url}") # Log sanitized URL
    try:
        with app.app_context():
            db.create_all()
        log("Status: SUCCESS")
    except Exception as e:
        log(f"Status: FAILED")
        log(f"Error during db.create_all(): {e}")
        # If postgres fails, we should not hide it on Render
        if "postgresql" in db_url or "postgres" in db_url:
            log("Action: Connection failed. Check DATABASE_URL and Postgres availability.")
        raise e
    log(f"-------------------------------")

try:
    init_db()
except Exception as e:
    log(f"CRITICAL STARTUP ERROR: {e}")
    # Don't raise here if we want to allow gunicorn to start but it's probably better to die
    raise e

@app.route('/')
def index():
    """Fetch all todos from the database and render the index page."""
    todos = Todo.query.all()
    # Converting to tuples to maintain compatibility with existing template if needed,
    # though it's better to update the template to use object attributes.
    return render_template('index.html', todos=todos)

@app.route('/add', methods=['POST'])
def add():
    """Add a new task to the database and redirect to the index page."""
    task_content = request.form['task']
    new_todo = Todo(task=task_content)
    try:
        db.session.add(new_todo)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error adding task: {e}")
        return "There was an issue adding your task"

@app.route('/delete/<int:todo_id>')
def delete(todo_id):
    """Delete a task from the database by its ID and redirect to the index page."""
    todo_to_delete = Todo.query.get_or_404(todo_id)
    try:
        db.session.delete(todo_to_delete)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error deleting task: {e}")
        return "There was a problem deleting that task"

@app.route('/edit/<int:todo_id>', methods=['POST'])
def edit(todo_id):
    """Update the text of an existing task in the database and redirect to the index page."""
    todo = Todo.query.get_or_404(todo_id)
    todo.task = request.form['task']
    try:
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error editing task: {e}")
        return "There was an issue updating your task"

if __name__ == '__main__':
    app.run(debug=True)
