# 🚀 Sentinel Setup & Deployment Guide

## Table of Contents
1. [Quick Start (Development)](#quick-start)
2. [Production Deployment](#production-deployment)
3. [ESP32 Hardware Setup](#esp32-hardware-setup)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- ESP32-CAM module (optional for demo mode)

### Step 1: Clone and Setup
```bash
git clone <repository-url>
cd sentinel-security
```

### Step 2: Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python -m app.main
```

Backend will start at `http://localhost:8000`

### Step 3: Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will start at `http://localhost:5173`

### Step 4: Verify Connection
1. Open browser to `http://localhost:5173`
2. Check connection status indicator (top right)
3. You should see "Connected" in green

---

## Production Deployment

### Docker Deployment (Recommended)

#### Option A: Docker Compose (Full Stack)
```bash
# Copy environment variables
cp .env.example .env

# Edit .env with your configuration
nano .env

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Option B: Individual Containers
```bash
# Build backend
cd backend
docker build -t sentinel-backend .
docker run -d -p 8000:8000 --name sentinel-backend sentinel-backend

# Build frontend
cd frontend
docker build -t sentinel-frontend .
docker run -d -p 80:80 --name sentinel-frontend sentinel-frontend
```

### Manual Production Deployment

#### Backend
```bash
cd backend
pip install -r requirements.txt

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Frontend
```bash
cd frontend
npm install
npm run build

# Serve with any static server
npx serve dist
```

---

## ESP32 Hardware Setup

### Wiring Diagram
```
ESP32-CAM Pinout:
┌─────────────────────────────────────┐
│  3.3V  →  Power Supply (3.3V)       │
│  GND   →  Ground                    │
│  GPIO4 →  Status LED                │
│  GPIO12→  Relay Module              │
│  GPIO13→  PIR Motion Sensor         │
│  GPIO14→  Window Contact Sensor     │
│  GPIO15→  Buzzer/Siren              │
│  GPIO34→  MQ-2 Gas Sensor (ADC)     │
└─────────────────────────────────────┘
```

### Sensor Connections

#### PIR Motion Sensor (HC-SR501)
- VCC → 3.3V
- GND → GND
- OUT → GPIO13

#### MQ-2 Gas Sensor
- VCC → 5V
- GND → GND
- A0  → GPIO34 (ADC)
- D0  → Not used (analog preferred)

#### Window Contact Sensor
- One wire → GPIO14
- Other wire → GND
- Enable internal pull-up in code

#### Relay Module
- VCC → 3.3V
- GND → GND
- IN  → GPIO12

#### Buzzer/Siren
- Positive → GPIO15
- Negative → GND

### Uploading Firmware

1. Install Arduino IDE
2. Add ESP32 board support:
   - File → Preferences → Additional Board Manager URLs
   - Add: `https://dl.espressif.com/dl/package_esp32_index.json`
3. Install libraries:
   - `ESPAsyncWebServer`
   - `AsyncTCP`
   - `esp32cam`
4. Open `hardware/esp32_sentinel.ino`
5. Update WiFi credentials
6. Select board: "AI Thinker ESP32-CAM"
7. Upload

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ESP32_IP` | 192.168.1.100 | ESP32-CAM IP address |
| `ESP32_PORT` | 81 | ESP32 stream port |
| `BACKEND_PORT` | 8000 | FastAPI server port |
| `FRONTEND_PORT` | 5173 | React dev server port |
| `JWT_SECRET` | - | JWT signing key |
| `DEBUG` | true | Enable debug mode |

### Frontend Configuration

Edit `frontend/vite.config.js` to change proxy settings:
```javascript
server: {
  proxy: {
    '/ws': {
      target: 'ws://your-backend-ip:8000',
      ws: true,
    }
  }
}
```

### Backend Configuration

Edit `backend/app/main.py` to adjust:
- WebSocket reconnection settings
- Frame processing rate
- AI confidence thresholds
- Alert triggers

---

## Troubleshooting

### WebSocket Connection Issues
```bash
# Check if backend is running
curl http://localhost:8000/health

# Test WebSocket connection
wscat -c ws://localhost:8000/ws/telemetry

# Check firewall rules
sudo ufw allow 8000
```

### ESP32 Camera Not Connecting
```bash
# Test ESP32 stream directly
curl http://192.168.1.100:81/stream

# Check ESP32 IP
# Serial monitor will print IP after connection
```

### Face Recognition Not Working
1. Ensure OpenCV is installed: `pip install opencv-python-headless`
2. Check cascade file exists:
   ```python
   import cv2
   print(cv2.data.haarcascades)
   ```
3. Add known faces to `backend/face_db/`

### Performance Issues
1. Reduce frame processing rate:
   ```python
   # In ai_engine.py
   self.frame_skip = 5  # Process every 5th frame
   ```
2. Lower camera resolution:
   ```cpp
   // In ESP32 sketch
   Resolution resolution = Resolution::find(320, 240);
   ```
3. Enable GPU acceleration for OpenCV (if available)

---

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/telemetry` | GET | Current telemetry |
| `/video` | GET | MJPEG stream |
| `/snapshots/{filename}` | GET | Get snapshot image |

### WebSocket Protocol

**Client → Server Commands:**
```json
{"action": "arm"}
{"action": "disarm"}
{"action": "reset_alert"}
```

**Server → Client Telemetry:**
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

---

## Security Considerations

### Production Checklist
- [ ] Change default JWT secret
- [ ] Enable HTTPS/WSS
- [ ] Set strong admin password
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Set up log rotation
- [ ] Configure backup strategy
- [ ] Enable camera authentication

### Network Security
```bash
# Allow only necessary ports
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # Backend API (internal)
sudo ufw enable
```

---

## Maintenance

### Log Rotation
```bash
# Install logrotate
sudo apt-get install logrotate

# Create config
sudo tee /etc/logrotate.d/sentinel << EOF
/path/to/sentinel/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 user user
}
EOF
```

### Backup Strategy
```bash
# Backup face database
rsync -avz backend/face_db/ backup/face_db/

# Backup logs
rsync -avz backend/logs/ backup/logs/

# Backup snapshots (security footage)
rsync -avz backend/snapshots/ backup/snapshots/
```

---

## Support

For issues and feature requests, please refer to the project repository.

**Emergency Contacts:**
- System Admin: admin@sentinel.local
- Security Team: security@sentinel.local
