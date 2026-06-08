# SENTINEL — AI-Powered Home Security System

Real hardware. Real AI. Built by a first-year CSE student.

## What is SENTINEL?

SENTINEL is an AI-powered home security system that combines computer vision, gas detection, and motion sensing into one unified system — running on cheap embedded hardware.

## Hardware Stack

| Component | Role |
|-----------|------|
| ESP32-CAM | Live video streaming + face capture |
| Arduino Nano | Sensor data controller |
| PIR Sensor | Motion detection |
| MQ-2 Sensor | Gas and smoke detection |
| SSD1306 OLED | Local status display |
| Relay + Buzzer | Physical alert system |

## Software Stack

| Layer | Technology |
|-------|------------|
| Firmware | Arduino C++ |
| Backend | Python Flask + DeepFace |
| Frontend | React + Vite |
| Face Recognition | DeepFace deep learning |
| Video Stream | MJPEG over HTTP |

## How It Works

Motion detected by PIR sensor
ESP32-CAM captures face image
Image sent to Flask server
DeepFace compares against known faces
Known face → access granted, OLED shows name
Unknown face → buzzer triggers, alert sent
Live stream visible on React dashboard

MQ-2 detects gas/smoke simultaneously
Consecutive readings filter false triggers
Relay triggers alarm if threshold exceeded

## Key Engineering Challenges Solved

ESP32-CAM GPIO conflict — OLED on GPIO 15/16 caused boot loop. Resolved by remapping I2C pins.

MQ-2 false triggers — eliminated using consecutive reading logic with threshold averaging.

UART reliability — fixed communication drops between ESP32-CAM and Arduino Nano.

MJPEG stream stability — tuned Flask streaming buffer for smooth live feed.

## Features

- Real-time face recognition using deep learning
- Gas and smoke detection with false-trigger elimination
- Live MJPEG video stream on web dashboard
- Local OLED status display
- Physical buzzer alert on intrusion
- Works on local network — no cloud dependency

## Tech Stack

Arduino C++ · Python Flask · React · Vite · DeepFace · OpenCV

## Part of

This project is part of my Edge AI and Autonomous Systems portfolio — building real AI systems that work in the real world on cheap hardware.

EDGE-AI repo: github.com/saumyajichkar21-a11y/EDGE-AI
