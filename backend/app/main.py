"""
Sentinel Security Platform - FastAPI Backend
Real-time WebSocket telemetry server with ESP32 camera integration
"""

import os
import sys
import asyncio
import json
import logging
import time
import math
import queue
import threading
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel
import uvicorn

# ── Import your real face detection pipeline ──
# Adjust this path to match your actual home_secure folder location
HOME_SECURE_PATH = r"C:\Users\Saumya\OneDrive\Desktop\home_secure"
if HOME_SECURE_PATH not in sys.path:
    sys.path.insert(0, HOME_SECURE_PATH)

try:
    from detect import process_frame as real_process_frame
    REAL_DETECTION = True
    print("[AI] Real face detection loaded from home_secure/detect.py")
except ImportError as e:
    REAL_DETECTION = False
    print(f"[AI] detect.py not found — using simulation. Error: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SNAPSHOT_DIR = os.path.join("backend", "snapshots")
CAPTURE_FILE = os.path.join("backend", "snapshots", "latest_capture.jpg")
LOG_FILE     = os.path.join("backend", "security_log.txt")
ESP_TIMEOUT  = 5
LAP_CAM_ID   = 0

os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# ==================== DATA MODELS ====================

class SensorData(BaseModel):
    pir_motion       : int   = 0
    mq2_gas_ppm      : int   = 120
    window_intrusion : int   = 0

class AIAnalysis(BaseModel):
    face_detected       : bool            = False
    verdict             : str             = "SCANNING"
    person_name         : str             = ""
    confidence_score    : float           = 0.0
    latest_snapshot_url : Optional[str]   = None
    bounding_box        : Optional[List[float]] = None

class HardwareOutputs(BaseModel):
    relay_state  : int = 0
    buzzer_siren : int = 0
    warning_led  : int = 0

class TelemetryPayload(BaseModel):
    timestamp        : str
    system_status    : str = "DISARMED"
    threat_level     : str = "LOW"
    sensors          : SensorData
    ai_analysis      : AIAnalysis
    hardware_outputs : HardwareOutputs

# ==================== GLOBAL STATE ====================

class SecurityState:
    def __init__(self):
        self.system_status   = "DISARMED"
        self.threat_level    = "LOW"
        self.sensors         = SensorData()
        self.ai_analysis     = AIAnalysis()
        self.hardware_outputs = HardwareOutputs()
        self.last_alert_type = ""
        self.last_esp_time   = 0.0
        self.using_laptop_cam = False
        self.latest_frame    = None
        self.frame_lock      = threading.Lock()

    def get_telemetry(self) -> dict:
        base = {
            "timestamp"       : datetime.utcnow().isoformat() + "Z",
            "system_status"   : self.system_status,
            "threat_level"    : self.threat_level,
            "sensors"         : self.sensors.model_dump()
                                if hasattr(self.sensors, 'model_dump')
                                else self.sensors.dict(),
            "ai_analysis"     : self.ai_analysis.model_dump()
                                if hasattr(self.ai_analysis, 'model_dump')
                                else self.ai_analysis.dict(),
            "hardware_outputs": self.hardware_outputs.model_dump()
                                if hasattr(self.hardware_outputs, 'model_dump')
                                else self.hardware_outputs.dict(),
            "source"          : "LAPTOP-CAM" if self.using_laptop_cam else "ESP32-CAM",
            "esp32_online"    : (time.time() - self.last_esp_time) < ESP_TIMEOUT,
        }
        return base

security_state = SecurityState()

# Detection queue — maxsize 1 = always process latest frame only
detection_queue = queue.Queue(maxsize=1)
main_loop       = None

# ==================== WEBSOCKET MANAGER ====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# ==================== ESP32 CAMERA CLIENT ====================

class ESP32CameraClient:
    def __init__(self, stream_url: str = "http://10.98.121.237:81/stream"):
        self.stream_url   = stream_url
        self.cap          = None
        self.is_connected = False

    async def connect(self):
        try:
            self.cap = await asyncio.to_thread(cv2.VideoCapture, self.stream_url)
            if self.cap.isOpened():
                self.is_connected = True
                logger.info(f"ESP32 camera connected: {self.stream_url}")
                return True
            logger.error("Failed to open ESP32 stream")
            return False
        except Exception as e:
            logger.error(f"ESP32 connection error: {e}")
            return False

    async def get_frame(self):
        if not self.is_connected or not self.cap:
            return None
        ret, frame = await asyncio.to_thread(self.cap.read)
        return frame if ret else None

    def release(self):
        if self.cap:
            self.cap.release()
            self.is_connected = False
            logger.info("ESP32 camera released")

esp32_client = ESP32CameraClient()

# ==================== AI ENGINE ====================

class AIEngine:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.frame_skip  = 2
        self.frame_count = 0

    def process_frame_simulation(self, frame: np.ndarray) -> dict:
        """Fallback simulation when detect.py is not available."""
        self.frame_count += 1
        if self.frame_count % self.frame_skip != 0:
            return {
                "face_detected"  : security_state.ai_analysis.face_detected,
                "verdict"        : security_state.ai_analysis.verdict,
                "person_name"    : security_state.ai_analysis.person_name,
                "confidence_score": security_state.ai_analysis.confidence_score,
                "bounding_box"   : security_state.ai_analysis.bounding_box
            }

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) == 0:
            return {
                "face_detected"  : False,
                "verdict"        : "CLEAR",
                "person_name"    : "",
                "confidence_score": 0.0,
                "bounding_box"   : None
            }

        largest  = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest
        confidence = min(0.95, float((w * h) / (frame.shape[0] * frame.shape[1]) * 10))

        import random
        verdict     = "KNOWN" if random.random() > 0.3 else "UNKNOWN"
        person_name = "Demo Person" if verdict == "KNOWN" else ""

        return {
            "face_detected"  : True,
            "verdict"        : verdict,
            "person_name"    : person_name,
            "confidence_score": confidence,
            "bounding_box"   : [int(x), int(y), int(w), int(h)]
        }

    def process_frame_real(self, frame: np.ndarray) -> dict:
        """Real detection using home_secure/detect.py"""
        try:
            result = real_process_frame(frame)

            # Parse KNOWN:Name format
            if result.startswith("KNOWN:"):
                name    = result.split("KNOWN:")[1].strip()
                verdict = "KNOWN"
                return {
                    "face_detected"  : True,
                    "verdict"        : verdict,
                    "person_name"    : name,
                    "confidence_score": 0.92,
                    "bounding_box"   : None
                }
            elif result == "UNKNOWN":
                return {
                    "face_detected"  : True,
                    "verdict"        : "UNKNOWN",
                    "person_name"    : "",
                    "confidence_score": 0.75,
                    "bounding_box"   : None
                }
            elif result == "UNKNOWN_ARMED":
                return {
                    "face_detected"  : True,
                    "verdict"        : "UNKNOWN_ARMED",
                    "person_name"    : "",
                    "confidence_score": 0.88,
                    "bounding_box"   : None
                }
            else:
                return {
                    "face_detected"  : False,
                    "verdict"        : "SCANNING",
                    "person_name"    : "",
                    "confidence_score": 0.0,
                    "bounding_box"   : None
                }
        except Exception as e:
            logger.error(f"Real detection error: {e}")
            return {
                "face_detected"  : False,
                "verdict"        : "ERROR",
                "person_name"    : "",
                "confidence_score": 0.0,
                "bounding_box"   : None
            }

    def process_frame(self, frame: np.ndarray) -> dict:
        if REAL_DETECTION:
            return self.process_frame_real(frame)
        return self.process_frame_simulation(frame)

    def save_snapshot(self, frame: np.ndarray, filename: str):
        filepath = os.path.join(SNAPSHOT_DIR, filename)
        cv2.imwrite(filepath, frame)
        return f"/snapshots/{filename}"

