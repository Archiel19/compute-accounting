#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

WRAPPER_NAME="sbatch_wrapper.py"
INSTALL_DIR="$HOME/.slurm-wrapper"
TARGET_PATH="$INSTALL_DIR/$WRAPPER_NAME"

echo "=== Slurm Wrapper Uninstaller ==="

# Remove install directory and wrapper script
if [ -d "$INSTALL_DIR" ]; then
    echo "[INFO] Removing wrapper at $TARGET_PATH..."
    rm -r "$INSTALL_DIR"
    echo "[SUCCESS] Removed wrapper at $TARGET_PATH"
else
    echo "[WARNING] No wrapper found at $TARGET_PATH"
fi

# Remove alias from profile
CONFIG_FILE="$HOME/.profile"
if grep -q "Slurm Wrapper" "$CONFIG_FILE"; then
    sed -i.bak "/# >>> Slurm Wrapper >>>/,/# <<< Slurm Wrapper <<</d" "$CONFIG_FILE"
    echo "[SUCCESS] Removed alias from $CONFIG_FILE"
fi

echo "================================="
echo "[DONE] Uninstallation complete!"