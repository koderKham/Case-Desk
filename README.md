# CaseDesk — Python Law Firm Case Management App

A working Flask + SQLite case-management MVP for a small law firm.

## Included

- User login with hashed password
- Dashboard
- Unified People & Organizations directory
- Individual and Business contact types
- Multiple contact roles, including Client, Heir, Interested Person, Witness,
  Decedent, Beneficiary, Personal Representative, Opposing Party, Expert, and custom roles
- Matter-specific contact roles and relationship notes
- Matter / case CRUD
- Case number, matter type, court, judge, opposing counsel, status, next hearing
- Tasks with due dates, priority, assignment, and completion
- Case notes
- Calendar events / hearings / depositions / trials / deadlines
- Matter document uploads and downloads
- Time entries, billing rate, and tracked value
- Cross-application search
- CSRF protection on write actions
- SQLite relational database with foreign keys and indexes
- Seeded demo data
- Responsive custom UI
- Practice-area client intake pipeline for Estate Planning, Personal Injury, Probate, and Criminal Defense
- Intake status tracking, editing, conflict-check fields, and one-click conversion to a client + matter
- Basic smoke tests

## Quick start

### macOS / Linux

```bash
cd daley_case_management_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Windows

```powershell
cd daley_case_management_app
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open:

`http://127.0.0.1:5000`

## Demo login

- Email: `admin@example.com`
- Password: `ChangeMe123!`

**Change the demo credentials before entering real client information.**

Change the password with:

```bash
python set_password.py
```


## Client intake

CaseDesk includes structured intake questionnaires for:

- Estate Planning
- Personal Injury
- Probate
- Criminal Defense

Use **Client Intake** in the left navigation to start, review, filter, edit, and convert prospective-client intakes. Each intake stores general contact/conflict-check information plus practice-area-specific answers. Accepted intakes can be converted into a Person with the Client role and an active Matter without retyping the basic information.

## People and organizations

Use **People** for every individual or organization connected to a case. A contact can
have several directory roles at once, and each matter can give that contact a separate
case-specific role with relationship notes. Existing clients are migrated automatically
to Person records with the Client role when the application starts.

## Database

The working database is:

`instance/case_manager.db`

The schema is defined in:

`schema.sql`

To rebuild it from scratch, delete `instance/case_manager.db` and restart the app. The application will initialize and seed a fresh database automatically.

You can also use Flask CLI commands:

```bash
flask --app app init-db
flask --app app seed-db
```

## Secret key

For development, the app contains a fallback secret. For any real deployment, set a strong environment variable:

```bash
export CASE_MANAGER_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

## Tests

```bash
pytest -q
```

## Important production notes

This is a functional MVP, not a substitute for a security-reviewed legal-practice platform. Before storing real privileged or confidential data on an internet-accessible server, add or review:

- HTTPS/TLS
- Strong secret management
- Production WSGI server
- Encrypted backups
- Full database/storage encryption strategy
- Multi-user roles and permissions
- Audit logs
- MFA
- Password reset / account lockout
- Malware scanning for uploads
- Retention / deletion policies
- Off-site backup and restore testing
- Cloud object storage rather than local uploads
- Monitoring and security patch process
- Ethics / confidentiality requirements applicable to your jurisdiction and firm

## Project layout

```text
daley_case_management_app/
├── app.py
├── schema.sql
├── requirements.txt
├── README.md
├── instance/
│   └── case_manager.db
├── uploads/
├── static/
│   └── styles.css
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── people.html
│   ├── person_form.html
│   ├── person_detail.html
│   ├── matters.html
│   ├── matter_form.html
│   ├── matter_detail.html
│   ├── tasks.html
│   ├── calendar.html
│   ├── time.html
│   ├── search.html
│   ├── intakes.html
│   ├── intake_choose.html
│   ├── intake_form.html
│   ├── intake_detail.html
│   └── error.html
└── tests/
    └── test_app.py
```
