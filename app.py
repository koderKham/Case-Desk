import os
import sqlite3
import json
import secrets
import hashlib
import hmac
import uuid
from datetime import datetime, date
from functools import wraps
from pathlib import Path

from flask import (
    Flask, abort, flash, g, redirect, render_template,
    request, send_from_directory, session, url_for
)
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE = INSTANCE_DIR / "case_manager.db"

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "txt",
    "png", "jpg", "jpeg"
}

INTAKE_TYPES = {
    "estate-planning": {
        "name": "Estate Planning",
        "matter_type": "Estate Planning",
        "description": "Wills, trusts, powers of attorney, health-care directives, asset planning, and family objectives.",
        "sections": [
            ("Family & Household", [
                ("date_of_birth", "Date of Birth", "date"),
                ("marital_status", "Marital Status", "select", ["Single", "Married", "Divorced", "Widowed", "Domestic Partnership", "Other"]),
                ("spouse_name", "Spouse / Partner Name", "text"),
                ("children", "Children / Descendants (names, ages, relationships)", "textarea"),
                ("minor_children", "Minor Children", "textarea"),
                ("dependents", "Other Dependents", "textarea"),
                ("blended_family", "Blended Family / Prior Marriage Concerns", "textarea"),
            ]),
            ("Existing Planning", [
                ("existing_documents", "Existing Will, Trust, POA, Health-Care Documents", "textarea"),
                ("existing_plan_date", "Date of Most Recent Estate Plan", "date"),
                ("existing_attorney", "Attorney Who Prepared Existing Plan", "text"),
                ("prior_gifts", "Prior Gifts / Transfers That May Affect Planning", "textarea"),
            ]),
            ("Planning Goals", [
                ("planning_goals", "Primary Estate Planning Goals", "textarea"),
                ("beneficiaries", "Intended Beneficiaries", "textarea"),
                ("specific_gifts", "Specific Gifts / Bequests", "textarea"),
                ("fiduciaries", "Preferred Personal Representative / Trustee / Agent", "textarea"),
                ("guardians", "Preferred Guardians for Minor Children", "textarea"),
                ("disinheritance", "Anyone to Exclude or Limit", "textarea"),
                ("charitable_gifts", "Charitable Giving Goals", "textarea"),
                ("special_needs", "Special-Needs Beneficiary or Supplemental-Needs Concerns", "textarea"),
            ]),
            ("Assets & Liabilities", [
                ("real_property", "Real Property (addresses, ownership, mortgages)", "textarea"),
                ("business_interests", "Businesses / LLCs / Partnerships", "textarea"),
                ("bank_investment", "Bank / Brokerage / Investment Accounts", "textarea"),
                ("retirement", "Retirement Accounts", "textarea"),
                ("life_insurance", "Life Insurance / Annuities", "textarea"),
                ("digital_assets", "Digital Assets / Cryptocurrency", "textarea"),
                ("debts", "Significant Debts / Liabilities", "textarea"),
                ("estimated_estate_value", "Approximate Total Estate Value", "text"),
                ("out_of_state_property", "Property Outside Florida", "textarea"),
            ]),
            ("Health, Incapacity & Other Concerns", [
                ("health_care_choices", "Health-Care Surrogate / Living Will Preferences", "textarea"),
                ("durable_poa_choices", "Durable Power of Attorney Preferences", "textarea"),
                ("long_term_care", "Long-Term Care / Medicaid Planning Concerns", "textarea"),
                ("tax_concerns", "Estate / Gift / Income Tax Concerns", "textarea"),
                ("other_concerns", "Other Family, Asset-Protection, or Planning Concerns", "textarea"),
            ]),
        ],
    },
    "personal-injury": {
        "name": "Personal Injury",
        "matter_type": "Personal Injury",
        "description": "Accident facts, injuries, treatment, insurance, witnesses, damages, and preservation issues.",
        "sections": [
            ("Incident", [
                ("date_of_birth", "Date of Birth", "date"),
                ("incident_date", "Incident Date", "date"),
                ("incident_time", "Approximate Time", "time"),
                ("incident_type", "Type of Incident", "select", ["Auto Collision", "Premises Liability", "Slip / Trip and Fall", "Negligent Security", "Dog Bite", "Medical Negligence", "Assault / Battery", "Other"]),
                ("incident_location", "Incident Location", "text"),
                ("incident_narrative", "Describe What Happened", "textarea"),
                ("fault_theory", "Why Do You Believe the Other Party Was at Fault?", "textarea"),
                ("police_agency", "Police / Reporting Agency", "text"),
                ("report_number", "Police / Incident Report Number", "text"),
                ("citations", "Citations / Charges Issued", "textarea"),
            ]),
            ("Injuries & Medical Treatment", [
                ("injuries", "Injuries / Symptoms", "textarea"),
                ("emergency_treatment", "Ambulance / ER / Hospital Treatment", "textarea"),
                ("providers", "Current Medical Providers", "textarea"),
                ("future_treatment", "Recommended / Upcoming Treatment or Surgery", "textarea"),
                ("prior_injuries", "Prior Similar Injuries / Conditions", "textarea"),
                ("health_insurance", "Health Insurance / Medicare / Medicaid", "textarea"),
            ]),
            ("Insurance & Property Damage", [
                ("client_auto_insurance", "Client Auto Carrier / Policy / Claim No.", "textarea"),
                ("pip_um_coverage", "PIP / UM-UIM Coverage Information", "textarea"),
                ("adverse_insurance", "At-Fault Party Carrier / Policy / Claim No.", "textarea"),
                ("vehicle_info", "Vehicle Year / Make / Model", "text"),
                ("property_damage", "Property Damage / Repair / Total Loss", "textarea"),
                ("photos_video", "Photos / Video / Dashcam / Surveillance Available", "textarea"),
            ]),
            ("Witnesses & Damages", [
                ("witnesses", "Witnesses and Contact Information", "textarea"),
                ("lost_wages", "Employment / Lost Wages / Missed Work", "textarea"),
                ("out_of_pocket", "Out-of-Pocket Expenses", "textarea"),
                ("other_losses", "Other Damages / Losses", "textarea"),
                ("liens", "Known Medical Liens / Letters of Protection", "textarea"),
            ]),
            ("Representation & Preservation", [
                ("prior_attorney", "Prior Attorney / Law Firm", "text"),
                ("communications", "Statements to Insurers / Recorded Statements", "textarea"),
                ("evidence_to_preserve", "Evidence That Should Be Preserved Immediately", "textarea"),
                ("deadlines", "Known Deadlines / Notices / Statute Concerns", "textarea"),
            ]),
        ],
    },
    "probate": {
        "name": "Probate",
        "matter_type": "Probate",
        "description": "Decedent, will, heirs, assets, creditors, administration status, and potential probate disputes.",
        "sections": [
            ("Decedent", [
                ("decedent_name", "Decedent's Full Legal Name", "text"),
                ("date_of_death", "Date of Death", "date"),
                ("domicile", "Decedent's County / State of Domicile", "text"),
                ("last_address", "Decedent's Last Address", "text"),
                ("relationship_to_decedent", "Your Relationship to Decedent", "text"),
                ("death_certificate", "Death Certificate Available?", "select", ["Yes", "No", "Ordered / Pending"]),
            ]),
            ("Will & Family", [
                ("will_exists", "Did Decedent Leave a Will?", "select", ["Yes", "No", "Unknown"]),
                ("original_will_location", "Location of Original Will / Codicils", "textarea"),
                ("will_date", "Date of Will", "date"),
                ("named_pr", "Personal Representative Named in Will", "text"),
                ("proposed_pr", "Proposed Personal Representative", "text"),
                ("surviving_spouse", "Surviving Spouse", "text"),
                ("heirs_beneficiaries", "Heirs / Beneficiaries (names, relationships, addresses)", "textarea"),
                ("minor_beneficiaries", "Minor / Incapacitated Beneficiaries", "textarea"),
            ]),
            ("Estate Assets", [
                ("homestead", "Florida Homestead / Primary Residence", "textarea"),
                ("other_real_estate", "Other Real Property", "textarea"),
                ("bank_accounts", "Bank / Investment Accounts", "textarea"),
                ("retirement_insurance", "Retirement / Life Insurance / Annuities", "textarea"),
                ("vehicles", "Vehicles / Boats / Other Titled Property", "textarea"),
                ("business_interests", "Business / LLC / Partnership Interests", "textarea"),
                ("personal_property", "Significant Personal Property", "textarea"),
                ("estimated_estate_value", "Approximate Probate Estate Value", "text"),
            ]),
            ("Debts & Administration", [
                ("creditors", "Known Creditors / Debts", "textarea"),
                ("mortgages_foreclosure", "Mortgage / Foreclosure / Property Preservation Issues", "textarea"),
                ("taxes", "Known Tax Issues", "textarea"),
                ("probate_opened", "Has a Probate Case Already Been Opened?", "select", ["Yes", "No", "Unknown"]),
                ("case_number", "Existing Probate Case Number", "text"),
                ("court", "Court / County", "text"),
                ("current_pr", "Current Personal Representative", "text"),
                ("current_counsel", "Current / Prior Probate Counsel", "text"),
            ]),
            ("Disputes & Urgent Issues", [
                ("will_dispute", "Will Contest / Undue Influence / Capacity Concerns", "textarea"),
                ("pr_dispute", "Personal Representative Removal / Misconduct Concerns", "textarea"),
                ("family_dispute", "Family / Beneficiary Disputes", "textarea"),
                ("missing_assets", "Missing / Transferred / Disputed Assets", "textarea"),
                ("urgent_deadlines", "Hearings, Foreclosure, Creditor, or Other Urgent Deadlines", "textarea"),
            ]),
        ],
    },
    "criminal": {
        "name": "Criminal Defense",
        "matter_type": "Criminal Defense",
        "description": "Charges, arrest and custody, bond, evidence, statements, searches, witnesses, defenses, and collateral consequences.",
        "sections": [
            ("Case & Custody", [
                ("date_of_birth", "Date of Birth", "date"),
                ("case_number", "Case Number", "text"),
                ("charges", "Charges / Alleged Offenses", "textarea"),
                ("arrest_date", "Arrest Date", "date"),
                ("arresting_agency", "Arresting / Investigating Agency", "text"),
                ("court", "Court / County", "text"),
                ("judge", "Judge", "text"),
                ("custody_status", "Custody Status", "select", ["In Custody", "Released on Bond", "Pretrial Release", "Notice to Appear", "Warrant / Not Yet Arrested", "Other"]),
                ("bond", "Bond Amount / Hold / Release Conditions", "textarea"),
                ("next_court_date", "Next Court Date", "datetime-local"),
            ]),
            ("Incident & Client Account", [
                ("incident_date", "Incident Date", "date"),
                ("incident_location", "Incident Location", "text"),
                ("client_account", "Client's Account of What Happened", "textarea"),
                ("alleged_victim", "Alleged Victim / Complaining Witness", "text"),
                ("relationship_to_victim", "Relationship to Alleged Victim", "text"),
                ("co_defendants", "Co-Defendants / Other Suspects", "textarea"),
                ("defense_witnesses", "Defense Witnesses / Contact Information", "textarea"),
            ]),
            ("Statements, Search & Evidence", [
                ("statements", "Statements Made to Police / Detectives / Others", "textarea"),
                ("miranda", "Miranda Warnings / Request for Counsel", "textarea"),
                ("searches", "Searches of Person, Vehicle, Home, Phone, or Property", "textarea"),
                ("warrants", "Search / Arrest Warrants or Warrant Applications", "textarea"),
                ("video_evidence", "Bodycam / Surveillance / Cellphone / Social Media Evidence", "textarea"),
                ("physical_evidence", "Physical / DNA / Fingerprint / Firearm / Forensic Evidence", "textarea"),
                ("discovery_status", "Discovery Received / Missing Evidence", "textarea"),
            ]),
            ("Defenses & Injury", [
                ("self_defense", "Self-Defense / Defense of Others / Stand Your Ground Facts", "textarea"),
                ("alibi", "Alibi / Misidentification Facts", "textarea"),
                ("client_injuries", "Client Injuries / Medical Treatment", "textarea"),
                ("victim_condition", "Observed Condition of Alleged Victim", "textarea"),
                ("other_defenses", "Other Defense Facts / Exculpatory Evidence", "textarea"),
            ]),
            ("Background & Consequences", [
                ("prior_record", "Prior Arrests / Convictions / Withholds", "textarea"),
                ("supervision", "Probation / Community Control / Pretrial / Parole Status", "textarea"),
                ("employment", "Employment / School", "textarea"),
                ("family_ties", "Family / Community Ties", "textarea"),
                ("immigration", "Immigration / Non-Citizen Consequences to Flag", "textarea"),
                ("professional_license", "Professional License / Employment Consequences", "textarea"),
                ("prior_attorney", "Prior / Current Attorney", "text"),
                ("client_goal", "Client's Primary Goal / Immediate Concern", "textarea"),
            ]),
        ],
    },
}

