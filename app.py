import os
from datetime import datetime, timedelta, timezone
from functools import wraps

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, render_template
from pymongo import MongoClient

from utils import generate_otp, hash_otp, verify_otp, send_otp_email, send_task_assignment_email

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://mydb:sachin65200@cluster0.39fbg5g.mongodb.net/?appName=Cluster0")
db_name = os.getenv("MONGO_DB_NAME", "task_collab")
client = MongoClient(mongo_uri)
db = client[db_name]
users_col = db["users"]
tasks_col = db["tasks"]

TASK_STATUSES = ["To Do", "In Progress", "Done"]
ALLOWED_ROLES = ["Manager", "Member"]
OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "10"))


def serialize_task(task: dict) -> dict:
    return {
        "id": str(task["_id"]),
        "title": task.get("title"),
        "assigned_to": task.get("assigned_to"),
        "status": task.get("status"),
        "due_date": task.get("due_date"),
        "created_by": task.get("created_by"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
    }


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"ok": False, "error": "Authentication required"}), 401
        return fn(*args, **kwargs)

    return wrapper


def role_required(required_role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                return jsonify({"ok": False, "error": "Authentication required"}), 401
            if user.get("role") != required_role:
                return jsonify({"ok": False, "error": "Forbidden"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _create_and_send_otp(email: str, purpose: str) -> tuple[bool, str]:
    otp = generate_otp()
    otp_hash = hash_otp(otp)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

    users_col.update_one(
        {"email": email},
        {
            "$set": {
                "otp": {
                    "hash": otp_hash,
                    "purpose": purpose,
                    "expires_at": expires_at,
                    "created_at": now,
                },
                "updated_at": now,
            }
        },
        upsert=True,
    )

    try:
        send_otp_email(email, otp, purpose, expires_at)
    except Exception as exc:
        return False, str(exc)

    return True, ""


@app.get("/")
def home_page():
    return render_template("dashboard.html")


@app.get("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.post("/auth/register/request-otp")
def request_register_otp():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "").strip()

    if not email or role not in ALLOWED_ROLES:
        return jsonify({"ok": False, "error": "Valid email and role are required"}), 400

    existing = users_col.find_one({"email": email})
    if existing and existing.get("is_verified"):
        return jsonify({"ok": False, "error": "User already registered. Please log in."}), 409

    now = datetime.now(timezone.utc)
    users_col.update_one(
        {"email": email},
        {
            "$set": {
                "email": email,
                "role": role,
                "is_verified": False,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    sent, error = _create_and_send_otp(email, "register")
    if not sent:
        return jsonify({"ok": False, "error": f"Failed to send OTP: {error}"}), 500

    return jsonify({"ok": True, "message": "Registration OTP sent"})


@app.post("/auth/register/verify")
def verify_register_otp():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()

    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"ok": False, "error": "User not found. Register first."}), 404

    otp_data = user.get("otp") or {}
    if otp_data.get("purpose") != "register":
        return jsonify({"ok": False, "error": "No registration OTP found"}), 400
    if not otp_data.get("expires_at") or otp_data["expires_at"] < datetime.now(timezone.utc):
        return jsonify({"ok": False, "error": "OTP expired"}), 400
    if not verify_otp(otp, otp_data.get("hash", "")):
        return jsonify({"ok": False, "error": "Invalid OTP"}), 400

    now = datetime.now(timezone.utc)
    users_col.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"is_verified": True, "updated_at": now},
            "$unset": {"otp": ""},
        },
    )

    session["user"] = {"id": str(user["_id"]), "email": email, "role": user.get("role")}
    return jsonify({"ok": True, "message": "Registration verified", "user": session["user"]})


@app.post("/auth/login/request-otp")
def request_login_otp():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"ok": False, "error": "Email is required"}), 400

    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"ok": False, "error": "User not found. Register first."}), 404
    if not user.get("is_verified"):
        return jsonify({"ok": False, "error": "User is not verified. Complete registration first."}), 403

    sent, error = _create_and_send_otp(email, "login")
    if not sent:
        return jsonify({"ok": False, "error": f"Failed to send OTP: {error}"}), 500

    return jsonify({"ok": True, "message": "Login OTP sent"})


