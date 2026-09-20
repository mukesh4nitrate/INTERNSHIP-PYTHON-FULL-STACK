from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)
DATABASE = 'database.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the users table if it does not exist yet."""
    conn = get_db_connection()
    conn.execute(
        'CREATE TABLE IF NOT EXISTS users ('
        'id INTEGER PRIMARY KEY, name TEXT, email TEXT)'
    )
    conn.commit()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()

        if name and email:
            conn.execute(
                'INSERT INTO users (name, email) VALUES (?, ?)',
                (name, email)
            )
            conn.commit()
        conn.close()
        return redirect('/')

    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('index.html', users=users)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
