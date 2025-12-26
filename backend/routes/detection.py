"""
Detection routes for video processing and anomaly detection
Uses tempfile for temporary video storage
"""
from flask import Blueprint, request, jsonify, current_app, send_file, Response
import os
import uuid
import cv2
import tempfile
from datetime import datetime

from models.detection_log import DetectionLog

detection_bp = Blueprint('detection', __name__, url_prefix='/api/detect')

# Active detection sessions (keyed by email or session_id)
active_sessions = {}

# Temporary video storage (keyed by file_id)
temp_videos = {}

def get_db():
    """Get database from app context"""
    return current_app.config.get('db')

def get_detector():
    """Get combined detector from app context - lazy load if needed"""
    detector = current_app.config.get('detector')
    if detector is None:
        # Try to load it now
        try:
            from config import Config
            from services.pose_detector import PoseDetector
            from services.combined_detector import CombinedDetector
            
            print("Loading ML models on demand...")
            
            pose_detector = PoseDetector(
                Config.MODEL_PATH,
                sequence_length=Config.SEQUENCE_LENGTH,
                smoothing_alpha=Config.SMOOTHING_ALPHA
            )
            
            # Audio detector removed for lighter deployment
            detector = CombinedDetector(
                pose_detector,
                None,  # Audio detector removed
                anomaly_threshold=Config.ANOMALY_THRESHOLD,
                clip_duration=Config.CLIP_DURATION
            )
            
            current_app.config['detector'] = detector
            print("ML models loaded successfully!")
            
        except Exception as e:
            print(f"Error loading ML models: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    return detector

def get_email_service():
    """Get email service from app context"""
    return current_app.config.get('email_service')

def cleanup_old_temp_videos():
    """Remove temp videos older than 5 minutes"""
    now = datetime.utcnow()
    expired_ids = []
    
    for file_id, info in temp_videos.items():
        age_seconds = (now - info['created']).total_seconds()
        if age_seconds > 300:  # 5 minutes = 300 seconds
            try:
                if os.path.exists(info['path']):
                    os.remove(info['path'])
                    print(f"Cleaned up temp video: {info['path']}")
                expired_ids.append(file_id)
            except Exception as e:
                print(f"Failed to cleanup {info['path']}: {e}")
    
    for file_id in expired_ids:
        del temp_videos[file_id]

@detection_bp.route('/upload', methods=['POST'])
def upload_video():
    """Process an uploaded video file using tempfile"""
    try:
        # Cleanup old temp files before processing new upload
        cleanup_old_temp_videos()
        
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'No video file selected'}), 400
        
        # Get email from form data
        user_email = request.form.get('email', '').strip()
        
        # Get detector
        detector = get_detector()
        if not detector:
            return jsonify({'error': 'Detection service not available. Check server logs.'}), 503
        
        # Use tempfile for input
        original_ext = os.path.splitext(video_file.filename)[1] or '.mp4'
        
        with tempfile.NamedTemporaryFile(suffix=original_ext, delete=False) as temp_input:
            video_file.save(temp_input.name)
            input_path = temp_input.name
        
        # Use tempfile for output (not saved permanently)
        file_id = str(uuid.uuid4())
        temp_output = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        output_path = temp_output.name
        temp_output.close()
        
        # Store output path for later retrieval
        temp_videos[file_id] = {
            'path': output_path,
            'created': datetime.utcnow()
        }
        
        try:
            # Process video
            result = detector.process_video_with_audio(input_path, output_path)
            
            # Log detection to database
            db = get_db()
            anomaly_type = 'combined' if result['combined_score'] > 0.5 else 'normal'
            
            log = None
            if db is not None:
                log = DetectionLog.create_log(
                    db,
                    email=user_email,
                    source_type='upload',
                    anomaly_type=anomaly_type,
                    confidence_score=result['combined_score'],
                    metadata={
                        'original_filename': video_file.filename,
                        'anomaly_frame_count': len(result['anomaly_frames'])
                    }
                )
            
            # Send email alert if anomaly detected
            email_sent = False
            if anomaly_type != 'normal' and user_email:
                email_service = get_email_service()
                if email_service:
                    email_sent = email_service.send_anomaly_alert(
                        user_email,
                        anomaly_type='Violence/Anomaly',
                        confidence=result['combined_score'],
                        timestamp=datetime.utcnow(),
                        video_clip_path=output_path
                    )
                    if db and log:
                        DetectionLog.update_email_status(db, log['_id'], email_sent)
            
            return jsonify({
                'message': 'Video processed successfully',
                'file_id': file_id,
                'combined_score': float(result['combined_score']),
                'is_anomaly': anomaly_type != 'normal',
                'anomaly_frames': result['anomaly_frames'][:10],
                'preview_url': f'/api/detect/preview/{file_id}',
                'download_url': f'/api/detect/download/{file_id}',
                'email_sent': email_sent,
                'log_id': str(log['_id']) if log else None
            })
            
        finally:
            # Cleanup temp input file
            try:
                os.remove(input_path)
            except:
                pass
        
    except Exception as e:
        print(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/preview/<file_id>')
def preview_video(file_id):
    """Stream a processed video for preview (inline playback)"""
    try:
        if file_id not in temp_videos:
            return jsonify({'error': 'Video not found or expired'}), 404
        
        file_path = temp_videos[file_id]['path']
        
        if not os.path.exists(file_path):
            del temp_videos[file_id]
            return jsonify({'error': 'Video file not found'}), 404
        
        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=False
        )
        
    except Exception as e:
        print(f"Preview error: {e}")
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/download/<file_id>')
def download_video(file_id):
    """Download a processed video"""
    try:
        if file_id not in temp_videos:
            return jsonify({'error': 'Video not found or expired'}), 404
        
        file_path = temp_videos[file_id]['path']
        
        if not os.path.exists(file_path):
            del temp_videos[file_id]
            return jsonify({'error': 'Video file not found'}), 404
        
        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f'processed_{file_id}.mp4'
        )
        
    except Exception as e:
        print(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/start-camera', methods=['POST'])
def start_camera():
    """Start webcam detection session"""
    try:
        data = request.get_json() or {}
        user_email = data.get('email', '').strip()
        
        # Check if already has active session
        session_key = user_email if user_email else 'anonymous'
        if session_key in active_sessions:
            return jsonify({'error': 'Session already active. Stop it first.'}), 400
        
        # Create session
        session_id = str(uuid.uuid4())
        
        active_sessions[session_key] = {
            'session_id': session_id,
            'type': 'camera',
            'source': 0,  # Default webcam
            'email': user_email,
            'active': True,
            'started_at': datetime.utcnow()
        }
        
        return jsonify({
            'message': 'Camera session started',
            'session_id': session_id,
            'stream_url': f'/api/detect/stream/{session_id}'
        })
        
    except Exception as e:
        print(f"Start camera error: {e}")
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/start-cctv', methods=['POST'])
def start_cctv():
    """Start CCTV stream detection"""
    try:
        data = request.get_json() or {}
        cctv_url = data.get('url', '')
        user_email = data.get('email', '').strip()
        
        if not cctv_url:
            return jsonify({'error': 'CCTV URL is required'}), 400
        
        # Check if already has active session
        session_key = user_email if user_email else 'anonymous'
        if session_key in active_sessions:
            return jsonify({'error': 'Session already active. Stop it first.'}), 400
        
        # Test connection
        cap = cv2.VideoCapture(cctv_url)
        if not cap.isOpened():
            return jsonify({'error': 'Could not connect to CCTV stream'}), 400
        cap.release()
        
        # Create session
        session_id = str(uuid.uuid4())
        
        active_sessions[session_key] = {
            'session_id': session_id,
            'type': 'cctv',
            'source': cctv_url,
            'email': user_email,
            'active': True,
            'started_at': datetime.utcnow()
        }
        
        return jsonify({
            'message': 'CCTV session started',
            'session_id': session_id,
            'stream_url': f'/api/detect/stream/{session_id}'
        })
        
    except Exception as e:
        print(f"Start CCTV error: {e}")
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/stop', methods=['POST'])
def stop_detection():
    """Stop active detection session"""
    try:
        data = request.get_json() or {}
        user_email = data.get('email', '').strip()
        
        # Find and remove session
        session_key = user_email if user_email else 'anonymous'
        
        if session_key in active_sessions:
            active_sessions[session_key]['active'] = False
            del active_sessions[session_key]
        
        return jsonify({'message': 'Detection stopped'})
        
    except Exception as e:
        print(f"Stop error: {e}")
        return jsonify({'error': str(e)}), 500

@detection_bp.route('/stream/<session_id>')
def stream_video(session_id):
    """Stream video with detection overlay"""
    # Find session
    session_info = None
    
    for key, sess in active_sessions.items():
        if sess['session_id'] == session_id:
            session_info = sess
            break
    
    if not session_info:
        return jsonify({'error': 'Session not found'}), 404
    
    # Get detector and services
    detector = get_detector()
    if not detector:
        return jsonify({'error': 'Detection service not available'}), 503
    
    db = get_db()
    email_service = get_email_service()
    output_folder = current_app.config.get('OUTPUT_FOLDER', 'outputs')
    
    def generate_frames():
        source = session_info['source']
        user_email = session_info.get('email', '')
        session_key = user_email if user_email else 'anonymous'
        
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            yield b'--frame\r\nContent-Type: text/plain\r\n\r\nError: Could not open video source\r\n'
            return
        
        try:
            while session_key in active_sessions and active_sessions[session_key].get('active', False):
                ret, frame = cap.read()
                if not ret:
                    if session_info['type'] == 'cctv':
                        # Try to reconnect
                        cap.release()
                        cap = cv2.VideoCapture(source)
                        continue
                    break
                
                # Process frame
                result = detector.process_frame(frame)
                
                # Draw skeleton
                if result['landmarks']:
                    skeleton_color = (0, 0, 255) if result['is_anomaly'] else (0, 255, 0)
                    detector.pose_detector.draw_skeleton(frame, result['landmarks'], skeleton_color)
                
                # Draw overlay
                height, width = frame.shape[:2]
                if result['combined_prediction'] is not None:
                    label = "ANOMALY DETECTED" if result['is_anomaly'] else "NORMAL"
                    color = (0, 0, 255) if result['is_anomaly'] else (0, 255, 0)
                    confidence = result['combined_prediction']
                else:
                    buf_cur, buf_max = result['buffer_status']
                    label = f"Buffering... ({buf_cur}/{buf_max})"
                    color = (0, 255, 255)
                    confidence = 0
                
                # Draw overlay box
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (width, 50), color, -1)
                frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
                cv2.putText(frame, f"{label} ({confidence:.2%})", (10, 35),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                # Encode frame
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        finally:
            cap.release()
            detector.reset()
    
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@detection_bp.route('/logs', methods=['GET'])
def get_logs():
    """Get detection history for an email"""
    try:
        user_email = request.args.get('email', '').strip()
        limit = request.args.get('limit', 50, type=int)
        skip = request.args.get('skip', 0, type=int)
        
        db = get_db()
        if db is None:
            return jsonify({'logs': []})
        
        logs = DetectionLog.find_by_email(db, user_email, limit=limit, skip=skip)
        
        # Format for JSON
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                'id': str(log['_id']),
                'source_type': log['source_type'],
                'timestamp': log['timestamp'].isoformat(),
                'anomaly_type': log['anomaly_type'],
                'confidence_score': log['confidence_score'],
                'email_sent': log.get('email_sent', False)
            })
        
        return jsonify({'logs': formatted_logs})
        
    except Exception as e:
        print(f"Get logs error: {e}")
        return jsonify({'error': str(e)}), 500