ai_engine = AIEngine()

# ==================== LOGGING ====================

def log_event(event_type: str, result: str, source: str = "ESP32-CAM"):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] SOURCE={source} | TYPE={event_type} | RESULT={result}"
    logger.info(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ==================== DETECTION WORKER THREAD ====================

def detection_worker():
    """Runs in background thread. Picks frames from queue and runs detection."""
    logger.info("[Detection] Worker thread started.")

    while True:
        try:
            frame, alert_type = detection_queue.get(timeout=1)
            logger.info(f"[Detection] Processing | Alert={alert_type}")

            result_dict = ai_engine.process_frame(frame)

            # Update global state
            security_state.ai_analysis = AIAnalysis(**result_dict)
            security_state.last_alert_type = alert_type

            # Update sensor states based on alert type
            if alert_type == "MOTION":
                security_state.sensors.pir_motion = 1
            elif alert_type == "GAS":
                security_state.sensors.mq2_gas_ppm = 350
            elif alert_type == "DOOR":
                security_state.sensors.window_intrusion = 1

            # Update hardware outputs based on verdict
            verdict = result_dict.get("verdict", "SCANNING")
            if verdict == "UNKNOWN_ARMED":
                security_state.hardware_outputs.relay_state  = 1
                security_state.hardware_outputs.buzzer_siren = 1
                security_state.hardware_outputs.warning_led  = 1
                security_state.threat_level = "CRITICAL"
            elif verdict == "UNKNOWN":
                security_state.hardware_outputs.buzzer_siren = 1
                security_state.hardware_outputs.warning_led  = 1
                security_state.threat_level = "HIGH"
            elif verdict == "KNOWN":
                security_state.hardware_outputs.relay_state  = 0
                security_state.hardware_outputs.buzzer_siren = 0
                security_state.hardware_outputs.warning_led  = 0
                security_state.threat_level = "LOW"

            # Save snapshot for unknown persons
            if verdict in ["UNKNOWN", "UNKNOWN_ARMED"]:
                ts       = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"intruder_{ts}.jpg"
                url      = ai_engine.save_snapshot(frame, filename)
                security_state.ai_analysis.latest_snapshot_url = url

            # Save latest capture
            cv2.imwrite(CAPTURE_FILE, frame)

            log_event(alert_type, verdict)

            # Broadcast updated state to React
            if main_loop and not main_loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(security_state.get_telemetry()),
                    main_loop
                )

            logger.info(f"[Detection] Done | Verdict={verdict}")
            detection_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"[Detection] Error: {e}")
            continue

