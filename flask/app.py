from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import random

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            appearance TEXT DEFAULT 'Dark',
            language TEXT DEFAULT 'English',
            font_size TEXT DEFAULT 'Medium',
            email_notifications INTEGER DEFAULT 1,
            push_notifications INTEGER DEFAULT 0,
            inapp_notifications INTEGER DEFAULT 1,
            profile_visibility TEXT DEFAULT 'Friends Only',
            direct_messages TEXT DEFAULT 'Everyone',
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


import random

@app.route("/api/instagram/analytics")
def dynamic_mock_analytics():
    def generate_series(start):
        values = [start]
        for _ in range(6):
            values.append(values[-1] + random.randint(-50, 150))
        return values

    followers = generate_series(2500)
    impressions = generate_series(2000)
    likes = generate_series(800)

    analytics = {
        "followers": followers[-1],
        "followers_change": followers[-1] - followers[-2],
        "impressions": impressions[-1],
        "impressions_change": impressions[-1] - impressions[-2],
        "engagement_rate": round((likes[-1] / impressions[-1]) * 100, 2),
        "likes": likes[-1],
        "followers_graph": followers,
        "impressions_graph": impressions,
        "likes_graph": likes,
        "labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    }

    return jsonify(analytics)
import random
from flask import jsonify

@app.route("/api/analytics")
def analytics():
    followers = random.randint(2500, 4000)
    impressions = random.randint(2000, 5000)
    engagement = random.randint(20, 60)
    likes = random.randint(500, 2000)

    return jsonify({
        "followers": followers,
        "followers_change": random.randint(-100, 200),

        "impressions": impressions,
        "impressions_change": random.randint(-500, 500),

        "engagement_rate": engagement,
        "engagement_change": random.randint(-10, 15),

        "likes": likes,
        "likes_change": random.randint(-50, 100)
    })
import random
from flask import jsonify

@app.route("/api/youtube")
def youtube_analytics():

    def generate_series(start):
        values = [start]
        for _ in range(6):
            values.append(values[-1] + random.randint(-20, 200))
        return values

    subscribers = generate_series(2800)
    views = generate_series(5000)
    likes = generate_series(800)

    return jsonify({
        "subscribers": subscribers[-1],
        "subscribers_change": subscribers[-1] - subscribers[-2],

        "views": views[-1],
        "views_change": views[-1] - views[-2],

        "engagement_rate": random.randint(20, 50),
        "engagement_change": random.randint(-5, 10),

        "likes": likes[-1],
        "likes_change": likes[-1] - likes[-2],

        "subscribers_graph": subscribers,
        "views_graph": views,
        "labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    })

@app.route("/api/twitter")
def twitter_analytics():

    def generate_series(start):
        values = [start]
        for _ in range(6):
            values.append(values[-1] + random.randint(5, 120))
        return values

    followers = generate_series(1800)
    impressions = generate_series(9000)

    return jsonify({
        "followers": followers[-1],
        "followers_change": followers[-1] - followers[-2],

        "impressions": impressions[-1],
        "impressions_change": impressions[-1] - impressions[-2],

        "engagement_rate": random.randint(10, 40),
        "engagement_change": random.randint(-5, 12),

        "likes": random.randint(500, 2500),
        "likes_change": random.randint(-50, 120),

        "followers_graph": followers,
        "impressions_graph": impressions,

        "labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    })

@app.route("/api/facebook")
def facebook_analytics():

    def generate_series(start):
        values = [start]
        for _ in range(6):
            values.append(values[-1] + random.randint(10, 200))
        return values

    followers = generate_series(3200)
    reach = generate_series(7000)

    return jsonify({
        "followers": followers[-1],
        "followers_change": followers[-1] - followers[-2],

        "reach": reach[-1],
        "reach_change": reach[-1] - reach[-2],

        "engagement_rate": random.randint(20, 60),
        "engagement_change": random.randint(-10, 15),

        "likes": random.randint(1000, 4000),
        "likes_change": random.randint(-100, 200),

        "followers_graph": followers,
        "reach_graph": reach,

        "labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    })
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

@app.route("/api/settings")
def get_settings():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM settings WHERE user_id=?",
        (session["user_id"],)
    )
    data = cursor.fetchone()

    # create default settings if not exists
    if not data:
        cursor.execute(
            "INSERT INTO settings (user_id) VALUES (?)",
            (session["user_id"],)
        )
        conn.commit()

        cursor.execute(
            "SELECT * FROM settings WHERE user_id=?",
            (session["user_id"],)
        )
        data = cursor.fetchone()

    conn.close()

    return jsonify({
        "appearance": data[2],
        "language": data[3],
        "font_size": data[4],
        "email_notifications": bool(data[5]),
        "push_notifications": bool(data[6]),
        "inapp_notifications": bool(data[7]),
        "profile_visibility": data[8],
        "direct_messages": data[9]
    })

@app.route("/api/settings", methods=["POST"])
def update_settings():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE settings SET
        appearance=?,
        language=?,
        font_size=?,
        email_notifications=?,
        push_notifications=?,
        inapp_notifications=?,
        profile_visibility=?,
        direct_messages=?
        WHERE user_id=?
    """, (
        data.get("appearance"),
        data.get("language"),
        data.get("font_size"),
        1 if data.get("email_notifications") else 0,
        1 if data.get("push_notifications") else 0,
        1 if data.get("inapp_notifications") else 0,
        data.get("profile_visibility"),
        data.get("direct_messages"),
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Settings saved"})

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
