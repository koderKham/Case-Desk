PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Legacy client identities remain for existing matter foreign keys.  The
-- user-facing directory uses persons, which supports individuals, businesses,
-- and multiple roles per record.
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER UNIQUE,
    person_type TEXT NOT NULL DEFAULT 'Individual'
        CHECK(person_type IN ('Individual','Business')),
    organization_name TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CHECK(
        (person_type='Business' AND length(trim(COALESCE(organization_name,''))) > 0)
        OR
        (person_type='Individual' AND length(trim(COALESCE(first_name,''))) > 0
                                  AND length(trim(COALESCE(last_name,''))) > 0)
    )
);

CREATE TABLE IF NOT EXISTS person_roles (
    person_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(length(trim(role)) BETWEEN 1 AND 80),
    PRIMARY KEY(person_id, role),
    FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS matters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    case_number TEXT,
    title TEXT NOT NULL,
    matter_type TEXT,
    court TEXT,
    judge TEXT,
    opposing_counsel TEXT,
    status TEXT NOT NULL DEFAULT 'Active'
        CHECK(status IN ('Active','Pending','Closed','Archived')),
    opened_date TEXT,
    next_hearing TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS matter_people (
    matter_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(length(trim(role)) BETWEEN 1 AND 80),
    relationship_notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(matter_id, person_id, role),
    FOREIGN KEY(matter_id) REFERENCES matters(id) ON DELETE CASCADE,
    FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    priority TEXT NOT NULL DEFAULT 'Normal'
        CHECK(priority IN ('Low','Normal','High','Urgent')),
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK(status IN ('Open','In Progress','Completed')),
    assigned_to TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(matter_id) REFERENCES matters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(matter_id) REFERENCES matters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'Hearing',
    start_at TEXT NOT NULL,
    location TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(matter_id) REFERENCES matters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    uploaded_by TEXT,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(matter_id) REFERENCES matters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS time_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER NOT NULL,
    work_date TEXT NOT NULL,
    hours REAL NOT NULL CHECK(hours > 0),
    description TEXT NOT NULL,
    billable INTEGER NOT NULL DEFAULT 1 CHECK(billable IN (0,1)),
    rate REAL NOT NULL DEFAULT 0 CHECK(rate >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(matter_id) REFERENCES matters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matters_client ON matters(client_id);
CREATE INDEX IF NOT EXISTS idx_persons_client ON persons(client_id);
CREATE INDEX IF NOT EXISTS idx_person_roles_role ON person_roles(role);
CREATE INDEX IF NOT EXISTS idx_matter_people_person ON matter_people(person_id);
CREATE INDEX IF NOT EXISTS idx_matters_status ON matters(status);
CREATE INDEX IF NOT EXISTS idx_tasks_matter_due ON tasks(matter_id, due_date);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_at);
CREATE INDEX IF NOT EXISTS idx_notes_matter ON notes(matter_id);
CREATE INDEX IF NOT EXISTS idx_documents_matter ON documents(matter_id);
CREATE INDEX IF NOT EXISTS idx_time_matter_date ON time_entries(matter_id, work_date);

CREATE TABLE IF NOT EXISTS intake_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intake_type TEXT NOT NULL
        CHECK(intake_type IN ('estate-planning','personal-injury','probate','criminal')),
    status TEXT NOT NULL DEFAULT 'New'
        CHECK(status IN ('New','Under Review','Converted','Declined','Closed')),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    preferred_contact TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    referred_by TEXT,
    conflict_names TEXT,
    urgency TEXT,
    data_json TEXT NOT NULL DEFAULT '{}',
    linked_client_id INTEGER,
    linked_matter_id INTEGER,
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by TEXT,
    FOREIGN KEY(linked_client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY(linked_matter_id) REFERENCES matters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_intake_submissions_type_status
ON intake_submissions(intake_type, status);

CREATE INDEX IF NOT EXISTS idx_intake_submissions_submitted_at
ON intake_submissions(submitted_at DESC);
