"""
CUST Distributed Computing - Socket Programming
Client: Simulates a student/service node connecting to notification server
CPE4541 CEP Project - Phase 3
Run: python socket_client.py [student_id]
"""
import socket
import threading
import json
import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [CLIENT] %(message)s")

HOST = "127.0.0.1"
PORT = 9000

def receive_messages(sock):
    """Background thread to receive and print server messages."""
    buffer = ""
    try:
        while True:
            data = sock.recv(1024).decode()
            if not data:
                logging.info("Server closed connection.")
                break
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    try:
                        msg = json.loads(line)
                        mtype = msg.get("type","msg")
                        ts = time.strftime("%H:%M:%S", time.localtime(msg.get("timestamp", time.time())))
                        print(f"\n[{ts}] [{mtype.upper()}] {msg.get('msg', msg)}")
                    except json.JSONDecodeError:
                        print(f"\nRaw: {line}")
    except Exception as e:
        logging.error(f"Receive error: {e}")

def main():
    student_id = sys.argv[1] if len(sys.argv) > 1 else "FA21-BCE-001"
    logging.info(f"Connecting as {student_id} to {HOST}:{PORT}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        logging.info("Connected to CUST Notification Server")
    except ConnectionRefusedError:
        logging.error("Could not connect. Is socket_server.py running?")
        return

    # Start receiver thread
    t = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    t.start()

    # Simulate student sending messages
    test_messages = [
        {"type": "query",  "msg": f"Student {student_id} requesting registration status"},
        {"type": "update", "msg": f"Student {student_id} submitted assignment for CPE4541"},
        {"type": "query",  "msg": f"Student {student_id} checking exam schedule"},
    ]

    try:
        for msg in test_messages:
            time.sleep(2)
            sock.sendall((json.dumps(msg) + "\n").encode())
            logging.info(f"Sent: {msg['msg']}")

        # Keep alive to receive broadcasts
        logging.info("Listening for server broadcasts (Ctrl+C to exit)...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Client disconnecting...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
