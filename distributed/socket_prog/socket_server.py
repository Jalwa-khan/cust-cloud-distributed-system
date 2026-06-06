"""
CUST Distributed Computing - Socket Programming
Server: Simulates a distributed university notification server
CPE4541 CEP Project - Phase 3
Run: python socket_server.py
"""
import socket
import threading
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SERVER] %(message)s")

HOST = "0.0.0.0"
PORT = 9000
MAX_CLIENTS = 10

# Shared state simulating a distributed message board
messages = []
clients = []
lock = threading.Lock()

# Sample university notifications
NOTIFICATIONS = [
    {"type": "registration", "msg": "Course registration for Fall 2026 is now open."},
    {"type": "exam",         "msg": "Mid-term exams scheduled from April 10-15, 2026."},
    {"type": "lms",          "msg": "New lecture material uploaded for CPE4541."},
    {"type": "result",       "msg": "Spring 2026 results have been published."},
    {"type": "general",      "msg": "University will remain closed on June 24, 2026."},
]

def broadcast(message, sender_conn=None):
    """Send message to all connected clients."""
    with lock:
        dead = []
        for conn in clients:
            if conn != sender_conn:
                try:
                    conn.sendall((json.dumps(message) + "\n").encode())
                except Exception:
                    dead.append(conn)
        for conn in dead:
            clients.remove(conn)

def handle_client(conn, addr):
    """Handle individual client connection in a thread."""
    logging.info(f"Client connected: {addr}")
    with lock:
        clients.append(conn)

    # Send welcome + backlog of messages
    welcome = {"type": "welcome", "msg": f"Connected to CUST Notification Server. {len(messages)} pending messages.", "timestamp": time.time()}
    conn.sendall((json.dumps(welcome) + "\n").encode())
    for m in messages[-5:]:  # send last 5 messages
        conn.sendall((json.dumps(m) + "\n").encode())

    try:
        buffer = ""
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                    logging.info(f"From {addr}: {msg}")
                    msg["from"] = str(addr)
                    msg["timestamp"] = time.time()
                    with lock:
                        messages.append(msg)
                    # Echo to sender
                    ack = {"type": "ack", "status": "received", "timestamp": time.time()}
                    conn.sendall((json.dumps(ack) + "\n").encode())
                    # Broadcast to others
                    broadcast(msg, conn)
                except json.JSONDecodeError:
                    err = {"type": "error", "msg": "Invalid JSON"}
                    conn.sendall((json.dumps(err) + "\n").encode())
    except Exception as e:
        logging.error(f"Client {addr} error: {e}")
    finally:
        with lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        logging.info(f"Client disconnected: {addr}")

def notification_broadcaster():
    """Background thread that periodically broadcasts university notifications."""
    idx = 0
    while True:
        time.sleep(10)
        if clients:
            notif = NOTIFICATIONS[idx % len(NOTIFICATIONS)]
            notif["timestamp"] = time.time()
            notif["source"] = "university_system"
            broadcast(notif)
            logging.info(f"Broadcasted notification: {notif['msg']}")
        idx += 1

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(MAX_CLIENTS)
    logging.info(f"CUST Notification Server listening on {HOST}:{PORT}")

    # Start background broadcaster
    t = threading.Thread(target=notification_broadcaster, daemon=True)
    t.start()

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
            logging.info(f"Active connections: {len(clients)}")
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
    finally:
        server.close()

if __name__ == "__main__":
    main()
