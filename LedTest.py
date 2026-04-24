from pi5neo import Pi5Neo
import time

LED_BRIGHTNESS = 1.0
LED_COUNT = 144
LED_PIN = 10

strip = Pi5Neo('/dev/spidev0.0', LED_COUNT, 800) # creates LED strip object with 288 LEDs, connected to SPI port 0.0, with a frequency of 800kHz

def main():
    strip.fill_strip(0, 0, 255) # sets all LEDs to blue for testing
    strip.update_strip() # displays new color / brightness
    time.sleep(30)
main()

#sudo sh -c 'echo 32768 > /sys/module/spidev/parameters/bufsiz'
