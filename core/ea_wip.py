import numpy as np
from collections import deque


class EAWIP:
    def __init__(self, fps=30):
        self.fps = fps
        
        self.h_c_left = None
        self.h_c_right = None
        self.f_c_left = None
        self.f_c_right = None
        self.v0 = None
        
        self.lambda_weight = 0.5 #supplemental material table S1
        self.theta_o = 0.25 #supplemental material table S1
        
        self.T_window = int(2.0 * fps)
        self.vis_history_left = deque(maxlen=self.T_window)
        self.vis_history_right = deque(maxlen=self.T_window)
        
        self.speed_history = deque(maxlen=self.T_window)
        self.current_speed = 0.0
        
        self.frame_count = 0
        
    def set_calibration_results(self, calib_results):
        self.h_c_left = calib_results['h_c_left']
        self.h_c_right = calib_results['h_c_right']
        self.f_c_left = calib_results['f_c_left']
        self.f_c_right = calib_results['f_c_right']
    
    def set_base_speed(self, v0):
        self.v0 = v0
    
    def calculate_stride_cadence_index(self, h, f, h_c, f_c):
        if h_c is None or f_c is None or h_c <= 0 or f_c <= 0:
            return 1.0
        
        r_h = h / h_c
        r_f = f / f_c
        z = np.sqrt(r_h * r_f)
        
        return z
    
    def calculate_oci(self, vis_current, vis_history):
        if len(vis_history) < self.T_window:
            return 0.0
        
        vis_array = np.array(list(vis_history))
        vis_mean = np.mean(vis_array)
        vis_std = np.std(vis_array)
        
        delta_V = vis_mean - vis_current
        sigma_V = vis_std
        
        OCI = delta_V + self.lambda_weight * sigma_V
        
        return OCI
    
    def detect_occlusion(self, vis_left, vis_right):
        self.vis_history_left.append(vis_left)
        self.vis_history_right.append(vis_right)
        
        OCI_left = self.calculate_oci(vis_left, self.vis_history_left)
        OCI_right = self.calculate_oci(vis_right, self.vis_history_right)
        
        OCI_mean = (OCI_left + OCI_right) / 2.0
        
        return OCI_mean > self.theta_o
    
    def calculate_speed(self, h_left, h_right, f_left, f_right, vis_left, vis_right):
        if self.v0 is None:
            return 0.0
        
        z_left = self.calculate_stride_cadence_index(h_left, f_left, self.h_c_left, self.f_c_left)
        z_right = self.calculate_stride_cadence_index(h_right, f_right, self.h_c_right, self.f_c_right)
        
        if vis_left + vis_right == 0:
            return 0.0
        
        v_star = self.v0 / (vis_left + vis_right) * (vis_left * z_left + vis_right * z_right)
        
        is_occluded = self.detect_occlusion(vis_left, vis_right)
        
        if is_occluded:
            if len(self.speed_history) > 0:
                return self.speed_history[-1]
            else:
                return 0.0
        
        self.speed_history.append(v_star)
        smoothed_speed = np.mean(list(self.speed_history))
        
        return smoothed_speed
    
    def update(self, h_left, h_right, f_left, f_right, vis_left, vis_right):
        self.frame_count += 1
        
        speed = self.calculate_speed(h_left, h_right, f_left, f_right, vis_left, vis_right)
        self.current_speed = max(0.0, speed)
        
        return self.current_speed
    
    def reset(self):
        self.vis_history_left.clear()
        self.vis_history_right.clear()
        self.speed_history.clear()
        self.current_speed = 0.0
        self.frame_count = 0