from machine import Pin, ADC

class brightness :
    """ Read brightness sensor and return a rolling average
        between 0 and a max value as an integer.
        The value is used to set the brightness of a 7-seg display.
        Tested with a GM5537 photoresistor and a 10Kohm resistor

        $Revision: 1.1 $    $Locker:  $
    """

    MAX_HISTORY=6

    def __init__ (self, usepin=26, factor=0.67, max_set=16) :
        """ usepin is the GPIO pin#
            factor for scaling to less than physical max (if too bright)
            max_set is the max value to return to set the display brightness
        """
        self.adc = ADC(Pin(usepin))  # GP26 (ADC0)
        self.factor = factor
        self.max = max_set
        self.history = [5 for _ in range(brightness.MAX_HISTORY)]
        self.get_brightness()

    def get_brightness(self) :
        """ Return rolling average for value to set display brightness
            Will take MAX_HISTORY calls for it to settle from the
            preset static average
        """
        voltage = (self.adc.read_u16() / 65535) * 3.3
        val = voltage * 16.0 * self.factor
        self.history.pop(0)
        self.history.append(val)
        avg_bright = min(round(sum(self.history) / brightness.MAX_HISTORY), self.max)
        return avg_bright


if "__main__" == __name__ :

    sensor = brightness()
    from time import sleep
    while True :
        br = sensor.get_brightness()
        print (f"Brightness: {br}")
        sleep(1)
