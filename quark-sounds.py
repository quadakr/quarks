import json
import os
import readline
import select
import subprocess
import sys
import threading
import time

import numpy as np
import sounddevice as sd

SAMPLERATE = 44100
CHANNELS = 2
BLOCKSIZE = 1024


def cpu_temp_watcher():
    while True:
        global cpu_temp
        time.sleep(0.04)
        out = subprocess.check_output(["sensors", "-j"])
        data = json.loads(out)
        for chip in data.values():
            if "Tctl" in chip:
                cpu_temp = float(chip["Tctl"]["temp1_input"])


def keyboard_activity_watcher():
    global key_rate

    proc = subprocess.Popen(
        ["libinput", "debug-events"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    key_events = []
    smoothed_rate = 0
    alpha = 0.02  # smoothing

    window_size = 2.0
    output_interval = 1.0 / 60.0

    last_output_update = time.time()

    while True:
        timeout = max(0.001, output_interval - (time.time() - last_output_update))
        ready, _, _ = select.select([proc.stdout], [], [], timeout)
        if ready:
            line = proc.stdout.readline()
            if not line:
                break
            if "KEYBOARD_KEY" in line and "pressed" in line:
                key_events.append(time.time())

        now = time.time()

        if now - last_output_update >= output_interval:
            cutoff_time = now - window_size
            key_events = [t for t in key_events if t > cutoff_time]
            if len(key_events) > 1:
                if key_events:
                    time_span = (
                        now - key_events[0] if len(key_events) > 1 else window_size
                    )
                    instant_rate = len(key_events) / min(time_span, window_size)
                else:
                    instant_rate = 0
            else:
                instant_rate = 0
            smoothed_rate = alpha * instant_rate + (1 - alpha) * smoothed_rate
            key_rate = smoothed_rate
            last_output_update = now


def callback(outdata, frames, time_info, status):
    global sound_alpha, target_alpha, prev, cpu_temp, key_rate

    init_sounds_alpha = sound_alpha * 15

    if key_rate_affects:
        sound_alpha = ((sound_alpha) + ((key_rate + 10) / 2000)) / 8

    if cpu_affects:
        sound_alpha = sound_alpha + (cpu_temp + 1) / 20000

    noise = np.random.randn(frames, CHANNELS) * 0.2
    out = np.empty_like(noise)

    for i in range(frames):
        # prev += (init_sounds_alpha * 50 + sound_alpha / 100) * (noise[i] - prev)
        prev += (init_sounds_alpha * 1 + sound_alpha / 5) * (noise[i] - prev)

        out[i] = prev

    outdata[:] = out


def main():
    try:
        continue_program = input(
            f"Disclaimer: This program is n early developement stage, theoretically, it can hurt your audio device, or ears. Sure want to continue?[y/n]: "
        )

        if continue_program != "y":
            print("\n\nExited quark-sounds.\n")
            sys.exit(0)

        global prev
        prev = np.zeros(CHANNELS)
        global cpu_affects
        cpu_affects = False
        global cpu_temp
        cpu_temp = 40.0
        global key_rate_affects
        key_rate_affects = True
        global key_rate
        key_rate = 0.0
        global sound_alpha
        sound_alpha = 0

        threading.Thread(target=keyboard_activity_watcher, daemon=True).start()

        threading.Thread(target=cpu_temp_watcher, daemon=True).start()

        with sd.OutputStream(
            samplerate=SAMPLERATE,
            blocksize=BLOCKSIZE,
            channels=CHANNELS,
            callback=callback,
        ):
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nExited quark-sounds.\n")


if __name__ == "__main__":
    main()
