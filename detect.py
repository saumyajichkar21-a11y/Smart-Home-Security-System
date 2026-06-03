import cv2
import os
import time
import datetime
import requests
import pickle
import numpy as np
import face_recognition

# ══════════════════════════════════════════════════════════════════════
#  TELEGRAM CONFIG
# ══════════════════════════════════════════════════════════════════════
BOT_TOKEN = "8751792537:AAGQwCXSRQsx6B-AYfGTH3w-c88s1PDYJD4"
CHAT_ID   = "8351162212"

# ══════════════════════════════════════════════════════════════════════
#  FOLDERS
# ══════════════════════════════════════════════════════════════════════
SAVE_DIR = "intruders"
os.makedirs(SAVE_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════
#  LOAD KNOWN FACES DATABASE
# ══════════════════════════════════════════════════════════════════════
try:
    with open("faces.pkl", "rb") as f:
        db_data = pickle.load(f)

    if isinstance(db_data, dict):
        known_face_names      = list(db_data.keys())
        known_face_encodings  = list(db_data.values())
    elif isinstance(db_data, (tuple, list)):
        known_face_encodings  = db_data[0]
        known_face_names      = db_data[1]
    else:
        known_face_encodings  = []
        known_face_names      = []

    print(f"[DB] Loaded {len(known_face_encodings)} known faces.")

except Exception as e:
    print(f"[DB] Load failed — everyone will be UNKNOWN. Error: {e}")
    known_face_encodings = []
    known_face_names     = []

# ══════════════════════════════════════════════════════════════════════
#  TELEGRAM COOLDOWN
# ══════════════════════════════════════════════════════════════════════
_last_telegram_time = 0
TELEGRAM_COOLDOWN   = 30  # seconds between Telegram alerts

# ══════════════════════════════════════════════════════════════════════
#  LIGHTING PREPROCESSOR
# ══════════════════════════════════════════════════════════════════════

def _brightness(frame: np.ndarray) -> float:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return float(np.mean(hsv[:, :, 2]))

def _is_ir_frame(frame: np.ndarray) -> bool:
    b, g, r = cv2.split(frame)
    return float(np.mean(np.abs(b.astype(int) - r.astype(int)))) < 8.0

def _clahe_lab(frame: np.ndarray,
               clip: float = 3.0,
               tile: tuple  = (8, 8)) -> np.ndarray:
    lab      = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b  = cv2.split(lab)
    clahe    = cv2.createCLAHE(clipLimit=clip, tileGridSize=tile)
    l        = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

def _gamma(frame: np.ndarray, g: float) -> np.ndarray:
    lut = np.array([
        min(255, int((i / 255.0) ** (1.0 / g) * 255))
        for i in range(256)
    ], dtype=np.uint8)
    return cv2.LUT(frame, lut)

def _sharpen(frame: np.ndarray, amount: float = 0.6) -> np.ndarray:
    blur = cv2.GaussianBlur(frame, (0, 0), 3)
    return cv2.addWeighted(frame, 1 + amount, blur, -amount, 0)

def _denoise(frame: np.ndarray, h: int = 7) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(frame, None, h, h, 7, 21)

def preprocess(frame: np.ndarray) -> tuple:
    if frame is None or frame.size == 0:
        return frame, "invalid"

    if len(frame.shape) == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    bv = _brightness(frame)
    gv = float(np.std(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))
    ir = _is_ir_frame(frame)

    if ir:
        cond = "ir_night"
    elif bv < 40:
        cond = "very_dark"
    elif bv < 80:
        cond = "dim"
    elif bv > 220:
        cond = "backlight"
    elif bv > 190:
        cond = "bright"
    elif gv < 20:
        cond = "low_contrast"
    else:
        cond = "normal"

    if cond == "ir_night":
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        gray  = clahe.apply(gray)
        out   = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    elif cond == "very_dark":
        out = _denoise(frame, h=9)
        out = _gamma(out, g=0.35)
        out = _clahe_lab(out, clip=4.0, tile=(6, 6))

    elif cond == "dim":
        out = _gamma(frame, g=0.55)
        out = _clahe_lab(out, clip=3.0)

    elif cond == "backlight":
        out = _gamma(frame, g=1.6)
        out = _clahe_lab(out, clip=4.0, tile=(4, 4))

    elif cond == "bright":
        out = _gamma(frame, g=1.35)
        out = _clahe_lab(out, clip=2.0)

    elif cond == "low_contrast":
        out = _clahe_lab(frame, clip=5.0, tile=(4, 4))

    else:
        out = _clahe_lab(frame, clip=2.0)

    amount = 0.4 if cond == "backlight" else 0.65
    out    = _sharpen(out, amount)

    return out, cond


def preprocess_variants(frame: np.ndarray) -> list:
    variants = []

    v1 = _gamma(frame, g=0.38)
    v1 = _clahe_lab(v1, clip=4.5)
    variants.append((v1, "strong_gamma"))

    v2 = _clahe_lab(frame, clip=6.0, tile=(4, 4))
    variants.append((v2, "aggressive_clahe"))

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    eq   = cv2.equalizeHist(gray)
    v3   = cv2.cvtColor(eq, cv2.COLOR_GRAY2BGR)
    variants.append((v3, "histeq"))

    return variants

# ══════════════════════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════════════════════

def send_telegram_alert(message: str, image_path: str = None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message},
                      timeout=10)
        if image_path and os.path.exists(image_path):
            photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, "rb") as photo:
                requests.post(photo_url,
                              data={"chat_id": CHAT_ID},
                              files={"photo": photo},
                              timeout=15)
        print("[TG] Alert sent.")
    except Exception as e:
        print(f"[TG] Error: {e}")


