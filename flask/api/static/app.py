from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "Qwe123!@#"  # Change this to something secure!

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')
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
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
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
