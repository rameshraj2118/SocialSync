from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "Qwe123!@#"  # Change this to something secure!

# --- Database Setup ---
def get_db():
    return sqlite3.connect("users.db")
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            due_date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

# --- Routes ---
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password FROM users WHERE email=?",
            (email,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session.clear()  # important safety
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['handle'] = user[2].split('@')[0]  # ✅ THIS IS THE KEY LINE

            print("SESSION DEBUG:", dict(session))  # DEBUG
            return redirect(url_for('home'))

        flash("Invalid email or password", "danger")

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                           (username, email, hashed_password))
            conn.commit()
            flash("Signup successful! You can now log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists. Try logging in.", "danger")
        finally:
            conn.close()

    return render_template('signup.html')


@app.route('/home')
def home():
    if 'user_id' not in session:
        flash("Please log in to access home.", "warning")
        return redirect(url_for('login'))
    return render_template('home.html', username=session['username'])

# ================= TASK API =================

# GET user tasks
@app.route("/api/tasks")
def get_tasks():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, completed, due_date FROM tasks WHERE user_id=?",
        (session["user_id"],)
    )

    tasks = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "id": t[0],
            "title": t[1],
            "completed": bool(t[2]),
            "due_date": t[3]
        }
        for t in tasks
    ])


# ADD task (task list OR calendar)
@app.route("/api/tasks", methods=["POST"])
def add_task():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    title = data.get("title")
    due_date = data.get("due_date")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks (user_id, title, due_date) VALUES (?, ?, ?)",
        (session["user_id"], title, due_date)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Task added"})


# UPDATE checkbox status
@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    completed = 1 if data.get("completed") else 0

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tasks SET completed=? WHERE id=? AND user_id=?",
        (completed, task_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Task updated"})


# DELETE task (optional)
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id=? AND user_id=?",
        (task_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Task deleted"})



@app.route('/youtube')
def youtube():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('youtube.html')


@app.route('/facebook')
def facebook():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('facebook.html')


@app.route('/twitter')
def twitter():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('twitter.html')


@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('inbox.html')


@app.route('/post')
def post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('post.html')


@app.route('/schedule')
def schedule():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('schedule.html')


@app.route('/ads')
def ads():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('ads.html')


@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            flash("Password reset link sent to your email (feature under development).", "success")
        else:
            flash("No account found with that email.", "danger")

        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
