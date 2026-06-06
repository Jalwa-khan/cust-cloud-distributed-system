

## Project Structure
```
cust-cloud-project/
├── services/
│   ├── api-gateway/        ← Routes requests to all microservices
│   ├── registration/       ← Student & course registration portal
│   ├── lms/                ← Learning Management System
│   └── examination/        ← Exam scheduling, results, transcripts
├── k8s/                    ← Kubernetes manifests (Namespace → HPA)
├── distributed/
│   ├── socket_prog/        ← Socket server + client (Phase 3)
│   ├── mpi_prog/           ← MPI broadcast/scatter/gather/reduce
│   └── multithreading/     ← Thread pool, locks, producer-consumer
├── gpu/                    ← CPU vs GPU benchmark (Numba)
├── monitoring/             ← Docker stats + latency monitor
├── tests/                  ← Full integration + load tests
├── .github/workflows/      ← CI/CD pipeline (GitHub Actions)
├── docker-compose.yml
└── deploy-k8s.sh
```

---

## Phase 2 — Infrastructure Design & Cloud Config

### Architecture
```
Internet → API Gateway (:5000)
              ├─→ Registration Service (:5001)  [SQLite /data]
              ├─→ LMS Service         (:5002)  [SQLite /data]
              └─→ Examination Service (:5003)  [SQLite /data]
```

### Key Design Decisions
| Concern | Solution |
|---|---|
| Service Decomposition | 3 domain microservices + 1 gateway |
| Containerisation | Docker (python:3.11-slim base) |
| Orchestration | Kubernetes Deployments + HPA |
| Storage | PersistentVolumeClaims (1Gi each) |
| Config Management | K8s ConfigMap for service URLs |
| CI/CD | GitHub Actions (lint → build → integration test) |
| Monitoring | Docker stats + custom latency probe |

---

## Phase 3 — Running the System

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- (Optional) Minikube for Kubernetes
- (Optional) mpi4py: `pip install mpi4py`
- (Optional) numba: `pip install numba numpy`

---

### Option A: Docker Compose (Easiest — recommended first)

```bash
# 1. Clone/open the project folder
cd cust-cloud-project

# 2. Build and start all 4 services
docker-compose up --build

# 3. Services are now available:
#    API Gateway    → http://localhost:5000
#    Registration   → http://localhost:5001
#    LMS            → http://localhost:5002
#    Examination    → http://localhost:5003

# 4. Test health
curl http://localhost:5000/health

# 5. Stop
docker-compose down
```

#### Quick API Tests (no extra tools needed)
```bash
# Get all students
curl http://localhost:5000/api/registration/students

# Get courses
curl http://localhost:5000/api/registration/courses

# Register a new student
curl -X POST http://localhost:5000/api/registration/students \
  -H "Content-Type: application/json" \
  -d '{"student_id":"FA24-BCE-100","name":"New Student","email":"new@cust.edu.pk","program":"BCE","semester":1}'

# Register for a course
curl -X POST http://localhost:5000/api/registration/register-course \
  -H "Content-Type: application/json" \
  -d '{"student_id":"FA24-BCE-100","course_code":"CPE4541","semester":"Fall2026"}'

# LMS: Get course materials
curl http://localhost:5000/api/lms/materials/CPE4541

# LMS: Get assignments
curl http://localhost:5000/api/lms/assignments/CPE4541

# Exam: Get transcript
curl http://localhost:5000/api/exam/transcript/FA21-BCE-001

# Dashboard metrics (all services)
curl http://localhost:5000/api/dashboard/metrics
```

---

### Option B: Kubernetes (Minikube)

```bash
# Install Minikube if needed:
# https://minikube.sigs.k8s.io/docs/start/

# Start Minikube
minikube start --cpus=2 --memory=4096

# Enable metrics server (for HPA)
minikube addons enable metrics-server

# Deploy everything
bash deploy-k8s.sh

# Port-forward gateway to localhost
kubectl port-forward svc/gateway-service 5000:5000 -n cust-cloud

# Check pods
kubectl get pods -n cust-cloud

# Check HPA (auto-scaling)
kubectl get hpa -n cust-cloud

# View logs
kubectl logs -l app=registration -n cust-cloud

# Teardown
kubectl delete namespace cust-cloud
```

---

### Distributed Computing Modules

#### Socket Programming (Terminal 1 & 2)
```bash
# Terminal 1 — start server
python distributed/socket_prog/socket_server.py

# Terminal 2 — connect a client
python distributed/socket_prog/socket_client.py FA21-BCE-001

# Open more terminals to simulate multiple students connecting simultaneously
python distributed/socket_prog/socket_client.py FA21-BCE-002
python distributed/socket_prog/socket_client.py SP22-BCE-010
```

#### MPI Distributed Processing
```bash
# Install mpi4py (requires MPI runtime)
pip install mpi4py

# Run with 4 processes (simulates 4 compute nodes)
mpiexec -n 4 python distributed/mpi_prog/mpi_grade_processor.py

# Without MPI installed — runs simulation mode automatically
python distributed/mpi_prog/mpi_grade_processor.py
```

#### Multithreading Concurrent Processing
```bash
# Runs 3 demos: peak registration load, parallel result processing, producer-consumer
python distributed/multithreading/multithreaded_server.py
```

#### GPU Benchmark (Phase 4)
```bash
pip install numba numpy
python gpu/gpu_benchmark.py
```

---

## Phase 4 — Testing, Benchmarking & Evaluation

### Run Full Test Suite
```bash
# Make sure docker-compose is running first
docker-compose up -d

# Run all tests + load benchmark
pip install requests
python tests/test_and_benchmark.py
```

### Run Resource Monitor
```bash
# Collect 10 snapshots every 5 seconds
python monitoring/monitor.py 10 5

# Docker stats (manual)
docker stats cust_gateway cust_registration cust_lms cust_examination
```

### Expected Test Results
| Test | Expected |
|---|---|
| Health checks (4 services) | All healthy |
| GET /api/registration/students | 200 + list |
| POST new student | 201 created |
| Duplicate registration | 409 conflict |
| GET transcript | 200 + grade |
| Load test (concurrency=10) | < 200ms avg |
| Load test throughput | > 50 req/s |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Gateway + all services health |
| GET | `/api/registration/students` | List all students |
| POST | `/api/registration/students` | Add student |
| GET | `/api/registration/courses` | List courses |
| POST | `/api/registration/register-course` | Register course |
| GET | `/api/registration/registrations/{id}` | Student's courses |
| GET | `/api/lms/courses` | LMS course list |
| GET | `/api/lms/materials/{code}` | Course materials |
| POST | `/api/lms/materials` | Upload material |
| GET | `/api/lms/assignments/{code}` | Assignments |
| POST | `/api/lms/submit` | Submit assignment |
| GET | `/api/lms/announcements/{code}` | Announcements |
| GET | `/api/exam/exams` | All exams |
| GET | `/api/exam/results/{student_id}` | Student results |
| POST | `/api/exam/results` | Record result |
| GET | `/api/exam/transcript/{student_id}` | Full transcript |
| POST | `/api/exam/allocate-seat` | Allocate exam seat |
| GET | `/api/dashboard/metrics` | Aggregated metrics |

---

## SDG Alignment
- **SDG-4 (Quality Education):** Digital LMS, exam management, and registration portal improve accessibility and quality of educational services.
- **SDG-9 (Industry & Infrastructure):** Cloud-native, containerised microservices demonstrate modern resilient infrastructure.
- **SDG-11 (Sustainable Cities):** Efficient resource utilisation via auto-scaling reduces energy waste compared to over-provisioned on-premises servers.
