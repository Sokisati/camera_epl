import socket
import time
from picamera2 import Picamera2
from io import BytesIO
from PIL import Image
import signal
import sys
import threading
import cv2
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
        self.fps = fps
        self.camera = Picamera2()
        self.camera.configure(self.camera.create_still_configuration(main={"size": resolution}))
        self.camera.start()

    def captureFrame(self):
        image = self.camera.capture_array()

        # Convert the image to a PIL image
        pil_image = Image.fromarray(image)
    
        # Split the image into individual color channels
        r, g, b = pil_image.split()

        # Adjust the green channel - increase the intensity of green slightly
        g = g.point(lambda i: min(255, int(i * 1.2)))

        # Merge the channels back together
        pil_image = Image.merge("RGB", (b, g, r))  # still swap red and blue channels

        return pil_image

    def stop(self):
        self.camera.close()

class System:
    def __init__(self, udpConnection, camera, video_path, resolution, fps):
        self.udpConnection = udpConnection
        self.camera = camera
        self.capture_interval = 1 / self.camera.fps
        self.video_writer = None
        self.video_path = video_path
        self.init_video_writer(video_path, resolution, fps)

        signal.signal(signal.SIGINT, self.cleanup)
        self.timer = None

    def init_video_writer(self, video_path, resolution, fps):
        if not os.path.exists(os.path.dirname(video_path)):
            os.makedirs(os.path.dirname(video_path))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'mp4v' for MP4 files
        self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, resolution)

    def cleanup(self, signum, frame):
        print("Exiting gracefully...")
        if self.timer:
            self.timer.cancel()
        self.camera.stop()
        if self.video_writer:
            self.video_writer.release()
        self.udpConnection.close()
        sys.exit(0)

    def split_data(self, data, chunk_size):
        return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

    def capture_and_send(self):
        image = self.camera.captureFrame()
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=10)
        image_data = buffer.getvalue()

        # Convert PIL image to OpenCV format for video saving
        open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        self.video_writer.write(open_cv_image)

        print(f"Captured image of size: {len(image_data)} bytes")

        if len(image_data) > 0:
            chunk_size = 65507
            chunks = self.split_data(image_data, chunk_size)

            for chunk in chunks:
                self.udpConnection.send(chunk)

        # Schedule the next capture
        self.timer = threading.Timer(self.capture_interval, self.capture_and_send)
        self.timer.start()

    def run(self):
        self.capture_and_send()  # Start the capturing process


udp_ip = '192.168.137.1'
udp_port = 5005
fps = 5
resolution = (480, 360)
video_path = '/home/pi/camera_footage/footage.mp4'

udpConnection = UDPConnection(udp_ip, udp_port)
camera = Camera(fps=fps, resolution=resolution)

system = System(udpConnection, camera, video_path, resolution, fps)
system.run()