# ==================== LAPTOP CAMERA FALLBACK THREAD ====================

def laptop_cam_thread():
    """Activates laptop camera when ESP32-CAM goes offline."""
    cap         = None
    cam_open    = False
    frame_count = 0

    while True:
        time.sleep(0.033)

        esp_active = (time.time() - security_state.last_esp_time) < ESP_TIMEOUT

        if esp_active:
            if cam_open:
                cap.release()
                cam_open = False
                security_state.using_laptop_cam = False
                logger.info("[LapCam] ESP32-CAM back online.")
            continue

        if not cam_open:
            logger.info("[LapCam] Activating laptop camera...")
            cap = cv2.VideoCapture(LAP_CAM_ID)
            if not cap.isOpened():
                logger.warning("[LapCam] Camera not found. Retry in 3s...")
                time.sleep(3)
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cam_open = True
            security_state.using_laptop_cam = True
            frame_count = 0
            logger.info("[LapCam] Active.")

        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.05)
            continue

        frame_count += 1

        with security_state.frame_lock:
            security_state.latest_frame = frame.copy()

        if frame_count % 10 == 0:
            try:
                detection_queue.put_nowait((frame.copy(), "LAPTOP_CAM"))
            except queue.Full:
                pass

# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_event_loop()

    logger.info("Starting Sentinel Security Platform...")

    # Start background threads
    threading.Thread(target=detection_worker,  daemon=True).start()
    threading.Thread(target=laptop_cam_thread, daemon=True).start()
    logger.info("[Threads] Detection worker and laptop cam fallback started.")

    # Try to connect to ESP32 camera
    await esp32_client.connect()

    # Start async tasks
    telemetry_task = asyncio.create_task(telemetry_broadcast_loop())
    camera_task    = asyncio.create_task(camera_processing_loop())

    yield

    logger.info("Shutting down...")
    esp32_client.release()
    telemetry_task.cancel()
    camera_task.cancel()
    try:
        await asyncio.gather(telemetry_task, camera_task, return_exceptions=True)
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

