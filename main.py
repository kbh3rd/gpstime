#!/usr/bin/env python3
""" Implement a digital clock.
    Get the time from a GPS chip.
    Adjust automatically for local DST
    $Revision: 1.21 $    $Locker:  $
"""


from micropyGPS import MicropyGPS   # GPS Time and Position: https://github.com/inmcm/micropyGPS/
from machine import UART, Pin       # Raspberry Pi Pico specifics
import time

from mytz import MyTZ               # Timezone and DST
from epoch import UnixEpoch         # time to unix epoch for DST search
from lightsensor import brightness

# Try TM1637 and use if module present; else assume HT16K33
try :
    import tm1637                       # 4-digit 7-segment LED display: https://github.com/mcauser/micropython-tm1637
    CLK = 0   # e.g., GP0
    DIO = 1   # e.g., GP1
    clkdisp = tm1637.TM1637(clk=Pin(CLK), dio=Pin(DIO))
    clkdisp.brightness(1)  # Brightness level 0-7
except :
    DIO = 16
    CLK = 17
    from ht16k33 import backpack
    clkdisp = backpack(1, 18, 19) # bus, data, clock [, brightness]
    # If that doesn't work then let it abend X-P

# Use the RTC module if present, else continue w/o
has_rtc = False                     # There is a real time clock?
rtc_was_set = False                 # The real time clock has been set?
thertc = None                       # Real time clock object
try :
    from ds3231 import rtc          # DS3231 realtime clock module w/ battery backup
    thertc = rtc()
    has_rtc = True
    print("Has RTC")
except :
    thertc = None
    has_rtc = False
    print("No RTC")
    
# print extra stuff for debugging?
debugging = False

# Configure GPS UART (GP4 = TX, GP5 = RX for UART1)
uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))

# Create GPS parsing object
# Use 0 local offset (UTC); we'll manage timezones and DST ourselves
gps = MicropyGPS(location_formatting='dd', local_offset=0)
print("micropyGPS started. Waiting for data... (Place outside for best results)")


# Timezone change button
TZ_PIN = 28 # position 34
BUTTON_DOWN = 0 # tz_button.value() when button is down
LONG_PRESS = 2000 # milliseconds = 2 seconds
tz_button = Pin(TZ_PIN, Pin.IN, Pin.PULL_UP) # Internal pull-up enabled; active low
tz_button_press = 0
tz_button_released = 0

# Brightness Sensor
BRIGHT_PIN = 26
light_sensor = brightness()
old_bright = 99 # impossible, for state

# Variables for colon blinking and time string (need to send whole string when blinking colon)
time_str = "----"
colon_set = False
colon_flip = 0
clkdisp.show(time_str, colon=colon_set)

# For blinking the onboard LED to let us know the pgm is running
blink_led = Pin(25, Pin.OUT)  # Onboard LED
blink_led.on()

# We'll get multiple updates per second; only update when the second changes
prev_sec = -1
prev_min = -1

# Default to Central timezone
DEFAULT_ZONE = "Central"
default_zone = MyTZ.loadDefaultZone(DEFAULT_ZONE)
tzone = MyTZ(default_zone)
tz_string = tzone.display
tz_offset = 0 # hours from UTC. Will get real value on first fix when we know the date
time_str = tz_string # will show timezone indication until first fix

# Until we get first fix
waiting_for_fix = True
got_first_fix = False

wife_likes_blinking_leds = True
blink_led.off()

def twelvehrs(hr) :
    # 24-hour clock to 12-hour clock
    hr12 = hr
    if hr12 > 12 :
        hr12 -= 12
    elif hr12 == 0 :
        hr12 = 12
    return hr12

