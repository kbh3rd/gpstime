#!/usr/bin/env python3
""" Timezone data from /usr/share/zoneinfo/...
    Originally by gemini.google.com and expanded
    $Revision: 1.1 $
    $Locker:  $
"""

import struct
import array
import sys

class ZoneInfo:
    def __init__(self, filepath):
        """
        Initializes the ZoneInfo object by parsing a TZif binary file.
        Supports 64-bit transition times (TZif version 2+).
        """
        self.transitions = array.array('q') # Signed 64-bit integers
        self.indices = array.array('B')     # Unsigned 8-bit integers
        self.types = []                     # List of tuples: (gmtoff, isdst, abbr)

        with open(filepath, 'rb') as f:
            # --- 1. Read Header ---
            # 4 bytes magic, 1 byte version, 15 bytes reserved
            header = f.read(44)
            magic = header[:4]
            
            if magic != b'TZif':
                raise ValueError("Invalid zoneinfo file: missing magic header")
            
            # Version is the 5th byte (ASCII). 
            # b'\0' is V1 (32-bit), b'2' or b'3' is V2/V3 (64-bit)
            version = header[4] 

            # Unpack 32-bit counts (Big-Endian 32-bit integers)
            # isutc, isstd, leap, time, type, char
            counts = struct.unpack('>6l', header[20:])
            leap_cnt, time_cnt, type_cnt, char_cnt = counts[2], counts[3], counts[4], counts[5]
            
            # --- 2. Determine Data Block to Read ---
            # If Version 2+, we must skip the 32-bit block to get to the 64-bit block.
            # 32-bit block size calculation:
            #  time_cnt * 4 (transitions) +
            #  time_cnt * 1 (indices) +
            #  type_cnt * 6 (ttinfos) +
            #  char_cnt * 1 (abbrs) +
            #  leap_cnt * 8 (leaps) +
            #  counts[1] * 1 (isstd) +
            #  counts[0] * 1 (isutc)
            
            if version >= 50: # ASCII '2' or '3'
                skip_size = (
                    (time_cnt * 5) + 
                    (type_cnt * 6) + 
                    char_cnt + 
                    (leap_cnt * 8) + 
                    counts[1] + 
                    counts[0]
                )
                f.seek(skip_size, 1) # Skip 32-bit data

                # Read 64-bit Header
                header = f.read(44)
                counts = struct.unpack('>6l', header[20:])
                leap_cnt, time_cnt, type_cnt, char_cnt = counts[2], counts[3], counts[4], counts[5]
                
                # Format for 64-bit times is 'q' (long long)
                time_fmt = f'>{time_cnt}q'
            else:
                # Version 1 only has 32-bit data
                time_fmt = f'>{time_cnt}l'

            # --- 3. Read Transitions (Times) ---
            # We read all bytes and unpack into a tuple, then load into array.
            # This is RAM efficient enough for Pico (transitions usually < 2000).
            trans_data = f.read(struct.calcsize(time_fmt))
            # Unpack returns a tuple; array constructor takes an iterable
            self.transitions = array.array('q', struct.unpack(time_fmt, trans_data))

            # --- 4. Read Indices ---
            # These are 1-byte indexes mapping a transition to a type
            self.indices = array.array('B', f.read(time_cnt))

            # --- 5. Read Types (ttinfo structures) ---
            # Each type is 6 bytes: gmtoff (4b), isdst (1b), abbrind (1b)
            ttinfo_data = f.read(type_cnt * 6)
            
            # --- 6. Read Abbreviations ---
            abbr_data = f.read(char_cnt)
            
            # Process types
            for i in range(type_cnt):
                off = i * 6
                # unpack: gmtoff (signed int), isdst (byte), abbrind (byte)
                gmtoff, isdst, abbrind = struct.unpack('>lbb', ttinfo_data[off:off+6])
                
                # Extract abbreviation string
                # Find the null terminator starting at abbrind
                null_pos = abbr_data.find(b'\0', abbrind)
                if null_pos == -1: null_pos = len(abbr_data)
                abbr = abbr_data[abbrind:null_pos].decode('utf-8')
                
                self.types.append((gmtoff, isdst, abbr))

    def get_zoneinfo(self, timestamp):
        """
        Takes a Unix timestamp (seconds) and returns the (gmtoff, isdst, abbr) 
        tuple active at that time.
        """
        # Binary search to find the right transition
        # We are looking for the transition that happened *before* or *at* timestamp.
        # This is equivalent to bisect_right - 1.
        
        idx = self._bisect_right(timestamp) - 1
        
        if idx < 0:
            # Timestamp is before the first transition in the file.
            # Standard behavior is to use the first standard-time type found,
            # but simpler parsers often default to the very first type defined.
            # We will return the first type available in the file (index 0 of types list).
            # Note: A robust implementation might scan self.types for the first !isdst.
            if self.types:
                return self.types[0]
            return (0, 0, "UTC") # Fallback if file is empty
            
        type_idx = self.indices[idx]
        return self.types[type_idx]

    def _bisect_right(self, x):
        """
        MicroPython bisect_right implementation for self.transitions array.
        Returns the insertion point to maintain sorted order.
        """
        lo = 0
        hi = len(self.transitions)
        while lo < hi:
            mid = (lo + hi) // 2
            if x < self.transitions[mid]:
                hi = mid
            else:
                lo = mid + 1
        return lo

if __name__ == "__main__" :
    """ Test and demonstration
    """

    import time
    from epoch import UnixEpoch
    import os

    test_times = [
        (2026, 1, 1,  0, 0, 0),
        (2026, 1, 1,  6, 0, 0),
        (2026, 3, 8,  7, 59, 59),
        (2026, 3, 8,  8, 0, 0),
        (2026, 11, 1, 6, 59, 59),
        (2026, 11, 1, 7, 0, 0),
        (2026, 11, 2, 19, 0, 0),
        ]


    try :
        import machine # just as a test for micropython
        zonepath = "/zoneinfo"
    except ImportError:
        zonepath = "/usr/share/zoneinfo/US"

    # Initialize with the file
    if len(sys.argv) != 2 :
        zonefile = f"{zonepath}/Central"
    else :
        zonefile = f"{zonepath}/{sys.argv[1]}"
    print (f"Using {zonefile}")
    tz = ZoneInfo(zonefile)


    for dt in test_times :
        now = UnixEpoch.to_epoch_seconds(*dt) # Unix epoc seconds
        offset, is_dst, abbr = tz.get_zoneinfo(now) # Get timezone data
        loc = time.gmtime(now + offset) # Calculate local time

        print (f"\n{dt[0]}-{dt[1]:02}-{dt[2]:02} {dt[3]:02}:{dt[4]:02}:{dt[5]:02} GMT is {now}")
        print (f"\t{loc[0]}-{loc[1]:02}-{loc[2]:02} {loc[3]:02}:{loc[4]:02}:{loc[5]:02} {abbr} {'y' if is_dst else 'n'} {offset}")

