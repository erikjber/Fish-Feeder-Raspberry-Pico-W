"""Module for controlling the servo, and making sure it runs a determined amount of time.
This module is also responsible for handling the push-button and keeping track of feeding times.
"""
from machine import Pin, PWM
import time
import utime
from micropython import const
import _thread

DEBOUNCE_TIME_MS = const(30)

# These values are for the Feetech FS5106R servo.
# Your servo values may differ.
# Consult your servo documentation for the correct values.
STOPPED_DUTY_CYCLE_NS = const(1500000) # Duty cycle when the servo is stopped, in nanoseconds.
CW_ROTATION_DUTY_CYCLE_NS = const(700000) # Duty cycle when dispensing, in nanoseconds.
FREQUENCY_HZ = const(50) # Servo frequency.

class HardwareController:
    def __init__(self, servoPin:int, buttonPin:int, feeding_time_handler:FeedingTimeHandler):
        self.is_running = False
        self.feeding_time_handler = feeding_time_handler
        self.mutex = _thread.allocate_lock()
        self.buttonPin = Pin(buttonPin, Pin.IN, Pin.PULL_UP)
        self.lastDebounceTime = utime.ticks_ms()
        self.lastButtonState = self.buttonPin.value()
        self.buttonState = self.buttonPin.value()
        self.turn_off =  time.ticks_ms()
        self.last_second = 0
        self.pwm = PWM(Pin(servoPin))
        self.pwm.freq(FREQUENCY_HZ)
        self.stop_servo()
        # The servo controller runs in its own thread to ensure accurate timing.
        _thread.start_new_thread(self.run,())
        
    def start_servo(self, duration_ms:int) -> None:
        with self.mutex:
            if not self.is_running:
                self.is_running = True
                self.turn_off = time.ticks_add(time.ticks_ms(),duration_ms)
                self.pwm.duty_ns(CW_ROTATION_DUTY_CYCLE_NS)
        
    def stop_servo(self) -> None:
        with self.mutex:
            if self.is_running:
                self.pwm.duty_ns(STOPPED_DUTY_CYCLE_NS)
                # Wait a while to let the servo have time to stop
                utime.sleep_ms(300)
                self.pwm.deinit()
                self.is_running = False
        
    def check_servo(self) -> None:
        if self.is_running:
            if time.ticks_diff(time.ticks_ms(),self.turn_off)>=0:
                self.stop_servo()
                
    def check_button(self):
        """Check if the button has been pressed."""
        reading = self.buttonPin.value()
        if reading != self.lastButtonState:
            self.lastDebounceTime = utime.ticks_ms()
        last_debounce_timeout =  time.ticks_add(self.lastDebounceTime, DEBOUNCE_TIME_MS)
        if time.ticks_diff(time.ticks_ms(),last_debounce_timeout)>=0:
            if reading != self.buttonState:
                self.buttonState = reading
                if self.buttonState == 0:
                    self.start_servo(300)
        self.lastButtonState = reading
        
    
    def check_feeding_time(self, hour:int, minute:int):
        """Check if it's time to start a feeding event."""
        for i in range(18):
            (feeding_hour, feeding_minute, feeding_deciseconds) = self.feeding_time_handler.get_feeding_time(i)
            if hour == feeding_hour and minute == feeding_minute:
                print(f"Starting feeding time {feeding_deciseconds*100} ms.")
                self.start_servo(feeding_deciseconds*100)
                # Only one feeding time per minute, so we quit the loop here
                break
                
    def run(self) -> None:
        while True:
            self.check_servo()
            self.check_button()
            
            # Some functions are only called once per minute
            (year,month,mday,weekday,hour,minute,second) = self.feeding_time_handler.rtc.datetime()
            if (self.last_second-second) > 20:
                print(f"Checking for {hour:02d}:{minute:02d}")
                self.check_feeding_time(hour,minute)
            self.last_second = second
