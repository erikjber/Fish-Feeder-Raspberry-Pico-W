import time
import utime
import ntptime
import socket
from micropython import const

WIFI_CONNECTION_TIMEOUT_MS = const(5000)
HOURS24 = const(24*60) # Number of minutes in 24 hours

def connect_wifi(wlan, ssid, password):
    """ Wait for up to 30 seconds to connect to WiFi.
    """
    give_up_time = time.ticks_add(time.ticks_ms(),WIFI_CONNECTION_TIMEOUT_MS)
    wlan.connect(ssid, password)

    while True:
        if wlan.status()<0 or wlan.status() >= 3:
            break
        if time.ticks_diff(time.ticks_ms(),give_up_time)>=0:
            print("Connection attempt timed out.")
            break
        print("Waiting for connection...")
        time.sleep(1)
        
    if wlan.status() != 3:
        raise ValueError("network connection failed")
    else:
        print("connected")
        print(f"ip = {wlan.ifconfig()[0]}")
    
    
def setup_server_socket(listen_port:int) -> socket:
    """Initialise listening socket, using the designated port."""
    try:
        print("Attempting to create server socket...")
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.bind(("0.0.0.0",listen_port))
        serversocket.settimeout(0.001)
        serversocket.listen(5)
        print("Server socket created.")
        return serversocket
    except OSError as e:
        print(f"Could not create server socket. Error: {e}")
        return None
    
        
def sync_time(network_present:bool, rtc:DS1307):
    """Set the RTC to the NTP time. Gives up if it can't sync."""
    if network_present:
        print("Performing NTP time sync.")
        print(f"RTC datetime before sync: {rtc.get_weekday()}, {rtc.get_formatted_time()}")
        count = 0
        try:
            while True:
                try:
                    ntptime.settime()
                    (year, month, mday, hour, minute, second, weekday, yearday) = time.gmtime()
                    print(f"NTP time: {year:04d}-{month:02d}-{mday:02d} {hour:02d}:{minute:02d}:{second:02d}")
                    rtc.datetime((year,month,mday,weekday,hour,minute,second))
                    print("Sync completed successfully.")
                    break
                except OSError as e:
                    print(f"Exception in time sync: {e}")
                    if e.errno != 110:
                        # Ignore timeout errors, raise everything else
                        raise e
                
                count += 1
                if count > 3:
                    print("Giving up sync")
                    break
                print("Time sync timed out, trying again.")
        except:
            print("Time sync failed. Trying to carry on regardless.")
        print(f"RTC datetime after sync:  {rtc.get_weekday()}, {rtc.get_formatted_time()}")
        
def are_times_within_5_minutes(hour1:int, minute1:int, hour2:int, minute2: int) -> bool:
    """ Check if the two times, given in hours and minutes, are within 5 minutes of each other.
        Times wrap around midnight."""
    minutes_since_midnight1 = hour1*60+minute1
    minutes_since_midnight2 = hour2*60+minute2
    if abs(minutes_since_midnight1-minutes_since_midnight2) < 5:
        return True
    if minutes_since_midnight1 < 5:
        if abs((minutes_since_midnight1+HOURS24)-minutes_since_midnight2) < 5:
            return True
    if minutes_since_midnight2 < 5:
        if abs(minutes_since_midnight1-(minutes_since_midnight2+HOURS24)) < 5:
            return True
    return False
    
