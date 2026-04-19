import asyncio
import time
import adafruit_ble_midi
from adafruit_ble_midi import MIDIService
import adafruit_ble
import adafruit_midi
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_midi.control_change import ControlChange
from adafruit_midi.midi_message import MIDIUnknownEvent
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn

import numpy as np
import rpi_ws281x as LED

LED_BRIGHTNESS = 255
LED_COUNT = 288
LED_PIN = 18

strip = LED.PixelStrip(LED_COUNT, LED_PIN, LED_BRIGHTNESS)
strip.begin()

pedal = False

async def main():
    global pedal
    midi_service = adafruit_ble_midi.MIDIService() # creates MIDI service for BLE MIDI

    ble = adafruit_ble.BLERadio() # creates BLE radio for BLE MIDI
    if ble.connected:# just disconnects from everything if previously connected.
        for c in ble.connections:
            c.disconnect()

    midi = adafruit_midi.MIDI(midi_out=midi_service, midi_in=midi_service, out_channel=0) # creates MIDI object for MIDI messages, sets MIDI service as input and output, and sets channel to 0

    while True:
        print("Waiting for connection to a MIDI device")
        for advertisement in ble.start_scan(ProvideServicesAdvertisement, timeout=60):
            if MIDIService not in advertisement.services:
                continue
            ble.connect(advertisement)
            break

        if ble.connections:
            for connection in ble.connections:
                if connection.connected and not connection.paired:
                    print("Connected; Pairing with the MIDI device")
                    connection.pair()

            if connection.connected and connection.paired:
                print("Paired")
                midi_service = connection[MIDIService]
                midi = adafruit_midi.MIDI(midi_out=midi_service, midi_in=midi_service)

                while ble.connected:
                    midi_in = midi.receive()
                    if midi_in is None:
                        continue
                    if isinstance(midi_in, NoteOn):
                        strip.setPixelColor(ledLocation(midi_in.note), LED.Color(*ledColor(midi_in.note, midi_in.velocity))) # sets color based on pitch of note
                        strip.show()    # displays new color / brightness
                    elif isinstance(midi_in, NoteOff):
                        asyncio.create_task(ledFadeSustain(ledLocation(midi_in.note), ledColor(midi_in.note, midi_in.velocity), midi_in.velocity, pedal)) # calls fade and sustain function with pedal = false
                    elif isinstance(midi_in, ControlChange):
                        if midi_in.control == 64 and midi_in.value >= 64: # if pedal is pressed
                            pedal = True
                        elif midi_in.control == 64 and midi_in.value < 64: # if pedal is released
                            pedal = False
                    #midi_in.note = note type
                    #midi_in.velocity = how hard the note is played
                    #midi_in.channel = which channel the note is played on
                    #midi_in.control =  64 for pedal
                print("Disconnected")


def veloToBrightness(velocity):
    velocities = [0, 127] # data list 1 = potential velocities
    brightness = [100, 255] # data list 2 = potential brigthneses
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
    pass
async def ledFadeSustain (ledLocation, color, velocity, pedal): # fade and sustain function once LED is pressed
    (Red, Green, Blue) = color #unpacks tuple of RGB
    subR = Red / 5 # divides each color into 5 smaller steps
    subG = Green / 5 
    subB = Blue / 5
    timeDelay = sustainHelper(pedal, velocity) / 5 # divides sustain time into 5 smaller steps
    for i in range (5):
        Red -= subR
        Green -= subG
        Blue -= subB
        strip.setPixelColor(ledLocation, LED.Color(int(Red), int(Green), int(Blue))) #sets new color / brightness
        await asyncio.sleep(timeDelay) # delay between each step, so its a smooth fade
        strip.show() # displays new color / brightness
    strip.setPixelColor(ledLocation, LED.Color(0, 0, 0)) # makes sure goes to full black lastly
    strip.show() # displays new color / brightness

def sustainHelper(pedal, velocity):
    pedalVelo = [0, 40, 80, 127]
    if pedal == False:
        fadeTime = [0.5,1,2,3]
        interFadeTime = np.interp(velocity, pedalVelo, fadeTime) # interpolates fade time based on velocity input and data lists
    elif pedal == True:
        fadeTime = [0.5,5,10,20]
        interFadeTime = np.interp(velocity, pedalVelo, fadeTime) # interpolates fade time based on velocity input and data lists
    return float(interFadeTime) # returns interpolated fade time value as an float

asyncio.run(main())
