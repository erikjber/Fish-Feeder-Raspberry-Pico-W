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
        
def sync_time(rtc:DS1307) -> bool:
    """Set the RTC to the NTP time. Returns true if sync succeded."""
    result = False
    try:
        ntptime.settime()
        (year, month, mday, hour, minute, second, weekday, yearday) = time.gmtime()
        rtc.datetime((year,month,mday,weekday,hour,minute,second))
        result = True
    except OSError as e:
        print(f"Exception in time sync: {e}")
        if e.errno == 110:
            # Timeout error, do nothing
            pass
        else:
            raise e
    return result
