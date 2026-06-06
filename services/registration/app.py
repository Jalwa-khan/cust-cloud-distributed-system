"""CUST Registration Portal Microservice - CPE4541 CEP Project"""
from flask import Flask, jsonify, request
import sqlite3, os, time, logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
DB_PATH = "/data/registration.db"

def get_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            program TEXT NOT NULL,
            semester INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT UNIQUE NOT NULL,
            course_name TEXT NOT NULL,
            credit_hours INTEGER NOT NULL,
            instructor TEXT NOT NULL,
            capacity INTEGER DEFAULT 40,
            enrolled INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_code TEXT NOT NULL,
            semester TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, course_code, semester)
        );
    """)
    conn.executemany("INSERT OR IGNORE INTO students (student_id,name,email,program,semester) VALUES (?,?,?,?,?)", [
        ("FA21-BCE-001","Ali Hassan","ali@cust.edu.pk","BCE",7),
        ("FA21-BCE-002","Sara Khan","sara@cust.edu.pk","BCE",7),
        ("SP22-BCE-010","Umar Farooq","umar@cust.edu.pk","BCE",5),
    ])
    conn.executemany("INSERT OR IGNORE INTO courses (course_code,course_name,credit_hours,instructor,capacity) VALUES (?,?,?,?,?)", [
        ("CPE4541","Cloud and Distributed Computing",3,"Dr. Waseem Abbas",35),
        ("CPE4521","Computer Networks",3,"Dr. Ahmed",40),
        ("CPE4531","Operating Systems",3,"Dr. Bilal",40),
    ])
    conn.commit()
    conn.close()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "registration", "timestamp": time.time()})

@app.route("/api/students", methods=["GET"])
def get_students():
    conn = get_db()
    rows = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/students/<sid>", methods=["GET"])
def get_student(sid):
    conn = get_db()
    row = conn.execute("SELECT * FROM students WHERE student_id=?", (sid,)).fetchone()
    conn.close()
    return (jsonify(dict(row)), 200) if row else (jsonify({"error": "Not found"}), 404)

@app.route("/api/students", methods=["POST"])
def add_student():
    d = request.get_json()
    if not all(k in d for k in ["student_id","name","email","program","semester"]):
        return jsonify({"error": "Missing fields"}), 400
    try:
        conn = get_db()
        conn.execute("INSERT INTO students (student_id,name,email,program,semester) VALUES (?,?,?,?,?)",
            (d["student_id"],d["name"],d["email"],d["program"],d["semester"]))
        conn.commit(); conn.close()
        return jsonify({"message": "Student added", "student_id": d["student_id"]}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Student already exists"}), 409

@app.route("/api/courses", methods=["GET"])
def get_courses():
    conn = get_db()
    rows = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/register-course", methods=["POST"])
def register_course():
    d = request.get_json()
    if not all(k in d for k in ["student_id","course_code","semester"]):
        return jsonify({"error": "Missing fields"}), 400
    conn = get_db()
    c = conn.execute("SELECT * FROM courses WHERE course_code=?", (d["course_code"],)).fetchone()
    if not c:
        conn.close(); return jsonify({"error": "Course not found"}), 404
    if c["enrolled"] >= c["capacity"]:
        conn.close(); return jsonify({"error": "Course full"}), 409
    try:
        conn.execute("INSERT INTO registrations (student_id,course_code,semester) VALUES (?,?,?)",
            (d["student_id"],d["course_code"],d["semester"]))
        conn.execute("UPDATE courses SET enrolled=enrolled+1 WHERE course_code=?", (d["course_code"],))
        conn.commit(); conn.close()
        return jsonify({"message": "Registered successfully"}), 201
    except sqlite3.IntegrityError:
        conn.close(); return jsonify({"error": "Already registered"}), 409

@app.route("/api/registrations/<sid>", methods=["GET"])
def get_regs(sid):
    conn = get_db()
    rows = conn.execute(
        "SELECT r.*,c.course_name,c.credit_hours,c.instructor FROM registrations r "
        "JOIN courses c ON r.course_code=c.course_code WHERE r.student_id=?", (sid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/metrics", methods=["GET"])
def metrics():
    conn = get_db()
    ts = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    tr = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    conn.close()
    return jsonify({"total_students": ts, "total_registrations": tr, "service": "registration"})

# Initialize DB at module load time (works with both gunicorn and direct run)
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
