import tkinter as tk
from tkinter import Canvas
import cv2
import numpy as np
from PIL import Image, ImageTk
import time
from collections import deque

from core.ea_wip import EAWIP
from vision.pose_estimator import PoseEstimator, preprocess_image
from communication.udp_client import UDPClient


class InferenceWindow(tk.Tk):
    def __init__(self, camera_stream, calib_results, v0, udp_config=None):
        super().__init__()
        self.title("EA-WIP Real-time Tracking")
        self.geometry("640x480")
        
        self.camera_stream = camera_stream
        self.calib_results = calib_results
        
        self.pose_estimator = PoseEstimator()
        self.ea_wip = EAWIP(fps=30)
        self.ea_wip.set_calibration_results(calib_results)
        self.ea_wip.set_base_speed(v0)
        
        if udp_config is None:
            udp_config = {'ip': '127.0.0.1', 'port': 5005}
        
        self.udp_client = UDPClient(ip=udp_config['ip'], port=udp_config['port'])
        
        self.frame_count = 0
        self.current_speed = 0.0
        
        self.left_heel_heights = deque(maxlen=60)
        self.right_heel_heights = deque(maxlen=60)
        self.time_stamps = deque(maxlen=60)
        self.crossings_left = deque(maxlen=10)
        self.crossings_right = deque(maxlen=10)
        
        self.prev_left_heel_height = None
        self.prev_right_heel_height = None
        self.last_crossing_time_left = None
        self.last_crossing_time_right = None
        
        self.refractory_period = 0.3
        
        self.setup_gui()
        self.update_video_feed()
    
    def setup_gui(self):
        self.canvas = Canvas(self, width=640, height=480)
        self.canvas.pack()
        
        self.canvas_video = self.canvas.create_image(320, 240)
        
        self.speed_label = self.canvas.create_text(
            10, 10,
            text="Speed: 0.00 m/s",
            fill="white",
            font=('Arial', 24, 'bold'),
            anchor="nw"
        )
        
        self.frame_label = self.canvas.create_text(
            10, 45,
            text="Frame: 0",
            fill="white",
            font=('Arial', 14),
            anchor="nw"
        )
    
    def detect_step_events(self, left_heel_height, right_heel_height, current_time):
        left_threshold = self.calib_results['threshold_left']
        right_threshold = self.calib_results['threshold_right']
        
        if self.prev_left_heel_height is not None:
            left_cross = (self.prev_left_heel_height < left_threshold <= left_heel_height)
            if left_cross:
                if self.last_crossing_time_left is not None:
                    interval = current_time - self.last_crossing_time_left
                    
                    if interval >= self.refractory_period:
                        self.crossings_left.append((current_time, self.frame_count))
                        self.last_crossing_time_left = current_time
                else:
                    self.last_crossing_time_left = current_time
                    self.crossings_left.append((current_time, self.frame_count))
        
        if self.prev_right_heel_height is not None:
            right_cross = (self.prev_right_heel_height < right_threshold <= right_heel_height)
            if right_cross:
                if self.last_crossing_time_right is not None:
                    interval = current_time - self.last_crossing_time_right
                    
                    if interval >= self.refractory_period:
                        self.crossings_right.append((current_time, self.frame_count))
                        self.last_crossing_time_right = current_time
                else:
                    self.last_crossing_time_right = current_time
                    self.crossings_right.append((current_time, self.frame_count))
        
        self.prev_left_heel_height = left_heel_height
        self.prev_right_heel_height = right_heel_height
    
    def compute_stride_amplitude(self):
        if len(self.crossings_left) < 2:
            h_left = 0.0
        else:
            last_two = list(self.crossings_left)[-2:]
            start_frame = last_two[0][1]
            end_frame = last_two[1][1]
            
            start_idx = max(0, len(self.left_heel_heights) - (self.frame_count - start_frame + 1))
            end_idx = max(0, len(self.left_heel_heights) - (self.frame_count - end_frame + 1))
            
            if start_idx < end_idx and end_idx <= len(self.left_heel_heights):
                between = list(self.left_heel_heights)[start_idx:end_idx + 1]
                h_left = max(between) - min(between) if between else 0.0
            else:
                h_left = 0.0
        
        if len(self.crossings_right) < 2:
            h_right = 0.0
        else:
            last_two = list(self.crossings_right)[-2:]
            start_frame = last_two[0][1]
            end_frame = last_two[1][1]
            
            start_idx = max(0, len(self.right_heel_heights) - (self.frame_count - start_frame + 1))
            end_idx = max(0, len(self.right_heel_heights) - (self.frame_count - end_frame + 1))
            
            if start_idx < end_idx and end_idx <= len(self.right_heel_heights):
                between = list(self.right_heel_heights)[start_idx:end_idx + 1]
                h_right = max(between) - min(between) if between else 0.0
            else:
                h_right = 0.0
        
        return h_left, h_right
    
    def compute_cadence(self):
        if len(self.crossings_left) < 2:
            f_left = 0.0
        else:
            intervals = [t2 - t1 for (t1, _), (t2, _) in zip(list(self.crossings_left)[:-1], list(self.crossings_left)[1:])]
            avg_interval = np.mean(intervals[-1:]) if intervals else 1.0
            f_left = min(1.0 / avg_interval if avg_interval > 0 else 0.0, 4.5)
        
        if len(self.crossings_right) < 2:
            f_right = 0.0
        else:
            intervals = [t2 - t1 for (t1, _), (t2, _) in zip(list(self.crossings_right)[:-1], list(self.crossings_right)[1:])]
            avg_interval = np.mean(intervals[-1:]) if intervals else 1.0
            f_right = min(1.0 / avg_interval if avg_interval > 0 else 0.0, 4.5)
        
        return f_left, f_right
    
    def update_video_feed(self):
        frame = self.camera_stream.read()
        
        if frame is None:
            self.after(10, self.update_video_feed)
            return
        
        frame = preprocess_image(frame, target_size=(640, 480))
        results = self.pose_estimator.process(frame)
        
        current_time = time.time()
        
        if results.pose_landmarks:
            heel_data = self.pose_estimator.extract_heel_data(results)
            
            if heel_data:
                left_height = heel_data['left_height']
                right_height = heel_data['right_height']
                vis_left = heel_data['left_visibility']
                vis_right = heel_data['right_visibility']
                
                self.left_heel_heights.append(left_height)
                self.right_heel_heights.append(right_height)
                self.time_stamps.append(current_time)
                
                self.detect_step_events(left_height, right_height, current_time)
                
                h_left, h_right = self.compute_stride_amplitude()
                f_left, f_right = self.compute_cadence()
                
                speed = self.ea_wip.update(h_left, h_right, f_left, f_right, vis_left, vis_right)
                self.current_speed = speed
                
                self.udp_client.send_speed(
                    speed=speed,
                    frame_count=self.frame_count,
                    stride_frequency=max(f_left, f_right),
                    left_height_movement=h_left,
                    right_height_movement=h_right,
                    warning=False
                )
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = self.pose_estimator.draw_landmarks(frame_rgb, results)
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.current_speed = 0.0
        
        self.canvas.itemconfig(self.speed_label, text=f"Speed: {self.current_speed:.2f} m/s")
        self.canvas.itemconfig(self.frame_label, text=f"Frame: {self.frame_count}")
        
        self.display_image(frame_rgb)
        
        self.frame_count += 1
        self.after(10, self.update_video_feed)
    
    def display_image(self, img):
        imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.canvas.itemconfig(self.canvas_video, image=imgtk)
        self.canvas.image = imgtk
    
    def destroy(self):
        self.camera_stream.stop()
        self.udp_client.close()
        super().destroy()