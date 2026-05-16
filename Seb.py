import time
import mido
import threading

import numpy as np
from pi5neo import Pi5Neo, EPixelType

LED_BRIGHTNESS = 1.0
LED_COUNT = 180
LED_PIN = 10

strip = Pi5Neo('/dev/spidev0.0', LED_COUNT, 800) # creates LED strip object with 288 LEDs, connected to SPI port 0.0, with a frequency of 800kHz

pedal = False
Diffusion = 7 # must be odd
last_note_time = 0 # global variable to keep track of time of last note played

active_fades = {} # dictionary to keep track of which notes are currently fading, with LED location as key and boolean as value
frame_buffer = [(0,0,0)] * LED_COUNT # initializes frame buffer with all LEDs off
def main():
    global pedal
    global last_note_time
    global frame_buffer
    port_name = next(p for p in mido.get_input_names() if 'Roland' in p) # finds MIDI input port with "Roland" in name
    input_port =   mido.open_input(port_name) # opens MIDI input port
    threading.Thread(target=renderLoop, daemon=True).start() # starts render loop in separate thread
    print("Connected")
    for msg in input_port: # loops through MIDI messages
        if msg.type == 'note_on' and msg.velocity > 0: # if note is pressed):
            loc = ledLocation(msg.note) # finds LED location based on pitch of note
            R,G,B = ledColor(msg.note, msg.velocity) # sets color based on pitch of note
            half = Diffusion // 2
            last_note_time = time.perf_counter() # updates time of last note played
            if msg.note in active_fades:
                active_fades[msg.note].set() # if note is already fading, stop the fade
            for i in range(-half, half +1):
                multiplier = diffusionHelper(abs(i))
                frame_buffer[loc+i] = (int(R*multiplier), int(G*multiplier), int(B*multiplier)) # sets color based on pitch of note
            print(f"Note On: {msg.note}, Velocity: {msg.velocity}") # prints note and velocity in terminal for testing
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0): # if note is released
            loc = ledLocation(msg.note) # finds LED location based on pitch of note
            offEvent = threading.Event()
            active_fades[msg.note] = offEvent
            threading.Thread(target=ledFadeSustain, args=(loc, ledColor(msg.note, msg.velocity), msg.velocity, pedal, offEvent, msg.note), daemon = True).start() # calls fade and sustain function with pedal = false
        elif msg.type == 'control_change': # if control change message (pedal)
            if msg.control == 64 and msg.value >= 64: # if pedal is pressed
                    pedal = True
            elif msg.control == 64 and msg.value < 64: # if pedal is released
                    pedal = False
                    #msg.note = note type
                    #msg.velocity = how hard the note is played
                    #msg.channel = which channel the note is played on
                    #msg.control =  64 for pedal
    print("Disconnected")

def renderLoop():
    global frame_buffer
    while True:
        for i, (R,G,B) in enumerate(frame_buffer):
            strip.set_led_color(i, R, G, B) # sets LED colors based on frame buffer
        strip.update_strip() # updates LED strip to show new colors
        time.sleep(0.033) # delay between each frame, so it doesn't overload the CPU

def diffusionHelper(offset):
    offsets = [0,1,2,3]
    diffusion = [1.0, 0.25, 0.08, 0.02]
    interDiffusion = np.interp(offset, offsets, diffusion) # interpolates diffusion value based on Diffusion input and data lists 
    return float(interDiffusion) # returns interpolated diffusion value as an float

def veloToBrightness(velocity):
    velocities = [0, 127] # data list 1 = potential velocities
    brightness = [30, 180] # data list 2 = potential brigthneses
    interValueBrightness = np.interp(velocity, velocities, brightness) # interpolates brightness value based on velocity input and data lists
    return int(interValueBrightness) # returns interpolated brightness value as an integer

def ledColor(pitch, velocity):
    R = (ledColorHelper(pitch, [58,58])) * (veloToBrightness(velocity) / 255) # provides data list of RED in ROYGBIV
    G = (ledColorHelper(pitch, [28,28])) * (veloToBrightness(velocity) / 255) # provides data list of GREEN in ROYGBIV
    B = (ledColorHelper(pitch, [156,156])) * (veloToBrightness(velocity) / 255) # provides data list of BLUE in ROYGBIV
    return (int(R), int(G), int(B)) # returns tuple of RGB

def ledColorHelper(pitch, colorIndex):
    pitches = [21, 108] # data list of potential pitches
    color = colorIndex # data list of potential colors (0-255)
    interValueColor = np.interp(pitch, pitches, color) # interpolates color value based on pitch input and data lists
    return int(interValueColor) # returns interpolated color value as an integer

def ledLocation(pitch):
    pitches = [21, 108] # data list of potential pitches
    locations = [0, 179] # data list of potential LED locations
    interValueLocation = np.interp(pitch, pitches, locations) # interpolates LED location based on pitch input and data lists
    loc = interValueLocation
    loc = min(176, loc)
    loc = max(3, loc) # makes sure location is at least 1, so it doesn't try to light up LED -1
    print(f"LED Location: {loc}") # prints LED location in terminal for testing
    return int(loc) # returns interpolated LED location as an integer

def ledFadeSustain (ledLocation, color, velocity, pedal, event, note): # fade and sustain function once LED is pressed
    global last_note_time
    (Red, Green, Blue) = color #unpacks tuple of RGB
    subR = Red / 8
    subG = Green / 8
    subB = Blue / 8
    timeDelay = sustainHelper(pedal, velocity) / 8 # divides sustain time into 5 smaller steps
    loc = ledLocation
    for i in range (8):
        Red -= subR
        Green -= subG
        Blue -= subB
        if event.is_set():
            return
        for j in range(-Diffusion//2, Diffusion//2 + 1):
            if event.is_set():
                return
            multiplier = diffusionHelper(abs(j))
            frame_buffer[loc+j] = (int(Red*multiplier), int(Green*multiplier), int(Blue*multiplier)) # sets color based on pitch of note
        time.sleep(timeDelay) # delay between each step, so its a smooth fade
    active_fades.pop(note, None)


def sustainHelper(pedal, velocity):
    pedalVelo = [0, 40, 80, 127]
    if pedal == False:
        fadeTime = [0.1,0.15,0.2,0.25]
        interFadeTime = np.interp(velocity, pedalVelo, fadeTime) # interpolates fade time based on velocity input and data lists
    elif pedal == True:
        fadeTime = [0.5,0.7,0.9,1.1]
        interFadeTime = np.interp(velocity, pedalVelo, fadeTime) # interpolates fade time based on velocity input and data lists
    return float(interFadeTime) # returns interpolated fade time value as an float
    
main()

