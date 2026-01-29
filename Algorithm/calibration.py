import numpy as np
from collections import deque
import time


class CalibrationLogic:
    def __init__(self, fps=30, calibration_duration=8.0):
        self.fps = fps
        self.calibration_duration = calibration_duration
        self.max_frames = int(fps * calibration_duration)
        
        self.frame_count = 0
        self.left_heel_heights = deque(maxlen=self.max_frames)
        self.right_heel_heights = deque(maxlen=self.max_frames)
        self.time_stamps = deque(maxlen=self.max_frames)
        
        self.crossings_left = deque(maxlen=10)
        self.crossings_right = deque(maxlen=10)
        self.left_intervals = []
        self.right_intervals = []
        self.left_height_movements = []
        self.right_height_movements = []
        
        self.prev_left_heel_height = None
        self.prev_right_heel_height = None
        self.last_crossing_time_left = None
        self.last_crossing_time_right = None
        
        self.left_mu_h = 0.0
        self.right_mu_h = 0.0
        self.left_sigma_h = 0.0
        self.right_sigma_h = 0.0
        self.left_threshold = 0.0
        self.right_threshold = 0.0
        
    def compute_ground_reference(self, heights):
        TH = 2.0
        W = int(TH * self.fps)
        heights_array = np.array(list(heights))
        NW = len(heights_array) // W
        
        if NW == 0:
            return np.min(heights_array) if len(heights_array) > 0 else 0.0
        
        window_minima = []
        for k in range(NW):
            window = heights_array[k*W:(k+1)*W]
            if len(window) > 0:
                window_minima.append(np.min(window))
        
        return np.mean(window_minima) if window_minima else 0.0
    
    def process_frame(self, left_heel_height, right_heel_height, current_time):
        self.left_heel_heights.append(left_heel_height)
        self.right_heel_heights.append(right_heel_height)
        self.time_stamps.append(current_time)
        self.frame_count += 1
        
        if self.frame_count <= 90:
            self.prev_left_heel_height = left_heel_height
            self.prev_right_heel_height = right_heel_height
            return
        
        left_y = np.array(list(self.left_heel_heights))
        right_y = np.array(list(self.right_heel_heights))
        
        self.left_mu_h = self.compute_ground_reference(self.left_heel_heights)
        self.right_mu_h = self.compute_ground_reference(self.right_heel_heights)
        self.left_sigma_h = np.std(left_y) if len(left_y) > 0 else 0.0
        self.right_sigma_h = np.std(right_y) if len(right_y) > 0 else 0.0
        
        self.left_threshold = self.left_mu_h + 0.5 * self.left_sigma_h
        self.right_threshold = self.right_mu_h + 0.5 * self.right_sigma_h
        
        self._detect_crossing_left(left_heel_height, current_time)
        self._detect_crossing_right(right_heel_height, current_time)
        
        self.prev_left_heel_height = left_heel_height
        self.prev_right_heel_height = right_heel_height
    
    def _detect_crossing_left(self, left_heel_height, current_time):
        if self.prev_left_heel_height is None:
            return
        
        left_cross = (self.prev_left_heel_height < self.left_threshold <= left_heel_height)
        
        if left_cross:
            if self.last_crossing_time_left is not None:
                interval = current_time - self.last_crossing_time_left
                last_frame_left = self.crossings_left[-1][1] if self.crossings_left else 0
                frame_interval = self.frame_count - last_frame_left
                
                if frame_interval >= 10:
                    self.crossings_left.append((current_time, self.frame_count))
                    self.left_intervals.append(interval)
                    
                    start_idx = max(0, len(self.left_heel_heights) - frame_interval)
                    between = list(self.left_heel_heights)[start_idx:]
                    if between:
                        height_diff = max(between) - min(between)
                        self.left_height_movements.append(height_diff)
                    
                    self.last_crossing_time_left = current_time
            else:
                self.last_crossing_time_left = current_time
                self.crossings_left.append((current_time, self.frame_count))
    
    def _detect_crossing_right(self, right_heel_height, current_time):
        if self.prev_right_heel_height is None:
            return
        
        right_cross = (self.prev_right_heel_height < self.right_threshold <= right_heel_height)
        
        if right_cross:
            if self.last_crossing_time_right is not None:
                interval = current_time - self.last_crossing_time_right
                last_frame_right = self.crossings_right[-1][1] if self.crossings_right else 0
                frame_interval = self.frame_count - last_frame_right
                
                if frame_interval >= 10:
                    self.crossings_right.append((current_time, self.frame_count))
                    self.right_intervals.append(interval)
                    
                    start_idx = max(0, len(self.right_heel_heights) - frame_interval)
                    between = list(self.right_heel_heights)[start_idx:]
                    if between:
                        height_diff = max(between) - min(between)
                        self.right_height_movements.append(height_diff)
                    
                    self.last_crossing_time_right = current_time
            else:
                self.last_crossing_time_right = current_time
                self.crossings_right.append((current_time, self.frame_count))
    
    def is_calibration_complete(self):
        return self.frame_count >= self.max_frames
    
    def get_calibration_results(self):
        if len(self.left_heel_heights) < 90 or len(self.crossings_left) < 2 or len(self.crossings_right) < 2:
            left_mu_h = -0.3
            right_mu_h = -0.3
            left_sigma_h = 0.1
            right_sigma_h = 0.1
            left_threshold = left_mu_h + 0.5 * left_sigma_h
            right_threshold = right_mu_h + 0.5 * right_sigma_h
            left_fc = 1.2
            right_fc = 1.2
            left_hc = 0.12
            right_hc = 0.12
        else:
            avg_crossing_left = np.mean(self.left_intervals) if self.left_intervals else 1.0
            avg_crossing_right = np.mean(self.right_intervals) if self.right_intervals else 1.0
            left_fc = min(1.0 / avg_crossing_left if avg_crossing_left > 0 else 1.2, 4.5)
            right_fc = min(1.0 / avg_crossing_right if avg_crossing_right > 0 else 1.2, 4.5)
            left_hc = np.mean(self.left_height_movements) if self.left_height_movements else 0.12
            right_hc = np.mean(self.right_height_movements) if self.right_height_movements else 0.12
            
            left_mu_h = self.left_mu_h
            right_mu_h = self.right_mu_h
            left_sigma_h = self.left_sigma_h
            right_sigma_h = self.right_sigma_h
            left_threshold = self.left_threshold
            right_threshold = self.right_threshold
        
        return {
            'mu_h_left': left_mu_h,
            'mu_h_right': right_mu_h,
            'sigma_h_left': left_sigma_h,
            'sigma_h_right': right_sigma_h,
            'threshold_left': left_threshold,
            'threshold_right': right_threshold,
            'h_c_left': left_hc,
            'h_c_right': right_hc,
            'f_c_left': left_fc,
            'f_c_right': right_fc
        }