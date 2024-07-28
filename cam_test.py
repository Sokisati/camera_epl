import socket
import time
import cv2
from picamera2 import Picamera2
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
        
    
    def captureFrame(self):
        frame = self.camera.capture_array()
        return frame
    
    
    def stop(self):
        self.camera.stop()


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
            while True:
                frame = self.camera.captureFrame()
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.camera.resolution]
                _, buffer = cv2.imencode('.jpg', frame_bgr, encode_param)
                
                if len(buffer) <= 65507:
                    self.udpConnection.send(buffer.tobytes())

                time.sleep(1 / self.camera.fps)
        
        except KeyboardInterrupt:
            self.cleanup(None, None)

udp_ip = "192.168.138.243"
udp_port = 5005
    
udpConnection = UDPConnection(udp_ip, udp_port)
camera = Camera(fps=24, resolution=50)
    
system = System(udpConnection, camera)
system.run()
