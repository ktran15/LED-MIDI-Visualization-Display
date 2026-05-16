import time
from gpiozero import Button
import subprocess

pin = 17  #GPIO PIN NUMBER HERE
button = Button(pin, pull_up=True, bounce_time=0.3)

count = 0

def switchFlipped():
    global count
    count +=1
    print(f"Switch flipped, count: {count}")


button.when_pressed = switchFlipped

process = None

while True:
    count = -1
    while count == -1:
        time.sleep(0.1)  # wait for button press
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < 6:
        time.sleep(0.1)  # wait out the window, callbacks still fire
    print(f"Window closed, final count: {count}")
    if process:
        process.terminate()
    if count == 1:
        process = subprocess.Popen(['sudo', '.venv/bin/python3', 'RenderLoop2.py'])
    elif count == 2:
        process = subprocess.Popen(['sudo', '.venv/bin/python3', 'Birds.py'])
    elif count == 3:
        process = subprocess.Popen(['sudo', '.venv/bin/python3', 'Seb.py'])
    elif count == 4:
        process = subprocess.Popen(['sudo', '.venv/bin/python3', 'LeFestin.py'])
    else:
        process = subprocess.Popen(['sudo', '.venv/bin/python3', 'RenderLoop2.py'])