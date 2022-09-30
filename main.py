from machine import Pin
from ds1307 import DS1307
from feeding_time_handler import FeedingTimeHandler
from tools import connect_wifi, sync_time
from beacon import Beacon
from hardware_controller import HardwareController
from micropython import const
import time
import utime
import ntptime
import network
import socket
import wifi_secrets

BEACON_INTERVAL_MS = const(1000)
PORT = const(2390)

network_present = False

i2c = machine.I2C(0,
                  scl=machine.Pin(17),
                  sda=machine.Pin(16),
                  freq=100000)
    
rtc = DS1307(i2c)
feeding_time_handler = FeedingTimeHandler(rtc)
hardware_controller = HardwareController(21, 20, feeding_time_handler)

print("Starting FishFeeder 3000!")
print(f"RTC time: {rtc.get_weekday()} {rtc.get_formatted_time()}")

print("Creating network object.")
wlan = network.WLAN(network.STA_IF)
print("activating WLAN")
wlan.active(True)
print("Connecting to WiFi")
try:
    connect_wifi(wlan, wifi_secrets.ssid, wifi_secrets.password)
    network_present = True
    print("Connected to network")
except:
    print("Could not connect to network, trying to carry on regardless.")
    network_present = False
    
# Create a beacon that transmits the port we are listening on
beacon = Beacon(str(PORT))
beacon_deadline = time.ticks_add(time.ticks_ms(),BEACON_INTERVAL_MS)
    
def setup_server_socket():
    """Initialise listening socket"""
    try:
        print("Attempting to create server socket...")
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.bind(("0.0.0.0",PORT))
        serversocket.settimeout(0.001)
        serversocket.listen(5)
        print("Server socket created.")
        return serversocket
    except OSError as e:
        print(f"Could not create server socket. Error: {e}")
        return None
        

def handle_network():
    """ Check for incoming connections, handle them.
        If connection is lost, reconnect.
        Also sends beacon, if it's time."""
    global serversocket
    global hardware_controller
    global feeding_time_handler
    global wlan
    global beacon_deadline
    global beacon
    global network_present
    if network_present and serversocket is not None:
        try:
            (clientsocket, address) = serversocket.accept()
            clientsocket.settimeout(0.3)
            print(f"Got connection from {address}")
            feeding_time_handler.handle_client(clientsocket, hardware_controller)
        except OSError as e:
            if e.errno == 110:
                # This just means we timed out without getting a connection
                pass
            else:
                print(f"Failure in main loop: {e}")

        if time.ticks_diff(time.ticks_ms(),beacon_deadline)>=0:
            beacon.send()
            beacon_deadline = time.ticks_add(time.ticks_ms(),BEACON_INTERVAL_MS)
            
    if wlan.status() != 3 or not network_present:
        print("Lost WiFi connection, reconnecting.")
        try:
            connect_wifi(wlan,wifi_secrets.ssid, wifi_secrets.password)
            network_present = True
        except Exception as e:
            print(f"Could not connect to network {e}")
            network_present = False
    elif serversocket is None:
        print("Trying to set up server socket")
        serversocket = setup_server_socket()
        
sync_time(network_present, rtc)
utime.sleep_ms(1000)
serversocket = setup_server_socket()
last_second = 0

# Main loop
while True:
    handle_network()
    
    # Some functions are only called once per minute
    (year,month,mday,weekday,hour,minute,second) = rtc.datetime()
    if (last_second-second) > 20:
        # Time sync is carried out every hour, on the hour
        if minute == 0:
            sync_time(network_present, rtc)
    last_second = second