app = FastAPI(
    title="Sentinel Security API",
    description="Real-time security monitoring platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== BACKGROUND TASKS ====================

async def telemetry_broadcast_loop():
    while True:
        try:
            await manager.broadcast(security_state.get_telemetry())
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telemetry error: {e}")
            await asyncio.sleep(1)

async def camera_processing_loop():
    """Handles ESP32 stream frames when connected."""
    while True:
        try:
            frame = await esp32_client.get_frame()
            if frame is not None:
                with security_state.frame_lock:
                    security_state.latest_frame = frame.copy()
                # Queue for detection
                try:
                    detection_queue.put_nowait((frame.copy(), "ESP32_STREAM"))
                except queue.Full:
                    pass
            else:
                await simulate_sensor_data()
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Camera loop error: {e}")
            await asyncio.sleep(1)

# ==================== DEMO FRAME GENERATOR ====================

def generate_demo_frame() -> np.ndarray:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    for gx in range(0, 640, 40):
        cv2.line(frame, (gx, 0), (gx, 480), (15, 15, 22), 1)
    for gy in range(0, 480, 40):
        cv2.line(frame, (0, gy), (640, gy), (15, 15, 22), 1)

    tint_map = {
        'CRITICAL': (0, 0, 40), 'HIGH': (0, 10, 30),
        'MEDIUM': (0, 15, 20), 'LOW': (0, 0, 0)
    }
    tint = tint_map.get(security_state.threat_level, (0, 0, 0))
    if any(tint):
        overlay = np.full_like(frame, tint, dtype=np.uint8)
        cv2.addWeighted(frame, 0.85, overlay, 0.15, 0, frame)

    bracket_colors = {
        'CRITICAL': (50, 50, 220), 'HIGH': (50, 120, 220),
        'MEDIUM': (50, 180, 220), 'LOW': (120, 180, 212)
    }
    bc = bracket_colors.get(security_state.threat_level, (120, 180, 212))
    pts = [
        (20,20,60,20,20,60), (580,20,620,20,620,60),
        (20,420,20,460,60,460), (620,420,620,460,580,460)
    ]
    for x1,y1,x2,y2,x3,y3 in pts:
        cv2.line(frame, (x1,y1), (x2,y2), bc, 2)
        cv2.line(frame, (x1,y1), (x3,y3), bc, 2)

    if security_state.ai_analysis.face_detected and security_state.ai_analysis.bounding_box:
        bb = security_state.ai_analysis.bounding_box
        x, y, w, h = int(bb[0]), int(bb[1]), int(bb[2]), int(bb[3])
        verdict  = security_state.ai_analysis.verdict
        conf     = security_state.ai_analysis.confidence_score
        color_map = {
            'UNKNOWN': (60, 60, 230), 'UNKNOWN_ARMED': (30, 30, 255),
            'KNOWN': (80, 210, 80), 'CLEAR': (120, 180, 212)
        }
        fcolor = color_map.get(verdict, (120, 180, 212))
        cv2.rectangle(frame, (x-1, y-1), (x+w+1, y+h+1),
                      tuple(c//3 for c in fcolor), 3)
        cv2.rectangle(frame, (x, y), (x+w, y+h), fcolor, 2)

        # Show person name if known
        name    = security_state.ai_analysis.person_name
        label   = f"{verdict} — {name}  {conf*100:.0f}%" if name else f"{verdict}  {conf*100:.0f}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x, y-24), (x+tw+12, y), fcolor, -1)
        cv2.putText(frame, label, (x+6, y-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 1, cv2.LINE_AA)

    status_color = (80, 200, 80) if security_state.system_status == 'ARMED' else (120, 120, 120)
    cv2.rectangle(frame, (10, 440), (140, 468), (20, 20, 25), -1)
    cv2.putText(frame, security_state.system_status, (16, 459),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1, cv2.LINE_AA)

    threat_colors = {
        'CRITICAL': (40, 40, 210), 'HIGH': (40, 100, 210),
        'MEDIUM': (40, 160, 220), 'LOW': (80, 180, 80)
    }
    tc = threat_colors.get(security_state.threat_level, (80, 80, 80))
    cv2.rectangle(frame, (150, 440), (310, 468), (20, 20, 25), -1)
    cv2.putText(frame, f"THREAT: {security_state.threat_level}", (156, 459),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, tc, 1, cv2.LINE_AA)

    ts = datetime.utcnow().strftime("%Y-%m-%d  %H:%M:%S UTC")
    cv2.putText(frame, ts, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 130), 1, cv2.LINE_AA)

    src = "LAPTOP CAM" if security_state.using_laptop_cam else "ESP32-CAM"
    cv2.putText(frame, f"CAM-01  {src}", (10, 472),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (70, 70, 100), 1, cv2.LINE_AA)

    cv2.rectangle(frame, (560, 10), (628, 36), (30, 30, 160), -1)
    cv2.putText(frame, "LIVE", (568, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 255), 1, cv2.LINE_AA)
    cv2.circle(frame, (616, 52), 5, (0, 0, 200), -1)

    return frame

# ==================== SENSOR SIMULATION ====================

async def simulate_sensor_data():
    import random
    now = time.time()

    if not hasattr(simulate_sensor_data, '_motion_until'):
        simulate_sensor_data._motion_until = 0.0
    if now < simulate_sensor_data._motion_until:
        security_state.sensors.pir_motion = 1
    elif random.random() > 0.88:
        simulate_sensor_data._motion_until = now + random.uniform(3, 8)
        security_state.sensors.pir_motion = 1
    else:
        security_state.sensors.pir_motion = 0

    if not hasattr(simulate_sensor_data, '_gas_spike_end'):
        simulate_sensor_data._gas_spike_end  = 0.0
        simulate_sensor_data._gas_spike_peak = 0
    base   = 120 + 30 * math.sin(now * 0.04)
    noise  = random.gauss(0, 4)
    spike  = 0
    if now < simulate_sensor_data._gas_spike_end:
        remaining = simulate_sensor_data._gas_spike_end - now
        spike = simulate_sensor_data._gas_spike_peak * (remaining / 15.0)
    elif random.random() > 0.97:
        simulate_sensor_data._gas_spike_end  = now + 15.0
        simulate_sensor_data._gas_spike_peak = random.uniform(100, 280)
        spike = simulate_sensor_data._gas_spike_peak
    security_state.sensors.mq2_gas_ppm = max(80, min(600, int(base + noise + spike)))

    if not hasattr(simulate_sensor_data, '_window_until'):
        simulate_sensor_data._window_until = 0.0
    if now < simulate_sensor_data._window_until:
        security_state.sensors.window_intrusion = 1
    elif random.random() > 0.98:
        simulate_sensor_data._window_until = now + 10.0
        security_state.sensors.window_intrusion = 1
    else:
        security_state.sensors.window_intrusion = 0

    if not hasattr(simulate_sensor_data, '_face_until'):
        simulate_sensor_data._face_until   = 0.0
        simulate_sensor_data._face_verdict = 'CLEAR'
        simulate_sensor_data._face_duration = 8.0
    if now < simulate_sensor_data._face_until:
        elapsed_frac = 1.0 - (simulate_sensor_data._face_until - now) / simulate_sensor_data._face_duration
        security_state.ai_analysis.face_detected    = True
        security_state.ai_analysis.verdict          = simulate_sensor_data._face_verdict
        security_state.ai_analysis.confidence_score = min(0.97, 0.55 + 0.42 * elapsed_frac)
        security_state.ai_analysis.bounding_box     = [280, 140, 160, 185]
    elif random.random() > 0.90:
        dur = random.uniform(5, 12)
        simulate_sensor_data._face_until    = now + dur
        simulate_sensor_data._face_duration = dur
        simulate_sensor_data._face_verdict  = random.choice(['KNOWN', 'KNOWN', 'KNOWN', 'UNKNOWN'])
        security_state.ai_analysis.face_detected    = True
        security_state.ai_analysis.verdict          = simulate_sensor_data._face_verdict
        security_state.ai_analysis.person_name      = "Demo Person" if simulate_sensor_data._face_verdict == "KNOWN" else ""
        security_state.ai_analysis.confidence_score = 0.55
        security_state.ai_analysis.bounding_box     = [280, 140, 160, 185]
    else:
        security_state.ai_analysis.face_detected    = False
        security_state.ai_analysis.verdict          = 'CLEAR'
        security_state.ai_analysis.person_name      = ""
        security_state.ai_analysis.confidence_score = 0.0
        security_state.ai_analysis.bounding_box     = None

    # Threat auto-escalation
    if security_state.sensors.window_intrusion:
        security_state.threat_level = 'CRITICAL'
    elif security_state.ai_analysis.verdict == 'UNKNOWN' and security_state.system_status == 'ARMED':
        security_state.threat_level = 'HIGH'
    elif security_state.ai_analysis.verdict == 'UNKNOWN':
        security_state.threat_level = 'MEDIUM'
    elif security_state.sensors.mq2_gas_ppm > 300:
        security_state.threat_level = 'MEDIUM'
    elif security_state.sensors.pir_motion and security_state.system_status == 'ARMED':
        security_state.threat_level = 'MEDIUM'
    else:
        level_order = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        idx = level_order.index(security_state.threat_level)
        if idx > 0:
            if idx == 1 and random.random() > 0.70:
                security_state.threat_level = 'LOW'
            elif idx > 1:
                security_state.threat_level = level_order[idx - 1]

    # Hardware auto-response
    tl = security_state.threat_level
    if tl == 'CRITICAL':
        security_state.hardware_outputs.warning_led  = 1
        security_state.hardware_outputs.buzzer_siren = 1
        security_state.hardware_outputs.relay_state  = 1
    elif tl == 'HIGH':
        security_state.hardware_outputs.warning_led  = 1
        security_state.hardware_outputs.buzzer_siren = 1
        security_state.hardware_outputs.relay_state  = 0
    elif tl == 'MEDIUM':
        security_state.hardware_outputs.warning_led  = 1
        security_state.hardware_outputs.buzzer_siren = 0
        security_state.hardware_outputs.relay_state  = 0
    else:
        security_state.hardware_outputs.warning_led  = 0
        security_state.hardware_outputs.buzzer_siren = 0

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "name"     : "Sentinel Security API",
        "version"  : "1.0.0",
        "status"   : "running",
        "websocket": "ws://localhost:8000/ws/telemetry",
        "real_ai"  : REAL_DETECTION,
    }

@app.get("/health")
async def health():
    return {
        "status"          : "healthy",
        "camera_connected": esp32_client.is_connected,
        "real_detection"  : REAL_DETECTION,
        "using_laptop_cam": security_state.using_laptop_cam,
        "esp32_online"    : (time.time() - security_state.last_esp_time) < ESP_TIMEOUT,
        "clients"         : len(manager.active_connections),
        "timestamp"       : datetime.utcnow().isoformat(),
    }

@app.get("/telemetry")
async def get_telemetry():
    return security_state.get_telemetry()

# ── NEW: /detect endpoint for ESP32-CAM HTTP POST ──
@app.post("/detect")
async def detect(request: Request):
    """
    ESP32-CAM posts JPEG image here on motion/door/gas trigger.
    Returns KNOWN / UNKNOWN / UNKNOWN_ARMED / NO_FACE instantly.
    Actual detection happens async in background worker.
    """
    security_state.last_esp_time = time.time()
    alert_type = request.headers.get("X-Alert-Type", "MOTION")

    form = await request.form()
    if "image" not in form:
        return Response(content="NO_FACE", media_type="text/plain")

    data  = await form["image"].read()
    npimg = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return Response(content="NO_FACE", media_type="text/plain")

    # Update stream frame immediately
    with security_state.frame_lock:
        security_state.latest_frame = frame.copy()

    # Queue for async detection — returns instantly
    try:
        detection_queue.put_nowait((frame.copy(), alert_type))
    except queue.Full:
        logger.info("[Detect] Queue full — skipping.")

    # Return last known result immediately to ESP32-CAM
    current = security_state.ai_analysis.verdict
    if current == "KNOWN":
        return Response(content="KNOWN",        media_type="text/plain")
    elif current == "UNKNOWN":
        return Response(content="UNKNOWN",      media_type="text/plain")
    elif current == "UNKNOWN_ARMED":
        return Response(content="UNKNOWN_ARMED",media_type="text/plain")
    else:
        return Response(content="NO_FACE",      media_type="text/plain")

# ── NEW: /stream endpoint (alias for /video with laptop cam support) ──
@app.get("/stream")
async def stream():
    """MJPEG stream — uses laptop cam or ESP32 or demo frame."""
    async def generate():
        while True:
            # Priority 1 — latest frame from any source
            with security_state.frame_lock:
                frame = security_state.latest_frame.copy() \
                        if security_state.latest_frame is not None else None

            if frame is None:
                # Priority 2 — demo frame
                frame = generate_demo_frame()

            _, buffer    = cv2.imencode('.jpg', frame,
                           [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_bytes  = buffer.tobytes()
            yield (
    b'--frame\r\n'
    b'Content-Type: image/jpeg\r\n' +
    f'Content-Length: {len(frame_bytes)}\r\n\r\n'.encode() +
    frame_bytes + b'\r\n'
)
            yield header + frame_bytes + b"\r\n"

            await asyncio.sleep(0.033)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await manager.connect(websocket)

    # Send current state immediately on connect
    await websocket.send_json(security_state.get_telemetry())

    try:
        while True:
            data    = await websocket.receive_text()
            message = json.loads(data)
            action  = message.get("action", "")

            if action in ("arm", "ARM"):
                security_state.system_status = "ARMED"
                security_state.hardware_outputs.relay_state = 1
                logger.info("System ARMED")

            elif action in ("disarm", "DISARM"):
                security_state.system_status = "DISARMED"
                security_state.threat_level  = "LOW"
                security_state.hardware_outputs.relay_state  = 0
                security_state.hardware_outputs.buzzer_siren = 0
                security_state.hardware_outputs.warning_led  = 0
                logger.info("System DISARMED")

            elif action in ("reset_alert", "RESET_ALARM"):
                security_state.threat_level  = "LOW"
                security_state.hardware_outputs.buzzer_siren = 0
                security_state.hardware_outputs.warning_led  = 0
                security_state.ai_analysis = AIAnalysis()
                logger.info("Alarm RESET")

            # Broadcast updated state immediately after command
            await manager.broadcast(security_state.get_telemetry())

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/video")
async def video_stream():
    """Original /video endpoint — kept for compatibility."""
    async def generate():
        while True:
            with security_state.frame_lock:
                frame = security_state.latest_frame.copy() \
                        if security_state.latest_frame is not None else None

            if frame is None:
                frame = generate_demo_frame()

            _, buffer   = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (
                b'--frame\r\n' +
                b'Content-Type: image/jpeg\r\n' +
                f'Content-Length: {len(frame_bytes)}\r\n\r\n'.encode() +
                frame_bytes + b'\r\n'
            )
            await asyncio.sleep(0.033)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/snapshots/{filename}")
async def get_snapshot(filename: str):
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath)
    return {"error": "Snapshot not found"}

@app.get("/api/logs")
async def api_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return lines[-50:]

@app.get("/api/intruders")
async def api_intruders():
    files = [f for f in os.listdir(SNAPSHOT_DIR) if f.startswith("intruder_")]
    return sorted(files, reverse=True)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)