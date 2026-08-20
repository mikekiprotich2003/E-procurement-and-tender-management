from flask import Flask, render_template, request, redirect, session, Response, url_for
from scipy import io
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename, send_from_directory
import sqlite3
import os
import csv
from datetime import datetime
from functools import wraps
from flask import redirect, url_for

def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def log_activity(user_id, role, action):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO activity_log (user_id, role, action) VALUES (?, ?, ?)",
              (user_id, role, action))
    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = "secret123"

# --- Upload folder config ---
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# --- Helpers ---
def get_db():
    return sqlite3.connect("database.db")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def log_activity(user, role, action, db_path="database.db"):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO activity_log (user, role, action, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user, role, action, datetime.now()))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error logging activity: {e}")
    finally:
        conn.close()



@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form.get("role", "supplier")

        hashed_pw = generate_password_hash(password)

        conn = get_db()
        conn.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                     (name,email,hashed_pw,role))
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
  
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        conn.row_factory = sqlite3.Row  # dict-like access
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # Save session info
            session["user"] = user["name"]
            session["role"] = user["role"] if "role" in user.keys() else "supplier"



            # Redirect based on role
            if session["role"] == "admin":
                return redirect("/admin_dashboard")
            elif session["role"] == "procurement_officer":
                return redirect("/admin_dashboard")
            elif session["role"] == "supplier":
                return redirect("/supplier_dashboard")
            elif session["role"] == "auditor":
                return redirect("/auditor_dashboard")
            else:
                return redirect("/dashboard")  # fallback
        else:
            return  redirect(url_for("login"))

        return redirect(url_for("login"))
        print("Logged in as:", session["user"], "Role:", session["role"])


    return render_template("login.html")


@app.route('/activity_log')
def activity_log():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT user, role, action, timestamp FROM activity_log ORDER BY timestamp DESC")
    logs = cur.fetchall()
    conn.close()
    return render_template("activity_log.html", logs=logs)



@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    tenders = conn.execute("SELECT * FROM tenders").fetchall()

    bids_by_tender = {}
    lowest_bid_by_tender = {}

    for tender in tenders:
        tender_id = tender[0]
        bids = conn.execute(
            "SELECT supplier_name, amount FROM bids WHERE tender_id=?",
            (tender_id,)
        ).fetchall()
        bids_by_tender[tender_id] = bids

        if bids:
            lowest_bid = min(bids, key=lambda b: b[1])
            lowest_bid_by_tender[tender_id] = lowest_bid
        else:
            lowest_bid_by_tender[tender_id] = None

    conn.close()

    return render_template("dashboard.html",
                           user=session["user"],
                           tenders=tenders,
                           bids_by_tender=bids_by_tender,
                           lowest_bid_by_tender=lowest_bid_by_tender)


@app.route('/create_tender', methods=['GET', 'POST'])
@role_required('admin', 'procurement_officer')
def create_tender():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline = request.form['deadline']
        file = request.files.get('document')

        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Insert into database
        conn = get_db()
        conn.execute("""
            INSERT INTO tenders (title, description, deadline, document)
            VALUES (?, ?, ?, ?)
        """, (title, description, deadline, filename))
        conn.commit()
        conn.close()

        # Log activity
        log_activity(session["user"], session["role"], f"Created tender '{title}'")

        return redirect('/admin_dashboard')

    return render_template('tender.html')

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/bid/<int:tender_id>", methods=["GET", "POST"])
def bid(tender_id):
    if request.method == "POST":
        amount = request.form["amount"]
        file = request.files.get("document")
        filename = None
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db()
        conn.execute("""
            INSERT INTO bids (tender_id, supplier_name, amount, document, status)
            VALUES (?, ?, ?, ?, ?)
        """, (tender_id, session["user"], amount, filename, "Pending"))
        conn.commit()



        log_activity(session["user"], session["role"], f"Submitted bid for tender {tender_id}")
        conn.close()
        return redirect("/dashboard")

    conn = get_db()
    tender = conn.execute("SELECT * FROM tenders WHERE id=?", (tender_id,)).fetchone()
    conn.close()
    return render_template("bid.html", tender=tender)

@app.route('/view_document/<filename>')
def view_document(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

from flask import send_from_directory

@app.route('/download/<filename>')
def download(filename):
    print("Downloading:", filename)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)



