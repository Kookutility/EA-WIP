import tkinter as tk
from tkinter import messagebox
import argparse

from vision.pose_estimator import CameraStream
from ui.calibration_window import CalibrationWindow
from ui.inference_window import InferenceWindow
from utils.config import Config


class Application:
    def __init__(self, args):
        self.args = args
        self.camera_stream = None
        self.calib_results = None
        
        self.udp_config = Config.get_udp_config(
            ip=args.udp_ip,
            port=args.udp_port
        )
        
        self.camera_config = Config.get_camera_config(
            camera_id=args.camera_id
        )
        
        self.v0 = args.base_speed
    
    def start(self):
        try:
            self.camera_stream = CameraStream(
                camera_id=self.camera_config['camera_id']
            )
        except Exception as e:
            messagebox.showerror("Error", f"Camera initialization failed: {e}")
            return
        
        self.show_start_window()
    
    def show_start_window(self):
        root = tk.Tk()
        root.title("EA-WIP")
        root.geometry("400x300")
        
        title_label = tk.Label(
            root,
            text="EA-WIP: Ergonomic-Adaptive\nWalking-In-Place",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=30)
        
        info_label = tk.Label(
            root,
            text="Camera-based VR Locomotion with\nUser-Specific Calibration and Occlusion Handling",
            font=('Arial', 10)
        )
        info_label.pack(pady=10)
        
        start_button = tk.Button(
            root,
            text="Start Calibration",
            command=lambda: self.start_calibration(root),
            font=('Arial', 12),
            width=20,
            height=2
        )
        start_button.pack(pady=20)
        
        exit_button = tk.Button(
            root,
            text="Exit",
            command=root.destroy,
            font=('Arial', 12),
            width=20,
            height=1
        )
        exit_button.pack(pady=10)
        
        root.mainloop()
    
    def start_calibration(self, parent_window):
        parent_window.destroy()
        
        calib_window = CalibrationWindow(
            camera_stream=self.camera_stream,
            on_complete_callback=self.on_calibration_complete
        )
        calib_window.mainloop()
    
    def on_calibration_complete(self, calib_results):
        self.calib_results = calib_results
        self.start_inference()
    
    def start_inference(self):
        inference_window = InferenceWindow(
            camera_stream=self.camera_stream,
            calib_results=self.calib_results,
            v0=self.v0,
            udp_config=self.udp_config
        )
        inference_window.mainloop()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='EA-WIP: Ergonomic-Adaptive Walking-In-Place for VR Locomotion'
    )
    
    parser.add_argument(
        '--udp-ip',
        type=str,
        default=None,
        help=f'UDP target IP address (default: {Config.DEFAULT_UDP_IP})'
    )
    
    parser.add_argument(
        '--udp-port',
        type=int,
        default=None,
        help=f'UDP target port (default: {Config.DEFAULT_UDP_PORT})'
    )
    
    parser.add_argument(
        '--camera-id',
        type=int,
        default=None,
        help=f'Camera device ID (default: {Config.DEFAULT_CAMERA_ID})'
    )
    
    parser.add_argument(
        '--base-speed',
        type=float,
        default=Config.DEFAULT_BASE_SPEED,
        help=f'Base walking speed v0 in m/s (default: {Config.DEFAULT_BASE_SPEED})'
    )
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    app = Application(args)
    app.start()


if __name__ == "__main__":
    main()