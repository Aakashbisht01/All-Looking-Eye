"""
Pose-based anomaly detector using the trained LSTM model
Matches the user's working script exactly
"""
# --- CRITICAL FIX FOR PROTOBUF ERROR ---
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
from collections import deque

class PoseDetector:
    """LSTM-based pose anomaly detector"""
    
    def __init__(self, model_path, sequence_length=150, smoothing_alpha=0.7):
        self.sequence_length = sequence_length
        self.smoothing_alpha = smoothing_alpha
        self.raw_features = 132  # 33 landmarks * 4
        self.features_per_frame = 264
        
        # Load model exactly like user's script
        print(f"Loading pose model from {model_path}...")
        try:
            self.model = tf.keras.models.load_model(model_path)
            print("Pose model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
        
        # Setup MediaPipe exactly like user's script
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False, 
            model_complexity=1, 
            min_detection_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # State
        self.sequence_buffer = deque(maxlen=sequence_length)
        self.prev_smoothed_pose = None
        
    def reset(self):
        """Reset detector state"""
        self.sequence_buffer.clear()
        self.prev_smoothed_pose = None
    
    def normalize_pose_landmarks(self, landmarks):
        """
        Standardizes the pose to be centered and scaled.
        This allows the model to work on ANY camera size.
        """
        # Convert to numpy
        lm_array = np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in landmarks])
        
        # 1. Center the Hips to (0,0)
        center_x = (lm_array[23, 0] + lm_array[24, 0]) / 2
        center_y = (lm_array[23, 1] + lm_array[24, 1]) / 2
        center_z = (lm_array[23, 2] + lm_array[24, 2]) / 2
        
        lm_array[:, 0] -= center_x
        lm_array[:, 1] -= center_y
        lm_array[:, 2] -= center_z
        
        # 2. Scale to size 1.0
        max_dist = np.max(np.abs(lm_array[:, :3]))
        if max_dist < 1e-6:
            max_dist = 1
        
        lm_array[:, :3] /= max_dist
        
        return lm_array.flatten()
    
    def extract_features(self, image_rgb):
        """
        1. Detects Pose
        2. Normalizes
        3. Smooths (EMA)
        4. Calculates Velocity
        
        Returns: (features, landmarks) or (None, None)
        """
        results = self.pose.process(image_rgb)
        
        if results.pose_landmarks:
            # Step A: Get Normalized Pose
            current_pose = self.normalize_pose_landmarks(results.pose_landmarks.landmark)
            
            # Step B: Apply Smoothing
            if self.prev_smoothed_pose is not None:
                smoothed_pose = (self.smoothing_alpha * current_pose) + \
                               ((1 - self.smoothing_alpha) * self.prev_smoothed_pose)
            else:
                smoothed_pose = current_pose
                
            # Step C: Calculate Velocity
            if self.prev_smoothed_pose is not None:
                velocity = smoothed_pose - self.prev_smoothed_pose
            else:
                velocity = np.zeros(self.raw_features)
                
            # Step D: Combine
            combined_features = np.concatenate((smoothed_pose, velocity))
            
            # Update state
            self.prev_smoothed_pose = smoothed_pose
            
            return combined_features, results.pose_landmarks
            
        else:
            # Person lost - reset smoothing state
            self.prev_smoothed_pose = None
            return None, None
    
    def process_frame(self, frame):
        """
        Process a single frame and return prediction if buffer is full.
        
        Returns:
            dict with keys:
            - 'landmarks': MediaPipe landmarks for drawing
            - 'prediction': float (0-1) or None if buffer not full
            - 'is_anomaly': bool or None
            - 'buffer_status': (current, total)
        """
        # Convert BGR to RGB
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = frame
        
        # Extract features
        features, landmarks = self.extract_features(image_rgb)
        
        result = {
            'landmarks': landmarks,
            'prediction': None,
            'is_anomaly': None,
            'buffer_status': (len(self.sequence_buffer), self.sequence_length)
        }
        
        if features is not None:
            # Add to buffer
            self.sequence_buffer.append(features)
            
            # Predict if buffer is full
            if len(self.sequence_buffer) == self.sequence_length:
                input_data = np.expand_dims(np.array(self.sequence_buffer), axis=0)
                prediction = float(self.model.predict(input_data, verbose=0)[0][0])
                result['prediction'] = prediction
                result['is_anomaly'] = prediction > 0.5
        
        result['buffer_status'] = (len(self.sequence_buffer), self.sequence_length)
        return result
    
    def draw_skeleton(self, frame, landmarks, color=(0, 255, 0)):
        """Draw pose landmarks on frame"""
        if landmarks:
            self.mp_drawing.draw_landmarks(
                frame, landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
            )
        return frame
    
    def process_video(self, video_path, output_path=None, progress_callback=None):
        """
        Process an entire video file.
        
        Returns:
            list of dicts with frame-by-frame predictions
        """
        self.reset()
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
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
        
        results = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            result = self.process_frame(frame)
            result['frame_idx'] = frame_idx
            result['timestamp'] = frame_idx / fps
            results.append(result)
            
            # Draw overlay if writing output
            if out:
                # Draw skeleton
                if result['landmarks']:
                    skeleton_color = (0, 0, 255) if result['is_anomaly'] else (0, 255, 0)
                    self.draw_skeleton(frame, result['landmarks'], skeleton_color)
                
                # Draw status overlay
                if result['prediction'] is not None:
                    label = "VIOLENCE DETECTED" if result['is_anomaly'] else "NORMAL"
                    color = (0, 0, 255) if result['is_anomaly'] else (0, 255, 0)
                    confidence = result['prediction']
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
                
                out.write(frame)
            
            frame_idx += 1
            
            if progress_callback:
                progress_callback(frame_idx, total_frames)
        
        cap.release()
        if out:
            out.release()
        
        self.reset()
        return results
    
    def close(self):
        """Cleanup resources"""
        self.pose.close()
