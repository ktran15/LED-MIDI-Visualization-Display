import time
import mido
import threading

import numpy as np
from pi5neo import Pi5Neo, EPixelType

LED_BRIGHTNESS = 1.0
LED_COUNT = 286
LED_PIN = 10

strip = Pi5Neo('/dev/spidev0.0', LED_COUNT, 800) # creates LED strip object with 288 LEDs, connected to SPI port 0.0, with a frequency of 800kHz

pedal = False
Diffusion = 7 # must be odd
recent_colors = [] # list of tuples of RGB values for recently played notes
last_note_time = 0 # variable to track time of last note played, for tempo calculation

def main():
    global pedal
    global recent_colors
    global last_note_time
    port_name = next(p for p in mido.get_input_names() if 'Roland' in p) # finds MIDI input port with "Roland" in name
    input_port =   mido.open_input(port_name) # opens MIDI input port
    print("Connected")
    threading.Thread(target=bottomStripThread, daemon=True).start() # starts thread for bottom strip
    for msg in input_port: # loops through MIDI messages
        if msg.type == 'note_on' and msg.velocity > 0: # if note is pressed):
            loc = ledLocation(msg.note) # finds LED location based on pitch of note
            R,G,B = ledColor(msg.note, msg.velocity) # sets color based on pitch of note
            half = Diffusion // 2
            last_note_time = time.perf_counter() # updates time of last note played
            recent_colors.append((R,G,B)) # adds color to list of recently played notes
            if len(recent_colors) > 15: # keeps list of recently played notes to 5
                recent_colors.pop(0)
            for i in range(-half, half +1):
                multiplier = diffusionHelper(abs(i))
                strip.set_led_color(loc+i, int(R*multiplier), int(G*multiplier), int(B*multiplier)) # sets color based on pitch of note
            strip.update_strip()    # displays new color / brightness     
            print(f"Note On: {msg.note}, Velocity: {msg.velocity}") # prints note and velocity in terminal for testing
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0): # if note is released
            loc = ledLocation(msg.note) # finds LED location based on pitch of note
            threading.Thread(target=ledFadeSustain, args=(loc, ledColor(msg.note, msg.velocity), msg.velocity, pedal), daemon = True).start() # calls fade and sustain function with pedal = false
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
    R = (ledColorHelper(pitch, [255, 255, 255, 0, 0, 75, 148])) * (veloToBrightness(velocity) / 255) # provides data list of RED in ROYGBIV
    G = (ledColorHelper(pitch, [0, 127, 255, 255, 0, 0, 0])) * (veloToBrightness(velocity) / 255) # provides data list of GREEN in ROYGBIV
    B = (ledColorHelper(pitch, [0, 0, 0, 0, 255, 130, 211])) * (veloToBrightness(velocity) / 255) # provides data list of BLUE in ROYGBIV
    return (int(R), int(G), int(B)) # returns tuple of RGB

def ledColorHelper(pitch, colorIndex):
    pitches = [21, 35.5, 50, 64.5, 79, 93.5, 108] # data list of potential pitches
    color = colorIndex # data list of potential colors (0-255)
    interValueColor = np.interp(pitch, pitches, color) # interpolates color value based on pitch input and data lists
    return int(interValueColor) # returns interpolated color value as an integer

def ledLocation(pitch):
    pitches = [21, 108] # data list of potential pitches
    locations = [0, 180] # data list of potential LED locations
    interValueLocation = np.interp(pitch, pitches, locations) # interpolates LED location based on pitch input and data lists
    loc = interValueLocation
    loc = min(178, loc)
    loc = max(3, loc) # makes sure location is at least 1, so it doesn't try to light up LED -1
    print(f"LED Location: {loc}") # prints LED location in terminal for testing
    return int(loc) # returns interpolated LED location as an integer

def ledFadeSustain (ledLocation, color, velocity, pedal): # fade and sustain function once LED is pressed
    (Red, Green, Blue) = color #unpacks tuple of RGB
    subR = Red / 5
    subG = Green / 5
    subB = Blue / 5
    timeDelay = sustainHelper(pedal, velocity) / 5 # divides sustain time into 5 smaller steps
    loc = ledLocation
    for i in range (5):
        Red -= subR
        Green -= subG
        Blue -= subB
        for j in range(-Diffusion//2, Diffusion//2 + 1):
            multiplier = diffusionHelper(abs(j))
            strip.set_led_color(loc+j, int(Red*multiplier), int(Green*multiplier), int(Blue*multiplier)) # sets color based on pitch of note
        time.sleep(timeDelay) # delay between each step, so its a smooth fade
        strip.update_strip() # displays new color / brightness
    for i in range(-Diffusion//2, Diffusion//2 + 1):
        strip.set_led_color(loc+i, 0, 0, 0) # makes sure goes to full black lastly
    strip.update_strip() # displays new color / brightness

def sustainHelper(pedal, velocity):
    pedalVelo = [0, 40, 80, 127]
    if pedal == False:
        fadeTime = [0.1,0.15,0.2,0.25]
        interFadeTime = np.interp(velocity, pedalVelo, fadeTime) # interpolates fade time based on velocity input and data lists
    elif pedal == True:
        fadeTime = [0.5,0.7,0.9,1.1]
        interFadeTime = np.interp(velocity, pedalVelo, fadeTime) # interpolates fade time based on velocity input and data lists
    return float(interFadeTime) # returns interpolated fade time value as an float
    
def rollingAverage():
    if len(recent_colors) == 0:
        return (0,0,0) # if no recent colors, return black
    avg_R = sum(color[0] for color in recent_colors) / len(recent_colors) # calculates average RED value
    avg_G = sum(color[1] for color in recent_colors) / len(recent_colors) # calculates average GREEN value
    avg_B = sum(color[2] for color in recent_colors) / len(recent_colors) # calculates average BLUE value
    return (int(avg_R), int(avg_G), int(avg_B)) # returns tuple of average RGB

def bottomStripThread():
    current_avg_color = rollingAverage() # gets average color of recently played notes
    while True:
        for i in range(181, 286): # lights up bottom strip with average color
            strip.set_led_color(i, current_avg_color[0], current_avg_color[1], current_avg_color[2])
        strip.update_strip() # displays new color / brightness
        time.sleep(5) # updates every 5 seconds for smooth transition
        new_average_color = rollingAverage() # gets new average color of recently played notes
        if new_average_color != current_avg_color: # if average color has changed, update bottom strip to new average color
            step_R = (new_average_color[0] - current_avg_color[0]) / 5 # divides color change into 5 smaller steps for smooth transition
            step_G = (new_average_color[1] - current_avg_color[1]) / 5
            step_B = (new_average_color[2] - current_avg_color[2]) / 5 
            for step in range(5):
                intermediate_R = int(current_avg_color[0] + step_R * (step+1)) # calculates intermediate RED value for smooth transition
                intermediate_G = int(current_avg_color[1] + step_G * (step+1)) # calculates intermediate GREEN value for smooth transition
                intermediate_B = int(current_avg_color[2] + step_B * (step+1)) # calculates intermediate BLUE value for smooth transition
                for i in range(181, 286):
                    strip.set_led_color(i, intermediate_R, intermediate_G, intermediate_B) # sets color based on average color of recently played notes
                strip.update_strip() # displays new color / brightness
                time.sleep(1) # delay between each step, so its a smooth transition
        if time.perf_counter() - last_note_time > 6:
            recent_colors.clear() # if no notes played for 10 seconds, clear recent colors to turn off bottom strip
        current_avg_color = new_average_color # updates current average color to new average color for next loop
main()

