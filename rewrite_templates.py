from pathlib import Path

base_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Gym Management{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      color-scheme: light;
      color: #0f172a;
      background: #eef2ff;
      font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      --surface: #ffffff;
      --surface-muted: #f8fafc;
      --border: #e2e8f0;
      --primary: #2563eb;
      --primary-strong: #1d4ed8;
      --success: #16a34a;
      --info: #0ea5e9;
      --warning: #f59e0b;
      --danger: #dc2626;
      --radius: 18px;
      --shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; min-height: 100%; background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%); }
    body { color: #0f172a; font-size: 16px; line-height: 1.6; }
    a { color: inherit; text-decoration: none; }
    .page { max-width: 1180px; margin: 0 auto; padding: 24px 20px 40px; }
    .topbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 22px; }
    .topbar h1 { margin: 0; font-size: clamp(2rem, 2.4vw, 2.8rem); letter-spacing: -0.04em; }
    .topbar p { margin: 10px 0 0; color: #475569; max-width: 720px; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; }
    .button, .button-ghost, .button-small { display: inline-flex; align-items: center; justify-content: center; border-radius: 999px; padding: 12px 18px; font-weight: 600; transition: transform .18s ease, background .18s ease, box-shadow .18s ease; }
    .button { background: var(--primary); color: white; box-shadow: 0 14px 32px rgba(37, 99, 235, 0.18); }
    .button:hover { transform: translateY(-1px); }
    .button-ghost { background: var(--surface); border: 1px solid var(--border); color: #334155; }
    .button-small { background: var(--surface); border: 1px solid var(--border); color: #334155; padding: 10px 14px; }
    .nav { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }
    .nav a { padding: 12px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; text-align: center; color: #334155; }
    .nav a:hover { background: #eff6ff; border-color: #c7d2fe; }
    .panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; }
    .grid-2, .stats-grid { display: grid; gap: 18px; }
    .grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .stats-grid { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; box-shadow: 0 18px 38px rgba(15, 23, 42, 0.06); }
    .card strong { display: block; margin-bottom: 10px; color: #0f172a; }
    .section { margin-top: 24px; }
    .section h2, .section h3 { margin: 0 0 18px; color: #0f172a; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 650px; }
    th, td { padding: 16px 14px; border-bottom: 1px solid var(--border); }
    th { background: #eff6ff; color: #0f172a; text-align: left; font-weight: 600; }
    tr:last-child td { border-bottom: none; }
    tr:hover { background: #f8fafc; }
    label { display: block; margin-bottom: 8px; font-weight: 600; color: #334155; }
    input, select, textarea { width: 100%; padding: 14px 16px; border-radius: 14px; border: 1px solid var(--border); background: var(--surface); font: inherit; color: #0f172a; }
    textarea { resize: vertical; min-height: 120px; }
    form > * + * { margin-top: 16px; }
    .field-row { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .form-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
    .badge { display: inline-flex; gap: 6px; padding: 8px 12px; border-radius: 999px; background: #eff6ff; color: #0f172a; font-size: 0.93rem; }
    .badge.expired { background: #fee2e2; color: #b91c1c; }
    .badge.warning { background: #fef3c7; color: #92400e; }
    .badge.success { background: #dcfce7; color: #166534; }
    .note { color: #475569; font-size: 0.95rem; }
    @media (max-width: 880px) { .grid-2, .stats-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="page">
    <div class="topbar">
      <div>
        <p class="eyebrow">Gym Studio</p>
        <h1>{% block heading %}Gym Management{% endblock %}</h1>
        <p class="description">{% block description %}Manage leads, members, reminders, attendance, and revenue from one dashboard.{% endblock %}</p>
      </div>
      <div class="actions">{% block actions %}{% endblock %}</div>
    </div>
    <div class="nav">
      <a href="/">Dashboard</a>
      <a href="/inquiries">Inquiries</a>
      <a href="/members">Members</a>
      <a href="/trainers">Trainers</a>
      <a href="/attendance">Attendance</a>
      <a href="/payments">Payments</a>
      <a href="/reminders">Reminders</a>
      <a href="/archive">Archive</a>
    </div>
    <main>{% block content %}{% endblock %}</main>
  </div>
</body>
</html>
'''

pages = {
    'dashboard.html': '''{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block heading %}Gym Management Dashboard{% endblock %}
{% block description %}Quick view of leads, members, renewals, attendance, and revenue.{% endblock %}
{% block actions %}
  <a class="button" href="/add_inquiry">Add Lead</a>
  <a class="button" href="/new_member">Register Member</a>
  <a class="button" href="/reminders">Reminders</a>
  <a class="button" href="/attendance">Attendance</a>
  <a class="button" href="/payments">Payments</a>
{% endblock %}
{% block content %}
  <div class="stats-grid">
    <div class="card"><strong>Active Members</strong><div style="font-size:2rem; margin-top:10px;">{{ active_members }}</div></div>
    <div class="card"><strong>Active Inquiries</strong><div style="font-size:2rem; margin-top:10px;">{{ total_inquiries }}</div></div>
    <div class="card"><strong>Revenue Today</strong><div style="font-size:2rem; margin-top:10px;">₹{{ revenue }}</div></div>
    <div class="card"><strong>This Month</strong><div style="font-size:2rem; margin-top:10px;">₹{{ month_revenue }}</div></div>
  </div>
  <div class="section panel">
    <h3>Hot Inquiries (Next 7 days)</h3>
    {% if hot_inquiries %}
      {% for inquiry in hot_inquiries %}
        <div class="card item hot"><strong>{{ inquiry['name'] }}</strong><br><span class="note">{{ inquiry['plan_interest'] }} · Expected join: {{ inquiry['expected_join_date'] }}</span></div>
      {% endfor %}
    {% else %}
      <p class="note">No inquiries joining this week.</p>
    {% endif %}
  </div>
  <div class="section panel">
    <h3>Expiring Soon (Next 7 days)</h3>
    {% if expiry_soon %}
      {% for member in expiry_soon %}
        <div class="card item expiry"><strong>{{ member['name'] }}</strong><br><span class="note">{{ member['plan_name'] }} · Expires {{ member['expiry_date'] }}</span></div>
      {% endfor %}
    {% else %}
      <p class="note">No members expiring this week.</p>
    {% endif %}
  </div>
  <div class="section panel">
    <h3>Expired Members</h3>
    {% if expired_members %}
      {% for member in expired_members %}
        <div class="card item expired"><strong>{{ member['name'] }}</strong><br><span class="note">Expired {{ member['expiry_date'] }}</span></div>
      {% endfor %}
    {% else %}
      <p class="note">No expired members.</p>
    {% endif %}
  </div>
{% endblock %}
''',
    'inquiries.html': '''{% extends "base.html" %}
{% block title %}Inquiries{% endblock %}
{% block heading %}Active Inquiries{% endblock %}
{% block description %}Track leads and convert them into members quickly.{% endblock %}
{% block actions %}<a class="button" href="/add_inquiry">Add Inquiry</a>{% endblock %}
{% block content %}
  <div class="panel table-wrap">
    {% if inquiries %}
      <table>
        <thead>
          <tr><th>Name</th><th>Phone</th><th>Plan</th><th>Expected Join</th><th>Status</th><th>Action</th></tr>
        </thead>
        <tbody>
          {% for inquiry in inquiries %}
          <tr>
            <td>{{ inquiry['name'] }}</td>
            <td>{{ inquiry['phone'] }}</td>
            <td>{{ inquiry['plan_interest'] }}</td>
            <td>{{ inquiry['expected_join_date'] }}</td>
            <td>{{ inquiry['status'] }}</td>
            <td>
              <form method="POST" action="/convert_inquiry/{{ inquiry['id'] }}">
                <input type="hidden" name="plan_duration" value="30">
                <button class="button-small" type="submit">Convert</button>
              </form>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="note">No active inquiries found.</p>
    {% endif %}
  </div>
{% endblock %}
''',
    'add_inquiry.html': '''{% extends "base.html" %}
{% block title %}Add Inquiry or Member{% endblock %}
{% block heading %}Add Inquiry or New Member{% endblock %}
{% block description %}Capture a lead or register a direct member with the same form.{% endblock %}
{% block content %}
  <div class="panel">
    <form method="POST">
      <div class="field-row">
        <label>Name<input type="text" name="name" required></label>
        <label>Phone<input type="tel" name="phone" required></label>
      </div>
      <label>Plan Interested In
        <select name="plan" required>
          <option value="">Select Plan</option>
          <option value="Basic (1 month)">Basic (1 month)</option>
          <option value="Premium (3 months)">Premium (3 months)</option>
          <option value="Elite (6 months)">Elite (6 months)</option>
          <option value="Annual">Annual</option>
        </select>
      </label>
      <label>Type
        <select name="join_type" id="join_type" onchange="updateForm()" required>
          <option value="inquiry">Inquiry (Not joining now)</option>
          <option value="direct">Direct Member (Joining now)</option>
        </select>
      </label>
      <label>Joining Date<input type="date" name="join_date" required></label>
      <div id="duration-group" style="display:none;"><label>Plan Duration (days)<input type="number" name="plan_duration" min="1" value="30"></label></div>
      <div class="form-actions"><button class="button" type="submit">Save</button><a class="button-ghost" href="/">Cancel</a></div>
    </form>
  </div>
  <script>
    function updateForm() {
      document.getElementById('duration-group').style.display = document.getElementById('join_type').value === 'direct' ? 'block' : 'none';
    }
  </script>
{% endblock %}
''',
    'new_member.html': '''{% extends "base.html" %}
{% block title %}Register New Member{% endblock %}
{% block heading %}Register New Member{% endblock %}
{% block description %}Add a member and assign a trainer if needed.{% endblock %}
{% block content %}
  <div class="panel">
    <form method="POST">
      <label>Name<input type="text" name="name" required></label>
      <label>Phone<input type="tel" name="phone" required></label>
      <label>Plan<select name="plan_name" required>
          <option value="">Select Plan</option>
          <option value="Basic (1 month)">Basic (1 month)</option>
          <option value="Premium (3 months)">Premium (3 months)</option>
          <option value="Elite (6 months)">Elite (6 months)</option>
          <option value="Annual">Annual</option>
        </select></label>
      <label>Start Date<input type="date" name="start_date" required></label>
      <label>Trainer<select name="trainer_id"><option value="">No trainer</option>{% for trainer in trainers %}<option value="{{ trainer['id'] }}">{{ trainer['name'] }}</option>{% endfor %}</select></label>
      <label>Fee Status<select name="fee_status"><option value="paid">Paid</option><option value="pending">Pending</option></select></label>
      <div class="form-actions"><button class="button" type="submit">Register Member</button><a class="button-ghost" href="/members">Back</a></div>
    </form>
  </div>
{% endblock %}
''',
    'members.html': '''{% extends "base.html" %}
{% block title %}Members{% endblock %}
{% block heading %}Active Members{% endblock %}
{% block description %}View current members, trainers, plans, and quick actions.{% endblock %}
{% block actions %}<a class="button" href="/new_member">Add Member</a>{% endblock %}
{% block content %}
  <div class="panel table-wrap">
    {% if members %}
      <table>
        <thead><tr><th>Name</th><th>Phone</th><th>Plan</th><th>Start</th><th>Expiry</th><th>Trainer</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>
          {% for member in members %}
          <tr>
            <td>{{ member['name'] }}</td>
            <td>{{ member['phone'] }}</td>
            <td>{{ member['plan_name'] }}</td>
            <td>{{ member['start_date'] }}</td>
            <td>{{ member['expiry_date'] }}</td>
            <td>{{ member['trainer_id'] or '-' }}</td>
            <td><span class="badge {% if member['expiry_date'] < today %}expired{% elif member['expiry_date'] <= tomorrow %}warning{% else %}success{% endif %}">{{ member['fee_status'] }}</span></td>
            <td><a class="button-small" href="/member/{{ member['id'] }}">View</a></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="note">No active members found yet.</p>
    {% endif %}
  </div>
{% endblock %}
''',
    'member_detail.html': '''{% extends "base.html" %}
{% block title %}Member Details{% endblock %}
{% block heading %}Member Details{% endblock %}
{% block description %}Review member data, trainer info, and renewal options.{% endblock %}
{% block actions %}
  <a class="button" href="/renew_member/{{ member['id'] }}">Renew Plan</a>
  <a class="button" href="/record_attendance/{{ member['id'] }}">Attendance</a>
  <a class="button" href="/record_payment/{{ member['id'] }}">Record Payment</a>
{% endblock %}
{% block content %}
  <div class="panel grid-2">
    <div class="card"><strong>Name</strong>{{ member['name'] }}</div>
    <div class="card"><strong>Phone</strong>{{ member['phone'] }}</div>
    <div class="card"><strong>Plan</strong>{{ member['plan_name'] }}</div>
    <div class="card"><strong>Duration</strong>{{ member['plan_duration'] }} days</div>
    <div class="card"><strong>Start Date</strong>{{ member['start_date'] }}</div>
    <div class="card"><strong>Expiry Date</strong>{{ member['expiry_date'] }}</div>
    <div class="card"><strong>Fee Status</strong>{{ member['fee_status'] }}</div>
    <div class="card"><strong>Joined</strong>{{ member['created_date'] }}</div>
  </div>
  {% if trainer %}
  <div class="section panel">
    <h3>Trainer</h3>
    <p>{{ trainer['name'] }} · {{ trainer['specialty'] }}</p>
    <p class="note">Phone: {{ trainer['phone'] }}</p>
  </div>
  {% endif %}
{% endblock %}
''',
    'payments.html': '''{% extends "base.html" %}
{% block title %}Payments{% endblock %}
{% block heading %}Payments Overview{% endblock %}
{% block description %}Track revenue totals and record new payments for members.{% endblock %}
{% block actions %}<a class="button" href="/payments">Refresh</a>{% endblock %}
{% block content %}
  <div class="stats-grid">
    <div class="card"><strong>Today</strong>₹{{ today_revenue }}</div>
    <div class="card"><strong>This Week</strong>₹{{ week_revenue }}</div>
    <div class="card"><strong>This Month</strong>₹{{ month_revenue }}</div>
    <div class="card"><strong>Total</strong>₹{{ total_revenue }}</div>
  </div>
  <div class="section panel table-wrap">
    {% if payments %}
      <table>
        <thead><tr><th>Date</th><th>Member</th><th>Amount</th><th>Type</th><th>Action</th></tr></thead>
        <tbody>
          {% for payment in payments %}
          <tr>
            <td>{{ payment['payment_date'] }}</td>
            <td>{{ payment['name'] }}</td>
            <td>₹{{ payment['amount'] }}</td>
            <td>{{ payment['payment_type'] }}</td>
            <td><a class="button-small" href="/record_payment/{{ payment['member_id'] }}">New Payment</a></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="note">No payments recorded yet.</p>
    {% endif %}
  </div>
{% endblock %}
''',
    'attendance.html': '''{% extends "base.html" %}
{% block title %}Attendance{% endblock %}
{% block heading %}Attendance Records{% endblock %}
{% block description %}Record member check-ins and monitor today's gym traffic.{% endblock %}
{% block content %}
  <div class="panel">
    <p class="badge">Checked in today: {{ today_count }}</p>
  </div>
  <div class="section panel table-wrap">
    {% if attendance_records %}
      <table>
        <thead><tr><th>Date</th><th>Member</th><th>Check-in</th><th>Check-out</th><th>Action</th></tr></thead>
        <tbody>
          {% for record in attendance_records %}
          <tr>
            <td>{{ record['attendance_date'] }}</td>
            <td>{{ record['name'] }}</td>
            <td>{{ record['check_in_time'] }}</td>
            <td>{{ record['check_out_time'] or '-' }}</td>
            <td><a class="button-small" href="/record_attendance/{{ record['member_id'] }}">New</a></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="note">No attendance records yet.</p>
    {% endif %}
  </div>
{% endblock %}
''',
    'trainers.html': '''{% extends "base.html" %}
{% block title %}Trainers{% endblock %}
{% block heading %}Trainers{% endblock %}
{% block description %}Manage your gym staff and assign them to members.{% endblock %}
{% block actions %}<a class="button" href="/add_trainer">Add Trainer</a>{% endblock %}
{% block content %}
  <div class="section panel table-wrap">
    {% if trainers %}
      <table>
        <thead><tr><th>Name</th><th>Phone</th><th>Specialty</th></tr></thead>
        <tbody>
          {% for trainer in trainers %}
          <tr><td>{{ trainer['name'] }}</td><td>{{ trainer['phone'] }}</td><td>{{ trainer['specialty'] }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="note">No trainers added yet.</p>
    {% endif %}
  </div>
{% endblock %}
''',
    'add_trainer.html': '''{% extends "base.html" %}
{% block title %}Add Trainer{% endblock %}
{% block heading %}Add Trainer{% endblock %}
{% block description %}Add a trainer to your gym roster.{% endblock %}
{% block content %}
  <div class="panel">
    <form method="POST">
      <label>Name<input type="text" name="name" required></label>
      <label>Phone<input type="tel" name="phone" required></label>
      <label>Specialty<input type="text" name="specialty" value="General"></label>
      <div class="form-actions"><button class="button" type="submit">Save Trainer</button><a class="button-ghost" href="/trainers">Cancel</a></div>
    </form>
  </div>
{% endblock %}
''',
    'renew_member.html': '''{% extends "base.html" %}
{% block title %}Renew Member{% endblock %}
{% block heading %}Renew Membership{% endblock %}
{% block description %}Update the member's plan and extend their gym access.{% endblock %}
{% block content %}
  <div class="panel">
    <form method="POST">
      <label>Plan<select name="plan_name" required>
          <option value="Basic (1 month)">Basic (1 month)</option>
          <option value="Premium (3 months)">Premium (3 months)</option>
          <option value="Elite (6 months)">Elite (6 months)</option>
          <option value="Annual">Annual</option>
        </select></label>
      <label>Start Date<input type="date" name="start_date" required value="{{ member['start_date'] }}"></label>
      <label>Fee Status<select name="fee_status"><option value="paid">Paid</option><option value="pending">Pending</option></select></label>
      <div class="form-actions"><button class="button" type="submit">Renew</button><a class="button-ghost" href="/member/{{ member['id'] }}">Cancel</a></div>
    </form>
  </div>
{% endblock %}
''',
    'set_renewal.html': '''{% extends "base.html" %}
{% block title %}Set Renewal Reminder{% endblock %}
{% block heading %}Set Renewal Reminder{% endblock %}
{% block description %}Schedule a follow-up for member renewal or expiry outreach.{% endblock %}
{% block content %}
  <div class="panel">
    <form method="POST">
      <label>Member<input type="text" value="{{ member['name'] }}" disabled></label>
      <label>Reminder Date<input type="date" name="reminder_date" value="{{ today }}" required></label>
      <label>Reminder Type<select name="reminder_type">
          <option value="followup">Owner Follow-up</option>
          <option value="expiry_week">Expiry Week Reminder</option>
          <option value="expiry_1day">One-Day Reminder</option>
        </select></label>
      <div class="form-actions"><button class="button" type="submit">Save Reminder</button><a class="button-ghost" href="/reminders">Cancel</a></div>
    </form>
  </div>
{% endblock %}
''',
    'record_attendance.html': '''{% extends "base.html" %}
{% block title %}Record Attendance{% endblock %}
{% block heading %}Record Attendance{% endblock %}
{% block description %}Check a member in and record the session time.{% endblock %}
{% block content %}
  <div class="panel">
    <form method="POST">
      <label>Member<input type="text" value="{{ member['name'] }}" disabled></label>
      <label>Date<input type="date" name="attendance_date" value="{{ today }}" required></label>
      <label>Check-in Time<input type="time" name="check_in_time" required></label>
      <label>Check-out Time<input type="time" name="check_out_time"></label>
      <div class="form-actions"><button class="button" type="submit">Save Attendance</button><a class="button-ghost" href="/attendance">Cancel</a></div>
    </form>
  </div>
{% endblock %}
''',
    'record_payment.html': '''{% extends "base.html" %}
{% block title %}Record Payment{% endblock %}
{% block heading %}Record Payment{% endblock %}
{% block description %}Log a payment for the member and update revenue totals.{% endblock %}
{% block content %}
  <div class="panel">
    <form method="POST">
      <label>Member<input type="text" value="{{ member['name'] }}" disabled></label>
      <label>Payment Date<input type="date" name="payment_date" value="{{ today }}" required></label>
      <label>Amount<input type="number" name="amount" min="0" required></label>
      <label>Payment Type<select name="payment_type"><option value="membership">Membership</option><option value="renewal">Renewal</option><option value="other">Other</option></select></label>
      <div class="form-actions"><button class="button" type="submit">Save Payment</button><a class="button-ghost" href="/payments">Cancel</a></div>
    </form>
  </div>
{% endblock %}
''',
    'reminders.html': '''{% extends "base.html" %}
{% block title %}Reminders{% endblock %}
{% block heading %}Renewal & Expiry Reminders{% endblock %}
{% block description %}Send today’s reminders or schedule follow-ups for members due soon.{% endblock %}
{% block actions %}<a class="button" href="/set_renewal/{{ reminders[0]['member_id'] if reminders else 0 }}">Set Renewal</a>{% endblock %}
{% block content %}
  <div class="section panel">
    <h3>Expiry This Week</h3>
    <div class="form-actions">
      <a class="button-small" href="/auto_schedule/expiry_week">Auto-schedule Week</a>
    </div>
    {% if expiry_this_week %}
      {% for member in expiry_this_week %}
        <div class="card item expiry"><strong>{{ member['name'] }}</strong><br><span class="note">{{ member['plan_name'] }} · Expires {{ member['expiry_date'] }}</span><br><a class="button-small" href="/whatsapp/{{ member['id'] }}/expiry_week">WhatsApp</a><a class="button-small" href="/set_renewal/{{ member['id'] }}">Reminder</a></div>
      {% endfor %}
    {% else %}
      <p class="note">No members expiring this week.</p>
    {% endif %}
  </div>
  <div class="section panel">
    <h3>Expiry Tomorrow</h3>
    <div class="form-actions">
      <a class="button-small" href="/auto_schedule/expiry_1day">Auto-schedule Tomorrow</a>
    </div>
    {% if expiry_tomorrow %}
      {% for member in expiry_tomorrow %}
        <div class="card item expiry"><strong>{{ member['name'] }}</strong><br><span class="note">{{ member['plan_name'] }} · Expires {{ member['expiry_date'] }}</span><br><a class="button-small" href="/whatsapp/{{ member['id'] }}/expiry_1day">WhatsApp</a><a class="button-small" href="/set_renewal/{{ member['id'] }}">Reminder</a></div>
      {% endfor %}
    {% else %}
      <p class="note">No members expiring tomorrow.</p>
    {% endif %}
  </div>
  <div class="section panel">
    <h3>Today's Scheduled Reminders</h3>
    {% if scheduled_reminders_today %}
      {% for reminder in scheduled_reminders_today %}
        <div class="card item"><strong>{{ reminder['name'] }}</strong><br><span class="note">{{ reminder['reminder_date'] }} · {{ reminder['reminder_type'] }}</span><br><a class="button-small" href="/whatsapp/{{ reminder['member_id'] }}/{{ reminder['reminder_type'] }}">WhatsApp</a><a class="button-small" href="/mark_reminder_sent/{{ reminder['id'] }}">Mark Sent</a><a class="button-small" href="/delete_reminder/{{ reminder['id'] }}">Delete</a></div>
      {% endfor %}
    {% else %}
      <p class="note">No reminders scheduled for today.</p>
    {% endif %}
  </div>
  <div class="section panel">
    <h3>Upcoming Scheduled Reminders</h3>
    {% if scheduled_reminders_future %}
      {% for reminder in scheduled_reminders_future %}
        <div class="card item"><strong>{{ reminder['name'] }}</strong><br><span class="note">{{ reminder['reminder_date'] }} · {{ reminder['reminder_type'] }}</span><br><a class="button-small" href="/whatsapp/{{ reminder['member_id'] }}/{{ reminder['reminder_type'] }}">WhatsApp</a><a class="button-small" href="/mark_reminder_sent/{{ reminder['id'] }}">Mark Sent</a><a class="button-small" href="/delete_reminder/{{ reminder['id'] }}">Delete</a></div>
      {% endfor %}
    {% else %}
      <p class="note">No upcoming reminders scheduled.</p>
    {% endif %}
  </div>
{% endblock %}
''',
    'archive.html': '''{% extends "base.html" %}
{% block title %}Archive{% endblock %}
{% block heading %}Archive{% endblock %}
{% block description %}Review expired members and converted inquiries.{% endblock %}
{% block content %}
  <div class="section panel">
    <h3>Expired Members</h3>
    {% if expired_members %}
      <div class="table-wrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Plan</th><th>Expiry</th></tr></thead><tbody>{% for member in expired_members %}<tr><td>{{ member['name'] }}</td><td>{{ member['phone'] }}</td><td>{{ member['plan_name'] }}</td><td>{{ member['expiry_date'] }}</td></tr>{% endfor %}</tbody></table></div>
    {% else %}
      <p class="note">No expired members in archive.</p>
    {% endif %}
  </div>
  <div class="section panel">
    <h3>Converted Inquiries</h3>
    {% if converted_inquiries %}
      <div class="table-wrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Plan</th><th>Created</th></tr></thead><tbody>{% for inquiry in converted_inquiries %}<tr><td>{{ inquiry['name'] }}</td><td>{{ inquiry['phone'] }}</td><td>{{ inquiry['plan_interest'] }}</td><td>{{ inquiry['created_date'] }}</td></tr>{% endfor %}</tbody></table></div>
    {% else %}
      <p class="note">No converted inquiries yet.</p>
    {% endif %}
  </div>
{% endblock %}
'''
}

for name, content in pages.items():
    (Path('templates') / name).write_text(content, encoding='utf-8')

print('templates rewritten')
