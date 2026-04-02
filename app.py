from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
# Database path can be configured via environment variables for deployment
DB_PATH = os.environ.get('DATABASE_URL', 'todos.db')

# Initialize database
def init_db():
    """Initialize the SQLite database with the todos table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    """Fetch all todos from the database and render the index page."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM todos')
    todos = c.fetchall()
    conn.close()
    return render_template('index.html', todos=todos)

@app.route('/add', methods=['POST'])
def add():
    """Add a new task to the database and redirect to the index page."""
    task = request.form['task']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO todos (task) VALUES (?)', (task,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:todo_id>')
def delete(todo_id):
    """Delete a task from the database by its ID and redirect to the index page."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:todo_id>', methods=['POST'])
def edit(todo_id):
    """Update the text of an existing task in the database and redirect to the index page."""
    task = request.form['task']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE todos SET task = ? WHERE id = ?', (task, todo_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
