
from datetime import datetime, timedelta
from functools import wraps
import re
from urllib.parse import quote
import os
import sqlite3
import tempfile

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg2
    from psycopg2 import pool as psycopg2_pool
except ImportError:  # pragma: no cover - optional until cloud DB is enabled
    psycopg2 = None
    psycopg2_pool = None


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file()

DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
if psycopg2 is not None:
    DB_INTEGRITY_ERRORS = DB_INTEGRITY_ERRORS + (psycopg2.IntegrityError,)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "power-gym-secret-key")

PLAN_DURATIONS = {
    "Basic (1 month)": 30,
    "Premium (3 months)": 90,
    "Elite (6 months)": 180,
    "Annual": 365,
}


PRIMARY_DB = os.path.join(tempfile.gettempdir(), "power_gym.db")
FALLBACK_DB = os.path.join(tempfile.gettempdir(), "power_gym_fallback.db")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
USE_POSTGRES = bool(DATABASE_URL)
POSTGRES_POOL = None


class HybridRow:
    def __init__(self, columns, values):
        self._columns = list(columns)
        self._values = tuple(values)
        self._mapping = dict(zip(self._columns, self._values))

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._values[item]
        return self._mapping[item]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._mapping.keys()

    def get(self, key, default=None):
        return self._mapping.get(key, default)

    def items(self):
        return self._mapping.items()

    def values(self):
        return self._mapping.values()

    def __getattr__(self, item):
        try:
            return self._mapping[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
        self._pending_rows = []
        self.lastrowid = None
        self._is_postgres = True

    def _wrap_row(self, row):
        if row is None:
            return None
        columns = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
        return HybridRow(columns, row)

    def _wrap_rows(self, rows):
        return [self._wrap_row(row) for row in rows]

    def _translate_sql(self, sql):
        sql = re.sub(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", "BIGSERIAL PRIMARY KEY", sql, flags=re.IGNORECASE)
        sql = re.sub(r"INTEGER\s+PRIMARY\s+KEY", "SERIAL PRIMARY KEY", sql, count=1, flags=re.IGNORECASE)
        if sql.strip().upper().startswith("INSERT OR IGNORE INTO ADMIN_USERS"):
            sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1)
            if "ON CONFLICT" not in sql.upper():
                sql += " ON CONFLICT (username) DO NOTHING"
        sql = sql.replace("?", "%s")
        return sql

    def execute(self, sql, params=None):
        self._pending_rows = []
        if sql.strip().upper().startswith("PRAGMA TABLE_INFO("):
            table_name = sql[sql.find("(") + 1:sql.rfind(")")].strip().strip('"').strip("'")
            self._cursor.execute(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                (table_name.lower(),),
            )
            return self
        translated_sql = self._translate_sql(sql)
        translated_params = params or ()
        if translated_sql.lstrip().upper().startswith("INSERT") and "RETURNING" not in translated_sql.upper():
            translated_sql = f"{translated_sql.rstrip(';')} RETURNING id"
            self._cursor.execute(translated_sql, translated_params)
            rows = self._cursor.fetchall()
            self._pending_rows = self._wrap_rows(rows)
            self.lastrowid = self._pending_rows[0][0] if self._pending_rows else None
            return self
        self._cursor.execute(translated_sql, translated_params)
        self.lastrowid = None
        return self

    def fetchone(self):
        if self._pending_rows:
            return self._pending_rows.pop(0)
        row = self._cursor.fetchone()
        return self._wrap_row(row)

    def fetchall(self):
        if self._pending_rows:
            rows = self._pending_rows
            self._pending_rows = []
            return rows
        return self._wrap_rows(self._cursor.fetchall())

    def __getattr__(self, item):
        return getattr(self._cursor, item)


class PostgresConnectionWrapper:
    def __init__(self, connection):
        self._connection = connection
        self._is_postgres = True

    def cursor(self):
        return PostgresCursorWrapper(self._connection.cursor())

    def commit(self):
        return self._connection.commit()

    def close(self):
        return self._connection.close()

    def __getattr__(self, item):
        return getattr(self._connection, item)


class PooledPostgresConnectionWrapper(PostgresConnectionWrapper):
    def __init__(self, connection, pool_obj):
        super().__init__(connection)
        self._pool = pool_obj
        self._released = False

    def close(self):
        if not self._released:
            self._pool.putconn(self._connection)
            self._released = True


def init_postgres_pool():
    global POSTGRES_POOL
    if not USE_POSTGRES or psycopg2_pool is None or POSTGRES_POOL is not None:
        return
    POSTGRES_POOL = psycopg2_pool.ThreadedConnectionPool(
        1,
        5,
        DATABASE_URL,
    )


def disable_cloud_database():
    global DATABASE_URL, USE_POSTGRES
    DATABASE_URL = None
    USE_POSTGRES = False
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("SUPABASE_DB_URL", None)


def database_path():
    return os.environ.get("GYM_DB_PATH") or PRIMARY_DB


def connect_db(path=None):
    if USE_POSTGRES:
        if psycopg2 is None:
            raise RuntimeError("DATABASE_URL is set, but psycopg2-binary is not installed.")
        init_postgres_pool()
        if POSTGRES_POOL is not None:
            connection = POSTGRES_POOL.getconn()
            return PooledPostgresConnectionWrapper(connection, POSTGRES_POOL)
        connection = psycopg2.connect(DATABASE_URL)
        connection.autocommit = False
        return PostgresConnectionWrapper(connection)
    target = path or database_path()
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


def generate_member_code(member_id):
    return f"PGM{member_id:04d}"


def column_exists(cursor, table_name, column_name):
    if getattr(cursor, "_is_postgres", False):
        cursor.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
            (table_name.lower(), column_name),
        )
        return cursor.fetchone() is not None
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def initialize_database():
    if USE_POSTGRES:
        conn = None
        try:
            if psycopg2 is None:
                raise RuntimeError("DATABASE_URL is set, but psycopg2-binary is not installed.")
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS trainers(id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,phone TEXT NOT NULL,specialty TEXT,status TEXT DEFAULT 'active',created_date TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS inquiries(id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,phone TEXT NOT NULL,plan_interest TEXT NOT NULL,expected_join_date TEXT,status TEXT DEFAULT 'active',created_date TEXT,notes TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS members(id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,phone TEXT NOT NULL,plan_duration INTEGER,plan_name TEXT,start_date TEXT NOT NULL,expiry_date TEXT NOT NULL,fee_status TEXT DEFAULT 'paid',created_date TEXT,trainer_id INTEGER)")
            if not column_exists(cursor, "members", "member_code"):
                cursor.execute("ALTER TABLE members ADD COLUMN member_code TEXT")
            cursor.execute("CREATE TABLE IF NOT EXISTS payments(id BIGSERIAL PRIMARY KEY,member_id INTEGER NOT NULL,amount INTEGER NOT NULL,payment_date TEXT NOT NULL,payment_type TEXT DEFAULT 'monthly')")
            cursor.execute("CREATE TABLE IF NOT EXISTS renewal_reminders(id BIGSERIAL PRIMARY KEY,member_id INTEGER NOT NULL,reminder_date TEXT,message_sent INTEGER DEFAULT 0,reminder_type TEXT,created_date TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS attendance(id BIGSERIAL PRIMARY KEY,member_id INTEGER NOT NULL,attendance_date TEXT NOT NULL,check_in_time TEXT,check_out_time TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS admin_users(id BIGSERIAL PRIMARY KEY,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,full_name TEXT NOT NULL,created_date TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS customer_users(id BIGSERIAL PRIMARY KEY,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,full_name TEXT NOT NULL,status TEXT DEFAULT 'active',created_by_admin_id INTEGER,created_date TEXT)")
            cursor.execute("INSERT OR IGNORE INTO admin_users(username, password_hash, full_name, created_date) VALUES(%s, %s, %s, %s)", ("admin", generate_password_hash("admin123"), "Power Gym Admin", datetime.today().strftime("%Y-%m-%d")))
            cursor.execute("SELECT id FROM members WHERE member_code IS NULL OR member_code = ''")
            for row in cursor.fetchall():
                cursor.execute("UPDATE members SET member_code=%s WHERE id=%s", (generate_member_code(row["id"]), row["id"]))
            conn.commit()
            return
        except Exception as exc:
            print(f"Cloud database unavailable, falling back to local SQLite: {exc}")
            disable_cloud_database()
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
    for candidate in [database_path(), FALLBACK_DB]:
        try:
            if candidate == FALLBACK_DB:
                os.environ["GYM_DB_PATH"] = FALLBACK_DB
            conn = connect_db(candidate)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS trainers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT NOT NULL,specialty TEXT,status TEXT DEFAULT 'active',created_date TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS inquiries(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT NOT NULL,plan_interest TEXT NOT NULL,expected_join_date TEXT,status TEXT DEFAULT 'active',created_date TEXT,notes TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT NOT NULL,plan_duration INTEGER,plan_name TEXT,start_date TEXT NOT NULL,expiry_date TEXT NOT NULL,fee_status TEXT DEFAULT 'paid',created_date TEXT,trainer_id INTEGER)")
            if not column_exists(cursor, "members", "member_code"):
                cursor.execute("ALTER TABLE members ADD COLUMN member_code TEXT")
            cursor.execute("CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,member_id INTEGER NOT NULL,amount INTEGER NOT NULL,payment_date TEXT NOT NULL,payment_type TEXT DEFAULT 'monthly')")
            cursor.execute("CREATE TABLE IF NOT EXISTS renewal_reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,member_id INTEGER NOT NULL,reminder_date TEXT,message_sent INTEGER DEFAULT 0,reminder_type TEXT,created_date TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT,member_id INTEGER NOT NULL,attendance_date TEXT NOT NULL,check_in_time TEXT,check_out_time TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS admin_users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,full_name TEXT NOT NULL,created_date TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS customer_users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,full_name TEXT NOT NULL,status TEXT DEFAULT 'active',created_by_admin_id INTEGER,created_date TEXT)")
            cursor.execute("INSERT OR IGNORE INTO admin_users(username, password_hash, full_name, created_date) VALUES(?, ?, ?, ?)", ("admin", generate_password_hash("admin123"), "Power Gym Admin", datetime.today().strftime("%Y-%m-%d")))
            cursor.execute("SELECT id FROM members WHERE member_code IS NULL OR member_code = ''")
            for row in cursor.fetchall():
                cursor.execute("UPDATE members SET member_code=? WHERE id=?", (generate_member_code(row["id"]), row["id"]))
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError:
            try:
                conn.close()
            except Exception:
                pass
    raise sqlite3.OperationalError("Unable to initialize a writable SQLite database.")

def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not session.get("user_id") or not session.get("role"):
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                if session.get("role") == "customer":
                    return redirect(url_for("customer_portal"))
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped_view
    return decorator


def create_member(cursor, name, phone, plan_name, start_date, fee_status="paid", trainer_id=None):
    plan_duration = PLAN_DURATIONS.get(plan_name, 30)
    expiry_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=plan_duration)).strftime("%Y-%m-%d")
    today = datetime.today().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO members(name, phone, plan_duration, plan_name, start_date, expiry_date, fee_status, created_date, trainer_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, phone, plan_duration, plan_name, start_date, expiry_date, fee_status, today, trainer_id))
    member_id = cursor.lastrowid
    cursor.execute("UPDATE members SET member_code=? WHERE id=?", (generate_member_code(member_id), member_id))
    return member_id