INTAKE_STATUSES = ["New", "Under Review", "Converted", "Declined", "Closed"]

COMMON_INTAKE_FIELDS = [
    ("first_name", "First Name", "text"),
    ("last_name", "Last Name", "text"),
    ("email", "Email", "email"),
    ("phone", "Phone", "tel"),
    ("preferred_contact", "Preferred Contact", "select", ["Phone", "Email", "Text Message"]),
    ("address", "Street Address", "text"),
    ("city", "City", "text"),
    ("state", "State", "text"),
    ("zip_code", "ZIP Code", "text"),
    ("referred_by", "How Were You Referred to the Firm?", "text"),
    ("conflict_names", "Other Parties / Names for Conflict Check", "textarea"),
    ("urgency", "Urgency / Immediate Deadlines", "textarea"),
]

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("CASE_MANAGER_SECRET_KEY", "dev-change-this-secret-key"),
    MAX_CONTENT_LENGTH=25 * 1024 * 1024,
    DATABASE=str(DATABASE),
    UPLOAD_FOLDER=str(UPLOAD_DIR),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)



def generate_password_hash(password, iterations=600_000):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def check_password_hash(stored, password):
    try:
        algorithm, iterations, salt, expected = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


# ---------------------------
# Database helpers
# ---------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = BASE_DIR / "schema.sql"
    db.executescript(schema_path.read_text(encoding="utf-8"))
    migrate_clients_to_people(db)
    db.commit()


PERSON_ROLES = (
    "Client", "Heir", "Interested Person", "Witness", "Decedent",
    "Beneficiary", "Personal Representative", "Opposing Party", "Expert",
)


def migrate_clients_to_people(db):
    """Wrap every legacy client in a Person record without changing matter FKs."""
    db.execute(
        """INSERT INTO persons
           (client_id,person_type,first_name,last_name,email,phone,address,city,state,
            zip_code,notes,created_at,updated_at)
           SELECT c.id,'Individual',c.first_name,c.last_name,c.email,c.phone,c.address,
                  c.city,c.state,c.zip_code,c.notes,c.created_at,c.updated_at
           FROM clients c
           WHERE NOT EXISTS (SELECT 1 FROM persons p WHERE p.client_id=c.id)"""
    )
    db.execute(
        """INSERT OR IGNORE INTO person_roles (person_id,role)
           SELECT id,'Client' FROM persons WHERE client_id IS NOT NULL"""
    )