def trigger_alert(frame: np.ndarray, reason: str = "UNKNOWN") -> str:
    global _last_telegram_time

    ts         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(SAVE_DIR, f"intruder_{ts}.jpg")
    cv2.imwrite(image_path, frame)

    now = time.time()
    if now - _last_telegram_time >= TELEGRAM_COOLDOWN:
        message = f"SECURITY ALERT\nReason: {reason}\nTime: {ts}"
        send_telegram_alert(message, image_path)
        _last_telegram_time = now
    else:
        print("[TG] Cooldown active — skipping Telegram.")

    return image_path

# ══════════════════════════════════════════════════════════════════════
#  RECOGNITION HELPERS
# ══════════════════════════════════════════════════════════════════════

TOLERANCE_NORMAL = 0.50
TOLERANCE_DARK   = 0.54

def _to_rgb_small(frame: np.ndarray) -> np.ndarray:
    small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    return cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

def _detect_and_encode(rgb_frame: np.ndarray) -> tuple:
    try:
        locations = face_recognition.face_locations(rgb_frame, model="hog")
        if not locations:
            return [], []
        encodings = face_recognition.face_encodings(rgb_frame, locations,
                                                     num_jitters=1)
        return locations, encodings
    except Exception as e:
        print(f"[Detection] Error: {e}")
        return [], []

def _match(encoding: np.ndarray,
           tolerance: float = TOLERANCE_NORMAL) -> tuple:
    if not known_face_encodings:
        return "Unknown", False

    distances = face_recognition.face_distance(known_face_encodings, encoding)
    idx       = int(np.argmin(distances))

    if distances[idx] <= tolerance:
        return known_face_names[idx], True

    return "Unknown", False

# ══════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════

def process_frame(frame: np.ndarray) -> str:
    if frame is None:
        return "NO_FRAME"

    try:
        # Stage 1: preprocess
        processed, condition = preprocess(frame)
        print(f"[Pipeline] Lighting: {condition}")

        # Stage 2: detect on primary processed frame
        rgb                  = _to_rgb_small(processed)
        locations, encodings = _detect_and_encode(rgb)
        used_dark_variant    = False

        # Stage 3: fallback variants if no face found
        if not encodings:
            print("[Pipeline] No face on primary — trying variants")
            variants = preprocess_variants(frame)
            for v_frame, v_label in variants:
                v_rgb       = _to_rgb_small(v_frame)
                v_locs, v_encs = _detect_and_encode(v_rgb)
                if v_encs:
                    print(f"[Pipeline] Face found via variant: {v_label}")
                    encodings         = v_encs
                    locations         = v_locs
                    processed         = v_frame
                    used_dark_variant = True
                    break

        if not encodings:
            print("[Pipeline] No face in frame or any variant")
            return "NO_FACE"

        # Stage 4: match each detected face
        tolerance        = TOLERANCE_DARK if used_dark_variant else TOLERANCE_NORMAL
        has_known        = False
        has_unknown      = False
        known_names_found = []

        for encoding in encodings:
            name, is_known = _match(encoding, tolerance)
            if is_known:
                has_known = True
                known_names_found.append(name)
                print(f"[Match] KNOWN: {name}")
            else:
                has_unknown = True
                print("[Match] UNKNOWN face")

        # Stage 5: verdict + alert
        if has_unknown:
            trigger_alert(frame, reason="Unrecognized person detected")
            return "UNKNOWN"

        if has_known:
            names_str = ", ".join(set(known_names_found))
            return f"KNOWN:{names_str}"

        return "NO_FACE"

    except Exception as e:
        print(f"[Pipeline] Crash: {e}")
        return "ERROR"