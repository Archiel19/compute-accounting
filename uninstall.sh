#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

TARGET_PATH="$HOME/.local/bin/sbatch"

echo "=== Sbatch Wrapper Uninstaller ==="

# Remove install directory and wrapper script
if [ -f "$TARGET_PATH" ]; then
    echo "[INFO] Removing wrapper at $TARGET_PATH..."
    rm "$TARGET_PATH"
    echo "[SUCCESS] Removed wrapper at $TARGET_PATH"
else
    echo "[WARNING] No wrapper found at $TARGET_PATH"
fi

echo "================================="
echo "[DONE] Uninstallation complete!"