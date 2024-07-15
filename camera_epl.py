from picamera2 import PiCamera  
import io
import time
import socket
import signal
import sys
from datetime import datetime
import os  

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
        self.resolution = resolution
        self.fps = fps
        
        self.camera = PiCamera()
        self.camera.resolution = (640, 480)  
        self.camera.framerate = fps
        
        self.saveDirectory = "/home/pi/camera_footage"
        if not os.path.exists(self.saveDirectory):
            os.makedirs(self.saveDirectory)
        
        currentDateTime = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.videoFilename = os.path.join(self.saveDirectory, f"{currentDateTime}_epl.h264")
        
        self.udpConnection = None
    
    def captureFrame(self):
        stream = io.BytesIO()
        self.camera.capture(stream, format='jpeg', use_video_port=True)  
        return stream.getvalue()
    
    def saveFrame(self, frame):
       
        pass
    
    def startStreaming(self, udpConnection):
        self.udpConnection = udpConnection
        self.camera.start_recording(self.videoFilename)
    
    def stop(self):
        self.camera.stop_recording()
        self.camera.close()

class System:
    def __init__(self, udpConnection, camera):
        self.udpConnection = udpConnection
        self.camera = camera
        
        signal.signal(signal.SIGINT, self.cleanup)
    
    def cleanup(self, signum, frame):
        print("Exiting gracefully...")
        self.camera.stop()
        self.udpConnection.close()
        sys.exit(0)
    
    def run(self):
        try:
            self.camera.startStreaming(self.udpConnection)
            
            while True:
                frame = self.camera.captureFrame()
                
                if len(frame) <= 65507:
                    self.udpConnection.send(frame)
                
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
