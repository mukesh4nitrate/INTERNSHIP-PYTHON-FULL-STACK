from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "secure-secret-key"  # change this before deploying anywhere real
DATABASE = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the users table if it does not exist yet."""
    conn = get_db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY, "
        "username TEXT UNIQUE, "
        "password TEXT)"
    )
    conn.commit()
    conn.close()


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = generate_password_hash(request.form['password'])

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            db.commit()
            db.close()
            return redirect('/login')
        except sqlite3.IntegrityError:
            db.close()
            error = "That username is already taken."

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            return redirect('/dashboard')
        error = "Invalid username or password."

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html', user=session['user'])


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


@app.route('/')
def home():
    return redirect('/dashboard') if 'user' in session else redirect('/login')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
