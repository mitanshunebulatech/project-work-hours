# WorkHours – Employee Work Hours Management System
using **NiceGUI**, **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

---

## Features

| Role     | Capabilities |
|----------|-------------|
| Employee | Log daily work hours per project, view own history |
| Admin    | View/edit/delete all entries, manage projects, filter & search |

---

## Tech Stack

| Layer      | Technology        |
|------------|-------------------|
| Frontend   | NiceGUI           |
| Backend    | FastAPI (via NiceGUI) |
| Database   | PostgreSQL        |
| ORM        | SQLAlchemy 2.x    |
| Passwords  | bcrypt            |
| Config     | python-dotenv     |

---

## Project Structure

```
project/
├── main.py          # Entry point – starts NiceGUI/FastAPI server
├── database.py      # SQLAlchemy engine & session factory
├── models.py        # ORM table definitions
├── auth.py          # Password hashing & authentication
├── crud.py          # All database operations + seed data
├── ui.py            # All NiceGUI pages (login, employee, admin)
├── routes.py        # Placeholder for future REST API routes
├── config.py        # Loads .env variables
├── requirements.txt # Python dependencies
├── .env             # Environment variables (do not commit)
└── README.md        # This file
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ running locally

---

## Setup Instructions

### 1. Create a PostgreSQL database

```bash
psql -U postgres
CREATE DATABASE work_hours_db;
\q
```

### 2. Configure environment variables

Edit `.env` to match your PostgreSQL credentials:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/work_hours_db
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Create a virtual environment

```bash
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python main.py
```

Open your browser at: **http://localhost:8080**

The database tables are created automatically on first run.
Sample data (admin + 5 employees + 5 projects) is seeded automatically.

---

## Default Login Credentials

### Admin
| Username | Password |
|----------|----------|
| admin    | admin123 |

### Employees
| Username | Password   |
|----------|------------|
| mitanshu    | mitanshu123   |
| sahil      | sahil123     |
| garv    | garv123   |
| anish    | anish123   |
| vaibhav      | vaibhav123     |

---

## Database Schema

### `users`
| Column   | Type         | Notes               |
|----------|--------------|---------------------|
| id       | INTEGER PK   | Auto-increment      |
| username | VARCHAR(100) | Unique, indexed     |
| password | VARCHAR(255) | bcrypt hash         |
| role     | VARCHAR(20)  | `admin` or `employee` |

### `projects`
| Column       | Type         | Notes           |
|--------------|--------------|-----------------|
| id           | INTEGER PK   | Auto-increment  |
| project_name | VARCHAR(200) | Unique          |

### `work_entries`
| Column       | Type       | Notes                        |
|--------------|------------|------------------------------|
| id           | INTEGER PK | Auto-increment               |
| employee_id  | INTEGER FK | → users.id                   |
| project_id   | INTEGER FK | → projects.id                |
| date         | DATE       |                              |
| hours_worked | FLOAT      | Must be > 0 and ≤ 24        |
| remarks      | TEXT       | Optional                     |

---

## Validation Rules

- All form fields (except Remarks) are required
- Hours must be **> 0** and **≤ 24**
- No duplicate entries for the same employee + project + date
- Employees cannot edit or delete their own past entries
- Only the admin can edit or delete any record

---

## Stopping the App

Press `Ctrl+C` in the terminal to stop the server.
