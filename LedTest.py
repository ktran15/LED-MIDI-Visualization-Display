from pi5neo import Pi5Neo
import time

LED_BRIGHTNESS = 1.0
LED_COUNT = 144
LED_PIN = 10

strip = Pi5Neo('/dev/spidev0.0', LED_COUNT, 800) # creates LED strip object with 288 LEDs, connected to SPI port 0.0, with a frequency of 800kHz

def main():
    print("About to send data")
    strip.fill_strip(255, 255, 255)
    print("Data sent")
    strip.update_strip()
    print("Strip updated")
    time.sleep(25)
main()

#sudo sh -c 'echo 32768 > /sys/module/spidev/parameters/bufsiz'
# sudo tee /sys/module/spidev/parameters/bufsiz <<< 32768
