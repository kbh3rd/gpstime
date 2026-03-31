from machine import Pin, I2C

class backpack:
    """ 4-character 7-segment display
        Based on http://multiwingspan.co.uk/pico.php?page=ht16k33
        $Revision: 1.9 $
        $Locker:  $
    """
    ADDRESS             = 0x70  # 0x71 if solder bridge on A0 of backpack
    BLINK_CMD           = 0x80
    CMD_BRIGHTNESS      = 0xE0
    
    #              0     1     2     3     4     5     6     7     8     9
    NUMS =        [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]
    
    # Extended character map (most common readable forms)
    # Using standard bit order: dp g f e d c b a
    CHARS = {
        '0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F, '4': 0x66,
        '5': 0x6D, '6': 0x7D, '7': 0x07, '8': 0x7F, '9': 0x6F,
        
        # Hex + requested letters (common patterns)
        'A': 0x77,   # top + sides + middle
        'B': 0x7C,   # lowercase b (common for hex)
        'C': 0x39,   # or 0x4E in some fonts — 0x39 is more open
        'D': 0x5E,   # lowercase d
        'E': 0x79,
        'F': 0x71,
        'G': 0x6F,   # lowercase g (looks like 9 with bottom)
        'H': 0x76,
        'I': 0x30,   # looks like 1 (common)
        'J': 0x1E,   # bottom right hook
        'L': 0x38,
        'N': 0x54,   # lowercase n
        'O': 0x3F,   # same as 0 (very common)
        'P': 0x73,
        'S': 0x6D,   # same as 5 (very common)
        'T': 0x78,   # lowercase t
        'U': 0x3E,
        'Y': 0x6E,   # lowercase y
        '-': 0x40,   # middle bar only
        '_': 0x08,   # bottom bar only
        ' ': 0x00,   # space
        
        # Bonus: decimal point alone (useful in strings)
        '.': 0x80,
    }

    def __init__(self, i2c_bus, data_pin, clock_pin, brightness=5):
        self.buffer = bytearray([0]*16)
        self.i2c = I2C(1, sda=Pin(data_pin), scl=Pin(clock_pin))
        self.i2c.writeto(self.ADDRESS, b'\x21')
        self.blink_rate(0)
        self.brightness(brightness)
        self.update_display()
        self.colon_set = False

    # ──────────────────────────────────────────────
    #  Existing methods (unchanged except for context)
    # ──────────────────────────────────────────────
    def brightness(self, b):
        self.i2c.writeto(self.ADDRESS, bytes([self.CMD_BRIGHTNESS | (b & 0x0F)]))

    def blink_rate(self, b):
        self.i2c.writeto(self.ADDRESS, bytes([self.BLINK_CMD | 1 | ((b & 0x03) << 1)]))

    def write_digit(self, position, digit, dot=False):
        offset = 0 if position < 2 else 1
        pos = offset + position
        self.buffer[pos*2] = self.NUMS[digit] & 0xFF
        if dot:
            self.buffer[pos*2] |= 0x80

    def update_display(self):
        data = bytearray([0]) + self.buffer
        self.i2c.writeto(self.ADDRESS, data)

    def print(self, value, zeroes=True):
        self.buffer = bytearray([0]*16)
        if value < 0 or value > 9999:
            return
        sdig = '{:04d}'.format(value) if zeroes else f'{value:4d}'
        for i, d in enumerate(sdig):
            if d != ' ':
                self.write_digit(i, int(d))
            else:
                self.buffer[(i + (1 if i >= 2 else 0))*2] = 0

    def set_decimal(self, position, dot=True):
        offset = 0 if position < 2 else 1
        pos = offset + position
        if dot:
            self.buffer[pos*2] |= 0x80
        else:
            self.buffer[pos*2] &= 0x7F

    def clear(self):
        self.buffer = bytearray([0]*16)
        self.update_display()

    def set_colon(self, colon=True):
        if colon:
            self.buffer[4] |= 0x02
            self.colon_set = True
        else:
            self.buffer[4] &= 0xFD
            self.colon_set = False

    def toggle_colon(self, update_display=False):
        self.set_colon(not self.colon_set)
        if update_display :
            self.update_display()

    # ──────────────────────────────────────────────
    #  NEW: Display a string (up to 4 chars)
    # ──────────────────────────────────────────────
    def show (self, s:str, colon=False, right_align=False):
        """
        Display a string on the 4-digit display.
        Supports: 0-9, AbCdEFghIJLnOPStUy_-. and space
        Dots '.' turn on the decimal point of the previous digit.
        
        right_align=True → pads left with spaces (good for short words/numbers)
        """
        self.buffer = bytearray([0] * 16)
        
        # Normalize and take last 4 meaningful characters
        s = str(s).upper() if len(s) <= 4 else str(s)  # optional: force upper
        
        chars = []
        i = 0
        while len(chars) < 4 and i < len(s):
            c = s[i]
            if c == '.':
                # Apply dot to previous character (if any)
                if chars:
                    chars[-1] |= 0x80
            elif c in self.CHARS:
                chars.append(self.CHARS[c])
            # else: ignore unsupported chars
            i += 1
        
        # Pad if needed
        if right_align:
            chars = [0x00] * (4 - len(chars)) + chars
        else:
            chars += [0x00] * (4 - len(chars))
        
        # Write to buffer (skip colon position)
        for pos in range(4):
            offset = 0 if pos < 2 else 1
            buf_idx = (offset + pos) * 2
            self.buffer[buf_idx] = chars[pos] & 0xFF
        if colon :
            self.set_colon(True)
        
        self.update_display()

        
if __name__ == "__main__" :
    from time import sleep

    PIN_DISP_DIO = 6 #9
    PIN_DISP_CLK = 7 #10

    # declare an instance
    f = backpack(1, PIN_DISP_DIO,PIN_DISP_CLK) # bus, data, clock
    # f.brightness(6)

    # decimals on
    if False :
        for i in range(4):
            f.set_decimal(i)
            f.update_display()
            sleep(0.5)
        # decimals off
        for i in range(4):
            f.set_decimal(i, False)
            f.update_display()
            sleep(0.5)

    # print something w/o leading zeroes
    for something in (1, 12, 123, 1234) :
        f.print(something, False)
        f.update_display()
        sleep(0.5)

    # print something with leading zeroes
    for something in (1, 12, 123, 1234) :
        f.print(something, True)
        f.update_display()
        sleep(0.5)

    sleep(0.5)

    # clear the display
    # f.clear()
    sleep(0.5)
    # blink the colon
    for i in range(4):
        f.set_colon()
        f.update_display()
        sleep(0.5)
        f.set_colon(False)
        f.update_display()
        sleep(0.5)       

    # Show some hex strings
    f.show("deAd")
    sleep (0.25)
    f.show("BEEF")
    sleep (0.25)
    f.show("STL")
    sleep (1)

    # do some counting as fast as we can
    for i in range(10000):
        f.print(i, False)
        f.update_display()

    # Toggle the cursor
    while True :
        f.toggle_colon()
        f.update_display()
        sleep(0.5)
