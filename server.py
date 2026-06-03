import cv2
import numpy as np
import threading
import queue
import time
import os
from datetime import datetime
from flask import Flask, request, Response, jsonify
from detect import process_frame
from flask_cors import CORS

# ============================================================================
# CONFIGURATION
# ============================================================================
HOST         = "0.0.0.0"
PORT         = 5000
LOG_FILE     = "security_log.txt"
INTRUDER_DIR = "intruders"
SNAPSHOT_DIR = "snapshots"
CAPTURE_FILE = "latest_capture.jpg"

# Stream quality
STREAM_JPEG_QUALITY = 60
STREAM_WIDTH        = 640
STREAM_HEIGHT       = 480

os.makedirs(INTRUDER_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# ============================================================================
# FLASK APP
# ============================================================================
app = Flask(__name__)
CORS(app)

# ============================================================================
# SHARED STATE
# REMOVED: laptop cam variables — using_laptop_cam, last_esp_time, LAP_CAM_ID
# ============================================================================
latest_frame      = None
latest_result     = "WAITING..."
latest_alert_type = ""
frame_lock        = threading.Lock()

# ============================================================================
# DETECTION QUEUE
# ============================================================================
detection_queue = queue.Queue(maxsize=1)

# ============================================================================
# LOGGING
# ============================================================================
def log_event(event_type, result, source="ESP32-CAM"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] SOURCE={source} | TYPE={event_type} | RESULT={result}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ============================================================================
# DETECTION WORKER THREAD
# Runs continuously — picks frames from queue and runs DeepFace
# ============================================================================
def detection_worker():
    global latest_result

    print("[Detection] Worker thread started.")

    while True:
        try:
            frame, alert_type = detection_queue.get(timeout=1)

            print(f"[Detection] Processing frame | Alert={alert_type}")

            result = process_frame(frame)

            latest_result = result

            log_event(alert_type, result)

            print(f"[Detection] Done | Result={result}")

            detection_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[Detection] Error: {e}")
            continue

# ============================================================================
# HELPER — Display text and color from result
# ============================================================================
def get_display_info(result):
    if result.startswith("KNOWN:"):
        name  = result.split("KNOWN:")[1]
        text  = f"KNOWN: {name}"
        color = (0, 255, 0)
    elif result == "UNKNOWN":
        text  = "UNKNOWN PERSON"
        color = (0, 165, 255)
    elif result == "UNKNOWN_ARMED":
        text  = "ARMED INTRUDER"
        color = (0, 0, 255)
    elif result == "NO_FACE":
        text  = "NO FACE"
        color = (255, 255, 255)
    elif result == "WAITING...":
        text  = "WAITING FOR ESP32..."
        color = (200, 200, 200)
    elif result == "ERROR":
        text  = "ERROR"
        color = (0, 0, 255)
    else:
        text  = result
        color = (255, 255, 255)
    return text, color

# ============================================================================
# MJPEG STREAM GENERATOR
# Only shows ESP32-CAM frames — no laptop fallback
# ============================================================================
def generate_stream():
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY]

    while True:
        with frame_lock:
            frame = latest_frame.copy() if latest_frame is not None else None

        if frame is None:
            # Waiting for ESP32 to send first frame
            blank = np.zeros((STREAM_HEIGHT, STREAM_WIDTH, 3), dtype=np.uint8)
            cv2.putText(blank, "Waiting for ESP32-CAM...",
                        (120, 220), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (255, 255, 255), 2)
            cv2.putText(blank, "Trigger PIR sensor to capture",
                        (100, 260), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (180, 180, 180), 1)
            ret, jpeg = cv2.imencode(".jpg", blank, encode_params)
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" +
                       jpeg.tobytes() + b"\r\n")
            time.sleep(0.1)
            continue

        # Resize for streaming
        frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT))

        display_text, result_color = get_display_info(latest_result)

        # Result overlay
        cv2.putText(frame, display_text,
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, result_color, 2)

        # Trigger type
        cv2.putText(frame, f"Trigger: {latest_alert_type}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 0), 1)

        # Source — always ESP32
        cv2.putText(frame, "Source: ESP32-CAM",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 255, 0), 1)

        # Timestamp
        cv2.putText(frame,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    (10, STREAM_HEIGHT - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (200, 200, 200), 1)

        ret, jpeg = cv2.imencode(".jpg", frame, encode_params)
        if ret:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" +
                   jpeg.tobytes() + b"\r\n")

        time.sleep(0.033)

