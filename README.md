# LED MIDI Visualization Display

A Raspberry Pi 5 reads MIDI from a Roland FP-10 digital piano and drives a strip of addressable LEDs mounted behind the keys. Each note lights the LEDs nearest its key, colored according to pitch and brightened according to how hard the key was struck. Releasing a key starts a fade whose length depends on the sustain pedal, so the light decays roughly the way the sound does.

The unit runs headless. Power on the Pi and it starts listening. A single physical button cycles between color themes without a keyboard, screen, or network connection.

## Demo

<a href="https://youtu.be/B_Xjkx9cfeY">
  <img src="https://img.youtube.com/vi/B_Xjkx9cfeY/maxresdefault.jpg" alt="Demo video: LEDs responding to piano playing in real time" width="640">
</a>

[Watch the demo on YouTube](https://youtu.be/B_Xjkx9cfeY)

## Hardware

| Component | Detail |
| --- | --- |
| Controller | Raspberry Pi 5 |
| Instrument | Roland FP-10, connected over USB MIDI |
| LEDs | 180 WS2812B pixels, 144 LEDs/m, two segments soldered end to end |
| LED power | Separate 5 V 20 A supply, common ground with the Pi |
| Mode input | Momentary button on GPIO 17 |

180 pixels at 144 LEDs/m comes to about 1.25 m, which spans all 88 keys. No single segment on hand was long enough, so two were cut and soldered together by hand. The join has to respect data direction: WS2812B pixels pass data down the strip one way only, so the second segment's DIN must meet the first segment's DOUT or the second run simply never lights.

| Signal | Pi 5 connection | Notes |
| --- | --- | --- |
| LED data | GPIO 10, SPI0 MOSI, physical pin 19 | 800 kHz |
| Button | GPIO 17, physical pin 11 | internal pull-up |
| Ground | any GND pin | shared with the LED supply |
| LED +5 V | external supply | not the Pi's 5 V rail |

Two notes on the wiring, both deliberate and both worth stating plainly.

There is no level shifter. WS2812B expects a logic high near 0.7 × VDD, which is 3.5 V on a 5 V supply, and the Pi's GPIO only swings to 3.3 V. It runs reliably at this strip length, but it is out of specification, and a 74AHCT125 buffer would be the correct fix before extending the run any further.

LED power comes from a dedicated 5 V 20 A supply rather than the Pi's 5 V rail. A WS2812B pixel draws roughly 60 mA with all three channels at full, so 180 of them have a theoretical ceiling near 10.8 A. That is far past anything the Pi can source, and browning out the board that is generating your data signal is a bad failure mode. The 20 A supply leaves close to double the headroom the worst case needs, and in practice the brightness cap described below means real draw never approaches it. The Pi and the LED supply share a ground, since the data line needs a common reference to mean anything.

## How it works

### From MIDI message to lit LED

`mido` opens the first available input port with "Roland" in its name and blocks on the incoming message stream. Three message types matter:

- `note_on` with velocity above zero, meaning a key was pressed
- `note_off`, or `note_on` with velocity zero, meaning a key was released. Instruments differ on which of the two they send, so both are handled
- `control_change` on controller 64, the sustain pedal

Everything past that point is a mapping problem, and `numpy.interp` does most of the work as a piecewise-linear lookup.

**Position.** MIDI pitches 21 through 108 are the 88 keys of a full piano, A0 to C8. Those map linearly onto LED indices, then get clamped a few pixels in from each end so the diffusion spread around a note can never index past the array.

**Color.** Pitch maps to a rainbow across the keyboard. Instead of converting through HSV, each channel gets its own breakpoint list sampled at seven pitch anchors:

```python
pitches = [21, 35.5, 50, 64.5, 79, 93.5, 108]
R = [255, 255, 255,   0,   0,  75, 148]
G = [  0, 127, 255, 255,   0,   0,   0]
B = [  0,   0,   0,   0, 255, 130, 211]
```

Interpolating the three channels independently gives red in the bass, moving through orange, yellow, and green in the middle register, into blue and violet at the top.

**Brightness.** Velocity, 0 to 127, maps to a brightness multiplier spanning 30 to 180 out of a possible 255. The ceiling is intentionally well below maximum. At arm's length behind a piano, full-brightness WS2812B is unpleasant to look at, and it washes out the color separation between neighboring notes.

### Diffusion

A single lit pixel reads as a hard dot, which does not look anything like sound. Each note is spread across seven LEDs instead, with brightness falling off from the center:

| Distance from center | Multiplier |
| --- | --- |
| 0 | 1.00 |
| 1 | 0.25 |
| 2 | 0.08 |
| 3 | 0.02 |

The falloff is steep on purpose. Gentler curves looked better on a single note but smeared adjacent pitches into each other, and chords turned into an unreadable blob.

### Sustain and decay

Releasing a key does not blank the LED. It spawns a thread that steps the color down to black in eight increments, with the total fade time drawn from both velocity and pedal state:

- Pedal up: 0.1 s at the softest velocity, rising to 0.25 s at the hardest
- Pedal down: 0.5 s to 1.1 s across the same range

This is the detail that makes the display feel attached to the instrument rather than merely triggered by it. Pedaled passages leave color hanging in the air after the hands have moved on, and staccato playing snaps off cleanly.

### The render loop

The first working version had every MIDI handler and every fade thread call `update_strip()` directly. Holding a chord under the pedal meant a dozen threads contending for the SPI bus at once. The result was visible flicker and input latency that got worse the more notes were sounding.

The fix was to separate state from output. All note and fade logic now writes only into a shared `frame_buffer` list. One dedicated thread walks that buffer and performs a single SPI transfer at roughly 30 fps:

```python
def renderLoop():
    while True:
        for i, (R, G, B) in enumerate(frame_buffer):
            strip.set_led_color(i, R, G, B)
        strip.update_strip()
        time.sleep(0.033)
```

SPI traffic is now constant regardless of how many notes are held, and the flicker is gone. Of everything in this project, this is the change that made it feel finished.

### Cancelling stale fades

Replaying a note while its previous fade was still running produced a visible stutter. The old thread kept writing progressively dimmer values on top of the new, bright note.

Each fade now registers a `threading.Event` in an `active_fades` dictionary keyed by note number. A fresh `note_on` for that pitch sets the event, and the fade thread checks it at every step and returns immediately when it is set. Repeated notes, trills, and tremolos stay clean.

### Mode selection without a screen

The Pi runs headless, so changing themes had to work without SSH. `BootScript.py` watches the button on GPIO 17 and counts presses inside a six-second window, then launches the matching script with `subprocess.Popen` and terminates whichever one was already running.

One press selects the default rainbow, two selects Birds, three selects Seb, four selects Le Festin. Anything else falls through to the default.

Debouncing is handled by `gpiozero`'s `bounce_time=0.3`. Earlier versions counted a single press as three or four, which made the whole scheme useless until it was fixed.

## Themes

Each theme is the render loop with a different `ledColor` mapping. They were built for specific pieces:

| Script | Piece | Palette |
| --- | --- | --- |
| `RenderLoop2.py` | default | full rainbow across the keyboard |
| `Birds.py` | Birds of a Feather | dark navy in the bass to teal in the treble |
| `Seb.py` | Mia and Sebastian's Theme | a single deep purple across the whole range |
| `LeFestin.py` | Le Festin | split at middle C, deep red below and warm gold above |

`LeFestin.py` is the only one that abandons interpolation. It hard-switches at pitch 60 so the left and right hands read as visually separate voices.

## Repository contents

| File | Purpose |
| --- | --- |
| `RenderLoop2.py` | Current default. Frame buffer, render thread, cancellable fades |
| `RenderLoop.py` | Same architecture with an extra delayed fade-to-black stage |
| `Birds.py`, `Seb.py`, `LeFestin.py` | Themed variants of the render loop |
| `BootScript.py` | Button listener and process launcher |
| `LedTest.py` | Hardware smoke test. Fills the strip white and holds |
| `FindPiano.py` | BLE diagnostic from the abandoned Bluetooth MIDI approach. Lists every advertising device with its name, RSSI, and service UUIDs |
| `Main.py` | First working version. Direct SPI writes, no frame buffer. Kept as reference |
| `BackOnly.py`, `BackOnly2.py` | Pre-frame-buffer iterations, superseded by the render loop versions |
| `Defuse.py` | Experimental two-strip build. Adds a second run driven by a rolling average of recent note colors |
| `Mood.py` | Abandoned experiment tracking tempo and velocity history. Does not currently run |

`Defuse.py` is the most interesting of the unfinished work. It keeps the last fifteen note colors, averages them, and crossfades a second LED run to that average over five steps. The idea was an ambient layer reflecting the overall harmonic color of a passage rather than individual notes, clearing itself after six seconds of silence.

## Setup

Enable SPI:

```bash
sudo raspi-config   # Interface Options > SPI > Enable
```

Raise the spidev transfer buffer. The default is 4096 bytes. `pi5neo` encodes each WS2812B data bit as one SPI byte, so 180 pixels need 180 × 24 = 4320 bytes in a single transfer. Past the default limit the write fails and the strip simply does not update:

```bash
sudo sh -c 'echo 32768 > /sys/module/spidev/parameters/bufsiz'
```

To make that survive a reboot, append `spidev.bufsiz=32768` to `/boot/firmware/cmdline.txt`.

Install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install mido python-rtmidi numpy pi5neo gpiozero
```

Connect the FP-10 over USB, then run a theme directly:

```bash
sudo .venv/bin/python3 RenderLoop2.py
```

`sudo` is required for access to `/dev/spidev0.0`.

On the assembled unit, `BootScript.py` is registered to start at boot so the display comes up on power alone and the button takes over from there.

## Engineering notes

Two rewrites account for most of the work in this repository.

The first was the MIDI transport. The FP-10 advertises Bluetooth MIDI, so the original build used `adafruit_ble_midi` to scan for the piano and pair with it. It never connected. `FindPiano.py` was written purely to dump every advertising BLE device with its name, RSSI, and service UUIDs so I could confirm whether the piano was appearing at all. It was not, at least not in a form that scanner could pair with. Roland's Bluetooth MIDI is built around their own app and the BLE MIDI stacks on iOS, Android, and Windows, and getting a Raspberry Pi to speak it would have meant adding a third-party Bluetooth MIDI adapter to a project that already had a working wired path available.

So the transport became USB MIDI through `mido` and `python-rtmidi`. This is the better engineering answer regardless of whether Bluetooth could have been made to work. The piano and the Pi both sit inside the same piece of furniture, a cable between them costs nothing, and it removes pairing, radio interference, and battery state from a system that has to come up unattended every time it is powered on.

The second was the LED driver. Nearly every WS2812B guide for the Pi uses `rpi_ws281x`, which generates the strip's timing by driving the PWM, PCM, and DMA peripherals directly. The Pi 5 moved GPIO behind the RP1 I/O controller, so that approach does not work at all, and a fair amount of time went into debugging wiring and power before it became clear the library itself was the problem. `pi5neo` takes a different route, encoding the WS2812B waveform as an SPI bit stream clocked out of MOSI at 800 kHz. Discovering that, and then running straight into the 4096-byte spidev buffer ceiling, accounted for a large share of the project's total debugging time.

Everything else was tuning by eye. The diffusion falloff, the brightness ceiling, the fade durations, and each theme's palette were set by playing something, watching the strip, and adjusting. The commit history is an accurate record of that process, including the attempts that did not survive.

## Technical stack

**Language:** Python 3

**Libraries:** `mido` and `python-rtmidi` for MIDI input, `pi5neo` for WS2812B over SPI, NumPy for piecewise-linear mapping, `gpiozero` for debounced button input, plus `threading` and `subprocess` from the standard library

**Hardware:** Raspberry Pi 5, 180 WS2812B addressable LEDs, Roland FP-10, dedicated 5 V 20 A supply, momentary switch

**Interfaces and protocols:** MIDI 1.0 over USB, SPI, GPIO

**Concepts applied:** real-time event handling, thread synchronization and cancellation, double buffering, signal interpolation, hardware debouncing, headless embedded deployment

**Tools:** Raspberry Pi OS, git, SSH for headless development, soldering iron

## Known limitations

- No level shifter on the data line. It works at this strip length but is out of specification and would not scale to a longer run.
- Each theme is a near-copy of the full render loop. The correct structure is one engine with a swappable palette, and this duplication is the first thing to refactor.
- `Mood.py` and `Defuse.py` are unfinished and left in place as a record of what was tried. `Mood.py` has a syntax error and will not start.
- The MIDI port lookup matches on the literal string "Roland" and raises if the piano is not connected when the script launches.
- Changing themes requires waiting out the full six-second counting window before anything happens.
