
from flask import (
    Flask, render_template, request, redirect,
    session, url_for, flash, jsonify
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
import os
import sqlite3
from functools import wraps
from database import get_db, init_db

app = Flask(__name__)

# Read the secret from the environment in real use; the random fallback
# is fine for development (sessions just reset when the server restarts).
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32).hex()

# Create tables when the module loads, so it also works with `flask run`
init_db()


def is_valid_email(value):
    return "@" in value and "." in value.rsplit("@", 1)[-1] and " " not in value


def current_role():
    """Always read the role from the database, not from the cookie session.
    Returns None (and clears the session) if the account no longer exists."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    db = get_db()
    try:
        row = db.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        db.close()
    if row is None:
        session.clear()
        return None
    session["role"] = row["role"]
    return row["role"]

# AUTHENTICATION DECORATORS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_role() is None:
            flash("Please login first.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        role = current_role()
        if role is None:
            flash("Please login first.")
            return redirect(url_for("login"))

        if role != "admin":
            flash("Access denied. Admins only.")
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_role() is None:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


def api_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        role = current_role()
        if role is None:
            return jsonify({"error": "Authentication required"}), 401

        if role != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)
    return decorated


# -------------------------
# HOME
# -------------------------

@app.route("/")
def home():
    role = current_role()
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role is not None:
        return redirect(url_for("dashboard"))

    return redirect(url_for("register"))

# -------------------------
# REST API: REGISTER
# -------------------------

@app.route("/api/auth/register", methods=["POST"])
def api_register():

    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Content-Type must be application/json"
        }), 415

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Valid JSON body required"
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not username.strip():
        return jsonify({
            "success": False,
            "error": "Username is required"
        }), 400

    if not isinstance(password, str) or len(password) < 8:
        return jsonify({
            "success": False,
            "error": "Password must contain at least 8 characters"
        }), 400

    db = get_db()

    try:
        existing_user = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username.strip(),)
        ).fetchone()

        if existing_user:
            return jsonify({
                "success": False,
                "error": "Username already exists"
            }), 409

        cursor = db.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, 'user')
            """,
            (
                username.strip(),
                generate_password_hash(password)
            )
        )

        db.commit()

        return jsonify({
            "success": True,
            "message": "Registration successful",
            "data": {
                "user_id": cursor.lastrowid,
                "username": username.strip(),
                "role": "user"
            }
        }), 201

    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({
            "success": False,
            "error": "Username already exists"
        }), 409

    except Exception:
        db.rollback()
        app.logger.exception("API registration failed")

        return jsonify({
            "success": False,
            "error": "Registration could not be completed"
        }), 500

    finally:
        db.close()


