from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

@app.route("/")
def login():
    return render_template("login.html")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    app.run(debug=True)
