#!/usr/bin/env bash
set -e

echo "[*] Installing/updating quark-sounds..."

rm -rf "$HOME/.local/share/quarks" "$HOME/.local/bin/quarks"

command -v python3 >/dev/null || {
  echo "python3 not found"
  exit 1
}

command -v libinput >/dev/null || {
  echo "libinput not found (libinput-tools)"
  exit 1
}

INSTALL_DIR="$HOME/.local/share/quarks"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

echo "[*] Downloading quark-sounds..."
curl -fsSL https://raw.githubusercontent.com/quadakr/quarks/main/quark-sounds.py \
  -o "$INSTALL_DIR/quark-sounds.py"

echo "[*] Creating venv..."
python3 -m venv "$INSTALL_DIR/venv"

echo "[*] Installing dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install sounddevice numpy

echo "[*] Creating launcher..."
cat > "$BIN_DIR/quarks" << EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/venv/bin/python" \
     "$INSTALL_DIR/quark-sounds.py" "\$@"
EOF

chmod +x "$BIN_DIR/quarks"

echo "[✓] Installed!"
echo "Run with: quarks"