def selected_person_roles():
    roles = [role for role in PERSON_ROLES if role in request.form.getlist("roles")]
    for role in (item.strip() for item in request.form.get("custom_roles", "").split(",")):
        if role and len(role) <= 80 and role not in roles:
            roles.append(role)
    return roles


def sync_person_roles(db, person_id, roles):
    db.execute("DELETE FROM person_roles WHERE person_id=?", (person_id,))
    db.executemany(
        "INSERT INTO person_roles (person_id,role) VALUES (?,?)",
        [(person_id, role) for role in roles],
    )


def person_form_fields():
    person_type = request.form.get("person_type", "Individual")
    if person_type not in ("Individual", "Business"):
        abort(400, description="Invalid contact type.")
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    organization_name = request.form.get("organization_name", "").strip()
    if person_type == "Individual" and (not first_name or not last_name):
        raise ValueError("First and last name are required for an individual.")
    if person_type == "Business" and not organization_name:
        raise ValueError("Business name is required for a business.")
    return (
        person_type, organization_name, first_name, last_name,
        request.form.get("email", "").strip(), request.form.get("phone", "").strip(),
        request.form.get("address", "").strip(), request.form.get("city", "").strip(),
        request.form.get("state", "").strip(), request.form.get("zip_code", "").strip(),
        request.form.get("notes", "").strip(),
    )


def client_fields_from_person(fields):
    person_type, organization_name, first_name, last_name, *contact = fields
    if person_type == "Business":
        return (organization_name, "(Business)", *contact)
    return (first_name, last_name, *contact)


def create_client_identity(db, fields):
    db.execute(
        """INSERT INTO clients
           (first_name,last_name,email,phone,address,city,state,zip_code,notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        client_fields_from_person(fields),
    )
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def seed_db():
    db = get_db()
    existing = db.execute("SELECT id FROM users LIMIT 1").fetchone()
    if existing:
        return

    pw_hash = generate_password_hash("ChangeMe123!")
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Firm Administrator", "admin@example.com", pw_hash),
    )

    db.execute(
        """INSERT INTO clients
           (first_name,last_name,email,phone,address,city,state,zip_code,notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            "Jordan", "Smith", "jordan@example.com", "954-555-0101",
            "100 Las Olas Blvd", "Fort Lauderdale", "FL", "33301",
            "Demo client record."
        ),
    )
    client_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    migrate_clients_to_people(db)

    db.execute(
        """INSERT INTO matters
           (client_id, case_number, title, matter_type, court, judge, status,
            opened_date, next_hearing, description, opposing_counsel)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            client_id, "26-000123CF10A", "State v. Jordan Smith",
            "Criminal Defense", "17th Judicial Circuit - Broward County",
            "Hon. Demo Judge", "Active", date.today().isoformat(),
            "2026-09-02T09:00",
            "Demo criminal defense matter used to show the interface.",
            "Office of the State Attorney"
        ),
    )
    matter_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    db.execute(
        """INSERT INTO tasks (matter_id,title,description,due_date,priority,status,assigned_to)
           VALUES (?,?,?,?,?,?,?)""",
        (
            matter_id, "Review discovery", "Review body camera and reports.",
            "2026-08-21", "High", "Open", "Firm Administrator"
        ),
    )
    db.execute(
        """INSERT INTO events (matter_id,title,event_type,start_at,location,description)
           VALUES (?,?,?,?,?,?)""",
        (
            matter_id, "Status Conference", "Hearing", "2026-09-02T09:00",
            "Broward County Courthouse", "Appear in person."
        ),
    )
    db.execute(
        """INSERT INTO notes (matter_id,body,created_by)
           VALUES (?,?,?)""",
        (
            matter_id, "Client intake completed. Initial strategy meeting held.",
            "Firm Administrator"
        ),
    )
    db.execute(
        """INSERT INTO time_entries
           (matter_id,work_date,hours,description,billable,rate)
           VALUES (?,?,?,?,?,?)""",
        (
            matter_id, date.today().isoformat(), 1.5,
            "Initial case review and client conference", 1, 450.00
        ),
    )
    db.commit()


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Database initialized.")


@app.cli.command("seed-db")
def seed_db_command():
    seed_db()
    print("Database seeded.")


# ---------------------------
# Security / auth helpers
# ---------------------------

def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def csrf_field():
    return f'<input type="hidden" name="_csrf_token" value="{csrf_token()}">'


@app.context_processor
def inject_helpers():
    return {
        "csrf_field": csrf_field,
        "today": date.today().isoformat(),
    }


@app.before_request
def csrf_protect():
    if request.method == "POST":
        expected = session.get("_csrf_token")
        supplied = request.form.get("_csrf_token")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            abort(400, description="Invalid CSRF token.")


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped_view


@app.before_request
def load_logged_in_user():
    g.user = None
    if "user_id" in session:
        g.user = get_db().execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------
# Authentication
# ---------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            csrf_token()
            return redirect(request.args.get("next") or url_for("dashboard"))

    csrf_token()
    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------
# Dashboard / search
# ---------------------------

@app.route("/")
@login_required
def dashboard():
    db = get_db()
    stats = {
        "active_matters": db.execute(
            "SELECT COUNT(*) FROM matters WHERE status = 'Active'"
        ).fetchone()[0],
        "people": db.execute("SELECT COUNT(*) FROM persons").fetchone()[0],
        "open_tasks": db.execute(
            "SELECT COUNT(*) FROM tasks WHERE status != 'Completed'"
        ).fetchone()[0],
        "hours_month": db.execute(
            """SELECT COALESCE(SUM(hours),0) FROM time_entries
               WHERE substr(work_date,1,7)=substr(date('now'),1,7)"""
        ).fetchone()[0],
        "new_intakes": db.execute(
            "SELECT COUNT(*) FROM intake_submissions WHERE status = 'New'"
        ).fetchone()[0],
    }

    tasks = db.execute(
        """SELECT t.*, m.title AS matter_title
           FROM tasks t
           JOIN matters m ON m.id=t.matter_id
           WHERE t.status != 'Completed'
           ORDER BY
             CASE t.priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Normal' THEN 3 ELSE 4 END,
             COALESCE(t.due_date,'9999-12-31')
           LIMIT 8"""
    ).fetchall()

    events = db.execute(
        """SELECT e.*, m.title AS matter_title
           FROM events e
           JOIN matters m ON m.id=e.matter_id
           WHERE datetime(e.start_at) >= datetime('now','-1 day')
           ORDER BY datetime(e.start_at)
           LIMIT 8"""
    ).fetchall()

    recent_matters = db.execute(
        """SELECT m.*, CASE WHEN p.person_type='Business' THEN p.organization_name
                             ELSE p.first_name || ' ' || p.last_name END AS client_name
           FROM matters m
           JOIN persons p ON p.client_id=m.client_id
           ORDER BY m.updated_at DESC
           LIMIT 6"""
    ).fetchall()

    recent_intakes = db.execute(
        """SELECT * FROM intake_submissions
           ORDER BY datetime(submitted_at) DESC, id DESC
           LIMIT 5"""
    ).fetchall()

    return render_template(
        "dashboard.html",
        stats=stats,
        tasks=tasks,
        events=events,
        recent_matters=recent_matters,
        recent_intakes=recent_intakes,
        intake_types=INTAKE_TYPES,
    )


@app.get("/search")
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    results = {"people": [], "matters": [], "notes": [], "intakes": []}

    if q:
        like = f"%{q}%"
        db = get_db()
        results["people"] = db.execute(
            """SELECT p.*, GROUP_CONCAT(pr.role, ', ') AS roles
               FROM persons p LEFT JOIN person_roles pr ON pr.person_id=p.id
               WHERE p.first_name LIKE ? OR p.last_name LIKE ? OR p.organization_name LIKE ?
                  OR p.email LIKE ? OR p.phone LIKE ?
               GROUP BY p.id
               ORDER BY CASE WHEN p.person_type='Business' THEN p.organization_name ELSE p.last_name END,
                        p.first_name LIMIT 25""",
            (like, like, like, like, like),
        ).fetchall()
        results["matters"] = db.execute(
            """SELECT m.*, CASE WHEN p.person_type='Business' THEN p.organization_name
                                  ELSE p.first_name || ' ' || p.last_name END AS client_name
               FROM matters m JOIN persons p ON p.client_id=m.client_id
               WHERE m.title LIKE ? OR m.case_number LIKE ? OR m.matter_type LIKE ?
                  OR m.court LIKE ? OR m.description LIKE ?
               ORDER BY m.updated_at DESC LIMIT 25""",
            (like, like, like, like, like),
        ).fetchall()
        results["notes"] = db.execute(
            """SELECT n.*, m.title AS matter_title
               FROM notes n JOIN matters m ON m.id=n.matter_id
               WHERE n.body LIKE ?
               ORDER BY n.created_at DESC LIMIT 25""",
            (like,),
        ).fetchall()
        results["intakes"] = db.execute(
            """SELECT * FROM intake_submissions
               WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ?
                  OR conflict_names LIKE ? OR urgency LIKE ? OR data_json LIKE ?
               ORDER BY datetime(submitted_at) DESC LIMIT 25""",
            (like, like, like, like, like, like, like),
        ).fetchall()

    return render_template("search.html", q=q, results=results, intake_types=INTAKE_TYPES)


# ---------------------------
# People and organizations
# ---------------------------

@app.get("/people")
@login_required
def people():
    rows = get_db().execute(
        """SELECT p.*, GROUP_CONCAT(DISTINCT pr.role) AS roles,
                  (SELECT COUNT(*) FROM matters m WHERE m.client_id=p.client_id)
                  + (SELECT COUNT(DISTINCT mp.matter_id) FROM matter_people mp
                     WHERE mp.person_id=p.id
                       AND NOT EXISTS (
                           SELECT 1 FROM matters primary_m
                           WHERE primary_m.id=mp.matter_id AND primary_m.client_id=p.client_id
                       )) AS matter_count
           FROM persons p
           LEFT JOIN person_roles pr ON pr.person_id=p.id
           GROUP BY p.id
           ORDER BY CASE WHEN p.person_type='Business' THEN p.organization_name ELSE p.last_name END,
                    p.first_name"""
    ).fetchall()
    return render_template("people.html", people=rows)


@app.route("/people/new", methods=["GET", "POST"])
@login_required
def person_new():
    if request.method == "POST":
        db = get_db()
        roles = selected_person_roles()
        try:
            fields = person_form_fields()
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("person_form.html", person=None, person_roles=roles, custom_roles="", role_options=PERSON_ROLES)
        if not roles:
            flash("Select or enter at least one role.", "danger")
            return render_template("person_form.html", person=None, person_roles=[], custom_roles="", role_options=PERSON_ROLES)
        client_id = create_client_identity(db, fields) if "Client" in roles else None
        db.execute(
            """INSERT INTO persons
               (client_id,person_type,organization_name,first_name,last_name,email,
                phone,address,city,state,zip_code,notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, *fields),
        )
        person_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        sync_person_roles(db, person_id, roles)
        matter_id = request.form.get("matter_id", type=int)
        matter_role = request.form.get("matter_role", "").strip()
        association_added = False
        if matter_id and matter_role and matter_role in roles and db.execute(
            "SELECT id FROM matters WHERE id=?", (matter_id,)
        ).fetchone():
            db.execute(
                "INSERT INTO matter_people (matter_id,person_id,role) VALUES (?,?,?)",
                (matter_id, person_id, matter_role),
            )
            association_added = True
        db.commit()
        flash("Contact created.", "success")
        if association_added:
            return redirect(url_for("matter_detail", matter_id=matter_id))
        return redirect(url_for("person_detail", person_id=person_id))

    return render_template("person_form.html", person=None, person_roles=[], custom_roles="", role_options=PERSON_ROLES)


