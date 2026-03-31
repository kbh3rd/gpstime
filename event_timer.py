#!/usr/bin/env python3
""" Polled event timing
    $Revision: 1.1 $    $Locker:  $
"""

import time

class event_timer :
    """ Keep track of timed events and state flips
    """
    def __init__ (self, toggle:bool=False, name:str="timer") :
        self.set = False
        self.timeout = 0
        self.recurring = False
        self.toggle_state = toggle
        self.name = name

    def set_timeout_ms(self, ms, recur=False) :
        self.timeout = time.ticks_ms() + ms
        self.set = True
        self.recurring = recur
        if recur :
            self.increment = ms
        else : 
            self.increment = 0

    @property
    def is_set (self) :
        """ Return tuple of set, set and has timed out, toggle_state """
        return (self.set, self.set and time.ticks_diff (time.ticks_ms(), self.timeout) >= 0, self.toggle_state)

    def timed_out(self) :
        """ Return boolean of set and has timed out
            Reset 'set' if not recurring
            Toggle self.toggle_state if just timed out
        """
        now = time.ticks_ms()
        return_bool = self.set and time.ticks_diff(now, self.timeout) >= 0
        if self.set and self.recurring :
            if return_bool : # timed out
                self.timeout += self.increment
                self.toggle_state = False if self.toggle_state else True
        elif self.set :
            self.set = not return_bool # still set iff set and not timed out

        return return_bool

    @property
    def flipflop(self) :
        """ Return current toggle state """
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
