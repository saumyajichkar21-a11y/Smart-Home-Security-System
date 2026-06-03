import os
import pickle
import cv2
import face_recognition
import numpy as np

DB_FILE = "faces.pkl"


# ══════════════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════════════

def save_embeddings(db: dict):
    with open(DB_FILE, "wb") as f:
        pickle.dump(db, f)
    print(f"[DB] Saved {len(db)} faces.")

def load_embeddings() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            return pickle.load(f)
    return {}


# ══════════════════════════════════════════════════════════════════════
#  LIGHTING HELPERS  (shared by enroll + detect)
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
    lab     = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe   = cv2.createCLAHE(clipLimit=clip, tileGridSize=tile)
    l       = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

def _gamma(frame: np.ndarray, g: float) -> np.ndarray:
    lut = np.array([
        min(255, int((i / 255.0) ** (1.0 / g) * 255))
        for i in range(256)
    ], dtype=np.uint8)
    return cv2.LUT(frame, lut)

def _sharpen(frame: np.ndarray, amount: float = 0.65) -> np.ndarray:
    blur = cv2.GaussianBlur(frame, (0, 0), 3)
    return cv2.addWeighted(frame, 1 + amount, blur, -amount, 0)

def _denoise(frame: np.ndarray, h: int = 7) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(frame, None, h, h, 7, 21)


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Auto-detect lighting condition and apply the correct fix.
    This is the single function called by both enroll and detect paths.

    Handles all conditions:
      ir_night    — IR / monochrome camera
      very_dark   — mean brightness < 40
      dim         — mean brightness < 80
      backlight   — mean brightness > 220
      bright      — mean brightness > 190
      low_contrast— std dev < 20
      normal      — acceptable lighting
    """
    if frame is None or frame.size == 0:
        return frame

    # Grayscale input guard
    if len(frame.shape) == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    bv = _brightness(frame)
    gv = float(np.std(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))
    ir = _is_ir_frame(frame)

    # ── detect condition ──────────────────────────────────────────────
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

    # ── apply correction ──────────────────────────────────────────────
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

    # ── final sharpening ──────────────────────────────────────────────
    amount = 0.4 if cond == "backlight" else 0.65
    out    = _sharpen(out, amount)

    return out


# ══════════════════════════════════════════════════════════════════════
#  FACE ENCODING  (used during enroll)
# ══════════════════════════════════════════════════════════════════════

def get_face_encoding(frame: np.ndarray) -> tuple:
    """
    Preprocess → resize → detect → encode.
    Returns (scaled_locations, encodings) or None if no face found.

    num_jitters=3 during enroll for better embedding quality.
    (detect.py uses num_jitters=1 for speed at runtime.)
    """
    enhanced = enhance_frame(frame)

    small = cv2.resize(enhanced, (0, 0), fx=0.5, fy=0.5)
    rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    locations = face_recognition.face_locations(rgb, model="hog")

    if not locations:
        return None

    encodings = face_recognition.face_encodings(rgb, locations,
                                                  num_jitters=3)

    # Scale locations back to full-frame coordinates
    scaled_locations = [
        (top * 2, right * 2, bottom * 2, left * 2)
        for top, right, bottom, left in locations
    ]

    return scaled_locations, encodings


# ══════════════════════════════════════════════════════════════════════
#  FACE MATCHING  (used during enroll preview / standalone tools)
# ══════════════════════════════════════════════════════════════════════

def match_face(encoding: np.ndarray,
               db: dict,
               tolerance: float = 0.52) -> tuple:
    """
    Compare encoding against DB.
    Uses face_distance (best-match by minimum distance) rather than
    compare_faces hard cutoff — more accurate, same speed.
    Returns (name, is_known).
    """
    if not db:
        return "Unknown", False

    names           = list(db.keys())
    known_encodings = list(db.values())

    distances = face_recognition.face_distance(known_encodings, encoding)
    idx       = int(np.argmin(distances))

    if distances[idx] <= tolerance:
        return names[idx], True

    return "Unknown", False