class Config:
    DEFAULT_UDP_IP = "127.0.0.1"
    DEFAULT_UDP_PORT = 5005
    DEFAULT_UDP_RECV_PORT = 6000
    
    DEFAULT_CAMERA_ID = 0
    DEFAULT_FPS = 30
    
    DEFAULT_CALIBRATION_DURATION = 8.0
    DEFAULT_BASE_SPEED = 1.3
    
    LAMBDA_WEIGHT = 0.5
    THETA_O = 0.25
    
    MEDIAPIPE_MIN_DETECTION_CONFIDENCE = 0.5
    MEDIAPIPE_MIN_TRACKING_CONFIDENCE = 0.5
    
    @classmethod
    def get_udp_config(cls, ip=None, port=None):
        return {
            'ip': ip if ip is not None else cls.DEFAULT_UDP_IP,
            'port': port if port is not None else cls.DEFAULT_UDP_PORT
        }
    
    @classmethod
    def get_camera_config(cls, camera_id=None):
        return {
            'camera_id': camera_id if camera_id is not None else cls.DEFAULT_CAMERA_ID
        }