@app.post("/auth/login/verify")
def verify_login_otp():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()

    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"ok": False, "error": "User not found"}), 404

    otp_data = user.get("otp") or {}
    if otp_data.get("purpose") != "login":
        return jsonify({"ok": False, "error": "No login OTP found"}), 400
    if not otp_data.get("expires_at") or otp_data["expires_at"] < datetime.now(timezone.utc):
        return jsonify({"ok": False, "error": "OTP expired"}), 400
    if not verify_otp(otp, otp_data.get("hash", "")):
        return jsonify({"ok": False, "error": "Invalid OTP"}), 400

    users_col.update_one({"_id": user["_id"]}, {"$unset": {"otp": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}})

    session["user"] = {"id": str(user["_id"]), "email": user["email"], "role": user["role"]}
    return jsonify({"ok": True, "message": "Login successful", "user": session["user"]})


@app.post("/auth/logout")
@auth_required
def logout():
    session.clear()
    return jsonify({"ok": True, "message": "Logged out"})


@app.get("/auth/me")
def me():
    return jsonify({"ok": True, "user": session.get("user")})


@app.get("/api/tasks")
@auth_required
def list_tasks():
    user = session["user"]
    query = {}
    if user["role"] == "Member":
        query["assigned_to"] = user["email"]

    tasks = [serialize_task(task) for task in tasks_col.find(query).sort("created_at", -1)]
    return jsonify({"ok": True, "tasks": tasks})


@app.post("/api/tasks")
@role_required("Manager")
def create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    assigned_to = (data.get("assigned_to") or "").strip().lower()
    status = (data.get("status") or "To Do").strip()
    due_date = (data.get("due_date") or "").strip() or None

    if not title or not assigned_to:
        return jsonify({"ok": False, "error": "title and assigned_to are required"}), 400
    if status not in TASK_STATUSES:
        return jsonify({"ok": False, "error": f"status must be one of: {TASK_STATUSES}"}), 400

    assigned_member = users_col.find_one({"email": assigned_to, "role": "Member", "is_verified": True})
    if not assigned_member:
        return jsonify({"ok": False, "error": "Assigned member not found or not verified"}), 404

    now = datetime.now(timezone.utc)
    task_doc = {
        "title": title,
        "assigned_to": assigned_to,
        "status": status,
        "due_date": due_date,
        "created_by": session["user"]["email"],
        "created_at": now,
        "updated_at": now,
    }

    result = tasks_col.insert_one(task_doc)
    task_doc["_id"] = result.inserted_id

    try:
        send_task_assignment_email(assigned_to, title, due_date)
    except Exception:
        # Task creation should still succeed if SMTP fails.
        pass

    return jsonify({"ok": True, "task": serialize_task(task_doc)}), 201


@app.put("/api/tasks/<task_id>/status")
@auth_required
def update_task_status(task_id: str):
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()

    if new_status not in TASK_STATUSES:
        return jsonify({"ok": False, "error": f"status must be one of: {TASK_STATUSES}"}), 400

    try:
        object_id = ObjectId(task_id)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid task id"}), 400

    task = tasks_col.find_one({"_id": object_id})
    if not task:
        return jsonify({"ok": False, "error": "Task not found"}), 404

    current_user = session["user"]
    if current_user["role"] == "Member" and task.get("assigned_to") != current_user["email"]:
        return jsonify({"ok": False, "error": "Forbidden"}), 403

    tasks_col.update_one(
        {"_id": object_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    updated_task = tasks_col.find_one({"_id": object_id})
    return jsonify({"ok": True, "task": serialize_task(updated_task)})


if __name__ == "__main__":
    app.run(debug=False)
