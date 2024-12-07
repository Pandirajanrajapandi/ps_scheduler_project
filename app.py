from flask import Flask, render_template, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
import csv
import os
import math
from datetime import datetime

app = Flask(__name__)
app.secret_key = '9f9d51bc70ef21ca5c14f307980a29d8'

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# Generate hashed password
hashed_password = generate_password_hash("Pandirajan1993!", method="pbkdf2:sha256")

# User database
users = {
    "1": User("1", "pandirajan", hashed_password)  # Placeholder user
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Logic for user registration (if required)
    return render_template('register.html')


@app.before_request
def before_request():
    g.current_user = current_user

# Function to load tasks for the current user
def load_tasks():
    try:
        with open('tasks.json', 'r') as file:
            tasks = json.load(file)
    except FileNotFoundError:
        tasks = []
    return tasks

# Function to save tasks to tasks.json
def save_tasks(tasks):
    with open('tasks.json', 'w') as file:
        json.dump(tasks, file, indent=4)

# Update the task status
def update_task_status(tasks):
    current_date = datetime.now().strftime('%Y-%m-%d')
    for task in tasks:
        task_date = task['date']
        if task_date < current_date and task['status'] == 'pending':
            task['status'] = 'overdue'
        elif task_date > current_date:
            task['status'] = 'pending'
    save_tasks(tasks)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        for user in users.values():
            if user.username == username and check_password_hash(user.password_hash, password):
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))
        flash('Invalid username or password!', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
@app.route('/')
@login_required
def index():
    # Load tasks
    tasks = load_tasks()
    update_task_status(tasks)  # Ensure statuses are updated

    # Pagination parameters
    page = request.args.get('page', 1, type=int)  # Get current page number from query params
    per_page = 5  # Number of tasks to display per page
    total_tasks = len(tasks)  # Total number of tasks
    total_pages = math.ceil(total_tasks / per_page)  # Total pages required

    # Slice tasks for the current page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    tasks_on_page = tasks[start_index:end_index]

    # Render template with pagination info
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template(
        'index.html',
        tasks=tasks_on_page,
        current_date=current_date,
        page=page,
        total_pages=total_pages
    )

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        name = request.form.get('name')
        date = request.form.get('date')
        start_time = request.form.get('start_time')
        deadline = request.form.get('deadline')
        priority = request.form.get('priority')

        if not name:
            flash('Task name is required!', 'danger')
            return redirect(url_for('add_task'))

        if not date:
            date = datetime.today().strftime('%Y-%m-%d')

        if datetime.strptime(date, '%Y-%m-%d').date() < datetime.today().date():
            flash("Don't enter past dates!", 'danger')
            return redirect(url_for('add_task'))

        new_task = {
            'name': name,
            'date': date,
            'start_time': start_time,
            'deadline': deadline,
            'priority': priority,
            'status': 'pending'
        }

        tasks = load_tasks()
        tasks.append(new_task)
        save_tasks(tasks)
        flash('Task added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_task.html')


@app.route('/mark_as_completed/<int:task_id>', methods=['POST'])
@login_required
def mark_as_completed(task_id):
    tasks = load_tasks()
    current_date = datetime.now().strftime('%Y-%m-%d')

    if 0 <= task_id < len(tasks):
        task = tasks[task_id]
        if task['date'] == current_date and task['status'] == 'pending':
            task['status'] = 'completed'
            save_tasks(tasks)
            flash(f"Task '{task['name']}' marked as completed!", 'success')
        else:
            flash("Task cannot be marked as completed due to invalid conditions.", 'danger')

    return redirect(url_for('index'))


@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    tasks = load_tasks()
    if 0 <= task_id < len(tasks):
        task = tasks.pop(task_id)
        save_tasks(tasks)
        flash(f"Task '{task['name']}' deleted successfully!", 'success')

    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    tasks = load_tasks()
    total_tasks = len(tasks)

    today = datetime.today().date()
    relevant_tasks = [task for task in tasks if datetime.strptime(task['date'], '%Y-%m-%d').date() <= today]

    completed_tasks = sum(1 for task in relevant_tasks if task['status'] == 'completed')
    overdue_tasks = sum(1 for task in relevant_tasks if task['status'] == 'overdue')

    completion_percentage = (completed_tasks / (completed_tasks + overdue_tasks)) * 100 if (completed_tasks + overdue_tasks) > 0 else 0

    return render_template(
        'dashboard.html',
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        completion_percentage=round(completion_percentage, 2)
    )


@app.route('/export_tasks', methods=['GET'])
@login_required
def export_tasks():
    tasks = load_tasks()
    if not tasks:
        flash('No tasks available to export.', 'warning')
        return redirect(url_for('index'))

    with open('ps_scheduler.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Name', 'Date', 'Start Time', 'Deadline', 'Priority', 'Status'])
        for task in tasks:
            writer.writerow([task['name'], task['date'], task['start_time'], task['deadline'], task['priority'], task['status']])
    
    flash('Tasks successfully exported to ps_scheduler.csv.', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
