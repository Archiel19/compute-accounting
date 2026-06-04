#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

WRAPPER_NAME="sbatch_wrapper.py"
INSTALL_DIR="$HOME/.slurm-wrapper"
TARGET_PATH="$INSTALL_DIR/$WRAPPER_NAME"

echo "=== Slurm Wrapper Installer ==="


# Download wrapper script
mkdir -p "$INSTALL_DIR"
echo "[INFO] Downloading wrapper to $INSTALL_DIR..."
curl -sSL "https://raw.githubusercontent.com/Archiel19/compute-accounting/main/sbatch_wrapper.py" -o "$TARGET_PATH"
chmod +x "$TARGET_PATH"
echo "[INFO] Saved wrapper to $TARGET_PATH"


# Define shell alias
ALIAS_BLOCK=$(cat <<EOF

# >>> Slurm Wrapper >>>
sbatch() {
    python $TARGET_PATH /usr/bin/sbatch
}
# <<< Slurm Wrapper <<<
EOF
)

CONFIG_FILE="$HOME/.profile"

# Inject alias into profile
if grep -q "Slurm Wrapper" "$CONFIG_FILE"; then
    echo "[INFO] Alias already exists in $CONFIG_FILE. Skipping injection."
else
    echo "$ALIAS_BLOCK" >> "$CONFIG_FILE"
    echo "[SUCCESS] Added alias to $CONFIG_FILE"
fi

echo "================================="
echo "[DONE] Installation complete!"