@app.get("/people/<int:person_id>")
@login_required
def person_detail(person_id):
    db = get_db()
    person = db.execute("SELECT * FROM persons WHERE id=?", (person_id,)).fetchone()
    if not person:
        abort(404)
    roles = [row["role"] for row in db.execute(
        "SELECT role FROM person_roles WHERE person_id=? ORDER BY role", (person_id,)
    ).fetchall()]
    matters = db.execute(
        """SELECT m.*, 'Primary Client' AS person_matter_role
           FROM matters m JOIN persons p ON p.client_id=m.client_id WHERE p.id=?
           UNION
           SELECT m.*, mp.role AS person_matter_role
           FROM matter_people mp JOIN matters m ON m.id=mp.matter_id
           JOIN persons p ON p.id=mp.person_id
           WHERE mp.person_id=? AND m.client_id IS NOT p.client_id
           ORDER BY updated_at DESC""",
        (person_id, person_id),
    ).fetchall()
    custom_roles = [role for role in roles if role not in PERSON_ROLES]
    return render_template("person_detail.html", person=person, person_roles=roles, matters=matters, custom_roles=custom_roles)


@app.route("/people/<int:person_id>/edit", methods=["GET", "POST"])
@login_required
def person_edit(person_id):
    db = get_db()
    person = db.execute("SELECT * FROM persons WHERE id=?", (person_id,)).fetchone()
    if not person:
        abort(404)
    current_roles = [row["role"] for row in db.execute(
        "SELECT role FROM person_roles WHERE person_id=?", (person_id,)
    ).fetchall()]

    if request.method == "POST":
        roles = selected_person_roles()
        try:
            fields = person_form_fields()
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("person_edit", person_id=person_id))
        if not roles:
            flash("Select or enter at least one role.", "danger")
            return redirect(url_for("person_edit", person_id=person_id))
        if person["client_id"] and "Client" not in roles:
            matter_count = db.execute(
                "SELECT COUNT(*) FROM matters WHERE client_id=?", (person["client_id"],)
            ).fetchone()[0]
            if matter_count:
                flash("The Client role cannot be removed while this contact is the client on a matter.", "danger")
                return redirect(url_for("person_edit", person_id=person_id))
        original_client_id = person["client_id"]
        client_id = original_client_id
        if "Client" in roles and not client_id:
            client_id = create_client_identity(db, fields)
        elif "Client" not in roles:
            client_id = None
        db.execute(
            """UPDATE persons
               SET person_type=?, organization_name=?, first_name=?, last_name=?, email=?,
                   phone=?, address=?, city=?, state=?, zip_code=?, notes=?, client_id=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (*fields, client_id, person_id),
        )
        if client_id:
            db.execute(
                """UPDATE clients SET first_name=?,last_name=?,email=?,phone=?,address=?,city=?,
                   state=?,zip_code=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (*client_fields_from_person(fields), client_id),
            )
        elif original_client_id:
            db.execute("DELETE FROM clients WHERE id=?", (original_client_id,))
        sync_person_roles(db, person_id, roles)
        db.commit()
        flash("Contact updated.", "success")
        return redirect(url_for("person_detail", person_id=person_id))

    custom_roles = [role for role in current_roles if role not in PERSON_ROLES]
    return render_template("person_form.html", person=person, person_roles=current_roles, custom_roles=", ".join(custom_roles), role_options=PERSON_ROLES)


