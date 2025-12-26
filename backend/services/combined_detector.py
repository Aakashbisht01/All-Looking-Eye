"""
Combined detector that fuses pose and audio anomaly detection
"""
import cv2
import numpy as np
from collections import deque
from datetime import datetime
import os
import tempfile

class CombinedDetector:
    """Combines pose and audio detection for final anomaly prediction"""
    
    def __init__(self, pose_detector, audio_detector=None, 
                 pose_weight=0.6, audio_weight=0.4,
                 anomaly_threshold=0.5, clip_duration=5):
        """
        Initialize combined detector.
        
        Args:
            pose_detector: PoseDetector instance
            audio_detector: AudioDetector instance (optional)
            pose_weight: Weight for pose-based prediction
            audio_weight: Weight for audio-based prediction
            anomaly_threshold: Threshold for triggering alerts
            clip_duration: Duration of alert video clips in seconds
        """
        self.pose_detector = pose_detector
        self.audio_detector = audio_detector
        self.pose_weight = pose_weight
        self.audio_weight = audio_weight
        self.anomaly_threshold = anomaly_threshold
        self.clip_duration = clip_duration
        
        # Frame buffer for video clips (stores frames for alert clips)
        self.frame_buffer = deque(maxlen=300)  # ~10 seconds at 30fps
        self.fps = 30
        
        # State
        self.last_anomaly_time = None
        self.cooldown_seconds = 10  # Min time between alerts
    
    def reset(self):
        """Reset detector state"""
        self.pose_detector.reset()
        self.frame_buffer.clear()
        self.last_anomaly_time = None
    
    def process_frame(self, frame, timestamp=None):
        """
        Process a single frame with combined detection.
        
        Returns:
            dict with prediction results
        """
        # Store frame in buffer
        self.frame_buffer.append({
            'frame': frame.copy(),
            'timestamp': timestamp or datetime.utcnow()
        })
        
        # Get pose prediction
        pose_result = self.pose_detector.process_frame(frame)
        
        # Combined prediction (audio is processed separately for video files)
        result = {
            'pose_prediction': pose_result['prediction'],
            'pose_is_anomaly': pose_result['is_anomaly'],
            'audio_prediction': None,
            'combined_prediction': None,
            'is_anomaly': False,
            'landmarks': pose_result['landmarks'],
            'buffer_status': pose_result['buffer_status'],
            'should_alert': False,
            'timestamp': timestamp
        }
        
        # Combined prediction if pose prediction is available
        if pose_result['prediction'] is not None:
            # For real-time, we only have pose (audio requires more processing)
            combined = pose_result['prediction']
            result['combined_prediction'] = combined
            result['is_anomaly'] = combined > self.anomaly_threshold
            
            # Check if we should trigger an alert
            if result['is_anomaly']:
                now = datetime.utcnow()
                if self.last_anomaly_time is None or \
                   (now - self.last_anomaly_time).total_seconds() > self.cooldown_seconds:
                    result['should_alert'] = True
                    self.last_anomaly_time = now
        
        return result
    
    def process_video_with_audio(self, video_path, output_path=None, progress_callback=None):
        """
        Process a video file with both pose and audio detection.
        
        Returns:
            dict with:
            - 'frame_results': list of per-frame results
            - 'audio_result': audio detection result
            - 'combined_score': overall combined anomaly score
            - 'anomaly_frames': list of (timestamp, score) for high anomaly frames
        """
        self.reset()
        
        # First, extract and process audio
        audio_result = None
        if self.audio_detector:
            audio_result = self.audio_detector.extract_audio_from_video(video_path)
        
        # Process video frames
        frame_results = self.pose_detector.process_video(
            video_path, 
            output_path=None,  # We'll handle output ourselves
            progress_callback=progress_callback
        )
        
        # Get video properties for output
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        cap.release()
        
        # Setup output writer if needed
        out = None
        if output_path:
            # Try H.264 codec for browser compatibility, fallback to mp4v
            try:
                fourcc = cv2.VideoWriter_fourcc(*'avc1')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                if not out.isOpened():
                    raise Exception("avc1 codec failed")
            except:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Calculate combined scores
        audio_score = audio_result['anomaly_score'] if audio_result else 0.0
        
        # Reprocess for output with combined scores
        cap = cv2.VideoCapture(video_path)
        anomaly_frames = []
        max_combined = 0.0
        
        for i, result in enumerate(frame_results):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate combined score
            if result['prediction'] is not None:
                pose_score = result['prediction']
                
                if self.audio_detector and audio_result:
                    combined = (self.pose_weight * pose_score) + (self.audio_weight * audio_score)
                else:
                    combined = pose_score
                
                result['combined_prediction'] = combined
                result['audio_prediction'] = audio_score
                result['is_anomaly'] = combined > self.anomaly_threshold
                
                max_combined = max(max_combined, combined)
                
                if combined > self.anomaly_threshold:
                    anomaly_frames.append({
                        'frame_idx': i,
                        'timestamp': result['timestamp'],
                        'score': combined
                    })
            else:
                result['combined_prediction'] = None
                result['is_anomaly'] = False
            
            # Draw output if needed
            if out:
                # Draw skeleton
                if result.get('landmarks'):
                    skeleton_color = (0, 0, 255) if result['is_anomaly'] else (0, 255, 0)
                    self.pose_detector.draw_skeleton(frame, result['landmarks'], skeleton_color)
                
                # Draw overlay
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
                cv2.rectangle(overlay, (0, 0), (width, 60), color, -1)
                frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
                cv2.putText(frame, f"{label} ({confidence:.2%})", (20, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Add audio indicator if available
                if audio_result and audio_result.get('detected_classes'):
                    audio_text = f"Audio: {audio_result['detected_classes'][0]['class']}"
                    cv2.putText(frame, audio_text, (20, height - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                out.write(frame)
        
        cap.release()
        if out:
            out.release()
        
        return {
            'frame_results': frame_results,
            'audio_result': audio_result,
            'combined_score': max_combined,
            'anomaly_frames': anomaly_frames,
            'output_path': output_path
        }
    
    def extract_alert_clip(self, output_path, center_timestamp=None):
        """
        Extract a clip from the frame buffer centered around an anomaly.
        
        Args:
            output_path: Path to save the clip
            center_timestamp: Optional timestamp to center the clip around
        
        Returns:
            Path to the saved clip or None if not enough frames
        """
        if len(self.frame_buffer) < 10:
            return None
        
        # Calculate frame indices
        half_frames = int(self.clip_duration * self.fps / 2)
        
        if center_timestamp:
            # Find the frame closest to the timestamp
            center_idx = len(self.frame_buffer) - 1
            for i, item in enumerate(self.frame_buffer):
                if item['timestamp'] >= center_timestamp:
                    center_idx = i
                    break
        else:
            # Use the most recent frames
            center_idx = len(self.frame_buffer) - half_frames
        
        # Get frame range
        start_idx = max(0, center_idx - half_frames)
        end_idx = min(len(self.frame_buffer), center_idx + half_frames)
        
        # Extract frames
        frames = [self.frame_buffer[i]['frame'] for i in range(start_idx, end_idx)]
        
        if len(frames) < 10:
            return None
        
        # Get frame dimensions
        height, width = frames[0].shape[:2]
        
        # Write video clip
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))
        
        for frame in frames:
            out.write(frame)
        
        out.release()
        
        return output_path
    
    def close(self):
        """Cleanup resources"""
        self.pose_detector.close()
