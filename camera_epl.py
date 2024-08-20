import socket
import time
from picamera2 import Picamera2
from picamera2 import Preview
from io import BytesIO
from PIL import Image
import signal
import sys
import os
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
        self.fps = fps
        self.camera = Picamera2()
        self.camera.configure(self.camera.create_still_configuration())
        self.camera.start()
        self.camera.resolution = (640, 480)
        self.resolution = resolution
        
        # Create directory for video footage
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.saveDirectory = os.path.join(script_dir, "camera_footage")
        if not os.path.exists(self.saveDirectory):
            os.makedirs(self.saveDirectory)
        
        # Prepare for video recording
        currentDateTime = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        self.videoFilename = os.path.join(self.saveDirectory, f"{currentDateTime}_footage.mp4")
        self.camera.configure(self.camera.create_video_configuration(main={"size": (640, 480)}))
        self.camera.start_recording(self.videoFilename, format='mp4')
    
    def captureFrame(self):
        image = self.camera.capture_array()
        pil_image = Image.fromarray(image)
        return pil_image
    
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
    
    def split_data(self, data, chunk_size):
        return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    
    def run(self):
        try:
            while True:
                image = self.camera.captureFrame()
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=10)
                image_data = buffer.getvalue()
            
                print(f"Captured image of size: {len(image_data)} bytes")
            
                if len(image_data) > 0:
                    chunk_size = 65507  
                    chunks = self.split_data(image_data, chunk_size)
                
                    for chunk in chunks:
                        self.udpConnection.send(chunk)
                        print(f"Sent chunk of size {len(chunk)} bytes")

                time.sleep(1 / self.camera.fps)
    
        except KeyboardInterrupt:
            self.cleanup(None, None)

udp_ip = '192.168.138.243'
udp_port = 5005
    
udpConnection = UDPConnection(udp_ip, udp_port)
camera = Camera(fps=24, resolution=(640, 480))
    
system = System(udpConnection, camera)
system.run()
