import socket
import time
from picamera2 import Picamera2
from PIL import Image
import os
import signal
import sys
from datetime import datetime

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
        
        self.camera = Picamera2()
        self.camera.configure(self.camera.create_preview_configuration(main={"size": (self.frameWidth, self.frameHeight)}))
        self.camera.start()
        
        self.fps = fps
        self.saveDirectory = "/home/camera_footage"
        if not os.path.exists(self.saveDirectory):
            os.makedirs(self.saveDirectory)
        
        currentDateTime = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.videoFilename = os.path.join(self.saveDirectory, f"{currentDateTime}_epl.mp4")
        
        self.ffmpeg_process = os.popen(
            f"ffmpeg -y -f rawvideo -vcodec rawvideo -s {self.frameWidth}x{self.frameHeight} -pix_fmt rgb24 -r {self.fps} "
            f"-i - -an -vcodec libx264 {self.videoFilename}", 'w')

    def captureFrame(self):
        frame = self.camera.capture_array()
        return frame

    def saveFrame(self, frame):
        self.ffmpeg_process.write(frame.tobytes())

    def stop(self):
        self.camera.stop()
        self.ffmpeg_process.close()

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
                
                self.camera.saveFrame(frame)
                
                time.sleep(1 / self.camera.fps)
        
        except KeyboardInterrupt:
            self.cleanup(None, None)

udp_ip = "192.168.138.243"
udp_port = 5005

udpConnection = UDPConnection(udp_ip, udp_port)
camera = Camera(fps=24, resolution=50)

system = System(udpConnection, camera)
system.run()