while True:

    # colon blink timing
    now_ms = time.ticks_ms()
    if now_ms > colon_flip :
        clkdisp.show(time_str, colon_set)
        if wife_likes_blinking_leds:
            if colon_set :
                blink_led.on()
            else :
                blink_led.off()
        colon_flip = now_ms + 750 if colon_set else now_ms + 250
        colon_set = not colon_set # for next flip
        # Check brightness when colon was set on
        if not colon_set :
            bright = light_sensor.get_brightness()
            if bright != old_bright:
                clkdisp.brightness(bright)
                old_bright = bright

    # Check timzezone change button state changes
    if tz_button.value() == BUTTON_DOWN :
        if not tz_button_press : # just now pressed
            tz_button_press = time.ticks_ms()   # when pressed (in milliseconds of runtime)
            tz_button_released = 0
    else :
        if tz_button_press :
            # had been pressed, just now released
            tz_button_released = time.ticks_ms() - tz_button_press # Duration of press in milliseconds
            tz_button_press = 0

    if uart.any():
        data = uart.read()
        if data:
            for byte in data:
                stat = gps.update(chr(byte))
                if stat:  # New sentence fully parsed and valid
                    if gps.valid:
                        timestamp = gps.timestamp  # (hours, minutes, seconds_float)
                        date = gps.date            # (day, month, year_since_2000)

                        hours24 = int(timestamp[0])
                        minutes = int(timestamp[1])
                        seconds = int(timestamp[2]) # This use case doesn't need sub-second precision

                        # if seconds == prev_sec and not tz_button_released :    # always false on first fix
                        #     continue
                        # prev_sec = seconds

                        if minutes == prev_min and not tz_button_released and not waiting_for_fix :
                            continue
                        prev_min = minutes

                        # Check timezone on first fix
                        # and when the tz change button is released
                        # and at top of hour; that's when DST will change 2x/year
                        if waiting_for_fix or tz_button_released or (minutes == 0 and seconds == 0) : # Zoneinfo check

                            # Incr timezone if that button was pressed and released
                            if tz_button_released :
                                if tz_button_released > LONG_PRESS : # long press, go to default zone
                                    tzone.set_zone(default_zone)
                                else :
                                    tzone.incr_zone() # short press, go to next zone
                                MyTZ.saveDefaultZone(tzone.current_zone)

                            # Get zone offset for this date and time
                            print ("Checking timezone info")
                            epochsec = UnixEpoch.to_epoch_seconds(date[2]+2000, date[1], date[0], hours24, minutes, seconds)
                            print (f"Date {date[2]+2000}-{date[1]:02}-{date[0]:02} {hours24:02}:{minutes:02}:{seconds:02} Epoch seconds {epochsec}")
                            new_offset, isdst, tz_abbr = tzone.get_zoneinfo(epochsec)
                            new_offset = int(new_offset)	# more general tz module returns a float; we're on whole hours
                            # Note changed offset
                            if not new_offset == tz_offset :
                                print (f"Offset change from {tz_offset} to {new_offset}")
                                print (new_offset, isdst, tz_abbr)
                                tz_offset = new_offset
                                if tz_button_released :
                                    # Show the new timezone name
                                    clkdisp.show(tzone.display)
                                    print("Timzone changed to", tzone.display)
                                    time.sleep(1.5)
                            tz_button_released = 0

                        # Do timezone adjustment of received hours only; we don't have fractional zones here.
                        # This will not adjust the date, but it shouldn't need to and we don't care anyways.
                        hours24 = (hours24 + tz_offset) % 24    # Yes, modulo works if negative

                        if debugging :
                            #print()
                            #print(f"Time (UTC): {gps.timestamp}")
                            #print(f"Local Time: {hours:02d}:{minutes:02d}:{seconds:05.2f}")
                            #print(f"Date: {date[1]:02d}/{date[0]:02d}/{date[2] + 2000}")
                            print (f"{hours:02d}:{minutes:02d}:{int(seconds):0.2d}", end="\r")

                        hours = twelvehrs (hours24)
                        time_str = f"{hours:-2d}{minutes:02d}"
                        clkdisp.show(time_str, colon=True)
                        now_ms = time.ticks_ms()
                        # colon_flip = now_ms + 750 if colon_set else now_ms + 250
                        # colon_set = False # next time

                        # Position - safely convert to decimal degrees
                        if gps.latitude and gps.longitude:
                            if waiting_for_fix :
                                print (f"Got a fix: {gps.latitude} {gps.longitude}")
                                waiting_for_fix = False
                                got_first_fix = True
                                wife_likes_blinking_leds = False
                                blink_led.off()
                                if has_rtc :
                                    # Set RTC everytime we were waiting; it could slowly drift from GPS time
                                    thertc.set_time(date[2]+2000, date[1], date[0], hours24, minutes, seconds)
                                    rtc_was_set = True
                                    print (f"Set the RTC clock to {date[2]+2000}-{date[1]:02d}-{date[0]:02d} {hours24:02d}:{minutes:02d}:{seconds:02d}")
                            if debugging :
                                lat_deg = float(gps.latitude[0])          # degrees as float
                                #lat_sign = -1 if gps.latitude[1] == "S" else 1
                                lon_deg = float(gps.longitude[0])
                                #lon_sign = -1 if gps.longitude[1] == "W" else 1

                                decimal_lat = lat_deg # / 60.0
                                decimal_lon = lon_deg # / 60.0

                                # Handle S/W negative signs
                                if gps.latitude[1] == 'S':
                                    decimal_lat = -decimal_lat
                                if gps.longitude[1] == 'W':
                                    decimal_lon = -decimal_lon

                                lat_str = gps.latitude_string()
                                lon_str = gps.longitude_string()
                                print(f"Location: {lat_str}, {lon_str}")
                                print(f"Google Maps: https://maps.google.com/?q={decimal_lat},{decimal_lon}")
                                print(f"Satellites in use: {gps.satellites_in_use}")
                                print(f"Fix type: {gps.fix_type} (2=2D, 3=3D)")
                    else:
                        print("No valid fix yet...")
                        if has_rtc :
                            nowish = thertc.get_time() # Assume the RTC was set _sometime_ or another
                            hours_ish = twelvehrs (nowish[3])
                            time_str = f"{hours_ish:-2d}{nowish[4]:0.2d}"


    time.sleep(0.025)
