"""Driver for the DS1307 module with code for reading/writing NVRAM."""
from micropython import const
import utime

DATETIME_REG = const(0) 
CHIP_HALT    = const(128)
CONTROL_REG  = const(7) 
RAM_REG      = const(8) 


class DS1307(object):
    """Driver for the DS1307 RTC."""
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        self.weekday_start = 1
        self.weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday", "Sunday"]
        self._halted = self.is_running()==False
        

    def _dec2bcd(self, value):
        """Convert decimal to binary coded decimal (BCD) format"""
        return (value // 10) << 4 | (value % 10)
    

    def _bcd2dec(self, value):
        """Convert binary coded decimal (BCD) format to decimal"""
        return ((value >> 4) * 10) + (value & 0x0F)
    

    def datetime(self, datetime=None):
        """Get or set datetime"""
        if datetime is None:
            buf = self._guaranteed_read(DATETIME_REG, 7)
            return (
                self._bcd2dec(buf[6]) + 2000, # year
                self._bcd2dec(buf[5]), # month
                self._bcd2dec(buf[4]), # day
                self._bcd2dec(buf[3] - self.weekday_start), # weekday
                self._bcd2dec(buf[2]), # hour
                self._bcd2dec(buf[1]), # minute
                self._bcd2dec(buf[0] & 0x7F) # second
            )
        buf = bytearray(7)
        buf[0] = self._dec2bcd(datetime[6]) & 0x7F # second, msb = CH, 1=halt, 0=go
        buf[1] = self._dec2bcd(datetime[5]) # minute
        buf[2] = self._dec2bcd(datetime[4]) # hour
        buf[3] = self._dec2bcd(datetime[3] + self.weekday_start) # weekday
        buf[4] = self._dec2bcd(datetime[2]) # day
        buf[5] = self._dec2bcd(datetime[1]) # month
        buf[6] = self._dec2bcd(datetime[0] - 2000) # year
        if (self._halted):
            buf[0] |= CHIP_HALT
        self._guranteed_write(DATETIME_REG, buf)
        
        
    def start(self):
        reg = self._guaranteed_read(DATETIME_REG, 1)[0]
        reg &= ~CHIP_HALT
        self._guranteed_write(DATETIME_REG, bytearray([reg]))
        self._halted = False
        
        
    def halt(self):
        reg = self._guaranteed_read(DATETIME_REG, 1)[0]
        reg |= CHIP_HALT
        self._guranteed_write(DATETIME_REG, bytearray([reg]))
        self._halted = True
        
        
    def is_running(self) -> bool:
        reg = self._guaranteed_read(DATETIME_REG, 1)[0]
        reg &= CHIP_HALT
        self._halted = reg != 0
        return self._halted == False
    
    
    def read_nvram(self, address, length) -> bytearray:
        """Read length bytes, starting at address. The address is zero-based, relative to the start of RAM."""
        return self._guaranteed_read(RAM_REG+address, length)
    
    
    def write_nvram(self, address, bytes):
        """Write bytes to NVRAM, starting at address. The address is zero-based, relative to the start of RAM."""
        self._guranteed_write( RAM_REG+address, bytearray(bytes))
        
        
    def get_formatted_time(self) -> str:
        """Get the time in ISO8601 format"""
        (year,month,mday,weekday,hour,minute,second) = self.datetime()
        return f"{year:04d}-{month:02d}-{mday:02d} {hour:02d}:{minute:02d}:{second:02d}"
    
    
    def get_weekday(self) -> str:
        """Get an English string representation of the current weekday."""
        (year,month,mday,weekday,hour,minute,second) = self.datetime()
        return self.weekdays[weekday]
    
    
    def _guranteed_write(self, address:int, bytes:bytearray) -> None:
        """ Retry the write untill it succeeds. Each failure causes a 1 ms delay.
            This can hang forever if there is a hardware fault.
        """
        success = False
        while not success:
            try:
                self.i2c.writeto_mem(self.addr, address, bytes)
                success = True
            except:
                print("Retrying write.")
                utime.sleep_ms(1)
                
                
    def _guaranteed_read(self, address:int, length:int) -> bytearray:
        """ Retry the read untill it succeeds. Each failure causes a 1 ms delay.
            This can hang forever if there is a hardware fault.
        """
        success = False
        while not success:
            try:
                return self.i2c.readfrom_mem(self.addr, address, length)
                success = True
            except:
                print("Retrying read.")
                utime.sleep_ms(1)
                
            
        
