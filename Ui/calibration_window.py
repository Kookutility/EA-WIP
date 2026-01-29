import tkinter as tk
from tkinter import Canvas
import cv2
import numpy as np
from PIL import Image, ImageTk
import time

from core.calibration import CalibrationLogic
from vision.pose_estimator import PoseEstimator, preprocess_image


class CalibrationWindow(tk.Tk):
    def __init__(self, camera_stream, on_complete_callback):
        super().__init__()
        self.title("EA-WIP Calibration")
        self.geometry("640x480")
        
        self.camera_stream = camera_stream
        self.on_complete_callback = on_complete_callback
        
        self.pose_estimator = PoseEstimator()
        self.calibration_logic = CalibrationLogic(fps=30, calibration_duration=8.0)
        
        self.setup_gui()
        self.update_video_feed()
    
    def setup_gui(self):
        self.canvas = Canvas(self, width=640, height=480)
        self.canvas.pack()
        
        self.canvas_video = self.canvas.create_image(320, 240)
        
        self.state_label = self.canvas.create_text(
            10, 10, 
            text="Calibrating... 0/240 frames", 
            fill="white", 
            font=('Arial', 14, 'bold'), 
            anchor="nw"
        )
        
        self.progress_label = self.canvas.create_text(
            10, 35,
            text="Progress: 0%",
            fill="white",
            font=('Arial', 12),
            anchor="nw"
        )
    
    def update_video_feed(self):
        frame = self.camera_stream.read()
        
        if frame is None:
            self.after(10, self.update_video_feed)
            return
        
        frame = preprocess_image(frame, target_size=(640, 480))
        results = self.pose_estimator.process(frame)
        
        if results.pose_landmarks:
            heel_data = self.pose_estimator.extract_heel_data(results)
            
            if heel_data:
                current_time = time.time()
                self.calibration_logic.process_frame(
                    heel_data['left_height'],
                    heel_data['right_height'],
                    current_time
                )
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = self.pose_estimator.draw_landmarks(frame_rgb, results)
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        progress = (self.calibration_logic.frame_count / self.calibration_logic.max_frames) * 100
        self.canvas.itemconfig(
            self.state_label,
            text=f"Calibrating... {self.calibration_logic.frame_count}/{self.calibration_logic.max_frames} frames"
        )
        self.canvas.itemconfig(
            self.progress_label,
            text=f"Progress: {progress:.1f}%"
        )
        
        self.display_image(frame_rgb)
        
        if self.calibration_logic.is_calibration_complete():
            self.finish_calibration()
            return
        
        self.after(10, self.update_video_feed)
    
    def display_image(self, img):
        imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))
        self.canvas.itemconfig(self.canvas_video, image=imgtk)
        self.canvas.image = imgtk
    
    def finish_calibration(self):
        results = self.calibration_logic.get_calibration_results()
        
        print("=" * 60)
        print("EA-WIP Calibration Complete")
        print("=" * 60)
        print(f"Ground Reference (mu_h):")
        print(f"  Left:  {results['mu_h_left']:.4f}")
        print(f"  Right: {results['mu_h_right']:.4f}")
        print(f"Variability (sigma_h):")
        print(f"  Left:  {results['sigma_h_left']:.4f}")
        print(f"  Right: {results['sigma_h_right']:.4f}")
        print(f"Step Detection Threshold (T):")
        print(f"  Left:  {results['threshold_left']:.4f}")
        print(f"  Right: {results['threshold_right']:.4f}")
        print(f"Stride Amplitude Baseline (h_c):")
        print(f"  Left:  {results['h_c_left']:.4f}")
        print(f"  Right: {results['h_c_right']:.4f}")
        print(f"Cadence Baseline (f_c):")
        print(f"  Left:  {results['f_c_left']:.2f} Hz")
        print(f"  Right: {results['f_c_right']:.2f} Hz")
        print("=" * 60)
        
        self.destroy()
        
        if self.on_complete_callback:
            self.on_complete_callback(results)