@app.post("/people/<int:person_id>/delete")
@login_required
def person_delete(person_id):
    db = get_db()
    person = db.execute("SELECT * FROM persons WHERE id=?", (person_id,)).fetchone()
    if not person:
        abort(404)
    matters = db.execute(
        "SELECT COUNT(*) FROM matters WHERE client_id=?", (person["client_id"],)
    ).fetchone()[0] if person["client_id"] else 0
    if matters:
        flash("Delete or reassign this contact's client matters before deleting it.", "danger")
        return redirect(url_for("person_detail", person_id=person_id))
    client_id = person["client_id"]
    db.execute("DELETE FROM persons WHERE id=?", (person_id,))
    if client_id:
        db.execute("DELETE FROM clients WHERE id=?", (client_id,))
    db.commit()
    flash("Contact deleted.", "success")
    return redirect(url_for("people"))


# Preserve old bookmarks while directing users to the unified directory.
@app.get("/clients")
@login_required
def clients():
    return redirect(url_for("people"))


@app.get("/clients/new")
@login_required
def client_new():
    return redirect(url_for("person_new"))


@app.get("/clients/<int:client_id>")
@login_required
def client_detail(client_id):
    person = get_db().execute(
        "SELECT id FROM persons WHERE client_id=?", (client_id,)
    ).fetchone()
    if not person:
        abort(404)
    return redirect(url_for("person_detail", person_id=person["id"]))


# ---------------------------
# Matters
# ---------------------------

@app.get("/matters")
@login_required
def matters():
    status = request.args.get("status", "").strip()
    db = get_db()
    sql = """SELECT m.*, CASE WHEN p.person_type='Business' THEN p.organization_name
                               ELSE p.first_name || ' ' || p.last_name END AS client_name
             FROM matters m JOIN persons p ON p.client_id=m.client_id"""
    params = []
    if status:
        sql += " WHERE m.status=?"
        params.append(status)
    sql += " ORDER BY CASE m.status WHEN 'Active' THEN 1 ELSE 2 END, m.updated_at DESC"
    rows = db.execute(sql, params).fetchall()
    return render_template("matters.html", matters=rows, selected_status=status)


@app.route("/matters/new", methods=["GET", "POST"])
@login_required
def matter_new():
    db = get_db()
    client_rows = db.execute(
        """SELECT p.client_id AS id, p.person_type, p.organization_name,
                  p.first_name, p.last_name
           FROM persons p JOIN person_roles pr ON pr.person_id=p.id
           WHERE pr.role='Client' AND p.client_id IS NOT NULL
           ORDER BY CASE WHEN p.person_type='Business' THEN p.organization_name ELSE p.last_name END,
                    p.first_name"""
    ).fetchall()
    if not client_rows:
        flash("Create a contact with the Client role before creating a matter.", "warning")
        return redirect(url_for("person_new"))

    if request.method == "POST":
        db.execute(
            """INSERT INTO matters
               (client_id,case_number,title,matter_type,court,judge,status,opened_date,
                next_hearing,description,opposing_counsel)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                int(request.form["client_id"]),
                request.form.get("case_number", "").strip(),
                request.form["title"].strip(),
                request.form.get("matter_type", "").strip(),
                request.form.get("court", "").strip(),
                request.form.get("judge", "").strip(),
                request.form.get("status", "Active"),
                request.form.get("opened_date") or None,
                request.form.get("next_hearing") or None,
                request.form.get("description", "").strip(),
                request.form.get("opposing_counsel", "").strip(),
            ),
        )
        db.commit()
        matter_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        flash("Matter created.", "success")
        return redirect(url_for("matter_detail", matter_id=matter_id))

    return render_template("matter_form.html", matter=None, clients=client_rows)


@app.get("/matters/<int:matter_id>")
@login_required
def matter_detail(matter_id):
    db = get_db()
    matter = db.execute(
        """SELECT m.*, CASE WHEN p.person_type='Business' THEN p.organization_name
                             ELSE p.first_name || ' ' || p.last_name END AS client_name,
                  p.id AS client_person_id, p.email AS client_email, p.phone AS client_phone
           FROM matters m JOIN persons p ON p.client_id=m.client_id
           WHERE m.id=?""",
        (matter_id,),
    ).fetchone()
    if not matter:
        abort(404)

    tasks = db.execute(
        "SELECT * FROM tasks WHERE matter_id=? ORDER BY status, COALESCE(due_date,'9999-12-31')",
        (matter_id,),
    ).fetchall()
    notes = db.execute(
        "SELECT * FROM notes WHERE matter_id=? ORDER BY created_at DESC",
        (matter_id,),
    ).fetchall()
    events = db.execute(
        "SELECT * FROM events WHERE matter_id=? ORDER BY datetime(start_at)",
        (matter_id,),
    ).fetchall()
    documents = db.execute(
        "SELECT * FROM documents WHERE matter_id=? ORDER BY uploaded_at DESC",
        (matter_id,),
    ).fetchall()
    time_entries = db.execute(
        "SELECT * FROM time_entries WHERE matter_id=? ORDER BY work_date DESC, id DESC",
        (matter_id,),
    ).fetchall()
    totals = db.execute(
        """SELECT COALESCE(SUM(hours),0) AS hours,
                  COALESCE(SUM(CASE WHEN billable=1 THEN hours*rate ELSE 0 END),0) AS fees
           FROM time_entries WHERE matter_id=?""",
        (matter_id,),
    ).fetchone()
    matter_people = db.execute(
        """SELECT mp.*, p.person_type, p.organization_name, p.first_name, p.last_name,
                  p.email, p.phone
           FROM matter_people mp JOIN persons p ON p.id=mp.person_id
           WHERE mp.matter_id=?
           ORDER BY mp.role,
                    CASE WHEN p.person_type='Business' THEN p.organization_name ELSE p.last_name END,
                    p.first_name""",
        (matter_id,),
    ).fetchall()
    available_people = db.execute(
        """SELECT p.id, p.person_type, p.organization_name, p.first_name, p.last_name,
                  GROUP_CONCAT(pr.role, ', ') AS roles
           FROM persons p LEFT JOIN person_roles pr ON pr.person_id=p.id
           GROUP BY p.id
           ORDER BY CASE WHEN p.person_type='Business' THEN p.organization_name ELSE p.last_name END,
                    p.first_name"""
    ).fetchall()

    return render_template(
        "matter_detail.html",
        matter=matter,
        tasks=tasks,
        notes=notes,
        events=events,
        documents=documents,
        time_entries=time_entries,
        totals=totals,
        matter_people=matter_people,
        available_people=available_people,
        person_role_options=PERSON_ROLES,
    )


@app.route("/matters/<int:matter_id>/edit", methods=["GET", "POST"])
@login_required
def matter_edit(matter_id):
    db = get_db()
    matter = db.execute("SELECT * FROM matters WHERE id=?", (matter_id,)).fetchone()
    if not matter:
        abort(404)
    client_rows = db.execute(
        """SELECT p.client_id AS id, p.person_type, p.organization_name,
                  p.first_name, p.last_name
           FROM persons p JOIN person_roles pr ON pr.person_id=p.id
           WHERE pr.role='Client' AND p.client_id IS NOT NULL
           ORDER BY CASE WHEN p.person_type='Business' THEN p.organization_name ELSE p.last_name END,
                    p.first_name"""
    ).fetchall()

    if request.method == "POST":
        db.execute(
            """UPDATE matters SET
               client_id=?, case_number=?, title=?, matter_type=?, court=?, judge=?, status=?,
               opened_date=?, next_hearing=?, description=?, opposing_counsel=?,
               updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                int(request.form["client_id"]),
                request.form.get("case_number", "").strip(),
                request.form["title"].strip(),
                request.form.get("matter_type", "").strip(),
                request.form.get("court", "").strip(),
                request.form.get("judge", "").strip(),
                request.form.get("status", "Active"),
                request.form.get("opened_date") or None,
                request.form.get("next_hearing") or None,
                request.form.get("description", "").strip(),
                request.form.get("opposing_counsel", "").strip(),
                matter_id,
            ),
        )
        db.commit()
        flash("Matter updated.", "success")
        return redirect(url_for("matter_detail", matter_id=matter_id))

    return render_template("matter_form.html", matter=matter, clients=client_rows)


