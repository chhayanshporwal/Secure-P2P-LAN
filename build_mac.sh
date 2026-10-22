#!/usr/bin/env bash
set -e

echo "========================================================"
echo " Secure P2P Client - macOS Standalone App Build"
echo "========================================================"
echo ""

if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "[2/3] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo ""
echo "[3/3] Building standalone macOS application..."
pyinstaller --onefile --windowed --noconfirm --paths src --name "SecureClient" main.py

echo ""
echo "========================================================"
echo "[SUCCESS] Build completed!"
echo "Your macOS application is ready at:"
echo " - dist/SecureClient.app (Double-clickable Mac App)"
echo " - dist/SecureClient (Executable binary)"
echo "========================================================"
