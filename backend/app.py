"""
All Looking Eye - Anomaly Detection System
Main Flask Application Entry Point (Simplified - No Auth)
"""
import os

# Critical fix for protobuf error
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from flask import Flask, send_from_directory, redirect
from flask_cors import CORS
from pymongo import MongoClient

# Import configuration
from config import Config

# Import routes
from routes.detection import detection_bp

# Import models for index creation
from models.detection_log import DetectionLog

# Import services
from services.email_service import EmailService

def create_app():
    """Create and configure Flask application"""
    
    # Create Flask app
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    
    # Load configuration
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    app.config['OUTPUT_FOLDER'] = Config.OUTPUT_FOLDER
    
    # Ensure directories exist
    Config.ensure_directories()
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    # Setup MongoDB
    print("Connecting to MongoDB...")
    try:
        mongo_client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.admin.command('ping')
        db = mongo_client.get_database()
        app.config['db'] = db
        print(f"Connected to MongoDB: {db.name}")
        
        # Create indexes
        DetectionLog.ensure_indexes(db)
        print("Database indexes created.")
        
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        print("Running without database - detection history will not be saved.")
        app.config['db'] = None
    
    # Setup Email Service
    if Config.SMTP_EMAIL and Config.SMTP_PASSWORD:
        app.config['email_service'] = EmailService(
            Config.SMTP_SERVER,
            Config.SMTP_PORT,
            Config.SMTP_EMAIL,
            Config.SMTP_PASSWORD
        )
        print("Email service configured.")
    else:
        print("Warning: Email service not configured. Alerts will not be sent.")
        app.config['email_service'] = None
    
    # Setup ML Detector (lazy loading to improve startup time)
    app.config['detector'] = None
    
    @app.before_request
    def load_detector():
        """Load detector on first request"""
        if app.config.get('detector') is None:
            try:
                from services.pose_detector import PoseDetector
                from services.combined_detector import CombinedDetector
                
                print("Loading ML models...")
                
                # Load pose detector
                pose_detector = PoseDetector(
                    Config.MODEL_PATH,
                    sequence_length=Config.SEQUENCE_LENGTH,
                    smoothing_alpha=Config.SMOOTHING_ALPHA
                )
                
                # Create combined detector (audio detector removed for lighter deployment)
                app.config['detector'] = CombinedDetector(
                    pose_detector,
                    None,  # Audio detector removed
                    anomaly_threshold=Config.ANOMALY_THRESHOLD,
                    clip_duration=Config.CLIP_DURATION
                )
                
                print("ML models loaded successfully!")
                
            except Exception as e:
                print(f"Error loading ML models: {e}")
                import traceback
                traceback.print_exc()
                app.config['detector'] = None
    
    # Register blueprints
    app.register_blueprint(detection_bp)
    
    # Serve frontend - redirect root to dashboard
    @app.route('/')
    def index():
        return redirect('/dashboard.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        # Check if file exists
        file_path = os.path.join(app.static_folder, path)
        if os.path.exists(file_path):
            return send_from_directory(app.static_folder, path)
        else:
            # Redirect to dashboard for unknown routes
            return redirect('/dashboard.html')
    
    # Health check
    @app.route('/api/health')
    def health():
        return {
            'status': 'ok',
            'mongodb': app.config['db'] is not None,
            'detector': app.config['detector'] is not None,
            'email': app.config['email_service'] is not None
        }
    
    return app

# Create app
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  All Looking Eye - Anomaly Detection System")
    print("="*50)
    print(f"\n  Open: http://localhost:5000")
    print("\n  Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG, threaded=True)
