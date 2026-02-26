from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import os
import time
import json
import urllib.parse
import urllib.request
import urllib.error

app = Flask(__name__)
app.secret_key = "Qwe123!@#"  # Change this to something secure!

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
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
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cursor.fetchall()]
    if "is_active" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )
    if "profile_image" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN profile_image TEXT"
        )
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            caption TEXT,
            image_path TEXT,
            platforms TEXT,
            status TEXT DEFAULT 'published',  -- draft / published
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'Running',
            budget INTEGER NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
        ''')
    cursor.execute("PRAGMA table_info(messages)")
    message_columns = [row[1] for row in cursor.fetchall()]
    if "is_read" not in message_columns:
        cursor.execute(
            "ALTER TABLE messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0"
        )
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocked_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            blocked_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, blocked_user_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(blocked_user_id) REFERENCES users(id)
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS live_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
    conn.commit()
    conn.close()

init_db()

TREND_CACHE_SECONDS = 900
trend_cache_data = None
trend_cache_time = 0


def get_fallback_creators():
    return [
        {
            "username": "MayaReels",
            "name": "Maya Reels",
            "avatar_url": "https://i.pravatar.cc/120?img=47",
            "platform": "Instagram",
            "score": 92,
            "followers": 184000,
            "bio": "Short-form storytelling creator",
            "profile_url": "#"
        },
        {
            "username": "CodeWithArun",
            "name": "Code With Arun",
            "avatar_url": "https://i.pravatar.cc/120?img=12",
            "platform": "YouTube",
            "score": 89,
            "followers": 126000,
            "bio": "Programming tutorials and live coding",
            "profile_url": "#"
        },
        {
            "username": "FitNova",
            "name": "Fit Nova",
            "avatar_url": "https://i.pravatar.cc/120?img=16",
            "platform": "Instagram",
            "score": 84,
            "followers": 97000,
            "bio": "Fitness and wellness routines",
            "profile_url": "#"
        }
    ]


def _safe_github_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SocialSync-App",
            "Accept": "application/vnd.github+json"
        }
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_trending_creators():
    query = urllib.parse.quote("followers:>1000")
    search_url = (
        "https://api.github.com/search/users"
        f"?q={query}&sort=followers&order=desc&per_page=8"
    )
    users_payload = _safe_github_json(search_url)
    items = users_payload.get("items", [])

    creators = []
    for item in items:
        details = _safe_github_json(item.get("url"))
        followers = int(details.get("followers") or 0)
        creators.append({
            "username": details.get("login") or item.get("login") or "unknown",
            "name": details.get("name") or details.get("login") or "Unknown Creator",
            "avatar_url": details.get("avatar_url") or item.get("avatar_url"),
            "platform": "GitHub",
            "score": min(99, 60 + int(followers / 5000)),
            "followers": followers,
            "bio": details.get("bio") or "Creator profile trending this week",
            "profile_url": details.get("html_url") or item.get("html_url")
        })

    if not creators:
        return get_fallback_creators()
    return creators

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
            "SELECT id, username, email, password, is_active FROM users WHERE email=?",
            (email,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and int(user[4]) == 0:
            flash("This account is deactivated. Contact support to reactivate.", "danger")
            return render_template('login.html')

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


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        message = (request.form.get('message') or '').strip()

        if not name or not email or not message:
            flash("Please fill out all contact form fields.", "danger")
            return redirect(url_for('contact'))

        flash("Thanks for contacting SocialSync. We'll get back to you soon.", "success")
        return redirect(url_for('contact'))

    return render_template('contact.html')


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


@app.route("/api/posts", methods=["POST"])
def create_post():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    caption = request.form.get("caption")
    platforms = request.form.get("platforms")
    status = request.form.get("status", "published")

    file = request.files.get("image")
    image_path = ""

    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)
        image_path = f"static/uploads/{filename}"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO posts (user_id, caption, image_path, platforms, status)
        VALUES (?, ?, ?, ?, ?)
    """, (session["user_id"], caption, image_path, platforms, status))

    conn.commit()
    conn.close()

    return jsonify({"message": "Post saved"})

@app.route("/api/posts")
def get_posts():
    if "user_id" not in session:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, caption, image_path FROM posts
        WHERE user_id=? AND status='published'
        ORDER BY created_at DESC
    """, (session["user_id"],))

    posts = cursor.fetchall()
    conn.close()

    return jsonify([
        {"id": p[0], "caption": p[1], "image": p[2]}
        for p in posts
    ])


@app.route("/api/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT image_path FROM posts WHERE id=? AND user_id=?",
        (post_id, session["user_id"])
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    image_path = row[0]

    cursor.execute(
        "DELETE FROM posts WHERE id=? AND user_id=?",
        (post_id, session["user_id"])
    )
    conn.commit()
    conn.close()

    if image_path and image_path.startswith("static/uploads/"):
        full_image_path = os.path.join(app.root_path, image_path)
        if os.path.exists(full_image_path):
            try:
                os.remove(full_image_path)
            except OSError:
                pass

    return jsonify({"message": "Post deleted"})


@app.route("/api/ads/campaigns", methods=["POST"])
def create_campaign():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    post_id = data.get("post_id")
    budget = data.get("budget")

    try:
        budget = int(budget)
    except (TypeError, ValueError):
        budget = 0

    if not post_id or budget < 1:
        return jsonify({"error": "post_id and budget are required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT caption, image_path FROM posts
        WHERE id=? AND user_id=? AND status='published'
        """,
        (post_id, session["user_id"])
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    title = (row[0] or "Boost Campaign").strip()
    title = title[:40] if title else "Boost Campaign"
    campaign_title = f"Boost: {title}"

    cursor.execute(
        """
        INSERT INTO campaigns (user_id, post_id, title, status, budget, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session["user_id"], post_id, campaign_title, "Running", budget, row[1])
    )
    campaign_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Campaign started",
        "campaign": {
            "id": campaign_id,
            "title": campaign_title,
            "status": "Running",
            "budget": budget,
            "post_id": post_id,
            "image": row[1]
        }
    })


@app.route("/api/ads/campaigns/custom", methods=["POST"])
def create_custom_campaign():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    caption = (request.form.get("caption") or "").strip()
    budget_raw = request.form.get("budget")
    file = request.files.get("image")

    try:
        budget = int(budget_raw)
    except (TypeError, ValueError):
        budget = 0

    if budget < 1:
        return jsonify({"error": "Valid budget is required"}), 400

    if not file or not file.filename:
        return jsonify({"error": "Image is required"}), 400

    filename = secure_filename(file.filename)
    filename = f"{int(time.time())}_{filename}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    image_path = f"static/uploads/{filename}"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO posts (user_id, caption, image_path, platforms, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session["user_id"], caption, image_path, "Ads", "published")
    )
    post_id = cursor.lastrowid

    title = caption[:40] if caption else "Boost Campaign"
    campaign_title = f"Ad: {title}"

    cursor.execute(
        """
        INSERT INTO campaigns (user_id, post_id, title, status, budget, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session["user_id"], post_id, campaign_title, "Running", budget, image_path)
    )
    campaign_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Ad campaign created",
        "campaign": {
            "id": campaign_id,
            "title": campaign_title,
            "status": "Running",
            "budget": budget,
            "post_id": post_id,
            "image": image_path
        }
    })


@app.route("/api/ads/campaigns")
def get_campaigns():
    if "user_id" not in session:
        return jsonify([]), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, status, budget, image_path
        FROM campaigns
        WHERE user_id=?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "title": r[1],
            "status": r[2],
            "budget": r[3],
            "image": r[4]
        }
        for r in rows
    ])


@app.route("/api/ads/campaigns/<int:campaign_id>", methods=["PATCH"])
def update_campaign(campaign_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    status = data.get("status")
    if status not in ("Running", "Paused"):
        return jsonify({"error": "Invalid status"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE campaigns
        SET status=?
        WHERE id=? AND user_id=?
        """,
        (status, campaign_id, session["user_id"])
    )
    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if not updated:
        return jsonify({"error": "Campaign not found"}), 404

    return jsonify({"message": "Campaign updated"})


@app.route("/api/ads/campaigns/<int:campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM campaigns WHERE id=? AND user_id=?",
        (campaign_id, session["user_id"])
    )
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if not deleted:
        return jsonify({"error": "Campaign not found"}), 404

    return jsonify({"message": "Campaign deleted"})
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


@app.route("/api/privacy/blocked")
def get_blocked_users():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id, u.username
        FROM blocked_users b
        JOIN users u ON u.id = b.blocked_user_id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
        """,
        (session["user_id"],)
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"id": row[0], "username": row[1]}
        for row in rows
    ])


@app.route("/api/privacy/blocked", methods=["POST"])
def block_user():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    blocked_user_id = data.get("blocked_user_id")

    try:
        blocked_user_id = int(blocked_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user"}), 400

    if blocked_user_id == session["user_id"]:
        return jsonify({"error": "You cannot block yourself"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id=?", (blocked_user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    try:
        cursor.execute(
            "INSERT INTO blocked_users (user_id, blocked_user_id) VALUES (?, ?)",
            (session["user_id"], blocked_user_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "User already blocked"}), 409

    conn.close()
    return jsonify({"message": "User blocked"})


@app.route("/api/privacy/blocked/<int:blocked_user_id>", methods=["DELETE"])
def unblock_user(blocked_user_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM blocked_users WHERE user_id=? AND blocked_user_id=?",
        (session["user_id"], blocked_user_id)
    )
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if not deleted:
        return jsonify({"error": "Blocked user not found"}), 404

    return jsonify({"message": "User unblocked"})


@app.route("/api/account/info")
def get_account_info():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, email, profile_image FROM users WHERE id=?",
        (session["user_id"],)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "username": row[0],
        "email": row[1],
        "profile_image": row[2] or ""
    })


@app.route("/api/account/profile-photo", methods=["POST"])
def upload_profile_photo():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    file = request.files.get("profile_photo")
    if not file or not file.filename:
        return jsonify({"error": "Profile photo is required"}), 400

    allowed_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    original_name = secure_filename(file.filename)
    _, ext = os.path.splitext(original_name.lower())
    if ext not in allowed_exts:
        return jsonify({"error": "Invalid file type"}), 400

    filename = f"profile_{session['user_id']}_{int(time.time())}{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    image_path = f"static/uploads/{filename}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT profile_image FROM users WHERE id=?",
        (session["user_id"],)
    )
    row = cursor.fetchone()
    old_image = row[0] if row else ""

    cursor.execute(
        "UPDATE users SET profile_image=? WHERE id=?",
        (image_path, session["user_id"])
    )
    conn.commit()
    conn.close()

    if old_image and old_image.startswith("static/uploads/") and old_image != image_path:
        old_full = os.path.join(app.root_path, old_image)
        if os.path.exists(old_full):
            try:
                os.remove(old_full)
            except OSError:
                pass

    return jsonify({
        "message": "Profile photo updated",
        "profile_image": image_path
    })


@app.route("/api/account/info", methods=["PUT"])
def update_account_info():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not username or not email:
        return jsonify({"error": "Username and email are required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE email=? AND id != ?",
        (email, session["user_id"])
    )
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Email already in use"}), 409

    cursor.execute(
        "UPDATE users SET username=?, email=? WHERE id=?",
        (username, email, session["user_id"])
    )
    conn.commit()
    conn.close()

    session["username"] = username
    session["handle"] = email.split("@")[0] if "@" in email else email

    return jsonify({"message": "Account information updated"})


@app.route("/api/account/password", methods=["POST"])
def update_account_password():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not current_password or not new_password or not confirm_password:
        return jsonify({"error": "All fields are required"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    if new_password != confirm_password:
        return jsonify({"error": "New password and confirm password do not match"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password FROM users WHERE id=?",
        (session["user_id"],)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    if not check_password_hash(row[0], current_password):
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 400

    hashed_password = generate_password_hash(new_password)
    cursor.execute(
        "UPDATE users SET password=? WHERE id=?",
        (hashed_password, session["user_id"])
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Password updated successfully"})


@app.route("/api/account/deactivate", methods=["POST"])
def deactivate_account():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_active=0 WHERE id=?",
        (session["user_id"],)
    )
    conn.commit()
    conn.close()

    session.clear()
    return jsonify({"message": "Account deactivated"})


@app.route("/api/account/delete", methods=["DELETE"])
def delete_account():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE sender_id=? OR receiver_id=?", (user_id, user_id))
    cursor.execute("DELETE FROM campaigns WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM posts WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM tasks WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM live_sessions WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM settings WHERE user_id=?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    return jsonify({"message": "Account deleted"})

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


@app.route("/api/notifications")
def get_notifications():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT inapp_notifications
        FROM settings
        WHERE user_id=?
        """,
        (user_id,)
    )
    settings_row = cursor.fetchone()
    if settings_row is not None and int(settings_row[0]) == 0:
        conn.close()
        return jsonify({"items": [], "disabled": True})

    cursor.execute(
        """
        SELECT
            m.id,
            u.username,
            m.body,
            m.created_at
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE m.receiver_id = ?
        AND m.sender_id NOT IN (
            SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
        )
        AND m.sender_id NOT IN (
            SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
        )
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT 12
        """,
        (user_id, user_id, user_id)
    )
    message_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            p.id,
            u.username,
            p.caption,
            p.created_at
        FROM posts p
        JOIN users u ON u.id = p.user_id
        WHERE p.user_id != ?
        AND p.status = 'published'
        AND p.user_id NOT IN (
            SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
        )
        AND p.user_id NOT IN (
            SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
        )
        ORDER BY p.created_at DESC, p.id DESC
        LIMIT 12
        """,
        (user_id, user_id, user_id)
    )
    post_rows = cursor.fetchall()

    conn.close()

    items = []
    for row in message_rows:
        preview = (row[2] or "").strip()
        if len(preview) > 70:
            preview = preview[:67] + "..."
        items.append({
            "kind": "message",
            "created_at": row[3],
            "title": f"{row[1]} sent you a message",
            "description": preview or "Tap Inbox to view message."
        })

    for row in post_rows:
        caption = (row[2] or "").strip()
        if len(caption) > 70:
            caption = caption[:67] + "..."
        items.append({
            "kind": "post",
            "created_at": row[3],
            "title": f"{row[1]} published a new post",
            "description": caption or "Open Explore to check this creator."
        })

    items.sort(key=lambda item: item["created_at"] or "", reverse=True)
    items = items[:20]

    return jsonify({"items": items, "disabled": False})


@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "Message is required"}), 400

    api_key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        return jsonify({
            "error": "Google AI key missing. Set GOOGLE_API_KEY in environment."
        }), 500

    model = (os.environ.get("GOOGLE_AI_MODEL") or "gemini-2.0-flash").strip()
    if model.startswith("models/"):
        model = model.split("/", 1)[1]

    def parse_google_error(error_body):
        if not error_body:
            return None, None, None
        try:
            payload = json.loads(error_body)
        except Exception:
            return None, None, None
        error_obj = payload.get("error") or {}
        message = error_obj.get("message")
        status = error_obj.get("status")
        retry_after = None
        for detail in error_obj.get("details") or []:
            if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                retry_after = detail.get("retryDelay")
                break
        return message, status, retry_after

    def list_supported_models():
        list_url = (
            "https://generativelanguage.googleapis.com/v1beta/models"
            f"?key={urllib.parse.quote(api_key)}"
        )
        list_req = urllib.request.Request(
            list_url,
            headers={"Content-Type": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(list_req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("models") or []
        return [
            (m.get("name") or "").split("/", 1)[-1]
            for m in models
            if "generateContent" in (m.get("supportedGenerationMethods") or [])
        ]

    contents = []
    for item in history[-10:]:
        role = "model" if str(item.get("role")) == "assistant" else "user"
        text = str(item.get("content") or "").strip()
        if text:
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })
    contents.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    max_output_tokens_raw = (os.environ.get("GOOGLE_AI_MAX_OUTPUT_TOKENS") or "").strip()
    try:
        max_output_tokens = int(max_output_tokens_raw) if max_output_tokens_raw else 1536
    except ValueError:
        max_output_tokens = 1536
    max_output_tokens = max(256, min(max_output_tokens, 4096))

    payload = json.dumps({
        "systemInstruction": {
            "parts": [{
                "text": (
                    "Give complete, clear answers. "
                    "Use multiple sentences and include useful detail when appropriate."
                )
            }]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_output_tokens
        }
    }).encode("utf-8")

    preferred_fallbacks = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]

    model_candidates = [model]
    for candidate in preferred_fallbacks:
        if candidate not in model_candidates:
            model_candidates.append(candidate)

    result = None
    used_model = None
    last_error = None
    available_models = []
    quota_exceeded = False
    retry_after_delay = None

    for candidate_model in model_candidates:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{urllib.parse.quote(candidate_model)}:generateContent?key={urllib.parse.quote(api_key)}"
        )
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read().decode("utf-8")
            result = json.loads(raw)
            used_model = candidate_model
            break
        except urllib.error.HTTPError as err:
            error_body = ""
            try:
                error_body = err.read().decode("utf-8")
            except Exception:
                error_body = ""
            google_message, google_status, google_retry_after = parse_google_error(error_body)
            if err.code == 404:
                last_error = error_body or str(err)
                continue
            if err.code == 429 or google_status == "RESOURCE_EXHAUSTED":
                quota_exceeded = True
                retry_after_delay = google_retry_after or retry_after_delay
                last_error = google_message or error_body or str(err)
                continue
            return jsonify({
                "error": "Google AI request failed",
                "details": error_body or str(err)
            }), 502
        except urllib.error.URLError as err:
            return jsonify({
                "error": "Google AI is unreachable",
                "details": str(err)
            }), 502
        except Exception as err:
            return jsonify({
                "error": "Could not process AI response",
                "details": str(err)
            }), 500

    if result is None:
        try:
            available_models = list_supported_models()
        except Exception:
            available_models = []

    if result is None and available_models:
        for listed_model in available_models:
            if listed_model in model_candidates:
                continue
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{urllib.parse.quote(listed_model)}:generateContent?key={urllib.parse.quote(api_key)}"
            )
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as response:
                    raw = response.read().decode("utf-8")
                result = json.loads(raw)
                used_model = listed_model
                break
            except urllib.error.HTTPError as err:
                if err.code == 429:
                    quota_exceeded = True
                    try:
                        body = err.read().decode("utf-8")
                    except Exception:
                        body = ""
                    google_message, _, google_retry_after = parse_google_error(body)
                    retry_after_delay = google_retry_after or retry_after_delay
                    last_error = google_message or body or str(err)
                    continue
                last_error = str(err)
                continue
            except Exception as err:
                last_error = str(err)
                continue

    if result is None and quota_exceeded:
        response = jsonify({
            "error": "Google AI quota exceeded",
            "details": (
                (last_error or "Quota exhausted for the configured API key/project.")
                + " Check API key project, billing plan, and Gemini rate limits."
            ),
            "retry_after": retry_after_delay or ""
        })
        if retry_after_delay:
            response.headers["Retry-After"] = retry_after_delay.rstrip("s")
        return response, 429

    if result is None:
        available_preview = ", ".join(available_models[:8]) if available_models else "none"
        return jsonify({
            "error": "Google AI request failed",
            "details": (
                (last_error or "No working model found")
                + f" | Available generateContent models: {available_preview}"
            )
        }), 502

    candidates = result.get("candidates") or []
    if not candidates:
        return jsonify({"error": "No response from Google AI"}), 502

    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    reply = "".join(str(part.get("text") or "") for part in parts).strip()
    if not reply:
        reply = "I could not generate a response right now."

    return jsonify({"reply": reply, "model": used_model or model})


@app.route("/api/inbox/users")
def inbox_users():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username
        FROM users
        WHERE id != ?
        AND id NOT IN (
            SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
        )
        AND id NOT IN (
            SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
        )
        ORDER BY username COLLATE NOCASE ASC
        """,
        (session["user_id"], session["user_id"], session["user_id"])
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"id": row[0], "username": row[1]}
        for row in rows
    ])


@app.route("/api/inbox/conversations")
def inbox_conversations():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            u.id,
            u.username,
            m.body,
            m.created_at,
            (
                SELECT COUNT(*)
                FROM messages m3
                WHERE m3.sender_id = u.id
                  AND m3.receiver_id = ?
                  AND m3.is_read = 0
            ) AS unread_count
        FROM users u
        JOIN messages m
            ON (
                (m.sender_id = u.id AND m.receiver_id = ?)
                OR
                (m.receiver_id = u.id AND m.sender_id = ?)
            )
        WHERE u.id != ?
        AND u.id NOT IN (
            SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
        )
        AND u.id NOT IN (
            SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
        )
        AND m.id = (
            SELECT m2.id
            FROM messages m2
            WHERE (
                (m2.sender_id = u.id AND m2.receiver_id = ?)
                OR
                (m2.receiver_id = u.id AND m2.sender_id = ?)
            )
            ORDER BY m2.created_at DESC, m2.id DESC
            LIMIT 1
        )
        ORDER BY m.created_at DESC, m.id DESC
        """,
        (
            session["user_id"],
            session["user_id"],
            session["user_id"],
            session["user_id"],
            session["user_id"],
            session["user_id"],
            session["user_id"],
            session["user_id"]
        )
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "id": row[0],
            "username": row[1],
            "last_text": row[2],
            "last_time": row[3],
            "unread_count": int(row[4] or 0)
        }
        for row in rows
    ])


@app.route("/api/inbox/chats/<int:other_user_id>/messages")
def get_chat_messages(other_user_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if other_user_id == session["user_id"]:
        return jsonify({"error": "Invalid user"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE id=?",
        (other_user_id,)
    )
    other_user = cursor.fetchone()
    if not other_user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    cursor.execute(
        """
        SELECT 1
        FROM blocked_users
        WHERE
            (user_id=? AND blocked_user_id=?)
            OR
            (user_id=? AND blocked_user_id=?)
        LIMIT 1
        """,
        (session["user_id"], other_user_id, other_user_id, session["user_id"])
    )
    blocked = cursor.fetchone()
    if blocked:
        conn.close()
        return jsonify({"error": "Chat unavailable"}), 403

    cursor.execute(
        """
        UPDATE messages
        SET is_read = 1
        WHERE sender_id = ?
          AND receiver_id = ?
          AND is_read = 0
        """,
        (other_user_id, session["user_id"])
    )

    cursor.execute(
        """
        SELECT id, sender_id, receiver_id, body, created_at
        FROM messages
        WHERE
            (sender_id=? AND receiver_id=?)
            OR
            (sender_id=? AND receiver_id=?)
        ORDER BY created_at ASC, id ASC
        """,
        (session["user_id"], other_user_id, other_user_id, session["user_id"])
    )
    rows = cursor.fetchall()
    conn.commit()
    conn.close()

    return jsonify([
        {
            "id": row[0],
            "sender_id": row[1],
            "receiver_id": row[2],
            "body": row[3],
            "created_at": row[4]
        }
        for row in rows
    ])


@app.route("/api/inbox/chats/<int:other_user_id>/messages", methods=["POST"])
def send_chat_message(other_user_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if other_user_id == session["user_id"]:
        return jsonify({"error": "Invalid user"}), 400

    data = request.json or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(body) > 2000:
        return jsonify({"error": "Message too long"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE id=?",
        (other_user_id,)
    )
    other_user = cursor.fetchone()
    if not other_user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    cursor.execute(
        """
        SELECT 1
        FROM blocked_users
        WHERE
            (user_id=? AND blocked_user_id=?)
            OR
            (user_id=? AND blocked_user_id=?)
        LIMIT 1
        """,
        (session["user_id"], other_user_id, other_user_id, session["user_id"])
    )
    blocked = cursor.fetchone()
    if blocked:
        conn.close()
        return jsonify({"error": "Chat unavailable"}), 403

    cursor.execute(
        """
        INSERT INTO messages (sender_id, receiver_id, body, is_read)
        VALUES (?, ?, ?, 0)
        """,
        (session["user_id"], other_user_id, body)
    )
    message_id = cursor.lastrowid

    cursor.execute(
        """
        SELECT created_at
        FROM messages
        WHERE id=?
        """,
        (message_id,)
    )
    created_at = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Sent",
        "data": {
            "id": message_id,
            "sender_id": session["user_id"],
            "receiver_id": other_user_id,
            "body": body,
            "created_at": created_at
        }
    })


@app.route("/api/inbox/chats/<int:other_user_id>", methods=["DELETE"])
def delete_chat(other_user_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if other_user_id == session["user_id"]:
        return jsonify({"error": "Invalid user"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM messages
        WHERE
            (sender_id=? AND receiver_id=?)
            OR
            (sender_id=? AND receiver_id=?)
        """,
        (session["user_id"], other_user_id, other_user_id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Chat deleted"})


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


@app.route('/explore')
def explore():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('explore.html')


@app.route('/trends')
def trends():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('trends.html')


@app.route("/api/trends/creators")
def trends_creators():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    global trend_cache_data, trend_cache_time

    now = time.time()
    if trend_cache_data and (now - trend_cache_time) < TREND_CACHE_SECONDS:
        return jsonify({
            "source": "cache",
            "creators": trend_cache_data
        })

    try:
        creators = fetch_trending_creators()
        trend_cache_data = creators
        trend_cache_time = now
        return jsonify({
            "source": "github",
            "creators": creators
        })
    except Exception:
        fallback = get_fallback_creators()
        trend_cache_data = fallback
        trend_cache_time = now
        return jsonify({
            "source": "fallback",
            "creators": fallback
        })


@app.route('/live')
def live():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('live.html')


@app.route("/api/live/summary")
def live_summary():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT EXISTS(
            SELECT 1
            FROM live_sessions
            WHERE user_id=? AND ended_at IS NULL
        )
        """,
        (session["user_id"],)
    )
    currently_live = bool(cursor.fetchone()[0])

    cursor.execute(
        """
        SELECT COALESCE(
            SUM((julianday(COALESCE(ended_at, CURRENT_TIMESTAMP)) - julianday(started_at)) * 24),
            0
        )
        FROM live_sessions
        WHERE user_id=?
        """,
        (session["user_id"],)
    )
    total_hours = float(cursor.fetchone()[0] or 0)

    cursor.execute(
        """
        SELECT started_at
        FROM live_sessions
        WHERE user_id=? AND ended_at IS NULL
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (session["user_id"],)
    )
    active_session = cursor.fetchone()
    conn.close()

    return jsonify({
        "currently_live": currently_live,
        "total_hours": round(total_hours, 2),
        "active_since": active_session[0] if active_session else None
    })


@app.route("/api/live/creators")
def live_creators():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id, u.username, ls.started_at
        FROM live_sessions ls
        JOIN users u ON u.id = ls.user_id
        WHERE ls.ended_at IS NULL
          AND u.id != ?
          AND u.is_active = 1
          AND u.id NOT IN (
              SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
          )
          AND u.id NOT IN (
              SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
          )
        ORDER BY ls.started_at DESC
        """,
        (session["user_id"], session["user_id"], session["user_id"])
    )
    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "id": row[0],
            "username": row[1],
            "started_at": row[2]
        }
        for row in rows
    ])


@app.route("/api/live/toggle", methods=["POST"])
def toggle_live():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM live_sessions
        WHERE user_id=? AND ended_at IS NULL
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (session["user_id"],)
    )
    active = cursor.fetchone()

    if active:
        cursor.execute(
            "UPDATE live_sessions SET ended_at=CURRENT_TIMESTAMP WHERE id=?",
            (active[0],)
        )
        status = "stopped"
    else:
        cursor.execute(
            "INSERT INTO live_sessions (user_id) VALUES (?)",
            (session["user_id"],)
        )
        status = "started"

    conn.commit()
    conn.close()
    return jsonify({"message": status})


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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
