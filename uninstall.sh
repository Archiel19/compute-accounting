#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

WRAPPER_NAME="sbatch_wrapper.py"
INSTALL_DIR="$HOME/.sbatch-wrapper"
TARGET_PATH="$INSTALL_DIR/$WRAPPER_NAME"

echo "=== Sbatch Wrapper Uninstaller ==="

# Remove install directory and wrapper script
if [ -d "$INSTALL_DIR" ]; then
    echo "[INFO] Removing wrapper at $TARGET_PATH..."
    rm -r "$INSTALL_DIR"
    echo "[SUCCESS] Removed wrapper at $TARGET_PATH"
else
    echo "[WARNING] No wrapper found at $TARGET_PATH"
fi

# Disable wrapper and remove function from profile
unset sbatch
CONFIG_FILE="$HOME/.profile"
if grep -q "Sbatch Wrapper" "$CONFIG_FILE"; then
    sed -i.bak "/# >>> Sbatch Wrapper >>>/,/# <<< Sbatch Wrapper <<</d" "$CONFIG_FILE"
    echo "[SUCCESS] Removed alias from $CONFIG_FILE"
fi

echo "================================="
echo "[DONE] Uninstallation complete!"
echo "Run 'source \$HOME/.profile' or log in again for changes to take place"