def get_current_user():
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id or not role:
        return None
    conn = connect_db()
    cursor = conn.cursor()
    table = "admin_users" if role == "admin" else "customer_users"
    cursor.execute(f"SELECT * FROM {table} WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def build_whatsapp_link(phone, text):
    safe_phone = "".join([c for c in phone if c.isdigit()])
    if not safe_phone:
        return url_for("reminders")
    return f"https://wa.me/{safe_phone}?text={quote(text, safe='')}"


def reminder_message(member, message_type):
    if message_type == "expiry_1day":
        return f"Hello {member['name']}, your gym plan {member['plan_name']} expires tomorrow ({member['expiry_date']}). Please contact us to renew your membership."
    if message_type == "expiry_week":
        return f"Hello {member['name']}, your gym plan {member['plan_name']} will expire on {member['expiry_date']}. Please renew before it expires."
    return f"Hello {member['name']}, we have scheduled your plan renewal follow-up on the agreed date. Please contact us if you need help."


@app.context_processor
def inject_layout_context():
    return {"current_user": get_current_user(), "current_role": session.get("role")}


@app.route("/")
def home():
    if session.get("role") == "admin":
        return redirect(url_for("dashboard"))
    if session.get("role") == "customer":
        return redirect(url_for("customer_portal"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("role") == "admin":
        return redirect(url_for("dashboard"))
    if session.get("role") == "customer":
        return redirect(url_for("customer_portal"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE username=?", (username,))
        admin = cursor.fetchone()
        conn.close()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["user_id"] = admin["id"]
            session["role"] = "admin"
            flash("Admin login successful.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid admin username or password.", "error")
    return render_template("login.html")


@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():
    if session.get("role") == "customer":
        return redirect(url_for("customer_portal"))
    if session.get("role") == "admin":
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_users WHERE username=? AND status='active'", (username,))
        customer = cursor.fetchone()
        conn.close()
        if customer and check_password_hash(customer["password_hash"], password):
            session.clear()
            session["user_id"] = customer["id"]
            session["role"] = "customer"
            flash("Customer login successful.", "success")
            return redirect(url_for("customer_portal"))
        flash("Invalid customer username or password.", "error")
    return render_template("customer_login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required("admin")
def dashboard():
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    next7 = (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM inquiries WHERE expected_join_date BETWEEN ? AND ? AND status='active' ORDER BY expected_join_date ASC", (today, next7))
    hot_inquiries = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM inquiries WHERE status='active'")
    total_inquiries = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM members WHERE expiry_date >= ?", (today,))
    active_members = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM members WHERE expiry_date BETWEEN ? AND ? AND expiry_date >= ? ORDER BY expiry_date ASC", (today, next7, today))
    expiry_soon = cursor.fetchall()
    cursor.execute("SELECT * FROM members WHERE expiry_date < ? ORDER BY expiry_date DESC", (today,))
    expired_members = cursor.fetchall()
    cursor.execute("SELECT SUM(amount) FROM payments WHERE payment_date=?", (today,))
    revenue = cursor.fetchone()[0] or 0
    start_of_month = datetime.today().replace(day=1).strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(amount) FROM payments WHERE payment_date BETWEEN ? AND ?", (start_of_month, today))
    month_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM customer_users WHERE status='active'")
    active_customer_users = cursor.fetchone()[0]
    conn.close()
    return render_template("dashboard.html", hot_inquiries=hot_inquiries, total_inquiries=total_inquiries, active_members=active_members, expiry_soon=expiry_soon, expired_members=expired_members, revenue=revenue, month_revenue=month_revenue, active_customer_users=active_customer_users)


@app.route("/inquiries")
@login_required("admin")
def inquiries():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inquiries WHERE status='active' ORDER BY expected_join_date ASC")
    all_inquiries = cursor.fetchall()
    conn.close()
    return render_template("inquiries.html", inquiries=all_inquiries)


@app.route("/add_inquiry", methods=["GET", "POST"])
@login_required("admin")
def add_inquiry():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        plan = request.form["plan"]
        join_type = request.form["join_type"]
        join_date = request.form["join_date"]
        conn = connect_db()
        cursor = conn.cursor()
        today = datetime.today().strftime("%Y-%m-%d")
        if join_type == "direct":
            create_member(cursor, name, phone, plan, join_date, "paid")
        else:
            cursor.execute("INSERT INTO inquiries(name, phone, plan_interest, expected_join_date, status, created_date) VALUES(?, ?, ?, ?, ?, ?)", (name, phone, plan, join_date, "active", today))
        conn.commit()
        conn.close()
        return redirect("/inquiries" if join_type == "inquiry" else "/members")
    return render_template("add_inquiry.html")


@app.route("/convert_inquiry/<int:id>", methods=["POST"])
@login_required("admin")
def convert_inquiry(id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inquiries WHERE id=?", (id,))
    inquiry = cursor.fetchone()
    if inquiry:
        create_member(cursor, inquiry["name"], inquiry["phone"], inquiry["plan_interest"], datetime.today().strftime("%Y-%m-%d"), "paid")
        cursor.execute("UPDATE inquiries SET status='converted' WHERE id=?", (id,))
        conn.commit()
    conn.close()
    return redirect("/inquiries")


@app.route("/members")
@login_required("admin")
def members():
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    cursor.execute("SELECT m.*, t.name AS trainer_name FROM members m LEFT JOIN trainers t ON m.trainer_id = t.id WHERE m.expiry_date >= ? ORDER BY m.expiry_date ASC, m.name ASC", (today,))
    active_members = cursor.fetchall()
    conn.close()
    return render_template("members.html", members=active_members, today=today, tomorrow=tomorrow)


@app.route("/archive")
@login_required("admin")
def archive():
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM members WHERE expiry_date < ? ORDER BY expiry_date DESC", (today,))
    expired_members = cursor.fetchall()
    cursor.execute("SELECT * FROM inquiries WHERE status='converted' OR status='closed' ORDER BY created_date DESC")
    converted_inquiries = cursor.fetchall()
    conn.close()
    return render_template("archive.html", expired_members=expired_members, converted_inquiries=converted_inquiries)


@app.route("/trainers")
@login_required("admin")
def trainers_list():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trainers WHERE status='active' ORDER BY name")
    trainers = cursor.fetchall()
    conn.close()
    return render_template("trainers.html", trainers=trainers)


@app.route("/add_trainer", methods=["GET", "POST"])
@login_required("admin")
def add_trainer():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        specialty = request.form.get("specialty", "General")
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO trainers(name, phone, specialty, status, created_date) VALUES(?, ?, ?, ?, ?)", (name, phone, specialty, "active", datetime.today().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        return redirect("/trainers")
    return render_template("add_trainer.html")


@app.route("/new_member", methods=["GET", "POST"])
@login_required("admin")
def new_member():
    if request.method == "POST":
        conn = connect_db()
        cursor = conn.cursor()
        create_member(cursor, request.form["name"], request.form["phone"], request.form["plan_name"], request.form["start_date"], request.form.get("fee_status", "paid"), request.form.get("trainer_id") or None)
        conn.commit()
        conn.close()
        return redirect("/members")
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM trainers WHERE status='active' ORDER BY name")
    trainers = cursor.fetchall()
    conn.close()
    return render_template("new_member.html", trainers=trainers)


@app.route("/member/<int:id>")
@login_required("admin")
def member_detail(id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT m.*, t.name AS trainer_name, t.phone AS trainer_phone, t.specialty AS trainer_specialty FROM members m LEFT JOIN trainers t ON m.trainer_id = t.id WHERE m.id=?", (id,))
    member = cursor.fetchone()
    conn.close()
    if not member:
        return redirect("/members")
    return render_template("member_detail.html", member=member)


@app.route("/renew_member/<int:id>", methods=["GET", "POST"])
@login_required("admin")
def renew_member(id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (id,))
    member = cursor.fetchone()
    if request.method == "POST" and member:
        plan_name = request.form["plan_name"]
        new_start_date = request.form["start_date"]
        fee_status = request.form.get("fee_status", "paid")
        plan_duration = PLAN_DURATIONS.get(plan_name, 30)
        new_expiry_date = (datetime.strptime(new_start_date, "%Y-%m-%d") + timedelta(days=plan_duration)).strftime("%Y-%m-%d")
        cursor.execute("UPDATE members SET plan_name=?, plan_duration=?, start_date=?, expiry_date=?, fee_status=? WHERE id=?", (plan_name, plan_duration, new_start_date, new_expiry_date, fee_status, id))
        conn.commit()
        conn.close()
        return redirect(f"/member/{id}")
    conn.close()
    return render_template("renew_member.html", member=member)

@app.route("/attendance")
@login_required("admin")
def attendance():
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT a.*, m.name, m.member_code FROM attendance a JOIN members m ON a.member_id = m.id ORDER BY attendance_date DESC, check_in_time DESC")
    attendance_records = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date = ?", (today,))
    today_count = cursor.fetchone()[0]
    conn.close()
    return render_template("attendance.html", attendance_records=attendance_records, today=today, today_count=today_count)


@app.route("/record_attendance/<int:member_id>", methods=["GET", "POST"])
@login_required("admin")
def record_attendance(member_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = cursor.fetchone()
    if not member:
        conn.close()
        return redirect("/members")
    if request.method == "POST":
        attendance_date = request.form["attendance_date"]
        check_in_time = request.form["check_in_time"]
        check_out_time = request.form.get("check_out_time")
        cursor.execute("SELECT id FROM attendance WHERE member_id=? AND attendance_date=?", (member_id, attendance_date))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE attendance SET check_in_time=?, check_out_time=? WHERE id=?", (check_in_time, check_out_time or None, existing["id"]))
        else:
            cursor.execute("INSERT INTO attendance(member_id, attendance_date, check_in_time, check_out_time) VALUES(?, ?, ?, ?)", (member_id, attendance_date, check_in_time, check_out_time or None))
        conn.commit()
        conn.close()
        return redirect("/attendance")
    conn.close()
    return render_template("record_attendance.html", member=member, today=datetime.today().strftime("%Y-%m-%d"))


@app.route("/payments")
@login_required("admin")
def payments():
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT p.*, m.name FROM payments p JOIN members m ON p.member_id = m.id ORDER BY payment_date DESC, p.id DESC")
    payment_rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM payments")
    payment_count = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM payments WHERE payment_date = ?", (today,))
    today_revenue = cursor.fetchone()[0] or 0
    week_start = (datetime.today() - timedelta(days=datetime.today().weekday())).strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(amount) FROM payments WHERE payment_date BETWEEN ? AND ?", (week_start, today))
    week_revenue = cursor.fetchone()[0] or 0
    start_of_month = datetime.today().replace(day=1).strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(amount) FROM payments WHERE payment_date BETWEEN ? AND ?", (start_of_month, today))
    month_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM payments")
    total_revenue = cursor.fetchone()[0] or 0
    conn.close()
    return render_template("payments.html", payments=payment_rows, today=today, today_revenue=today_revenue, week_revenue=week_revenue, month_revenue=month_revenue, total_revenue=total_revenue, payment_count=payment_count)


@app.route("/record_payment/<int:member_id>", methods=["GET", "POST"])
@login_required("admin")
def record_payment(member_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = cursor.fetchone()
    if not member:
        conn.close()
        return redirect("/members")
    if request.method == "POST":
        amount = request.form.get("amount")
        payment_type = request.form.get("payment_type", "membership")
        payment_date = request.form.get("payment_date")
        if not amount or not payment_date:
            conn.close()
            return redirect(f"/record_payment/{member_id}")
        cursor.execute("INSERT INTO payments(member_id, amount, payment_date, payment_type) VALUES(?, ?, ?, ?)", (member_id, int(amount), payment_date, payment_type))
        if int(amount) > 0:
            cursor.execute("UPDATE members SET fee_status='paid' WHERE id=?", (member_id,))
        conn.commit()
        conn.close()
        return redirect("/payments")
    conn.close()
    return render_template("record_payment.html", member=member, today=datetime.today().strftime("%Y-%m-%d"))


@app.route("/reminders")
@login_required("admin")
def reminders():
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    next7 = (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM members WHERE expiry_date BETWEEN ? AND ? ORDER BY expiry_date ASC", (today, next7))
    expiry_this_week = cursor.fetchall()
    cursor.execute("SELECT * FROM members WHERE expiry_date = ?", (tomorrow,))
    expiry_tomorrow = cursor.fetchall()
    cursor.execute("SELECT rr.*, m.name, m.phone, m.plan_name, m.expiry_date FROM renewal_reminders rr JOIN members m ON rr.member_id = m.id WHERE rr.reminder_date = ? ORDER BY rr.reminder_date ASC", (today,))
    scheduled_reminders_today = cursor.fetchall()
    cursor.execute("SELECT rr.*, m.name, m.phone, m.plan_name, m.expiry_date FROM renewal_reminders rr JOIN members m ON rr.member_id = m.id WHERE rr.reminder_date > ? ORDER BY rr.reminder_date ASC", (today,))
    scheduled_reminders_future = cursor.fetchall()
    conn.close()
    return render_template("reminders.html", expiry_this_week=expiry_this_week, expiry_tomorrow=expiry_tomorrow, scheduled_reminders_today=scheduled_reminders_today, scheduled_reminders_future=scheduled_reminders_future, today=today, tomorrow=tomorrow)


@app.route("/auto_schedule/<message_type>")
@login_required("admin")
def auto_schedule(message_type):
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    next7 = (datetime.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    if message_type == "expiry_1day":
        cursor.execute("SELECT * FROM members WHERE expiry_date = ?", (tomorrow,))
        members = cursor.fetchall()
    elif message_type == "expiry_week":
        cursor.execute("SELECT * FROM members WHERE expiry_date BETWEEN ? AND ?", (today, next7))
        members = cursor.fetchall()
    else:
        conn.close()
        return redirect(url_for("reminders"))
    for member in members:
        reminder_date = tomorrow if message_type == "expiry_1day" else member["expiry_date"]
        cursor.execute("SELECT COUNT(*) FROM renewal_reminders WHERE member_id = ? AND reminder_date = ? AND reminder_type = ?", (member["id"], reminder_date, message_type))
        if not cursor.fetchone()[0]:
            cursor.execute("INSERT INTO renewal_reminders(member_id, reminder_date, reminder_type, created_date) VALUES(?, ?, ?, ?)", (member["id"], reminder_date, message_type, today))
    conn.commit()
    conn.close()
    return redirect(url_for("reminders"))


@app.route("/delete_reminder/<int:reminder_id>")
@login_required("admin")
def delete_reminder(reminder_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM renewal_reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("reminders"))


@app.route("/set_renewal/<int:member_id>", methods=["GET", "POST"])
@login_required("admin")
def set_renewal(member_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = cursor.fetchone()
    if request.method == "POST" and member:
        cursor.execute("INSERT INTO renewal_reminders(member_id, reminder_date, reminder_type, created_date) VALUES(?, ?, ?, ?)", (member_id, request.form["reminder_date"], request.form.get("reminder_type", "followup"), datetime.today().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        return redirect("/reminders")
    conn.close()
    return render_template("set_renewal.html", member=member, today=datetime.today().strftime("%Y-%m-%d"))


@app.route("/mark_reminder_sent/<int:reminder_id>")
@login_required("admin")
def mark_reminder_sent(reminder_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE renewal_reminders SET message_sent = 1 WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("reminders"))


@app.route("/whatsapp/<int:member_id>/<message_type>")
@login_required("admin")
def whatsapp(member_id, message_type):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = cursor.fetchone()
    conn.close()
    if not member:
        return redirect(url_for("reminders"))
    return redirect(build_whatsapp_link(member["phone"], reminder_message(member, message_type)))

@app.route("/admin/customer_accounts", methods=["GET", "POST"])
@login_required("admin")
def customer_accounts():
    conn = connect_db()
    cursor = conn.cursor()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if full_name and username and password:
            try:
                cursor.execute("INSERT INTO customer_users(username, password_hash, full_name, status, created_by_admin_id, created_date) VALUES(?, ?, ?, 'active', ?, ?)", (username, generate_password_hash(password), full_name, session.get("user_id"), datetime.today().strftime("%Y-%m-%d")))
                conn.commit()
                flash("Customer account created successfully.", "success")
            except DB_INTEGRITY_ERRORS:
                flash("That customer username already exists.", "error")
        else:
            flash("Fill in full name, username, and password.", "error")
    cursor.execute("SELECT cu.*, au.full_name AS admin_name FROM customer_users cu LEFT JOIN admin_users au ON cu.created_by_admin_id = au.id ORDER BY cu.created_date DESC, cu.id DESC")
    customers = cursor.fetchall()
    conn.close()
    return render_template("customer_accounts.html", customers=customers)


@app.route("/customer")
@login_required("customer")
def customer_portal():
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT a.attendance_date, a.check_in_time, m.name, m.member_code FROM attendance a JOIN members m ON a.member_id = m.id ORDER BY a.id DESC LIMIT 8")
    recent_scans = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date=?", (today,))
    today_count = cursor.fetchone()[0]
    conn.close()
    return render_template("customer_portal.html", today=today, today_count=today_count, recent_scans=recent_scans)


@app.route("/customer/scan", methods=["POST"])
@login_required("customer")
def customer_scan():
    raw_code = request.form.get("member_code", "").strip().upper()
    member_code = "".join(ch for ch in raw_code if ch.isalnum())
    if not member_code:
        flash("Enter or scan a valid member code.", "error")
        return redirect(url_for("customer_portal"))
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE member_code=?", (member_code,))
    member = cursor.fetchone()
    if not member:
        conn.close()
        flash("Member code not found.", "error")
        return redirect(url_for("customer_portal"))

        
    today = datetime.today().strftime("%Y-%m-%d")
    if member["expiry_date"] < today:
        conn.close()
        flash(f"{member['name']} has an expired membership.", "error")
        return redirect(url_for("customer_portal"))
    cursor.execute("SELECT id FROM attendance WHERE member_id=? AND attendance_date=?", (member["id"], today))
    if cursor.fetchone():
        conn.close()
        flash(f"{member['name']} is already checked in today.", "info")
        return redirect(url_for("customer_portal"))
    current_time = datetime.now().strftime("%H:%M")
    cursor.execute("INSERT INTO attendance(member_id, attendance_date, check_in_time, check_out_time) VALUES(?, ?, ?, ?)", (member["id"], today, current_time, None))
    conn.commit()
    conn.close()
    flash(f"Attendance marked for {member['name']} at {current_time}.", "success")
    return redirect(url_for("customer_portal"))


initialize_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
