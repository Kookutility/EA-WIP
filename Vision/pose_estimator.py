import cv2
import numpy as np
import mediapipe as mp
import threading


class PoseEstimator:
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
    def process(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        return results
    
    def extract_heel_data(self, results, y_scale=1.0, x_scale=1.0):
        if not results.pose_landmarks:
            return None
        
        landmarks = results.pose_landmarks.landmark
        left_heel = landmarks[self.mp_pose.PoseLandmark.LEFT_HEEL]
        right_heel = landmarks[self.mp_pose.PoseLandmark.RIGHT_HEEL]
        
        left_heel_height = -0.5 + (1.0 - left_heel.y) * y_scale
        right_heel_height = -0.5 + (1.0 - right_heel.y) * y_scale
        
        left_heel_x = (left_heel.x - 0.5) * x_scale
        right_heel_x = (right_heel.x - 0.5) * x_scale
        
        left_visibility = left_heel.visibility
        right_visibility = right_heel.visibility
        
        return {
            'left_height': left_heel_height,
            'right_height': right_heel_height,
            'left_x': left_heel_x,
            'right_x': right_heel_x,
            'left_visibility': left_visibility,
            'right_visibility': right_visibility,
            'left_heel_2d': left_heel,
            'right_heel_2d': right_heel
        }
    
    def draw_landmarks(self, image, results):
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )
        return image
    
    def __del__(self):
        if hasattr(self, 'pose'):
            self.pose.close()


class CameraStream:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(camera_id)
        
        if not self.cap.isOpened():
            raise ConnectionError(f"Could not open camera {camera_id}")
        
        self.image_from_thread = None
        self.image_ready = False
        self.running = True
        
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
    
    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.image_from_thread = frame
                self.image_ready = True
            else:
                print("ERROR: Camera capture failed!")
                break
    
    def read(self):
        if self.image_ready:
            self.image_ready = False
            return self.image_from_thread.copy()
        return None
    
    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        if self.cap.isOpened():
            self.cap.release()
    
    def __del__(self):
        self.stop()


def preprocess_image(image, target_size=(640, 480)):
    image = cv2.resize(image, target_size)
    return image