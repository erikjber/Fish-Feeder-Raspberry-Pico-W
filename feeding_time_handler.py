"""Module that manages the feeding times, reading and writing them to NVRAM,
and updating them in response to network client requests."""

from ds1307 import DS1307
from hardware_controller import HardwareController
from tools import are_times_within_5_minutes
import utime

class FeedingTimeHandler:
    def __init__(self, rtc):
        self.rtc = rtc
        self.is_dirty = False
        if not self.rtc.is_running():
            self.rtc.start()
            self.is_dirty = True
        if not self._is_memory_initialised():
            self._initialise_memory()
            # If the memory has not been set up it is safe to assume the time is not correct either
            self.is_dirty = True
        
    def get_feeding_time(self, time_slot:int) -> (int, int, int):
        """ Read the feeding time at a given slot.
            Returns a tuple of a daily feeding time: hour, minute, and feeding duration in deciseconds.

        """
        if time_slot < 0 or time_slot >= 18:
            raise ValueError("Invalid time slot.")
        addr = time_slot*3
        return self.rtc.read_nvram(addr,3)
    
    def set_feeding_time(self, time_slot:int, hour:int, minute:int, deciseconds:int) -> None:
        """Save the feeding time at a given slot."""
        if time_slot < 0 or time_slot >= 18:
            raise ValueError("Invalid time slot.")
        addr = time_slot*3
        self.rtc.write_nvram(addr,[hour,minute,deciseconds])
        
    def erase_feeding_time(self, time_slot:int) -> None:
        """Erase a feeding time, marking it as unused."""
        self.set_feeding_time(time_slot,255,255,255)
    
    def _initialise_memory(self) -> None:
        """ Initialise the memory to a known state with no feeding times.
            This will typically only run once, the first time the device is turned on.
        """
        for i in range(18):
            self.set_feeding_time(i,255,255,255)
            
    def _is_memory_initialised(self) -> None:
        """ Check if the memory values are sane. Upon first power-on, the memory will be scrambled
            and the chance of it being in a sane state is very small.
        """
        for i in range(18):
            val = self.get_feeding_time(i)
            if val[0] == 255 and val[1] == 255 and val[2] == 255:
                # The time slot is unused
                pass
            elif val[0] < 24 and val[1] < 60 and val[2] > 0:
                # The time slot is used
                pass
            else:
                # Found an invalid timeslot, the memory is in an invalid state
                return False
        return True
    
    
    def handle_client(self, client_socket:socket, hardware_controller:HardwareController) -> None:
        """Read the request from the client and react accordingly."""
        recv_data = []
        while True:
            nu_data = client_socket.read(1)
            if nu_data is None or nu_data == b'':
                break
            recv_data.append(nu_data[0])
            if len(recv_data) == 1 and recv_data[0] == b'u'[0]:
                # Update
                self._send_data(client_socket)
                break
            elif len(recv_data) == 5 and recv_data[0] == b'c'[0]:
                # Create
                self.set_feeding_time(recv_data[1], recv_data[2], recv_data[3], recv_data[4])
                self._send_data(client_socket)
                break
            elif len(recv_data) == 2 and recv_data[0] == b'd'[0]:
                # Delete
                self.erase_feeding_time(recv_data[1])
                self._send_data(client_socket)
                break
            elif len(recv_data) == 2 and recv_data[0] == b'm'[0]:
                # Manual running
                millis = recv_data[1]*100
                print(f"Manual running for {millis} ms.")
                hardware_controller.start_servo(millis)
                break
            elif len(recv_data) > 5:
                # Client sent long request, goodbye
                break
        utime.sleep_ms(1)
        client_socket.close()
            
    def _send_data(self, client_socket:socket) -> None:
        for address in range(18):
            (hour,minute,deciseconds) = self.get_feeding_time(address)
            client_socket.write(bytearray([hour,minute,deciseconds]))
            
    def no_feeding_time_within_5_min(self) -> bool:
        """ Return true if there is a feeding time starting within five minutes of the current time,
            false otherwise."""
        (year,month,mday,weekday,the_hour,the_minute,second) = self.rtc.datetime()
        for address in range(18):
            (hour,minute,deciseconds) = self.get_feeding_time(address)
            if are_times_within_5_minutes(hour,minute, the_hour, the_minute):
                return False
        return True
        
    
        

            
