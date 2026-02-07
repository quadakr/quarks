# quarks

Simple **Linux Only** CLI tool for real-time adaptive [white] noise generation.
Volume [and frequency] dynamically respond to keyboard and mouse activity.

---

## Status
In development. Behavior may change.

---

## Features
- Real-time white noise synthesis and output
- Activity-responsive frequency (typing/mouse speed increases pitch)
- Uses libinput for hardware event monitoring
- Smooth audio transitions (low-pass filtering)

---

## Requirements
- Linux with libinput
- Python 3
- PortAudio (Debian/Ubuntu: `sudo apt install libportaudio2`)
- User must be in `input` group (`sudo usermod -a -G input $USER`)
- Python packages: numpy, sounddevice (automatically installing with install.sh)

---

## Installing/Updating

Download install.sh, then:

```bash
cd ~/Downloads/ ; chmod +x install.sh ; sudo ./install.sh
```

Or just with one command:
```bash
curl -fsSL https://raw.githubusercontent.com/quadakr/quarks/main/install.sh | bash
```

**And uninstalling if you want:**
```bash
rm -rf ~/.local/share/quarks ~/.local/bin/quarks
```

---

## Usage
```bash
quarks
```
## Advanced usage
```bash
quarks -b 40 -m -k -ms 50 -ks 50 # base sound volume 40, mouse affects, keyboard affects, mouse sensitivity 50, keyboard sensitivity 50
```

<!-- <p> No one will read this line >:3 </p> -->
