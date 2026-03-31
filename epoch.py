#!/usr/bin/env python3

class UnixEpoch :
    """ Utility function(s) for dealing with dates in Unix Epoch seconds
        $Revision: 1.2 $    $Locker:  $
    """

    @staticmethod
    def to_epoch_seconds(year, month, day, hour=0, minute=0, second=0):
        """
        Calculates the Unix timestamp (seconds since Jan 1, 1970 00:00:00 UTC)
        for a given date and time.
        
        Compatible with MicroPython on Raspberry Pi Pico.
        """
        
        # 0. Force all inputs to integers to prevent float contagion
        #    If 'second' comes in as 30.0, the whole math chain becomes float.
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        second = int(second)
        
        # 1. Define constants
        SECONDS_PER_MINUTE = 60
        SECONDS_PER_HOUR   = 3600
        SECONDS_PER_DAY    = 86400
        
        # Days in each month (index 0 is a placeholder to make 1-12 align)
        # February (index 2) is 28 by default, handled dynamically for leap years.
        DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

        # 2. Helper to check for leap years
        # Rule: Divisible by 4, unless divisible by 100 but not 400.
        def is_leap(y):
            return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)

        # 3. Calculate total days from past years (1970 up to current year)
        total_days = 0
        for y in range(1970, year):
            if is_leap(y):
                total_days += 366
            else:
                total_days += 365

        # 4. Calculate days from past months in the current year
        for m in range(1, month):
            if m == 2 and is_leap(year):
                total_days += 29
            else:
                total_days += DAYS_IN_MONTH[m]

        # 5. Add days from current month (minus 1, because today isn't over)
        total_days += (day - 1)

        # 6. Convert everything to total seconds
        total_seconds = (total_days * SECONDS_PER_DAY) + \
                        (hour * SECONDS_PER_HOUR) + \
                        (minute * SECONDS_PER_MINUTE) + \
                        second

        return total_seconds

if __name__ == "__main__" :

    import time
    from sys import stderr
    
    # Example usage:
    year = 2026
    month = 1
    day = 8
    hour = 5
    minute = 8
    second = 37

    thenusec=time.time() # MicroPython
    unix_seconds = UnixEpoch.to_epoch_seconds(year, month, day, hour, minute, second)
    nowusec=time.time()
    print(f"{year}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}", file=stderr)
    print(unix_seconds)

    delta_msec = nowusec-thenusec
    print (f"{delta_msec:.4} msec elapsed")

