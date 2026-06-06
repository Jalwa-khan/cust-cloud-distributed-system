"""CUST Examination System Microservice - CPE4541 CEP Project"""
from flask import Flask, jsonify, request
import sqlite3, os, time, random, logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
DB_PATH = "/data/examination.db"

def get_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_grade(pct):
    if pct >= 90: return "A"
    elif pct >= 80: return "B+"
    elif pct >= 70: return "B"
    elif pct >= 60: return "C+"
    elif pct >= 50: return "C"
    elif pct >= 45: return "D"
    else: return "F"

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            exam_type TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            venue TEXT NOT NULL,
            total_marks INTEGER DEFAULT 100
        );
        CREATE TABLE IF NOT EXISTS exam_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_code TEXT NOT NULL,
            exam_type TEXT NOT NULL,
            marks_obtained REAL NOT NULL,
            total_marks REAL NOT NULL,
            grade TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, course_code, exam_type)
        );
        CREATE TABLE IF NOT EXISTS seat_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            exam_id INTEGER NOT NULL,
            seat_number TEXT NOT NULL,
            hall TEXT NOT NULL,
            UNIQUE(student_id, exam_id)
        );
    """)
    conn.executemany("INSERT OR IGNORE INTO exams (course_code,exam_type,exam_date,start_time,end_time,venue,total_marks) VALUES (?,?,?,?,?,?,?)", [
        ("CPE4541","Mid Term","2026-04-10","09:00","11:00","Exam Hall A",30),
        ("CPE4541","Final Term","2026-06-25","09:00","12:00","Exam Hall B",50),
        ("CPE4521","Mid Term","2026-04-11","14:00","16:00","Exam Hall A",30),
    ])
    for sid,marks in [("FA21-BCE-001",25),("FA21-BCE-002",22),("SP22-BCE-010",27)]:
        g = calculate_grade(marks/30*100)
        try:
            conn.execute("INSERT OR IGNORE INTO exam_results (student_id,course_code,exam_type,marks_obtained,total_marks,grade) VALUES (?,?,?,?,?,?)",
                (sid,"CPE4541","Mid Term",marks,30,g))
        except: pass
    conn.commit(); conn.close()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"healthy","service":"examination","timestamp":time.time()})

@app.route("/api/exams", methods=["GET"])
def get_exams():
    conn = get_db()
    rows = conn.execute("SELECT * FROM exams").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/exams/<course_code>", methods=["GET"])
def get_course_exams(course_code):
    conn = get_db()
    rows = conn.execute("SELECT * FROM exams WHERE course_code=?", (course_code,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/results/<student_id>", methods=["GET"])
def get_results(student_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM exam_results WHERE student_id=?", (student_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/results", methods=["POST"])
def record_result():
    d = request.get_json()
    if not all(k in d for k in ["student_id","course_code","exam_type","marks_obtained","total_marks"]):
        return jsonify({"error":"Missing fields"}), 400
    pct = (d["marks_obtained"] / d["total_marks"]) * 100
    grade = calculate_grade(pct)
    try:
        conn = get_db()
        conn.execute("INSERT INTO exam_results (student_id,course_code,exam_type,marks_obtained,total_marks,grade) VALUES (?,?,?,?,?,?)",
            (d["student_id"],d["course_code"],d["exam_type"],d["marks_obtained"],d["total_marks"],grade))
        conn.commit(); conn.close()
        return jsonify({"message":"Result recorded","grade":grade,"percentage":round(pct,2)}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error":"Result already recorded"}), 409

@app.route("/api/allocate-seat", methods=["POST"])
def allocate_seat():
    d = request.get_json()
    if not all(k in d for k in ["student_id","exam_id"]):
        return jsonify({"error":"Missing fields"}), 400
    seat = f"R{random.randint(1,10)}-S{random.randint(1,30)}"
    hall = f"Hall {random.choice(['A','B','C'])}"
    try:
        conn = get_db()
        conn.execute("INSERT INTO seat_allocations (student_id,exam_id,seat_number,hall) VALUES (?,?,?,?)",
            (d["student_id"],d["exam_id"],seat,hall))
        conn.commit(); conn.close()
        return jsonify({"message":"Seat allocated","seat_number":seat,"hall":hall}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error":"Already allocated"}), 409

@app.route("/api/transcript/<student_id>", methods=["GET"])
def get_transcript(student_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM exam_results WHERE student_id=?", (student_id,)).fetchall()
    conn.close()
    if not rows: return jsonify({"error":"No results found"}), 404
    results = [dict(r) for r in rows]
    tot_obt = sum(r["marks_obtained"] for r in results)
    tot_max = sum(r["total_marks"] for r in results)
    ovr = round(tot_obt/tot_max*100, 2) if tot_max else 0
    return jsonify({"student_id":student_id,"results":results,"overall_percentage":ovr,"overall_grade":calculate_grade(ovr)})

@app.route("/metrics", methods=["GET"])
def metrics():
    conn = get_db()
    te = conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
    tr = conn.execute("SELECT COUNT(*) FROM exam_results").fetchone()[0]
    conn.close()
    return jsonify({"total_exams":te,"total_results":tr,"service":"examination"})

# Initialize DB at module load time (works with both gunicorn and direct run)
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
