import time
from gpiozero import Button
import subprocess

pin =    #GPIO PIN NUMBER HERE
button = Button(pin, pull_up=True)

count = 0

def switchFlipped():
    global count
    count +=1

button.when_pressed = switchFlipped

process = None

while True:
    count = -1
    button.wait_for_press()  # wait for first flip
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < 4:
        time.sleep(0.1)  # wait out the window, callbacks still fire
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