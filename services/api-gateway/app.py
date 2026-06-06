"""CUST API Gateway - CPE4541 CEP Project"""
from flask import Flask, jsonify, request, make_response, send_from_directory
import requests, os, time, logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

REGISTRATION_URL = os.getenv("REGISTRATION_URL", "http://registration:5001")
LMS_URL          = os.getenv("LMS_URL",          "http://lms:5002")
EXAM_URL         = os.getenv("EXAM_URL",         "http://examination:5003")

# ====================== WEB DASHBOARD ======================
@app.route("/")
@app.route("/ui")
@app.route("/dashboard")
def web_dashboard():
    return send_from_directory("static", "index.html")

# ====================== HEALTH ======================
@app.route("/health", methods=["GET"])
def health():
    services = {"registration": REGISTRATION_URL, "lms": LMS_URL, "examination": EXAM_URL}
    statuses = {}
    for name, url in services.items():
        try:
            r = requests.get(f"{url}/health", timeout=8)
            statuses[name] = r.json()
        except Exception as e:
            statuses[name] = {"status": "unreachable", "error": str(e)}
    overall = "healthy" if all(s.get("status") == "healthy" for s in statuses.values()) else "degraded"
    return jsonify({"gateway": "healthy", "overall": overall, "services": statuses})

# ====================== PROXY HELPER ======================
def proxy(base, path, method="GET", data=None):
    url = f"{base}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=30)
        else:
            r = requests.post(url, json=data, timeout=30)
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 503

def respond(base, path, method="GET", data=None):
    body, status = proxy(base, path, method, data)
    return make_response(jsonify(body), status)

# ====================== REGISTRATION ======================
@app.route("/api/registration/students", methods=["GET"])
def reg_students():
    return respond(REGISTRATION_URL, "/api/students")

@app.route("/api/registration/students", methods=["POST"])
def add_student():
    return respond(REGISTRATION_URL, "/api/students", "POST", request.get_json())

@app.route("/api/registration/courses", methods=["GET"])
def reg_courses():
    return respond(REGISTRATION_URL, "/api/courses")

# ====================== LMS ======================
@app.route("/api/lms/materials/<course_code>", methods=["GET"])
def lms_materials(course_code):
    return respond(LMS_URL, f"/api/materials/{course_code}")

# ====================== EXAM ======================
@app.route("/api/exam/transcript/<student_id>", methods=["GET"])
def exam_transcript(student_id):
    return respond(EXAM_URL, f"/api/transcript/{student_id}")

# ====================== DASHBOARD METRICS ======================
@app.route("/api/dashboard/metrics", methods=["GET"])
def get_dashboard_metrics():
    m = {}
    for name, url in {"registration": REGISTRATION_URL, "lms": LMS_URL, "examination": EXAM_URL}.items():
        body, status = proxy(url, "/metrics")
        m[name] = body if status == 200 else {"error": "unavailable"}
    return jsonify({"metrics": m, "timestamp": time.time()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)