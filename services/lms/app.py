"""CUST Learning Management System Microservice - CPE4541 CEP Project"""
from flask import Flask, jsonify, request
import sqlite3, os, time, logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
DB_PATH = "/data/lms.db"

def get_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT UNIQUE NOT NULL,
            course_name TEXT NOT NULL,
            instructor TEXT NOT NULL,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            title TEXT NOT NULL,
            material_type TEXT NOT NULL,
            content TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT NOT NULL,
            total_marks INTEGER DEFAULT 100
        );
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            content TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            marks_obtained INTEGER,
            UNIQUE(assignment_id, student_id)
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.executemany("INSERT OR IGNORE INTO courses (course_code,course_name,instructor,description) VALUES (?,?,?,?)", [
        ("CPE4541","Cloud and Distributed Computing","Dr. Waseem Abbas","Cloud computing, containerization, distributed systems."),
        ("CPE4521","Computer Networks","Dr. Ahmed","Networking protocols, OSI, TCP/IP."),
    ])
    conn.executemany("INSERT OR IGNORE INTO materials (course_code,title,material_type,content) VALUES (?,?,?,?)", [
        ("CPE4541","Lecture 1 - Intro to Cloud","slides","Introduction to cloud computing paradigms and service models..."),
        ("CPE4541","Lab 1 - Docker Basics","lab_manual","Docker installation, images, containers, volumes..."),
        ("CPE4541","Lecture 2 - Kubernetes","slides","Pods, deployments, services, ingress controllers..."),
    ])
    conn.executemany("INSERT OR IGNORE INTO assignments (course_code,title,description,due_date,total_marks) VALUES (?,?,?,?,?)", [
        ("CPE4541","CEP Phase 2 - Architecture Design","Design cloud-native architecture diagram","2026-06-03",25),
        ("CPE4541","CEP Phase 3 - Implementation","Implement and integrate all microservices","2026-06-10",30),
        ("CPE4541","CEP Phase 4 - Testing Report","Benchmark and evaluate system performance","2026-06-18",20),
    ])
    conn.executemany("INSERT OR IGNORE INTO announcements (course_code,title,body) VALUES (?,?,?)", [
        ("CPE4541","CEP Project Released","CEP project guidelines are available. All phases must be completed by June 24, 2026."),
        ("CPE4541","Lab Session Reminder","Please attend all lab sessions for project guidance and progress review."),
    ])
    conn.commit(); conn.close()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "lms", "timestamp": time.time()})

@app.route("/api/courses", methods=["GET"])
def get_courses():
    conn = get_db()
    rows = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/materials/<course_code>", methods=["GET"])
def get_materials(course_code):
    conn = get_db()
    rows = conn.execute("SELECT * FROM materials WHERE course_code=?", (course_code,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/materials", methods=["POST"])
def upload_material():
    d = request.get_json()
    if not all(k in d for k in ["course_code","title","material_type","content"]):
        return jsonify({"error": "Missing fields"}), 400
    conn = get_db()
    conn.execute("INSERT INTO materials (course_code,title,material_type,content) VALUES (?,?,?,?)",
        (d["course_code"],d["title"],d["material_type"],d["content"]))
    conn.commit(); conn.close()
    return jsonify({"message": "Material uploaded"}), 201

@app.route("/api/assignments/<course_code>", methods=["GET"])
def get_assignments(course_code):
    conn = get_db()
    rows = conn.execute("SELECT * FROM assignments WHERE course_code=?", (course_code,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/submit-assignment", methods=["POST"])
def submit_assignment():
    d = request.get_json()
    if not all(k in d for k in ["assignment_id","student_id","content"]):
        return jsonify({"error": "Missing fields"}), 400
    try:
        conn = get_db()
        conn.execute("INSERT INTO submissions (assignment_id,student_id,content) VALUES (?,?,?)",
            (d["assignment_id"],d["student_id"],d["content"]))
        conn.commit(); conn.close()
        return jsonify({"message": "Assignment submitted"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Already submitted"}), 409

@app.route("/api/announcements/<course_code>", methods=["GET"])
def get_announcements(course_code):
    conn = get_db()
    rows = conn.execute("SELECT * FROM announcements WHERE course_code=?", (course_code,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/metrics", methods=["GET"])
def metrics():
    conn = get_db()
    tc = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    tm = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
    ts = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    conn.close()
    return jsonify({"total_courses": tc, "total_materials": tm, "total_submissions": ts, "service": "lms"})

# Initialize DB at module load time (works with both gunicorn and direct run)
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
