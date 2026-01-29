import socket


class UDPClient:
    def __init__(self, ip=None, port=None):
        self.ip = ip if ip is not None else "127.0.0.1"
        self.port = port if port is not None else 5005
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def send_speed(self, speed, frame_count=0, stride_frequency=0.0, 
                   left_height_movement=0.0, right_height_movement=0.0, warning=False):
        message = (f"{speed:.4f},{frame_count},{stride_frequency:.2f},"
                  f"{left_height_movement:.4f},{right_height_movement:.4f},{int(warning)}")
        try:
            self.sock.sendto(message.encode('utf-8'), (self.ip, self.port))
        except Exception as e:
            print(f"UDP Send Error: {e}")
    
    def send_message(self, message):
        try:
            self.sock.sendto(message.encode('utf-8'), (self.ip, self.port))
        except Exception as e:
            print(f"UDP Send Error: {e}")
    
    def close(self):
        if hasattr(self, 'sock'):
            self.sock.close()
    
    def __del__(self):
        self.close()


class UDPReceiver:
    def __init__(self, ip=None, port=None, timeout=0.5):
        self.ip = ip if ip is not None else "0.0.0.0"
        self.port = port if port is not None else 6000
        self.timeout = timeout
        self.sock = None
        self._initialize_socket()
    
    def _initialize_socket(self):
        try:
            if self.sock:
                self.sock.close()
            
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.ip, self.port))
            self.sock.settimeout(self.timeout)
        except Exception as e:
            print(f"UDP Receiver initialization failed: {e}")
            self.sock = None
    
    def receive(self):
        if self.sock is None:
            self._initialize_socket()
            return None
        
        try:
            data, addr = self.sock.recvfrom(1024)
            message = data.decode('utf-8')
            return message
        except socket.timeout:
            return None
        except Exception as e:
            print(f"UDP Receive Error: {e}")
            self._initialize_socket()
            return None
    
    def close(self):
        if hasattr(self, 'sock') and self.sock:
            self.sock.close()
            self.sock = None
    
    def __del__(self):
        self.close()