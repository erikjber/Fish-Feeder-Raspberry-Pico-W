"""Module which broadcasts the UDP multicast beacon."""

import time
import socket

class Beacon:
    def __init__(self,message:str):
        self.group = "226.1.1.1"
        self.port = 5050
        self.ttl = 3
        self.message = message.encode()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send(self):
        try:
            self.sock.sendto(self.message, (self.group, self.port))
        except Exception as e:
            print(f"Beacon exception: {e}")
