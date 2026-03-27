

import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "clinic.db"

# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    date_of_birth   DATE,
    gender          TEXT CHECK(gender IN ('M','F')),
    city            TEXT,
    registered_date DATE
);

CREATE TABLE IF NOT EXISTS doctors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    specialization  TEXT,
    department      TEXT,
    phone           TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER REFERENCES patients(id),
    doctor_id        INTEGER REFERENCES doctors(id),
    appointment_date DATETIME,
    status           TEXT CHECK(status IN ('Scheduled','Completed','Cancelled','No-Show')),
    notes            TEXT
);

CREATE TABLE IF NOT EXISTS treatments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id   INTEGER REFERENCES appointments(id),
    treatment_name   TEXT,
    cost             REAL,
    duration_minutes INTEGER
);

CREATE TABLE IF NOT EXISTS invoices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id   INTEGER REFERENCES patients(id),
    invoice_date DATE,
    total_amount REAL,
    paid_amount  REAL,
    status       TEXT CHECK(status IN ('Paid','Pending','Overdue'))
);
"""

# ── Seed data ─────────────────────────────────────────────────────────────────

FIRST_NAMES_M = ["James","John","Robert","Michael","William","David","Richard","Joseph",
                 "Thomas","Charles","Arun","Vijay","Rahul","Arjun","Sanjay","Anand",
                 "Deepak","Rajesh","Suresh","Manoj","Ali","Omar","Hassan","Ravi","Nikhil"]
FIRST_NAMES_F = ["Mary","Patricia","Jennifer","Linda","Barbara","Elizabeth","Susan","Jessica",
                 "Sarah","Karen","Priya","Anita","Sunita","Kavita","Meera","Divya","Pooja",
                 "Lakshmi","Nisha","Sneha","Fatima","Aisha","Hana","Rekha","Chitra"]
LAST_NAMES    = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
                 "Nair","Menon","Pillai","Kumar","Sharma","Patel","Shah","Iyer","Reddy",
                 "Rao","Singh","Khan","Thomas","George","Paul","Joseph","Mathew"]
CITIES        = ["Kochi","Thiruvananthapuram","Kozhikode","Thrissur","Kannur",
                 "Kollam","Palakkad","Alappuzha","Mumbai","Bengaluru"]
SPECIALIZATIONS = {
    "Dermatology":   "Skin & Hair",
    "Cardiology":    "Heart & Vascular",
    "Orthopedics":   "Bone & Joint",
    "General":       "General Medicine",
    "Pediatrics":    "Child Health",
}
DOCTOR_NAMES  = [
    ("Dr. Anil Kumar",      "Dermatology"),
    ("Dr. Priya Menon",     "Dermatology"),
    ("Dr. Suresh Nair",     "Dermatology"),
    ("Dr. Kavitha Pillai",  "Cardiology"),
    ("Dr. Rajesh Sharma",   "Cardiology"),
    ("Dr. Deepak Iyer",     "Cardiology"),
    ("Dr. Meera Thomas",    "Orthopedics"),
    ("Dr. Anand Reddy",     "Orthopedics"),
    ("Dr. Sanjay Patel",    "Orthopedics"),
    ("Dr. Sunita Rao",      "General"),
    ("Dr. Manoj Singh",     "General"),
    ("Dr. Fatima Khan",     "General"),
    ("Dr. Rekha George",    "Pediatrics"),
    ("Dr. Vijay Joseph",    "Pediatrics"),
    ("Dr. Chitra Mathew",   "Pediatrics"),
]
TREATMENT_MAP = {
    "Dermatology":  [("Skin Biopsy",800),("Acne Treatment",300),("Laser Therapy",2500),
                     ("Chemical Peel",1200),("Phototherapy",600)],
    "Cardiology":   [("ECG",500),("Echocardiogram",2000),("Stress Test",3000),
                     ("Angioplasty",45000),("Holter Monitor",1500)],
    "Orthopedics":  [("X-Ray",400),("MRI Scan",5000),("Physiotherapy",800),
                     ("Joint Injection",2500),("Fracture Management",6000)],
    "General":      [("Blood Test",300),("Urine Analysis",200),("General Checkup",500),
                     ("Vaccination",350),("Blood Pressure Monitoring",150)],
    "Pediatrics":   [("Well Baby Checkup",400),("Vaccination",350),("Growth Assessment",300),
                     ("Developmental Screening",600),("Pediatric Consultation",500)],
}

def rand_date(days_back: int) -> str:
    """Return a random date within the last `days_back` days as an ISO string (YYYY-MM-DD)."""
    return (datetime.now() - timedelta(days=random.randint(0, days_back))).strftime("%Y-%m-%d")

def rand_phone():
    return f"+91 9{random.randint(100000000,999999999)}" if random.random() > 0.15 else None

def rand_email(first, last):
    return f"{first.lower()}.{last.lower()}{random.randint(1,99)}@example.com" if random.random() > 0.1 else None


def build_db():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.executescript(SCHEMA_SQL)

    # ── Doctors ──────────────────────────────────────────────────────────────
    doctor_ids = []
    for name, spec in DOCTOR_NAMES:
        dept = SPECIALIZATIONS[spec]
        cur.execute(
            "INSERT INTO doctors(name,specialization,department,phone) VALUES(?,?,?,?)",
            (name, spec, dept, rand_phone() or f"+91 8{random.randint(100000000,999999999)}")
        )
        doctor_ids.append((cur.lastrowid, spec))

    # ── Patients ─────────────────────────────────────────────────────────────
    patient_ids = []
    for _ in range(200):
        gender = random.choice(["M","F"])
        first  = random.choice(FIRST_NAMES_M if gender=="M" else FIRST_NAMES_F)
        last   = random.choice(LAST_NAMES)
        dob    = rand_date(365*60)          # born within last 60 years
        cur.execute(
            "INSERT INTO patients(first_name,last_name,email,phone,date_of_birth,gender,city,registered_date)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (first, last, rand_email(first,last), rand_phone(),
             dob, gender, random.choice(CITIES), rand_date(365))
        )
        patient_ids.append(cur.lastrowid)

    # ── Appointments ─────────────────────────────────────────────────────────
    # Weight patients so some are repeat visitors
    weights = [random.choice([1,1,1,2,2,3,5]) for _ in patient_ids]
    statuses   = ["Completed","Completed","Completed","Scheduled","Cancelled","No-Show"]
    appt_ids   = []          # (appt_id, doctor_spec, status)
    for _ in range(500):
        pid   = random.choices(patient_ids, weights=weights, k=1)[0]
        doc   = random.choice(doctor_ids)
        dt    = datetime.now() - timedelta(days=random.randint(0,365),
                                           hours=random.randint(8,17),
                                           minutes=random.choice([0,15,30,45]))
        st    = random.choice(statuses)
        notes = random.choice(["Follow-up required","Routine visit",None,None,"Referred for tests"])
        cur.execute(
            "INSERT INTO appointments(patient_id,doctor_id,appointment_date,status,notes)"
            " VALUES(?,?,?,?,?)",
            (pid, doc[0], dt.strftime("%Y-%m-%d %H:%M:%S"), st, notes)
        )
        appt_ids.append((cur.lastrowid, doc[1], st, pid))

    # ── Treatments (only for Completed appointments) ──────────────────────────
    completed = [(aid, spec, pid) for aid, spec, st, pid in appt_ids if st == "Completed"]
    random.shuffle(completed)
    for aid, spec, pid in completed[:350]:
        t_name, base_cost = random.choice(TREATMENT_MAP[spec])
        cost = round(base_cost * random.uniform(0.8, 1.4), 2)
        dur  = random.randint(15, 90)
        cur.execute(
            "INSERT INTO treatments(appointment_id,treatment_name,cost,duration_minutes)"
            " VALUES(?,?,?,?)",
            (aid, t_name, cost, dur)
        )

    # ── Invoices ──────────────────────────────────────────────────────────────
    inv_statuses = ["Paid","Paid","Paid","Pending","Overdue"]
    patient_set  = list(set(pid for *_, pid in appt_ids))
    random.shuffle(patient_set)
    for pid in patient_set[:300]:
        total  = round(random.uniform(500, 25000), 2)
        status = random.choice(inv_statuses)
        paid   = total if status == "Paid" else round(total * random.uniform(0, 0.5), 2)
        cur.execute(
            "INSERT INTO invoices(patient_id,invoice_date,total_amount,paid_amount,status)"
            " VALUES(?,?,?,?,?)",
            (pid, rand_date(365), total, paid, status)
        )

    conn.commit()

    # Summary
    def count(table): return cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"✅  Created {count('patients')} patients, {count('doctors')} doctors, "
          f"{count('appointments')} appointments, {count('treatments')} treatments, "
          f"{count('invoices')} invoices")
    print(f"📁  Database saved to: {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    build_db()
