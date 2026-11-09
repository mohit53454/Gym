# Gym Management App

A free Flask-based gym management system for tracking leads, memberships, attendance, payments, and reminders.

## Features
- Lead/Inquiry Management
- Member Registration & Tracking
- Attendance Recording
- Payment Logging
- Renewal Reminders
- Trainer Management

## Local Development
1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python app.py`
3. Visit: http://127.0.0.1:5000

## Deployment
This app is configured for free hosting on Render, Railway, or similar platforms.

## Cloud Database
The app can now use a cloud Postgres database instead of local SQLite.

Set one of these environment variables before starting the app:
- `DATABASE_URL`
- `SUPABASE_DB_URL`

If a cloud database URL is present, the app will use it. Otherwise it falls back to local SQLite for development.
If you enable the cloud database path, install with `pip install -r requirements-cloud.txt`.

### Supabase setup
1. Create a free Supabase project.
2. Copy the PostgreSQL connection string from the project settings.
3. Put it in your `.env` file as `DATABASE_URL=...`.
4. Install cloud dependencies with `pip install -r requirements-cloud.txt`.
5. Start the app with `python app.py`.

Use `.env.example` as the template for your local `.env` file.
