#!/usr/bin/env python3
import argparse
import json
import readline
import select
import shutil
import subprocess
import sys
import threading
import time

import numpy as np
import sounddevice as sd

SAMPLERATE = 44100
CHANNELS = 2
BLOCKSIZE = 1024


def bar_return(reached, toreach, length):
    filled = int((reached / toreach) * length)
    unfilled = length - filled
    bar = "[" + "=" * filled + "-" * unfilled + "]"
    return bar


def activity_watcher():
    global mouse_rate, key_rate

    proc = subprocess.Popen(
        ["libinput", "debug-events"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    key_events = []
    mouse_events = []
    smoothed_key_rate = 0
    smoothed_mouse_rate = 0
    alpha = 0.01

    window_size = 2.0
    output_interval = 1.0 / 30.0
    last_output_update = time.time()

    while True:
        timeout = max(0.001, output_interval - (time.time() - last_output_update))
        ready, _, _ = select.select([proc.stdout], [], [], timeout)

        if ready:
            line = proc.stdout.readline()
            if not line:
                break
            elif any(
                x in line
                for x in ["POINTER_MOTION", "POINTER_SCROLL_WHEEL", "POINTER_BUTTON"]
            ):
                mouse_events.append(time.time())
            elif "KEYBOARD_KEY" in line:
                key_events.append(time.time())

        now = time.time()

        if now - last_output_update >= output_interval:
            cutoff_time = now - window_size

            mouse_events = [t for t in mouse_events if t > cutoff_time]
            if len(mouse_events) > 1:
                time_span = now - mouse_events[0]
                instant_mouse = len(mouse_events) / min(time_span, window_size)
            else:
                instant_mouse = 0
            smoothed_mouse_rate = (
                alpha * instant_mouse + (1 - alpha) * smoothed_mouse_rate
            )

            key_events = [t for t in key_events if t > cutoff_time]
            if len(key_events) > 1:
                time_span = now - key_events[0]
                instant_key = len(key_events) / min(time_span, window_size)
            else:
                instant_key = 0
            smoothed_key_rate = alpha * instant_key + (1 - alpha) * smoothed_key_rate

            mouse_rate = smoothed_mouse_rate
            key_rate = smoothed_key_rate

            last_output_update = now


def callback(outdata, frames, time_info, status):
    global sound_alpha, prev, key_rate, mouse_rate, base_sound, level, gain
    global mouse_sensitivity, keyboard_sensitivity, key_rate_affects, mouse_rate_affects

    target_alpha = base_sound

    if key_rate_affects:
        target_alpha += key_rate / (800 / keyboard_sensitivity)

    if mouse_rate_affects:
        target_alpha += mouse_rate / (8000 / mouse_sensitivity)

    sound_alpha = 0.9 * sound_alpha + 0.1 * target_alpha

    noise = np.random.randn(frames, CHANNELS) * 0.2
    out = np.empty_like(noise)

    for i in range(frames):
        prev += sound_alpha * (noise[i] - prev)
        out[i] = prev

    outdata[:] = out * gain
    level = float(np.sqrt(np.mean(out**2)))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Quarks - simple cli white noise generator depended on user actions. "
        )
    )

    parser.add_argument("-m", "--mouse-affects", required=False, action="store_true")

    parser.add_argument("-k", "--keyboard-affects", required=False, action="store_true")

    parser.add_argument(
        "-b",
        "--base-volume",
        help="0-200 is safe, only int numbers (1, not 1.5), 10 is recommended",
        required=False,
    )

    parser.add_argument(
        "-ms",
        "--mouse-sensitivity",
        help="0-200 is safe, only int numbers (1, not 1.5), 10 is recommended",
        required=False,
    )
    parser.add_argument(
        "-ks",
        "--keyboard-sensitivity",
        help="0-200 is safe, only int numbers (1, not 1.5), 10 is recommended",
        required=False,
    )

    args = parser.parse_args()

    try:
        global \
            gain, \
            level, \
            prev, \
            key_rate_affects, \
            mouse_rate_affects, \
            mouse_rate, \
            key_rate, \
            sound_alpha, \
            base_sound, \
            mouse_sensitivity, \
            keyboard_sensitivity

        prev = np.zeros(CHANNELS)
        gain = 1
        level = 0.01
        key_rate_affects = True
        mouse_rate_affects = True
        mouse_rate = 0.0
        key_rate = 0.0
        sound_alpha = 0
        base_sound = 0.02
        mouse_sensitivity = 3
        keyboard_sensitivity = 3

        threading.Thread(target=activity_watcher, daemon=True).start()

        if not any(vars(args).values()):  # checks if any agrument got any value
            print("Missing arguments. Falllback to defaults.")
        else:
            try:
                if args.base_volume is not None:
                    base_sound = int(args.base_volume) / 2000
            except AttributeError:
                pass
            try:
                if args.mouse_sensitivity is not None:
                    mouse_sensitivity = int(args.mouse_sensitivity) / 20
            except AttributeError:
                pass

            try:
                if args.keyboard_sensitivity is not None:
                    keyboard_sensitivity = int(args.keyboard_sensitivity) / 20
            except AttributeError:
                pass

            if args.mouse_affects:
                mouse_rate_affects = args.mouse_affects
            else:
                mouse_rate_affects = False

            if args.keyboard_affects:
                key_rate_affects = args.keyboard_affects
            else:
                key_rate_affects = False

        with sd.OutputStream(
            samplerate=SAMPLERATE,
            blocksize=BLOCKSIZE,
            channels=CHANNELS,
            callback=callback,
        ):
            print("", end="\n\n")
            while True:
                sys.stdout.write(
                    " | "
                    + "Mouse activity: "
                    + str(round(mouse_rate / 14, 1))
                    + "    | \n"
                    + " | "
                    + "Keyboard activity: "
                    + str(round(key_rate / 7, 1))
                    + " | \n"
                    + " | "
                    + str(bar_return(level, 0.08, 20))
                    + " | "
                )
                sys.stdout.flush()
                time.sleep(0.1)
                sys.stdout.write("\033[2K\033[A\033[2K\033[A\033[2K\r")

    except KeyboardInterrupt:
        print("\n\nExited quark-sounds.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()



