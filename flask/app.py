from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Login page
@app.route('/')
@app.route('/login')
def login():
    return render_template('login.html')

# Signup page
@app.route('/signup')
def signup():
    return render_template('signup.html')

# Home (after login)
@app.route('/home')
def home():
    return render_template('home.html')

# Home (after login)
@app.route('/youtube')
def youtube():
    return render_template('youtube.html')

@app.route('/facebook')
def facebook():
    return render_template('facebook.html')

# Inbox page
@app.route('/inbox')
def inbox():
    return render_template('inbox.html')

# Post page
@app.route('/post')
def post():
    return render_template('post.html')

# Schedule page
@app.route('/schedule')
def schedule():
    return render_template('schedule.html')

# Ads page
@app.route('/ads')
def ads():
    return render_template('ads.html')

# Settings page
@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/logout')
def logout():
     # remove all user data from session
    return redirect(url_for('login'))  # now safely go to login



if __name__ == "__main__":
    app.run(debug=True)
