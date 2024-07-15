import socket
import time
from picamera2 import PiCamera  # Import PiCamera from picamera2
from PIL import Image
import os
import signal
import sys
from datetime import datetime

class UDPConnection:
    def __init__(self, target_ip, port):
        self.target_ip = target_ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send(self, data):
        self.socket.sendto(data, (self.target_ip, self.port))
    
    def close(self):
        self.socket.close()

class Camera:
    def __init__(self, fps, resolution):
        self.frame_width = 640
        self.frame_height = 480
        self.resolution = resolution
        
        self.camera = PiCamera()
        self.camera.resolution = (self.frame_width, self.frame_height)
        
        self.fps = fps
        self.save_directory = "/home/camera_footage"
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
        
        current_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_filename = os.path.join(self.save_directory, f"{current_date_time}_epl.mp4")
        
        self.ffmpeg_process = os.popen(
            f"ffmpeg -y -f rawvideo -vcodec rawvideo -s {self.frame_width}x{self.frame_height} -pix_fmt rgb24 -r {self.fps} "
            f"-i - -an -vcodec libx264 {self.video_filename}", 'w')

    def capture_frame(self):
        frame = self.camera.capture()
        return frame

    def save_frame(self, frame):
        self.ffmpeg_process.write(frame.tobytes())

    def stop(self):
        self.camera.close()
        self.ffmpeg_process.close()

class System:
    def __init__(self, udp_connection, camera):
        self.udp_connection = udp_connection
        self.camera = camera
        
        # Set up signal handler for SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self.cleanup)
    
    def cleanup(self, signum, frame):
        print("Exiting gracefully...")
        self.camera.stop()
        self.udp_connection.close()
        sys.exit(0)
    
    def run(self):
        try:
            while True:
                frame = self.camera.capture_frame()
                image = Image.fromarray(frame)
                buffer = image.tobytes()
                
                if len(buffer) <= 65507:
                    self.udp_connection.send(buffer)
                
                self.camera.save_frame(frame)
                
                time.sleep(1 / self.camera.fps)
        
        except KeyboardInterrupt:
            self.cleanup(None, None)

udp_ip = "192.168.138.243"
udp_port = 5005

udp_connection = UDPConnection(udp_ip, udp_port)
camera = Camera(fps=24, resolution=50)

system = System(udp_connection, camera)
system.run()
