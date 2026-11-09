import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Trainers table (for Module 2)
cursor.execute("""
CREATE TABLE IF NOT EXISTS trainers(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
phone TEXT NOT NULL,
specialty TEXT,
status TEXT DEFAULT 'active',
created_date TEXT
)
""")

# Inquiries table - for people who expressed interest but not joining now
cursor.execute("""
CREATE TABLE IF NOT EXISTS inquiries(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
phone TEXT NOT NULL,
plan_interest TEXT NOT NULL,
expected_join_date TEXT,
status TEXT DEFAULT 'active',
created_date TEXT,
notes TEXT
)
""")

# Members table - for active gym members
cursor.execute("""
CREATE TABLE IF NOT EXISTS members(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
phone TEXT NOT NULL,
plan_duration INTEGER,
plan_name TEXT,
start_date TEXT NOT NULL,
expiry_date TEXT NOT NULL,
fee_status TEXT DEFAULT 'paid',
created_date TEXT,
trainer_id INTEGER
)
""")

# Payments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS payments(
id INTEGER PRIMARY KEY AUTOINCREMENT,
member_id INTEGER NOT NULL,
amount INTEGER NOT NULL,
payment_date TEXT NOT NULL,
payment_type TEXT DEFAULT 'monthly'
)
""")

# Renewal Reminders table (for Module 3)
cursor.execute("""
CREATE TABLE IF NOT EXISTS renewal_reminders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
member_id INTEGER NOT NULL,
reminder_date TEXT,
message_sent INTEGER DEFAULT 0,
reminder_type TEXT,
created_date TEXT
)
""")

# Attendance table (for Module 4)
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance(
id INTEGER PRIMARY KEY AUTOINCREMENT,
member_id INTEGER NOT NULL,
attendance_date TEXT NOT NULL,
check_in_time TEXT,
check_out_time TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully")