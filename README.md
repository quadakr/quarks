# quarks

Simple **Linux Only** CLI tool for real-time adaptive [white] noise generation.
Volume and frequency dynamically respond to keyboard and mouse activity.

## Status
Early development. Behavior may change.

## Features
- Real-time white noise synthesis and output
- Activity-responsive frequency (typing/mouse speed increases pitch)
- Uses libinput for hardware event monitoring
- Smooth audio transitions (low-pass filtering)

## Requirements
- Linux with libinput
- Python 3
- User must be in `input` group (`sudo usermod -a -G input $USER`)
- Python packages: numpy, sounddevice

## Usage
```bash
python quark-sounds.py