# -------------------------
# REGISTER
# -------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_role() is not None:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO users (username, password, role)
                VALUES (?, ?, 'user')
                """,
                (username, generate_password_hash(password))
            )
            db.commit()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            db.rollback()
            flash("Username already exists.")
            return redirect(url_for("register"))

        except Exception:
            db.rollback()
            app.logger.exception("Registration failed")
            flash("Registration failed. Please try again.")
            return redirect(url_for("register"))

        finally:
            db.close()

    return render_template("register.html")


# -------------------------
# REST API: LOGIN
# -------------------------

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    # Require JSON request
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Content-Type must be application/json"
        }), 415

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "A valid JSON body is required"
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not username.strip():
        return jsonify({
            "success": False,
            "error": "Username is required"
        }), 400

    if not isinstance(password, str) or not password:
        return jsonify({
            "success": False,
            "error": "Password is required"
        }), 400

    db = get_db()

    try:
        user = db.execute(
            """
            SELECT id, username, password, role
            FROM users
            WHERE username = ?
            """,
            (username.strip(),)
        ).fetchone()
    finally:
        db.close()

    if user is None or not check_password_hash(user["password"], password):
        return jsonify({
            "success": False,
            "error": "Invalid username or password"
        }), 401

    # Create a new authenticated session
    session.clear()
    session["user_id"] = user["id"]
    session["user"] = user["username"]
    session["role"] = user["role"]

    return jsonify({
        "success": True,
        "message": "Login successful",
        "data": {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }
    }), 200

# -------------------------
# REST API: LOGOUT
# -------------------------

@app.route("/api/auth/logout", methods=["POST"])
@api_login_required
def api_logout():
    session.clear()

    return jsonify({
        "success": True,
        "message": "Logout successful"
    }), 200


# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_role() is not None:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        try:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()
        finally:
            db.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user"] = user["username"]
            session["role"] = user["role"]

            flash("Login successful.")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


# -------------------------
# NORMAL USER DASHBOARD
# -------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        username=session["user"],
        role=session["role"]
    )


# -------------------------
# ADMIN DASHBOARD
# -------------------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    try:
        total_users = db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_students = db.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        users = db.execute(
            "SELECT id, username, role FROM users ORDER BY id"
        ).fetchall()
    finally:
        db.close()

    return render_template(
        "admin_dashboard.html",
        username=session["user"],
        total_users=total_users,
        total_students=total_students,
        users=users
    )


# -------------------------
# MANAGE USER ROLES
# -------------------------

@app.route("/admin/manage-users", methods=["GET", "POST"])
@admin_required
def manage_users():
    db = get_db()

    try:
        if request.method == "POST":
            user_id = request.form.get("user_id")
            new_role = request.form.get("role")

            if new_role not in ("user", "admin"):
                flash("Invalid role.")
                return redirect(url_for("manage_users"))

            if not user_id or not user_id.isdigit():
                flash("Invalid user.")
                return redirect(url_for("manage_users"))

            if int(user_id) == session["user_id"]:
                flash("You cannot change your own role.")
                return redirect(url_for("manage_users"))

            cursor = db.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (new_role, int(user_id))
            )
            db.commit()
            if cursor.rowcount == 0:
                flash("User not found.")
            else:
                flash("User role updated.")
            return redirect(url_for("manage_users"))

        users = db.execute(
            "SELECT id, username, role FROM users ORDER BY id"
        ).fetchall()

        return render_template("manage_users.html", users=users)

    finally:
        db.close()


# -------------------------
# ADD STUDENT - ADMIN ONLY
# -------------------------

@app.route("/add-student", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()

        if not name or not email or not course:
            flash("All fields are required.")
            return redirect(url_for("add_student"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return redirect(url_for("add_student"))

        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO students (name, email, course)
                VALUES (?, ?, ?)
                """,
                (name, email, course)
            )
            db.commit()
            flash("Student added successfully.")
        finally:
            db.close()

        return redirect(url_for("students"))

    return render_template("add_student.html")


# -------------------------
# VIEW STUDENTS - ALL USERS
# -------------------------

@app.route("/students")
@login_required
def students():
    db = get_db()
    try:
        students_list = db.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()
    finally:
        db.close()

    return render_template(
        "students.html",
        students=students_list,
        role=session["role"]
    )


