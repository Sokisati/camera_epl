import socket
import time
from picamera import PiCamera
from PIL import Image
import os
import signal
import sys
from datetime import datetime
import numpy as np

class UDPConnection:
    def __init__(self, targetIp, port):
        self.targetIp = targetIp
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send(self, data):
        self.socket.sendto(data, (self.targetIp, self.port))
    
    def close(self):
        self.socket.close()

class Camera:
    def __init__(self, fps, resolution):
        self.frameWidth = 640
        self.frameHeight = 480
        self.resolution = resolution
        
        self.camera = PiCamera()
        self.camera.resolution = (self.frameWidth, self.frameHeight)
        
        self.fps = fps
        self.saveDirectory = "/home/pi/camera_footage"  # Adjust this path as needed
        if not os.path.exists(self.saveDirectory):
            os.makedirs(self.saveDirectory)
        
        currentDateTime = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.videoFilename = os.path.join(self.saveDirectory, f"{currentDateTime}_epl.mp4")
        
        self.ffmpeg_process = os.popen(
            f"ffmpeg -y -f rawvideo -vcodec rawvideo -s {self.frameWidth}x{self.frameHeight} -pix_fmt rgb24 -r {self.fps} "
            f"-i - -an -vcodec libx264 {self.videoFilename}", 'wb')
        
    def captureFrame(self):
        frame = np.empty((self.frameHeight * self.frameWidth * 3,), dtype=np.uint8)
        self.camera.capture(frame, 'rgb')
        frame = frame.reshape((self.frameHeight, self.frameWidth, 3))
        return frame

    def saveFrame(self, frame):
        self.ffmpeg_process.stdin.write(frame)

    def stop(self):
        self.camera.close()
        self.ffmpeg_process.stdin.close()
        self.ffmpeg_process.wait()

class System:
    def __init__(self, udpConnection, camera):
        self.udpConnection = udpConnection
        self.camera = camera
        
        # Set up signal handler for SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self.cleanup)
    
    def cleanup(self, signum, frame):
        print("Exiting gracefully...")
        self.camera.stop()
        self.udpConnection.close()
        sys.exit(0)
    
    def run(self):
        try:
            while True:
                frame = self.camera.captureFrame()
                image = Image.fromarray(frame)
                buffer = image.tobytes()
                
                if len(buffer) <= 65507:
                    self.udpConnection.send(buffer)
                
                self.camera.saveFrame(buffer)
                
                time.sleep(1 / self.camera.fps)
        
        except KeyboardInterrupt:
            self.cleanup(None, None)

udp_ip = "192.168.138.243"
udp_port = 5005

udpConnection = UDPConnection(udp_ip, udp_port)
camera = Camera(fps=24, resolution="480p")

system = System(udpConnection, camera)
system.run()