@app.route("/admin_dashboard")
def admin_panel():
    if "user" not in session or session.get("role") != "admin":
        return redirect("/dashboard")

    conn = get_db()
    tenders = conn.execute("SELECT * FROM tenders").fetchall()

    bids_by_tender = {}
    lowest_bid_by_tender = {}

    for tender in tenders:
        tender_id = tender[0]
        bids = conn.execute(
            """
SELECT id, supplier_name, amount, document, status
FROM bids
WHERE tender_id = ?
""",
            (tender_id,)
        ).fetchall()
        bids_by_tender[tender_id] = bids

        if bids:
            lowest_bid = min(bids, key=lambda b: b[1])
            lowest_bid_by_tender[tender_id] = lowest_bid
        else:
            lowest_bid_by_tender[tender_id] = None

    conn.close()

    return render_template("admin_dashboard.html",
                           user=session["user"],
                           tenders=tenders,
                           bids_by_tender=bids_by_tender,
                           lowest_bid_by_tender=lowest_bid_by_tender)

@app.route("/supplier_dashboard")
@role_required('supplier')
def supplier_dashboard():
    if "user" not in session or session.get("role") != "supplier":
        return redirect("/dashboard")

    conn = get_db()
    tenders = conn.execute("SELECT * FROM tenders").fetchall()
    my_bids = conn.execute("SELECT * FROM bids WHERE supplier_name=?", (session["user"],)).fetchall()

    # Find tenders supplier has already bid on
    bid_tender_ids = {bid[1] for bid in my_bids}
    open_tenders = [t for t in tenders if t[0] not in bid_tender_ids]

    conn.close()

    return render_template("supplier_dashboard.html",
                           user=session["user"],
                           my_bids=my_bids,
                           open_tenders=open_tenders)

@app.route("/my_bids")
def my_bids():
    if "user" not in session or session.get("role") != "supplier":
        return redirect("/dashboard")

    conn = get_db()
    bids = conn.execute("SELECT * FROM bids WHERE supplier_name=?", (session["user"],)).fetchall()
    conn.close()

    return render_template("my_bids.html", bids=bids)

@app.route("/auditor_dashboard")
@role_required('auditor')
def auditor_dashboard():
    if "user" not in session or session.get("role") != "auditor":
        return redirect("/dashboard")

    conn = get_db()
    tenders = conn.execute("SELECT * FROM tenders").fetchall()
    bids = conn.execute("SELECT * FROM bids").fetchall()
    logs = conn.execute("SELECT * FROM activity_log ORDER BY timestamp DESC").fetchall()
    conn.close()

    return render_template("auditor_dashboard.html",
                           user=session["user"],
                           tenders=tenders,
                           bids=bids,
                           logs=logs)

@app.route("/procurement_officer_dashboard")
def procurement_officer_dashboard():
    if "user" not in session or session.get("role") != "procurement_officer":
        return redirect("/dashboard")
    return render_template("procurement_officer_dashboard.html", user=session["user"])


import csv
from flask import Response


@app.route('/export_logs')
def export_logs():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT user, role, action, timestamp FROM activity_log")
    logs = cur.fetchall()
    conn.close()

    output = []
    output.append(['User', 'Role', 'Action', 'Timestamp'])
    output.extend(logs)

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerows(output)

    return Response(si.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=activity_logs.csv"})


@app.route('/mark_winner/<int:bid_id>', methods=['POST'])
def mark_winner(bid_id):
    if "user" not in session or session.get("role") != "admin":
        return redirect("/dashboard")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Get tender_id for this bid
    c.execute("SELECT tender_id FROM bids WHERE id = ?", (bid_id,))
    tender = c.fetchone()
    if not tender:
        conn.close()
        return redirect('/admin_dashboard')

    tender_id = tender[0]

    # First mark all bids for this tender as 'Outbid'
    c.execute("UPDATE bids SET status = 'Outbid' WHERE tender_id = ?", (tender_id,))

    # Then mark the selected bid as 'Winner'
    c.execute("UPDATE bids SET status = 'Winner' WHERE id = ?", (bid_id,))

    conn.commit()
    conn.close()

    # Redirect back to admin dashboard to see the updated status
    return redirect('/admin_dashboard')




@app.route("/remove_tender/<int:tender_id>", methods=["POST"])
def remove_tender(tender_id):
    # Only allow admins
    if "role" not in session or session["role"] != "admin":
        return redirect("/login")

    conn = get_db()
    conn.execute("DELETE FROM tenders WHERE id=?", (tender_id,))
    conn.execute("DELETE FROM bids WHERE tender_id=?", (tender_id,))
    conn.commit()

    # Log activity (use session["user"], not user_id)
    log_activity(session["user"], session["role"], f"Removed tender {tender_id}")

    conn.close()
    return redirect("/admin_dashboard")

@app.route('/remove_bid/<int:bid_id>', methods=['POST'])
def remove_bid(bid_id):
    # Only allow admins
    if "user" not in session or session.get("role") != "admin":
        return redirect("/dashboard")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Delete the bid by ID
    c.execute("DELETE FROM bids WHERE id = ?", (bid_id,))

    conn.commit()
    conn.close()

    # Redirect back to admin dashboard
    return redirect('/admin_dashboard')



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)