# ============================================================================
# ROUTE 1 — /detect
# Receives image from ESP32, queues for detection, returns last result fast
# ============================================================================
@app.route("/detect", methods=["POST"])
def detect():
    global latest_frame, latest_alert_type

    alert_type = request.headers.get("X-Alert-Type", "MOTION")

    if "image" not in request.files:
        return "NO_FACE", 200

    file  = request.files["image"]
    npimg = np.frombuffer(file.read(), dtype=np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return "NO_FACE", 200

    # Save latest capture
    cv2.imwrite(CAPTURE_FILE, frame)

    # Update stream frame immediately
    with frame_lock:
        latest_frame      = frame.copy()
        latest_alert_type = alert_type

    # Queue for detection — non blocking
    try:
        detection_queue.put_nowait((frame.copy(), alert_type))
    except queue.Full:
        print("[Server] Detection busy — frame skipped.")

    # Return last known result immediately
    if latest_result.startswith("KNOWN:"):
        return "KNOWN", 200

    return latest_result if latest_result != "WAITING..." else "NO_FACE", 200

# ============================================================================
# ROUTE 2 — /stream
# ============================================================================
@app.route("/stream")
def stream():
    return Response(
        generate_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

# ============================================================================
# ROUTE 3 — /status
# ============================================================================
@app.route("/status")
def status():
    person_name    = ""
    display_result = latest_result
    if latest_result.startswith("KNOWN:"):
        person_name    = latest_result.split("KNOWN:")[1]
        display_result = "KNOWN"

    display_text, _ = get_display_info(latest_result)

    if display_result == "UNKNOWN_ARMED":
        threat_level = "CRITICAL"
    elif display_result == "UNKNOWN":
        threat_level = "HIGH"
    elif display_result == "KNOWN":
        threat_level = "LOW"
    else:
        threat_level = "LOW"

    hardware_outputs = {
        "relay_state" : 1 if display_result == "UNKNOWN_ARMED" else 0,
        "buzzer_siren": 1 if display_result in ["UNKNOWN", "UNKNOWN_ARMED"] else 0,
        "warning_led" : 1 if display_result in ["UNKNOWN", "UNKNOWN_ARMED"] else 0,
    }

    return jsonify({
        "result"          : display_result,
        "person_name"     : person_name,
        "display_text"    : display_text,
        "alert_type"      : latest_alert_type,
        "source"          : "ESP32-CAM",
        "esp32_online"    : latest_frame is not None,
        "timestamp"       : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "threat_level"    : threat_level,
        "hardware_outputs": hardware_outputs,
        "sensors"         : {
            "pir_motion"      : 1 if latest_alert_type == "MOTION" else 0,
            "mq2_gas_ppm"     : 120,
            "window_intrusion": 1 if latest_alert_type == "DOOR" else 0,
        },
        "face_detected"   : display_result in ["KNOWN", "UNKNOWN", "UNKNOWN_ARMED"],
        "confidence_score": 0.92 if display_result == "KNOWN" else
                            0.75 if display_result == "UNKNOWN" else
                            0.88 if display_result == "UNKNOWN_ARMED" else 0.0,
    })

# ============================================================================
# ROUTE 4 — /logs
# ============================================================================
@app.route("/logs")
def logs():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return jsonify(lines[-50:])

# ============================================================================
# ROUTE 5 — /intruders
# ============================================================================
@app.route("/intruders")
def intruders():
    files = sorted(os.listdir(INTRUDER_DIR), reverse=True)
    return jsonify(files)

# ============================================================================
# ROUTE 6 — /health
# ============================================================================
@app.route("/health")
def health():
    return jsonify({
        "status"          : "online",
        "faces_loaded"    : os.path.exists("faces.pkl"),
        "intruder_count"  : len(os.listdir(INTRUDER_DIR)),
        "esp32_online"    : latest_frame is not None,
        "using_laptop_cam": False,
        "detection_queue" : detection_queue.qsize()
    })

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    # Start detection worker only — no laptop cam thread
    d = threading.Thread(target=detection_worker, daemon=True)
    d.start()

    print("=" * 55)
    print("  HOME SECURITY SERVER STARTING")
    print("=" * 55)
    print(f"  Detection : http://0.0.0.0:{PORT}/detect")
    print(f"  Stream    : http://0.0.0.0:{PORT}/stream")
    print(f"  Status    : http://0.0.0.0:{PORT}/status")
    print(f"  Logs      : http://0.0.0.0:{PORT}/logs")
    print(f"  Intruders : http://0.0.0.0:{PORT}/intruders")
    print(f"  Health    : http://0.0.0.0:{PORT}/health")
    print("=" * 55)
    print("  Waiting for ESP32-CAM to send images...")
    print("=" * 55)

    app.run(host=HOST, port=PORT, threaded=True)