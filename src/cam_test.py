import socket
import time
from picamera2 import Picamera2
from io import BytesIO
from PIL import Image
import signal
import sys
import threading

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
    def __init__(self, udpConnection, camera):
        self.udpConnection = udpConnection
        self.camera = camera
        self.capture_interval = 1 / self.camera.fps

        signal.signal(signal.SIGINT, self.cleanup)
        self.timer = None

    def cleanup(self, signum, frame):
        print("Exiting gracefully...")
        if self.timer:
            self.timer.cancel()
        self.camera.stop()
        self.udpConnection.close()
        sys.exit(0)

    def split_data(self, data, chunk_size):
        return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

    def capture_and_send(self):
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

        # Schedule the next capture
        self.timer = threading.Timer(self.capture_interval, self.capture_and_send)
        self.timer.start()

    def run(self):
        self.capture_and_send()  # Start the capturing process


udp_ip = '192.168.137.1'
udp_port = 5005

udpConnection = UDPConnection(udp_ip, udp_port)
camera = Camera(fps=5, resolution=(480, 360))

system = System(udpConnection, camera)
system.run()