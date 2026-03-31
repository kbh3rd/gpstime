#!/usr/bin/env python3
# $Revision: 1.3 $     $Locker:  $

import machine
import time

class rtc :
    """ DS3231 Realtime Clock Module interface
    """

    SDA = 8 # Pico position 11
    SCL = 9 # Pico position 12
    I2C_ADDR = 0x68  # I2C address of DS3231

    def __init__ (self) :

        # Initialize I2C on bus 0 with specified pins
        self.i2c = machine.I2C(0, scl=machine.Pin(rtc.SCL), sda=machine.Pin(rtc.SDA))

    @staticmethod
    def int_to_bcd(n):
        """Convert integer to BCD."""
        return ((n // 10) << 4) + (n % 10)

    @staticmethod
    def bcd_to_int(bcd):
        """Convert BCD to integer."""
        return (bcd & 0x0F) + (bcd >> 4) * 10

    def set_time(self, year, month, day, hour, minute, second):
        """Set the time on DS3231 (year as full, e.g., 2026). Weekday set to 1 (Monday) for simplicity."""
        data = bytearray([
            rtc.int_to_bcd(second),
            rtc.int_to_bcd(minute),
            rtc.int_to_bcd(hour),
            rtc.int_to_bcd(1),  # Weekday (1-7)
            rtc.int_to_bcd(day),
            rtc.int_to_bcd(month),
            rtc.int_to_bcd(year - 2000)
        ])
        self.i2c.writeto_mem(rtc.I2C_ADDR, 0x00, data)

    def get_time(self):
        """ Read current time from DS3231.
            Return as Year, Month, Day, Hour, Minute, Second
        """
        self.i2c.writeto(rtc.I2C_ADDR, b'\x00')
        data = self.i2c.readfrom(rtc.I2C_ADDR, 7)
        return (
            2000 + rtc.bcd_to_int(data[6]),  # Year
            rtc.bcd_to_int(data[5]),         # Month
            rtc.bcd_to_int(data[4]),         # Day
            rtc.bcd_to_int(data[2]),         # Hour
            rtc.bcd_to_int(data[1]),         # Minute
            rtc.bcd_to_int(data[0])          # Second
        )

    def get_temperature(self):
        """Read temperature from DS3231."""
        self.i2c.writeto(rtc.I2C_ADDR, b'\x11')
        data = self.i2c.readfrom(rtc.I2C_ADDR, 2)
        temp = data[0] + (data[1] >> 6) * 0.25
        if temp > 127:  # Handle negative temps
            temp -= 256
        return temp

if __name__ == "__main__" :

    myrtc = rtc()
    # Example: Set initial time (uncomment and adjust to current time, then re-comment after first run)
    # myrtc.set_time(2026, 1, 24, 15, 9, 0)  # YYYY, MM, DD, HH, MM, SS (24-hour format)

    # Main loop to read and print time/temperature
    while True:
        year, month, day, hour, minute, second = myrtc.get_time()
        tempC = myrtc.get_temperature()
        tempF = (tempC * 9.0 / 5.0) + 32.0
        print(f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d} | Temp: {tempC:.2f}°C {tempF:.2f}°F")
        time.sleep(1)