# -------------------------
# EDIT STUDENT - ADMIN ONLY
# -------------------------

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_student(id):
    db = get_db()

    try:
        student = db.execute(
            "SELECT * FROM students WHERE id = ?", (id,)
        ).fetchone()

        if student is None:
            flash("Student not found.")
            return redirect(url_for("students"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            course = request.form.get("course", "").strip()

            if not name or not email or not course:
                flash("All fields are required.")
                return redirect(url_for("edit_student", id=id))

            if not is_valid_email(email):
                flash("Please enter a valid email address.")
                return redirect(url_for("edit_student", id=id))

            db.execute(
                """
                UPDATE students
                SET name = ?, email = ?, course = ?
                WHERE id = ?
                """,
                (name, email, course, id)
            )
            db.commit()
            flash("Student updated successfully.")
            return redirect(url_for("students"))

        return render_template("edit_student.html", student=student)

    finally:
        db.close()


# -------------------------
# DELETE STUDENT - ADMIN ONLY
# -------------------------

@app.route("/delete/<int:id>", methods=["POST"])
@admin_required
def delete_student(id):
    db = get_db()
    try:
        cursor = db.execute("DELETE FROM students WHERE id = ?", (id,))
        db.commit()
        if cursor.rowcount == 0:
            flash("Student not found.")
        else:
            flash("Student deleted successfully.")
    finally:
        db.close()

    return redirect(url_for("students"))


# -------------------------
# REST API: GET ALL STUDENTS
# -------------------------

@app.route("/api/students", methods=["GET"])
@api_login_required
def api_get_students():
    db = get_db()
    try:
        students_list = db.execute(
            "SELECT * FROM students ORDER BY id"
        ).fetchall()

        return jsonify([
            dict(student) for student in students_list
        ]), 200
    finally:
        db.close()


# -------------------------
# REST API: GET ONE STUDENT
# -------------------------

@app.route("/api/students/<int:id>", methods=["GET"])
@api_login_required
def api_get_student(id):
    db = get_db()
    try:
        student = db.execute(
            "SELECT * FROM students WHERE id = ?", (id,)
        ).fetchone()

        if student is None:
            return jsonify({"error": "Student not found"}), 404

        return jsonify(dict(student)), 200
    finally:
        db.close()


# -------------------------
# REST API: CREATE STUDENT
# ADMIN ONLY
# -------------------------

@app.route("/api/students", methods=["POST"])
@api_admin_required
def api_add_student():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    name = data.get("name")
    email = data.get("email")
    course = data.get("course")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (name, email, course)
    ):
        return jsonify({
            "error": "Name, email and course are required"
        }), 400

    if not is_valid_email(email.strip()):
        return jsonify({"error": "Invalid email address"}), 400

    db = get_db()
    try:
        cursor = db.execute(
            """
            INSERT INTO students (name, email, course)
            VALUES (?, ?, ?)
            """,
            (name.strip(), email.strip(), course.strip())
        )
        db.commit()

        return jsonify({
            "message": "Student created successfully",
            "id": cursor.lastrowid
        }), 201
    finally:
        db.close()


# -------------------------
# REST API: UPDATE STUDENT
# ADMIN ONLY
# -------------------------

@app.route("/api/students/<int:id>", methods=["PUT"])
@api_admin_required
def api_update_student(id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    name = data.get("name")
    email = data.get("email")
    course = data.get("course")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (name, email, course)
    ):
        return jsonify({
            "error": "Name, email and course are required"
        }), 400

    if not is_valid_email(email.strip()):
        return jsonify({"error": "Invalid email address"}), 400

    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM students WHERE id = ?", (id,)
        ).fetchone()

        if existing is None:
            return jsonify({"error": "Student not found"}), 404

        db.execute(
            """
            UPDATE students
            SET name = ?, email = ?, course = ?
            WHERE id = ?
            """,
            (name.strip(), email.strip(), course.strip(), id)
        )
        db.commit()

        return jsonify({"message": "Student updated successfully"}), 200
    finally:
        db.close()


# -------------------------
# REST API: DELETE STUDENT
# ADMIN ONLY
# -------------------------

@app.route("/api/students/<int:id>", methods=["DELETE"])
@api_admin_required
def api_delete_student(id):
    db = get_db()
    try:
        cursor = db.execute(
            "DELETE FROM students WHERE id = ?", (id,)
        )
        db.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Student not found"}), 404

        return jsonify({"message": "Student deleted successfully"}), 200
    finally:
        db.close()


# -------------------------
# JSON ERRORS FOR /api/*
# -------------------------

@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found"}), 404
    return error


@app.errorhandler(405)
def method_not_allowed(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Method not allowed"}), 405
    return error


# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


# -------------------------
# START APPLICATION
# -------------------------

if __name__ == "__main__":
    # Set debug=False before deploying anywhere public
    app.run(debug=True)
