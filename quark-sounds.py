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


def cpu_temp_watcher():
    while True:
        global cpu_temp
        time.sleep(0.04)
        out = subprocess.check_output(["sensors", "-j"])
        data = json.loads(out)
        for chip in data.values():
            if "Tctl" in chip:
                cpu_temp = float(chip["Tctl"]["temp1_input"])


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
    global \
        sound_alpha, \
        target_alpha, \
        prev, \
        cpu_temp, \
        key_rate, \
        sensitivity, \
        base_sound, \
        level, \
        gain

    init_sounds_alpha = sound_alpha * 15

    if key_rate_affects:
        sound_alpha = (
            (sound_alpha) + base_sound + ((key_rate + 0) / (800 / sensitivity))
        ) / 8

    if mouse_rate_affects:
        sound_alpha = (
            (sound_alpha * 10) + base_sound + ((mouse_rate + 0) / (8000 / sensitivity))
        ) / 8

    if cpu_affects:
        sound_alpha = sound_alpha + (cpu_temp + 1) / 20000

    noise = np.random.randn(frames, CHANNELS) * 0.2
    out = np.empty_like(noise)

    for i in range(frames):
        prev += (init_sounds_alpha * 1 + sound_alpha / 5) * (noise[i] - prev)

        out[i] = prev

    outdata[:] = out * gain

    level = float(np.sqrt(np.mean(out**2)))


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Quarks - simple cli white noise generator depended on user actions. "
        )
    )

    parser.add_argument(
        "-m",
        "--mouse-affects",
        required=False,
    )

    parser.add_argument(
        "-k",
        "--keyboard-affects",
        required=False,
    )

    parser.add_argument(
        "-c",
        "--cmd",
        help="Command to execute when notify. ",
    )

    try:
        global gain
        gain = 1
        global level
        level = 0.01
        global prev
        prev = np.zeros(CHANNELS)
        global cpu_affects
        cpu_affects = False
        global cpu_temp
        cpu_temp = 40.0
        global key_rate_affects
        key_rate_affects = True
        global mouse_rate_affects
        mouse_rate_affects = True
        global mouse_rate
        mouse_rate = 0.0
        global key_rate
        key_rate = 0.0
        global sound_alpha
        sound_alpha = 0

        continue_program = input(
            f"Disclaimer: This program is still in developement, theoretically, if something is wrong with libinput, it can show unexpected behavior. Sure want to continue?[y/n]: "
        )

        if continue_program != "y":
            print("\n\nExited quark-sounds.\n")
            sys.exit(0)

        global sensitivity
        sensitivity = 6

        try:
            sensitivity_assing = int(
                input(f"Sensitivity to user actions (0 - 100, 10 recommended): ")
            )
        except ValueError:
            print("Wtire an int number please. (ex: 12, not 12.5)")
            sys.exit(1)

        if sensitivity_assing > 100 or sensitivity_assing < 0:
            print("\n\nThis configuration is unsave.\n")
            sys.exit(1)

        sensitivity = sensitivity_assing / 20

        global base_sound
        base_sound = 6

        try:
            base_sound_assing = int(
                input(f"Base sound loudness (0 - 100, 20 recommended): ")
            )
        except ValueError:
            print("Wtire an int number please. (ex: 12, not 12.5)")
            sys.exit(1)

        if base_sound_assing > 100 or base_sound_assing < 0:
            print("\n\nThis configuration is unsave.\n")
            sys.exit(1)

        base_sound = base_sound_assing / 20000

        assing_mouse = input(f"Mouse will affect noise?[y/n]: ")

        if assing_mouse == "y":
            mouse_rate_affects = True
        else:
            mouse_rate_affects = False

        assing_keyboard = input(f"Keyboard will affect noise?[y/n]: ")

        if assing_keyboard == "y":
            key_rate_affects = True
        else:
            key_rate_affects = False

        threading.Thread(target=activity_watcher, daemon=True).start()

        # threading.Thread(target=keyboard_activity_watcher, daemon=True).start()

        # threading.Thread(target=mouse_activity_watcher, daemon=True).start()

        # threading.Thread(target=cpu_temp_watcher, daemon=True).start()

        with sd.OutputStream(
            samplerate=SAMPLERATE,
            blocksize=BLOCKSIZE,
            channels=CHANNELS,
            callback=callback,
        ):
            print("", end="\n\n")
            compacted = False
            while True:
                term_width = shutil.get_terminal_size().columns
                if term_width < 80:
                    if not compacted:
                        sys.stdout.write("\033[2K\r")
                    else:
                        sys.stdout.write("\033[2K\033[A\033[2K\033[A\033[2K\r")

                    compacted = True

                    # sys.stdout.write("\033[2K\r")
                    sys.stdout.write(
                        " | "
                        + "Mouse activity: "
                        + str(round(mouse_rate, 1))
                        + "    | \n"
                        + " | "
                        + "Keyboard activity: "
                        + str(round(key_rate, 1))
                        + " | \n"
                        + " | "
                        + str(bar_return(level, 0.08, 20))
                        + " | "
                    )
                else:
                    if compacted:
                        compacted = False
                        sys.stdout.write("\033[2K\033[A\033[2K\033[A\033[2K\r")
                    else:
                        sys.stdout.write("\033[2K\r")
                    sys.stdout.write(
                        " | "
                        + "Mouse activity: "
                        + str(round(mouse_rate, 1))
                        + " | "
                        + "Keyboard activity: "
                        + str(round(key_rate, 1))
                        + " | "
                        + str(bar_return(level, 0.08, 20))
                        + " | "
                    )

                sys.stdout.flush()
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nExited quark-sounds.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

