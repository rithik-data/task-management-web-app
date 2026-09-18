from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

DATABASE = "task_manager.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))

        conn = get_db()

        try:

            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )

            conn.commit()

        except sqlite3.IntegrityError:

            flash("Username already exists.")
            conn.close()

            return redirect(url_for("register"))

        conn.close()

        flash("Registration successful. Please log in.")

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        tasks=tasks
    )


@app.route("/task/add", methods=["POST"])
@login_required
def add_task():

    title = request.form["title"].strip()
    description = request.form.get(
        "description",
        ""
    ).strip()

    if title:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO tasks
            (user_id, title, description)
            VALUES (?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                description
            )
        )

        conn.commit()
        conn.close()

    return redirect(url_for("dashboard"))


@app.route("/task/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):

    conn = get_db()

    task = conn.execute(
        """
        SELECT * FROM tasks
        WHERE id = ? AND user_id = ?
        """,
        (
            task_id,
            session["user_id"]
        )
    ).fetchone()

    if task is None:

        conn.close()

        return redirect(url_for("dashboard"))

    if request.method == "POST":

        title = request.form["title"].strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        status = request.form.get(
            "status",
            "Pending"
        )

        if status not in ("Pending", "Completed"):
            status = "Pending"

        conn.execute(
            """
            UPDATE tasks
            SET title = ?,
                description = ?,
                status = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                title,
                description,
                status,
                task_id,
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()

    return render_template(
        "edit_task.html",
        task=task
    )


@app.route("/task/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle_task(task_id):

    conn = get_db()

    task = conn.execute(
        """
        SELECT status FROM tasks
        WHERE id = ? AND user_id = ?
        """,
        (
            task_id,
            session["user_id"]
        )
    ).fetchone()

    if task:

        new_status = (
            "Completed"
            if task["status"] == "Pending"
            else "Pending"
        )

        conn.execute(
            """
            UPDATE tasks
            SET status = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                new_status,
                task_id,
                session["user_id"]
            )
        )

        conn.commit()

    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/task/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):

    conn = get_db()

    conn.execute(
        """
        DELETE FROM tasks
        WHERE id = ? AND user_id = ?
        """,
        (
            task_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


if __name__ == "__main__":

    init_db()

    app.run(debug=True)
