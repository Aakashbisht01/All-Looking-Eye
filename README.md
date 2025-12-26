# 👁️ All Looking Eye

**AI-Powered Anomaly Detection System**

A real-time violence and anomaly detection system using LSTM deep learning models with pose estimation. Supports video uploads, webcam monitoring, and CCTV stream analysis with instant email alerts.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ Features

- 🎯 **Pose-Based Detection** – LSTM model analyzes body movements to detect violent or abnormal behavior
- 📹 **Multiple Input Sources** – Upload videos, use webcam, or connect CCTV streams (RTSP/HTTP/HLS)
- ⚡ **Real-Time Processing** – Live detection with skeleton overlay and confidence scores
- 📧 **Email Alerts** – Instant notifications with 5-second video clips when anomalies are detected
- 📊 **Detection History** – MongoDB-powered logging of all detection events
- 🌐 **Web Dashboard** – Modern, responsive UI for easy monitoring

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask, Python 3.10+ |
| ML/DL | TensorFlow/Keras, MediaPipe, OpenCV |
| Database | MongoDB |
| Frontend | HTML5, CSS3, JavaScript |
| Email | SMTP (Gmail compatible) |

---

## 📋 Prerequisites

- Python 3.10 or higher
- MongoDB (local or Atlas)
- SMTP email account (for alerts)
- Webcam (optional, for live detection)

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/all-looking-eye.git
cd all-looking-eye
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download ML Models
Download the trained models and place them in the project root:
- `final_model_normalized.keras` (Primary model)
- `best_model_81acc.keras` (Backup model with 81% accuracy)

> ⚠️ Models are not included in the repository. Contact the maintainer or train your own.

### 5. Configure Environment
Create a `.env` file in the project root:
```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017/all_looking_eye

# Email Alerts (Gmail example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# App Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
```

### 6. Start the Server
```bash
cd backend
python app.py
```

Open your browser and go to: **http://localhost:5000**

---

## 📁 Project Structure

```
All Looking Eye/
├── backend/
│   ├── app.py              # Flask application entry point
│   ├── config.py           # Configuration settings
│   ├── models/             # Database models
│   ├── routes/             # API endpoints
│   └── services/           # ML detectors & email service
├── frontend/
│   ├── dashboard.html      # Main web interface
│   ├── css/                # Stylesheets
│   └── js/                 # JavaScript files
├── outputs/                # Processed video outputs
├── uploads/                # Temporary video uploads
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (create this)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/detect/upload` | Upload video for analysis |
| `POST` | `/api/detect/start-camera` | Start webcam detection |
| `POST` | `/api/detect/start-cctv` | Start CCTV stream detection |
| `POST` | `/api/detect/stop` | Stop active detection session |
| `GET` | `/api/detect/stream/<session_id>` | Get video stream |
| `GET` | `/api/detect/logs` | Get detection history |
| `GET` | `/api/health` | Health check |

---

## 🧠 How It Works

1. **Frame Capture** – Video frames are captured from the input source
2. **Pose Estimation** – MediaPipe extracts 33 body landmarks per frame
3. **Sequence Analysis** – LSTM processes 150-frame sequences of pose data
4. **Anomaly Prediction** – Model outputs confidence score (0-1)
5. **Alert Generation** – If score > threshold, email alert with video clip is sent

---

## ⚙️ Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_PATH` | `final_model_normalized.keras` | Path to trained model |
| `SEQUENCE_LENGTH` | `150` | Frames per prediction sequence |
| `ANOMALY_THRESHOLD` | `0.5` | Confidence threshold for alerts |
| `CLIP_DURATION` | `5` | Seconds for email video clips |

---

## 📧 Email Alert Setup (Gmail)

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account → Security → App Passwords
   - Create new app password for "Mail"
3. Use this password in your `.env` file

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [MediaPipe](https://mediapipe.dev/) for pose estimation
- [TensorFlow/Keras](https://www.tensorflow.org/) for deep learning
- [Flask](https://flask.palletsprojects.com/) for the web framework

---