@app.post("/matters/<int:matter_id>/people")
@login_required
def matter_person_add(matter_id):
    db = get_db()
    if not db.execute("SELECT id FROM matters WHERE id=?", (matter_id,)).fetchone():
        abort(404)
    person_id = request.form.get("person_id", type=int)
    role = request.form.get("role", "").strip()
    if role == "Custom":
        role = request.form.get("custom_role", "").strip()
    if not person_id or not role or len(role) > 80:
        abort(400, description="Select a valid contact and role.")
    if not db.execute("SELECT id FROM persons WHERE id=?", (person_id,)).fetchone():
        abort(400, description="Select a valid contact and role.")
    db.execute("INSERT OR IGNORE INTO person_roles (person_id,role) VALUES (?,?)", (person_id, role))
    db.execute(
        """INSERT INTO matter_people (matter_id,person_id,role,relationship_notes)
           VALUES (?,?,?,?)
           ON CONFLICT(matter_id,person_id,role)
           DO UPDATE SET relationship_notes=excluded.relationship_notes""",
        (matter_id, person_id, role, request.form.get("relationship_notes", "").strip()),
    )
    db.commit()
    flash("Contact added to matter.", "success")
    return redirect(url_for("matter_detail", matter_id=matter_id))


@app.post("/matters/<int:matter_id>/people/<int:person_id>/delete")
@login_required
def matter_person_delete(matter_id, person_id):
    db = get_db()
    role = request.form.get("role", "")
    db.execute(
        "DELETE FROM matter_people WHERE matter_id=? AND person_id=? AND role=?",
        (matter_id, person_id, role),
    )
    db.commit()
    flash("Contact removed from matter.", "success")
    return redirect(url_for("matter_detail", matter_id=matter_id))


@app.post("/matters/<int:matter_id>/delete")
@login_required
def matter_delete(matter_id):
    db = get_db()
    docs = db.execute("SELECT stored_name FROM documents WHERE matter_id=?", (matter_id,)).fetchall()
    db.execute("DELETE FROM matters WHERE id=?", (matter_id,))
    db.commit()
    for doc in docs:
        path = UPLOAD_DIR / doc["stored_name"]
        if path.exists():
            path.unlink()
    flash("Matter and related records deleted.", "success")
    return redirect(url_for("matters"))


# ---------------------------
# Tasks
# ---------------------------

@app.get("/tasks")
@login_required
def tasks():
    db = get_db()
    rows = db.execute(
        """SELECT t.*, m.title AS matter_title
           FROM tasks t JOIN matters m ON m.id=t.matter_id
           ORDER BY CASE t.status WHEN 'Completed' THEN 2 ELSE 1 END,
                    CASE t.priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Normal' THEN 3 ELSE 4 END,
                    COALESCE(t.due_date,'9999-12-31')"""
    ).fetchall()
    matter_rows = db.execute(
        "SELECT id, title FROM matters WHERE status='Active' ORDER BY title"
    ).fetchall()
    return render_template("tasks.html", tasks=rows, matters=matter_rows)


@app.post("/tasks/new")
@login_required
def task_new():
    db = get_db()
    db.execute(
        """INSERT INTO tasks
           (matter_id,title,description,due_date,priority,status,assigned_to)
           VALUES (?,?,?,?,?,?,?)""",
        (
            int(request.form["matter_id"]),
            request.form["title"].strip(),
            request.form.get("description", "").strip(),
            request.form.get("due_date") or None,
            request.form.get("priority", "Normal"),
            "Open",
            request.form.get("assigned_to", g.user["name"]).strip(),
        ),
    )
    db.commit()
    flash("Task added.", "success")
    return redirect(request.referrer or url_for("tasks"))


@app.post("/tasks/<int:task_id>/toggle")
@login_required
def task_toggle(task_id):
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        abort(404)
    status = "Open" if task["status"] == "Completed" else "Completed"
    db.execute(
        "UPDATE tasks SET status=?, completed_at=? WHERE id=?",
        (status, datetime.now().isoformat(timespec="seconds") if status == "Completed" else None, task_id),
    )
    db.commit()
    return redirect(request.referrer or url_for("tasks"))


@app.post("/tasks/<int:task_id>/delete")
@login_required
def task_delete(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    db.commit()
    flash("Task deleted.", "success")
    return redirect(request.referrer or url_for("tasks"))


# ---------------------------
# Notes
# ---------------------------

@app.post("/matters/<int:matter_id>/notes")
@login_required
def note_new(matter_id):
    body = request.form.get("body", "").strip()
    if body:
        db = get_db()
        db.execute(
            "INSERT INTO notes (matter_id,body,created_by) VALUES (?,?,?)",
            (matter_id, body, g.user["name"]),
        )
        db.execute(
            "UPDATE matters SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (matter_id,),
        )
        db.commit()
        flash("Note added.", "success")
    return redirect(url_for("matter_detail", matter_id=matter_id) + "#notes")


@app.post("/notes/<int:note_id>/delete")
@login_required
def note_delete(note_id):
    db = get_db()
    note = db.execute("SELECT matter_id FROM notes WHERE id=?", (note_id,)).fetchone()
    if not note:
        abort(404)
    db.execute("DELETE FROM notes WHERE id=?", (note_id,))
    db.commit()
    flash("Note deleted.", "success")
    return redirect(url_for("matter_detail", matter_id=note["matter_id"]) + "#notes")


# ---------------------------
# Calendar / events
# ---------------------------

@app.get("/calendar")
@login_required
def calendar():
    db = get_db()
    rows = db.execute(
        """SELECT e.*, m.title AS matter_title
           FROM events e JOIN matters m ON m.id=e.matter_id
           ORDER BY datetime(e.start_at)"""
    ).fetchall()
    matter_rows = db.execute(
        "SELECT id, title FROM matters WHERE status='Active' ORDER BY title"
    ).fetchall()
    return render_template("calendar.html", events=rows, matters=matter_rows)


@app.post("/events/new")
@login_required
def event_new():
    db = get_db()
    db.execute(
        """INSERT INTO events
           (matter_id,title,event_type,start_at,location,description)
           VALUES (?,?,?,?,?,?)""",
        (
            int(request.form["matter_id"]),
            request.form["title"].strip(),
            request.form.get("event_type", "Hearing"),
            request.form["start_at"],
            request.form.get("location", "").strip(),
            request.form.get("description", "").strip(),
        ),
    )
    db.commit()
    flash("Calendar event added.", "success")
    return redirect(request.referrer or url_for("calendar"))


@app.post("/events/<int:event_id>/delete")
@login_required
def event_delete(event_id):
    db = get_db()
    event = db.execute("SELECT matter_id FROM events WHERE id=?", (event_id,)).fetchone()
    db.execute("DELETE FROM events WHERE id=?", (event_id,))
    db.commit()
    flash("Calendar event deleted.", "success")
    if event and "matters/" in (request.referrer or ""):
        return redirect(url_for("matter_detail", matter_id=event["matter_id"]) + "#events")
    return redirect(url_for("calendar"))


# ---------------------------
# Documents
# ---------------------------

@app.post("/matters/<int:matter_id>/documents")
@login_required
def document_upload(matter_id):
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Choose a file to upload.", "danger")
        return redirect(url_for("matter_detail", matter_id=matter_id) + "#documents")

    if not allowed_file(file.filename):
        flash("That file type is not allowed.", "danger")
        return redirect(url_for("matter_detail", matter_id=matter_id) + "#documents")

    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[1].lower()
    stored = f"{uuid.uuid4().hex}.{ext}"
    file.save(UPLOAD_DIR / stored)

    db = get_db()
    db.execute(
        """INSERT INTO documents
           (matter_id,original_name,stored_name,uploaded_by)
           VALUES (?,?,?,?)""",
        (matter_id, original, stored, g.user["name"]),
    )
    db.commit()
    flash("Document uploaded.", "success")
    return redirect(url_for("matter_detail", matter_id=matter_id) + "#documents")


@app.get("/documents/<int:document_id>/download")
@login_required
def document_download(document_id):
    doc = get_db().execute(
        "SELECT * FROM documents WHERE id=?", (document_id,)
    ).fetchone()
    if not doc:
        abort(404)
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        doc["stored_name"],
        as_attachment=True,
        download_name=doc["original_name"],
    )


