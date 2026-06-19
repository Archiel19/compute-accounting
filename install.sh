#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

TARGET_PATH="$HOME/.local/bin/sbatch"

echo "=== Sbatch Wrapper Installer ==="

# Download wrapper script
echo "[INFO] Downloading wrapper..."
curl -sSL "https://raw.githubusercontent.com/Archiel19/compute-accounting/main/sbatch_wrapper.py" -o "$TARGET_PATH"
chmod +x "$TARGET_PATH"
echo "[INFO] Saved wrapper to $TARGET_PATH"

echo "================================="
echo "[DONE] Installation complete!"