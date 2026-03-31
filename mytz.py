#!/usr/bin/env python3

import sys
import array
from tzoneinfo import ZoneInfo
import os

class MyTZ :
    """ Keep track of currently displayed timezone.
        Provide offsets from Unix Epoch time based on given UTC time
        Uses data from the *nix zoneinfo files as of 2026-01-05
        $Revision: 1.11 $   $Locker:  $
    """

    # I'm in US/Central. Change as much as you need if you're not
    default_zone = 1 # Central; i.e., index in tzdata,but will be overwritten in constructor
    default_dirpath = "/usr/share/zoneinfo/US" # regular Python3
    try :
        import machine # test for micropython
        default_dirpath = "/zoneinfo"   # MicroPython if the import doesn't trigger exception
    except :
        pass

    def __init__ (self, initial_zone="Central") :

        # Expand the supported timezones as necessary :-\
        self.tzdata = [{ "filename": "Eastern", "names": ["Eastern","EST","EDT"], "display": "NYC "},
                       { "filename": "Central", "names": ["Central","CST","CDT"], "display": "CHI "},
                       { "filename": "Mountain", "names": ["Mountain","MST","MDT"], "display": "DEN "},
                       { "filename": "Arizona", "names": ["Arizona","AZ"], "display": "PHOE"},
                       { "filename": "Pacific", "names": ["Pacific","PST","PDT"], "display": "LA  "},
                       { "filename": "Alaska", "names": ["Alaska","Anchorage","AKST","AKDT"], "display": "ANCH"},
                       { "filename": "Hawaii", "names": ["Hawaii","Aleutian","HST","HDT"], "display": "HONO"}
                      ]

        self.default = 1 # in case tzname doesn't match we'll use Central
        self.zoneix = MyTZ.default_zone
        for ix in range(len(self.tzdata)):
            # Initialize the ZoneInfo object for each zone
            self.tzdata[ix]["tz"] = ZoneInfo(f"{self.default_dirpath}/{self.tzdata[ix]['filename']}")
            if initial_zone == self.tzdata[ix]["filename"] or initial_zone in self.tzdata[ix]["names"] :
                self.zoneix = ix
                self.default_zone = ix

    def get_zoneinfo(self, timestamp_utc):
        types = self.tzdata[self.zoneix]["tz"].get_zoneinfo(timestamp_utc);
        return types[0]/3600, types[1], types[2] # Converting offset seconds to offset hours

    def get_tzoffset(self, timestamp_utc):
        return self.get_zoneinfo(timestamp_utc)[0]

    @property
    def display(self) :
        return self.tzdata[self.zoneix]["display"]

    @property
    def number_of_zones(self) :
        return len(self.tzdata)

    @property
    def current_zone(self) :
        return self.tzdata[self.zoneix]["filename"]

    def incr_zone(self) :
        self.zoneix = (self.zoneix+1) % len(self.tzdata)
        return self.current_zone

    def decr_zone(self) :
        self.zoneix = (self.zoneix-1) % len(self.tzdata)
        return self.current_zone

    def set_zone(self, newzone) :
        if type(newzone) == int :
            self.zoneix = newzone % len(self.tzdata)
        elif type(newzone) == str :
            for x in range(len(self.tzdata)) :
                if newzone in self.tzdata[x]["filename"] or newzone in self.tzdata[x]["names"] :
                    self.zoneix = x
                    break
        else :
            raise TypeError
        return self.display

    @property
    def tzlist(self) :
        """ A list of timezone names matching what's in tzdata """
        return ["Eastern","Central","Mountain","Pacific","Alaska","Hawaii"]

    @staticmethod
    def loadDefaultZone(zone_name, filename="defaultzone") :
        """ Load from file if it exists.
            Otherwise use what's given and save that to file
            Does not change current setting; use set_zone
        """
        retval = zone_name # if all else fails we return what was given
        if filename in os.listdir() :
            try :
                with open (filename, "rt") as file :
                    retval = file.read().rstrip()
            except Exception as e:
                print(f"An error occurred reading {filename}: {e}")
                retval = zone_name
        else :
            print("FILE DOES NOT EXIST")
            MyTZ.saveDefaultZone (retval)

        return retval


    @staticmethod
    def saveDefaultZone(zone_name, filename="defaultzone") :
        """ Save the given timezone name to a file. It will
            become the default when next restarted.
            Does not change current setting; use set_zone
        """
        try :
            with open (filename, "wt") as file :
                file.write(f"{zone_name}\n")
        except :
            pass

        return zone_name


if __name__ == "__main__" :

    from epoch import UnixEpoch
    import time

    tz = MyTZ("Pacific") # example set different default

    print (f"Current (default) = {tz.current_zone}")
    print (f"Display: {tz.display}")

    print ("\nScroll forward:")
    for i in range(6): 
        print (i)
        print (f"When incrementing = {tz.incr_zone()}")
        print (f"Current (updated) = {tz.current_zone}")

    print ("\nScroll backwards:")
    for i in range(6): 
        print (i)
        print (f"When decrementing = {tz.decr_zone()}")
        print (f"Current (updated) = {tz.current_zone}")

    
    timelist = [ [2026, 1, 6, 12, 0, 0], # yr mo dy hr mn se
                 [2026, 2, 7, 7, 0, 0],
                 [2026, 3, 7, 7, 0, 0],
                 [2026, 3, 8, 8, 0, 1],
                 [2026, 4, 8, 8, 0, 1],
                 [2026, 5, 8, 8, 0, 1],
                 [2026, 6, 8, 8, 0, 1],
                 [2026, 7, 8, 8, 0, 1],
                 [2026, 8, 8, 8, 0, 1],
                 [2026, 9, 8, 8, 0, 1],
                 [2026, 10, 8, 8, 0, 1],
                 [2026, 11, 1, 8, 0, 1],
                 [2026, 11, 8, 8, 0, 1],
                 [2027, 12, 1, 12, 0, 0],
               ]
    for tryit in timelist :
        seconds = UnixEpoch.to_epoch_seconds(*tryit)
        print (f"{seconds}: {tryit[0]:04}-{tryit[1]:02}-{tryit[2]:02} {tryit[3]:02}:{tryit[4]:02}:{tryit[5]:02}")
        for tznum in range(tz.number_of_zones) :
            tz.set_zone(tznum)
            zoneinfo = tz.get_zoneinfo(seconds)
            print (f"  {zoneinfo[2]} {float(zoneinfo[0])} {'*' if zoneinfo[1] else ' '}")

    seconds = 2500848000 # 2049-04-01 00:00:00 UTC
    tz.set_zone("Central")
    zoneinfo = tz.get_zoneinfo(seconds)
    localtime = time.gmtime(seconds + zoneinfo[0])
    print (f"\n{seconds} = {localtime} {zoneinfo[2]}")
