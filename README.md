# Multi-User-Task-Collaboration-System

A modern multi-user Kanban task collaboration system built with Flask, MongoDB, vanilla JavaScript, and SMTP OTP authentication.

## Tech Stack

- Backend: Flask (`app.py`)
- Helpers: SMTP + OTP utilities (`utils.py`)
- Database: MongoDB with PyMongo
- Frontend: Tailwind CSS (CDN) + vanilla JS (`fetch`)

## Features

- Email + OTP registration and login
- No login before registration/verification
- Role-based access: `Manager` and `Member`
- Async API with JSON responses for SPA-style updates
- 3-column Kanban board: `To Do`, `In Progress`, `Done`
- Manager-only task creation
- Member-only visibility of assigned tasks
- Task assignment email alerts via SMTP
- Drag-and-drop + button-based status updates with optimistic UI and rollback

## Project Structure

```text
.
|-- app.py
|-- utils.py
|-- requirements.txt
|-- .env.example
|-- templates/
|   `-- dashboard.html
`-- static/
		`-- board.js
```

## 1) Local Setup (No Docker)

### Prerequisites

- Python 3.10+
- MongoDB running locally (or reachable remotely)
- SMTP credentials (for OTP and task emails)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

Create `.env` from `.env.example` and fill real values:

```bash
cp .env.example .env
```

Required variables:

- `FLASK_SECRET_KEY`
- `MONGO_URI`
- `MONGO_DB_NAME`
- `OTP_SECRET_KEY`
- `OTP_TTL_MINUTES`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`

### Run app

```bash
python app.py
```

Open:

- Dashboard UI (login + registration): `http://127.0.0.1:5000/`

## 2) Collections and Data Model

### `users`

- `email` (string, unique in practice)
- `role` (`Manager` or `Member`)
- `is_verified` (bool)
- `otp` (temporary object while pending verification)
- `created_at`, `updated_at`

### `tasks`

- `title` (string)
- `assigned_to` (member email)
- `status` (`To Do`, `In Progress`, `Done`)
- `due_date` (string or null)
- `created_by` (manager email)
- `created_at`, `updated_at`

## 3) API Endpoints

All API responses are JSON.

### Auth

- `POST /auth/register/request-otp`
- `POST /auth/register/verify`
- `POST /auth/login/request-otp`
- `POST /auth/login/verify`
- `POST /auth/logout`
- `GET /auth/me`

### Tasks

- `GET /api/tasks`
- `POST /api/tasks` (Manager only)
- `PUT /api/tasks/<task_id>/status`

## 4) cURL Test Commands

Use cookie jar to persist session across requests.

### 4.1 Request registration OTP

```bash
curl -X POST http://127.0.0.1:5000/auth/register/request-otp \
	-H "Content-Type: application/json" \
	-d '{"email":"manager@example.com","role":"Manager"}'
```

### 4.2 Verify registration OTP

Replace `123456` with OTP received on email.

```bash
curl -X POST http://127.0.0.1:5000/auth/register/verify \
	-c cookies.txt -b cookies.txt \
	-H "Content-Type: application/json" \
	-d '{"email":"manager@example.com","otp":"123456"}'
```

### 4.3 Request login OTP (for existing verified user)

```bash
curl -X POST http://127.0.0.1:5000/auth/login/request-otp \
	-H "Content-Type: application/json" \
	-d '{"email":"manager@example.com"}'
```

### 4.4 Verify login OTP

```bash
curl -X POST http://127.0.0.1:5000/auth/login/verify \
	-c cookies.txt -b cookies.txt \
	-H "Content-Type: application/json" \
	-d '{"email":"manager@example.com","otp":"123456"}'
```

### 4.5 Create task (Manager session required)

```bash
curl -X POST http://127.0.0.1:5000/api/tasks \
	-c cookies.txt -b cookies.txt \
	-H "Content-Type: application/json" \
	-d '{"title":"Write Flask Routes","assigned_to":"member@example.com","status":"To Do","due_date":"2026-04-20"}'
```

### 4.6 List tasks

```bash
curl -X GET http://127.0.0.1:5000/api/tasks \
	-c cookies.txt -b cookies.txt
```

### 4.7 Update task status

Replace `<TASK_ID>` with task id from list/create response.

```bash
curl -X PUT http://127.0.0.1:5000/api/tasks/<TASK_ID>/status \
	-c cookies.txt -b cookies.txt \
	-H "Content-Type: application/json" \
	-d '{"status":"In Progress"}'
```

## 5) Frontend Notes

- Task card elements include task id in `data-id`.
- Status changes are done via `fetch` to `PUT /api/tasks/<id>/status`.
- Drag-and-drop and move buttons both use the same API update logic.
- On API failure, optimistic UI updates are automatically rolled back.

## 6) Security Notes (Important)

- Rotate `FLASK_SECRET_KEY` and `OTP_SECRET_KEY` in production.
- Store SMTP credentials securely.
- Use HTTPS in production.
- Consider adding rate limiting on OTP endpoints.
- Consider expiring/invalidation rules for repeated OTP requests.