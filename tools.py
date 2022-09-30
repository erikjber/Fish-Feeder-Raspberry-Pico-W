import time
import utime
import ntptime
from micropython import const

WIFI_CONNECTION_TIMEOUT_MS = const(5000)

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
        
        
def sync_time(network_present:bool, rtc:DS1307):
    """Set the RTC to the NTP time. Gives up if it can't sync."""
    if network_present:
        print(f"RTC datetime before sync: {rtc.get_weekday()}, {rtc.get_formatted_time()}")
        count = 0
        try:
            while True:
                try:
                    print("Syncing time with NTP server.")
                    ntptime.settime()
                    (year, month, mday, hour, minute, second, weekday, yearday) = time.gmtime()
                    print("Setting new datetime.")
                    rtc.datetime((year,month,mday,weekday,hour,minute,second))
                    print("Sync complete.")
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
    