@app.post("/documents/<int:document_id>/delete")
@login_required
def document_delete(document_id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    if not doc:
        abort(404)
    db.execute("DELETE FROM documents WHERE id=?", (document_id,))
    db.commit()
    path = UPLOAD_DIR / doc["stored_name"]
    if path.exists():
        path.unlink()
    flash("Document deleted.", "success")
    return redirect(url_for("matter_detail", matter_id=doc["matter_id"]) + "#documents")


# ---------------------------
# Time entries
# ---------------------------

@app.get("/time")
@login_required
def time_entries():
    db = get_db()
    rows = db.execute(
        """SELECT te.*, m.title AS matter_title
           FROM time_entries te JOIN matters m ON m.id=te.matter_id
           ORDER BY te.work_date DESC, te.id DESC"""
    ).fetchall()
    matter_rows = db.execute(
        "SELECT id, title FROM matters WHERE status='Active' ORDER BY title"
    ).fetchall()
    total = db.execute(
        """SELECT COALESCE(SUM(hours),0) AS hours,
                  COALESCE(SUM(CASE WHEN billable=1 THEN hours*rate ELSE 0 END),0) AS fees
           FROM time_entries"""
    ).fetchone()
    return render_template("time.html", entries=rows, matters=matter_rows, total=total)


@app.post("/time/new")
@login_required
def time_new():
    db = get_db()
    db.execute(
        """INSERT INTO time_entries
           (matter_id,work_date,hours,description,billable,rate)
           VALUES (?,?,?,?,?,?)""",
        (
            int(request.form["matter_id"]),
            request.form.get("work_date") or date.today().isoformat(),
            float(request.form["hours"]),
            request.form["description"].strip(),
            1 if request.form.get("billable") == "on" else 0,
            float(request.form.get("rate") or 0),
        ),
    )
    db.commit()
    flash("Time entry added.", "success")
    return redirect(request.referrer or url_for("time_entries"))


@app.post("/time/<int:entry_id>/delete")
@login_required
def time_delete(entry_id):
    db = get_db()
    entry = db.execute("SELECT matter_id FROM time_entries WHERE id=?", (entry_id,)).fetchone()
    db.execute("DELETE FROM time_entries WHERE id=?", (entry_id,))
    db.commit()
    flash("Time entry deleted.", "success")
    if entry and "matters/" in (request.referrer or ""):
        return redirect(url_for("matter_detail", matter_id=entry["matter_id"]) + "#time")
    return redirect(url_for("time_entries"))



# ---------------------------
# Client intake
# ---------------------------

def intake_config_or_404(intake_type):
    config = INTAKE_TYPES.get(intake_type)
    if not config:
        abort(404)
    return config


def intake_payload_from_form(config):
    payload = {}
    for _, fields in config["sections"]:
        for field in fields:
            key = field[0]
            payload[key] = request.form.get(key, "").strip()
    return payload


@app.get("/intakes")
@login_required
def intakes():
    intake_type = request.args.get("type", "").strip()
    status = request.args.get("status", "").strip()
    params = []
    clauses = []
    if intake_type in INTAKE_TYPES:
        clauses.append("intake_type = ?")
        params.append(intake_type)
    if status in INTAKE_STATUSES:
        clauses.append("status = ?")
        params.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = get_db().execute(
        f"""SELECT * FROM intake_submissions{where}
            ORDER BY
              CASE status WHEN 'New' THEN 1 WHEN 'Under Review' THEN 2 WHEN 'Converted' THEN 3 WHEN 'Declined' THEN 4 ELSE 5 END,
              datetime(submitted_at) DESC, id DESC""",
        params,
    ).fetchall()
    return render_template(
        "intakes.html",
        intakes=rows,
        intake_types=INTAKE_TYPES,
        intake_statuses=INTAKE_STATUSES,
        selected_type=intake_type,
        selected_status=status,
    )


@app.get("/intakes/new")
@login_required
def intake_choose():
    return render_template("intake_choose.html", intake_types=INTAKE_TYPES)


@app.route("/intakes/new/<intake_type>", methods=["GET", "POST"])
@login_required
def intake_new(intake_type):
    config = intake_config_or_404(intake_type)
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        if not first_name or not last_name:
            flash("First and last name are required.", "danger")
            return render_template(
                "intake_form.html",
                intake_type=intake_type,
                config=config,
                common_fields=COMMON_INTAKE_FIELDS,
                values=request.form,
            )

        payload = intake_payload_from_form(config)
        db = get_db()
        db.execute(
            """INSERT INTO intake_submissions
               (intake_type,status,first_name,last_name,email,phone,preferred_contact,
                address,city,state,zip_code,referred_by,conflict_names,urgency,data_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                intake_type,
                "New",
                first_name,
                last_name,
                request.form.get("email", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("preferred_contact", "").strip(),
                request.form.get("address", "").strip(),
                request.form.get("city", "").strip(),
                request.form.get("state", "FL").strip(),
                request.form.get("zip_code", "").strip(),
                request.form.get("referred_by", "").strip(),
                request.form.get("conflict_names", "").strip(),
                request.form.get("urgency", "").strip(),
                json.dumps(payload),
            ),
        )
        intake_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        flash(f"{config['name']} intake saved.", "success")
        return redirect(url_for("intake_detail", intake_id=intake_id))

    return render_template(
        "intake_form.html",
        intake_type=intake_type,
        config=config,
        common_fields=COMMON_INTAKE_FIELDS,
        values={},
    )


@app.route("/intakes/<int:intake_id>/edit", methods=["GET", "POST"])
@login_required
def intake_edit(intake_id):
    db = get_db()
    intake = db.execute("SELECT * FROM intake_submissions WHERE id=?", (intake_id,)).fetchone()
    if not intake:
        abort(404)
    if intake["linked_client_id"] or intake["linked_matter_id"]:
        flash("Converted intake records are preserved as submitted and cannot be edited here.", "warning")
        return redirect(url_for("intake_detail", intake_id=intake_id))
    config = intake_config_or_404(intake["intake_type"])

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        if not first_name or not last_name:
            flash("First and last name are required.", "danger")
            return render_template(
                "intake_form.html",
                intake_type=intake["intake_type"], config=config,
                common_fields=COMMON_INTAKE_FIELDS, values=request.form,
                editing=True, intake=intake,
            )
        payload = intake_payload_from_form(config)
        db.execute(
            """UPDATE intake_submissions
               SET first_name=?,last_name=?,email=?,phone=?,preferred_contact=?,address=?,city=?,state=?,zip_code=?,
                   referred_by=?,conflict_names=?,urgency=?,data_json=?,reviewed_by=?,updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                first_name, last_name, request.form.get("email", "").strip(), request.form.get("phone", "").strip(),
                request.form.get("preferred_contact", "").strip(), request.form.get("address", "").strip(),
                request.form.get("city", "").strip(), request.form.get("state", "FL").strip(),
                request.form.get("zip_code", "").strip(), request.form.get("referred_by", "").strip(),
                request.form.get("conflict_names", "").strip(), request.form.get("urgency", "").strip(),
                json.dumps(payload), g.user["name"], intake_id,
            ),
        )
        db.commit()
        flash("Intake updated.", "success")
        return redirect(url_for("intake_detail", intake_id=intake_id))

    try:
        payload = json.loads(intake["data_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}
    values = {key: intake[key] or "" for key, *_ in COMMON_INTAKE_FIELDS}
    values.update(payload)
    return render_template(
        "intake_form.html",
        intake_type=intake["intake_type"], config=config,
        common_fields=COMMON_INTAKE_FIELDS, values=values,
        editing=True, intake=intake,
    )


@app.get("/intakes/<int:intake_id>")
@login_required
def intake_detail(intake_id):
    intake = get_db().execute(
        "SELECT * FROM intake_submissions WHERE id=?", (intake_id,)
    ).fetchone()
    if not intake:
        abort(404)
    config = intake_config_or_404(intake["intake_type"])
    try:
        payload = json.loads(intake["data_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}
    return render_template(
        "intake_detail.html",
        intake=intake,
        config=config,
        payload=payload,
        common_fields=COMMON_INTAKE_FIELDS,
        intake_statuses=INTAKE_STATUSES,
    )


@app.post("/intakes/<int:intake_id>/status")
@login_required
def intake_status_update(intake_id):
    status = request.form.get("status", "")
    if status not in INTAKE_STATUSES:
        abort(400, description="Invalid intake status.")
    db = get_db()
    intake = db.execute("SELECT id FROM intake_submissions WHERE id=?", (intake_id,)).fetchone()
    if not intake:
        abort(404)
    db.execute(
        """UPDATE intake_submissions
           SET status=?, reviewed_by=?, updated_at=CURRENT_TIMESTAMP
           WHERE id=?""",
        (status, g.user["name"], intake_id),
    )
    db.commit()
    flash("Intake status updated.", "success")
    return redirect(url_for("intake_detail", intake_id=intake_id))


@app.post("/intakes/<int:intake_id>/convert")
@login_required
def intake_convert(intake_id):
    db = get_db()
    intake = db.execute("SELECT * FROM intake_submissions WHERE id=?", (intake_id,)).fetchone()
    if not intake:
        abort(404)
    if intake["linked_client_id"] or intake["linked_matter_id"]:
        flash("This intake has already been converted.", "warning")
        return redirect(url_for("intake_detail", intake_id=intake_id))

    config = intake_config_or_404(intake["intake_type"])
    try:
        payload = json.loads(intake["data_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}

    notes = [f"Converted from {config['name']} intake #{intake_id}."]
    if intake["referred_by"]:
        notes.append(f"Referred by: {intake['referred_by']}")
    if intake["conflict_names"]:
        notes.append(f"Conflict-check names: {intake['conflict_names']}")
    if intake["urgency"]:
        notes.append(f"Urgency / deadlines: {intake['urgency']}")

    db.execute(
        """INSERT INTO clients
           (first_name,last_name,email,phone,address,city,state,zip_code,notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            intake["first_name"], intake["last_name"], intake["email"], intake["phone"],
            intake["address"], intake["city"], intake["state"], intake["zip_code"],
            "\n".join(notes),
        ),
    )
    client_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute(
        """INSERT INTO persons
           (client_id,person_type,first_name,last_name,email,phone,address,city,state,zip_code,notes)
           VALUES (?,'Individual',?,?,?,?,?,?,?,?,?)""",
        (
            client_id, intake["first_name"], intake["last_name"], intake["email"], intake["phone"],
            intake["address"], intake["city"], intake["state"], intake["zip_code"], "\n".join(notes),
        ),
    )
    person_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO person_roles (person_id,role) VALUES (?,'Client')", (person_id,))

    full_name = f"{intake['first_name']} {intake['last_name']}"
    if intake["intake_type"] == "probate" and payload.get("decedent_name"):
        title = f"Estate of {payload['decedent_name']}"
    elif intake["intake_type"] == "criminal":
        title = f"Criminal Defense – {full_name}"
    else:
        title = f"{config['name']} – {full_name}"

    description_parts = [f"Created from {config['name']} intake #{intake_id}."]
    if intake["urgency"]:
        description_parts.append(f"Urgency / deadlines: {intake['urgency']}")
    if intake["intake_type"] == "criminal" and payload.get("charges"):
        description_parts.append(f"Charges: {payload['charges']}")
    if intake["intake_type"] == "personal-injury" and payload.get("incident_narrative"):
        description_parts.append(f"Incident: {payload['incident_narrative']}")
    if intake["intake_type"] == "estate-planning" and payload.get("planning_goals"):
        description_parts.append(f"Planning goals: {payload['planning_goals']}")
    if intake["intake_type"] == "probate" and payload.get("relationship_to_decedent"):
        description_parts.append(f"Relationship to decedent: {payload['relationship_to_decedent']}")

    case_number = payload.get("case_number", "") if intake["intake_type"] in ("criminal", "probate") else ""
    court = payload.get("court", "") if intake["intake_type"] in ("criminal", "probate") else ""
    judge = payload.get("judge", "") if intake["intake_type"] == "criminal" else ""
    next_hearing = payload.get("next_court_date", "") if intake["intake_type"] == "criminal" else ""

    db.execute(
        """INSERT INTO matters
           (client_id,case_number,title,matter_type,court,judge,status,opened_date,next_hearing,description,opposing_counsel)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            client_id, case_number, title, config["matter_type"], court, judge,
            "Active", date.today().isoformat(), next_hearing,
            "\n".join(description_parts), "",
        ),
    )
    matter_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    db.execute(
        """UPDATE intake_submissions
           SET status='Converted', linked_client_id=?, linked_matter_id=?, reviewed_by=?, updated_at=CURRENT_TIMESTAMP
           WHERE id=?""",
        (client_id, matter_id, g.user["name"], intake_id),
    )
    db.commit()
    flash("Intake converted to a client and active matter.", "success")
    return redirect(url_for("matter_detail", matter_id=matter_id))


@app.post("/intakes/<int:intake_id>/delete")
@login_required
def intake_delete(intake_id):
    db = get_db()
    intake = db.execute("SELECT * FROM intake_submissions WHERE id=?", (intake_id,)).fetchone()
    if not intake:
        abort(404)
    if intake["linked_client_id"] or intake["linked_matter_id"]:
        flash("Converted intakes cannot be deleted from this screen.", "warning")
        return redirect(url_for("intake_detail", intake_id=intake_id))
    db.execute("DELETE FROM intake_submissions WHERE id=?", (intake_id,))
    db.commit()
    flash("Intake deleted.", "success")
    return redirect(url_for("intakes"))


# ---------------------------
# Errors
# ---------------------------

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, message=str(error.description)), 400


@app.errorhandler(413)
def too_large(error):
    return render_template("error.html", code=413, message="Upload exceeds the 25 MB limit."), 413


# ---------------------------
# Bootstrap database + run
# ---------------------------

def ensure_database():
    # Re-run the idempotent schema on startup so new tables/indexes are added
    # to existing CaseDesk databases without destroying client data.
    with app.app_context():
        init_db()
        seed_db()


ensure_database()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
