# 🔐 Sentinel — Intelligent Security Command Platform

A production-grade, real-time security monitoring platform with Apple-level design perfection. Features WebSocket telemetry, ESP32-CAM integration, AI-powered facial recognition, and a glassmorphic React dashboard.

## ✨ Features

- **Real-time WebSocket Telemetry** — Sub-100ms data synchronization
- **Glassmorphic UI** — Frosted glass surfaces with champagne gold accents
- **3D House Visualization** — Three.js interactive sensor status model
- **AI Face Recognition** — HOG-based detection with confidence scoring
- **Event Timeline** — Chronological security event logging
- **Auto-reconnect** — Resilient WebSocket with exponential backoff
- **Audio Alerts** — Premium warning chimes on threat detection
- **Responsive Design** — Mobile-first with collapsible sidebar

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Port 5173)               │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │  Live Feed   │ │  3D House    │ │   Event Timeline    │ │
│  │  + Canvas    │ │   Model      │ │                     │ │
│  │  Overlay     │ │  (Three.js)  │ │                     │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
│                    WebSocket Client                          │
└────────────────────────┬────────────────────────────────────┘
                         │ ws://localhost:8000/ws/telemetry
┌────────────────────────┼────────────────────────────────────┐
│                    FastAPI Backend (Port 8000)              │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │   WebSocket  │ │  AI Engine   │ │  ESP32 Client       │ │
│  │   Manager    │ │  (OpenCV)    │ │  (Video Stream)     │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## 📡 WebSocket Protocol

### Telemetry Payload
```json
{
  "timestamp": "2026-05-21T13:35:54Z",
  "system_status": "ARMED",
  "threat_level": "LOW",
  "sensors": {
    "pir_motion": 1,
    "mq2_gas_ppm": 120,
    "window_intrusion": 0
  },
  "ai_analysis": {
    "face_detected": true,
    "verdict": "UNKNOWN",
    "confidence_score": 0.92,
    "latest_snapshot_url": "/snapshots/intruder_102.jpg"
  },
  "hardware_outputs": {
    "relay_state": 0,
    "buzzer_siren": 0,
    "warning_led": 1
  }
}
```

### Client Commands
```javascript
// Arm system
ws.send(JSON.stringify({ action: "arm" }));

// Disarm system
ws.send(JSON.stringify({ action: "disarm" }));

// Reset alert
ws.send(JSON.stringify({ action: "reset_alert" }));
```

## 🔧 ESP32 Configuration

Update `esp32_client.py` with your ESP32-CAM IP:
```python
esp32_client = ESP32CameraClient(stream_url="http://YOUR_ESP32_IP:81/stream")
```

## 🎨 Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--sentinel-gold` | `#d4af37` | Primary accent, highlights |
| `--sentinel-danger` | `#ff4757` | Alerts, threats |
| `--sentinel-success` | `#2ed573` | Normal status |
| `--sentinel-900` | `#0a0a0f` | Background |

## 📁 Project Structure

```
sentinel-security/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiveFeed.jsx
│   │   │   ├── SensorCard.jsx
│   │   │   ├── HouseModel.jsx
│   │   │   ├── Timeline.jsx
│   │   │   ├── ConnectionStatus.jsx
│   │   │   └── ThreatBanner.jsx
│   │   ├── context/
│   │   │   └── SecurityContext.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── ai_engine.py
│   │   ├── esp32_client.py
│   │   └── database.py
│   ├── face_db/
│   ├── logs/
│   └── snapshots/
└── README.md
```

## 🔒 Security Notes

- Add JWT authentication for production use
- Use WSS (WebSocket Secure) in production
- Implement rate limiting on WebSocket endpoints
- Sanitize all snapshot filenames to prevent path traversal

## 📄 License

MIT License — Built with precision for intelligent security monitoring.
