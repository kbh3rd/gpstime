#!/usr/bin/env python3
""" Polled event timing
    $Revision: 1.2 $    $Locker:  $
"""

import time

class event_timer:
    """ Keep track of timed events and state flips with rollover protection """
    def __init__(self, toggle:bool=False, name:str="timer"):
        self.set = False
        self.timeout = 0
        self.recurring = False
        self.toggle_state = toggle
        self.name = name
        self.increment = 0

    def set_timeout_ms(self, ms, recur=False):
        # FIX: Use ticks_add to calculate the future deadline
        self.timeout = time.ticks_add(time.ticks_ms(), ms)
        self.set = True
        self.recurring = recur
        if recur:
            self.increment = ms
        else:
            self.increment = 0

    @property
    def is_set(self):
        """ Return tuple of set, has timed out, and toggle_state """
        # ticks_diff is already used correctly here
        timed_out = time.ticks_diff(time.ticks_ms(), self.timeout) >= 0
        return (self.set, self.set and timed_out, self.toggle_state)

    def timed_out(self):
        now = time.ticks_ms()
        return_bool = self.set and time.ticks_diff(now, self.timeout) >= 0

        if self.set and return_bool:
            if self.recurring:
                # FIX: Use ticks_add to move the deadline forward
                self.timeout = time.ticks_add(self.timeout, self.increment)
                self.toggle_state = not self.toggle_state
            else:
                self.set = False
                self.toggle_state = not self.toggle_state

        return return_bool

    @property
    def flipflop(self):
        return self.toggle_state
    
  
if "__main__" == __name__ :
    
    timer1 = event_timer(name="One shot")
    timer2 = event_timer(name="Recurrer")

    timer1.set_timeout_ms (2000, recur=False)
    timer2.set_timeout_ms (3000, recur=True)
    
    print ("Starting...")

    while True :
        time.sleep (1)
        print (".", end="")
        if timer1.set and timer1.timed_out() :
            print (f"{timer1.name} timed out, state {timer1.flipflop}")
        if timer2.set and timer2.timed_out() :
            print (f"{timer2.name} timed out, state {timer2.flipflop}")


