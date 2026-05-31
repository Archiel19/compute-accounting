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

# >>> Slurm Wrapper Custom Alias >>>
alias sbatch='python $TARGET_PATH /usr/bin/sbatch'
# <<< Slurm Wrapper Custom Alias <<<
EOF
)

# Determine the active/default shell and ensure its RC file exists
# We check $SHELL first, fallback to the parent shell process name if empty
CURRENT_SHELL=$(basename "$SHELL")

if [[ "$CURRENT_SHELL" == "zsh" ]]; then
    PRIMARY_RC="$HOME/.zshrc"
    echo "[INFO] Detected Zsh as your default shell."
else
    PRIMARY_RC="$HOME/.bashrc"
    echo "[INFO] Fallback to Bash as your default shell."
fi

if [ ! -f "$PRIMARY_RC" ]; then
    echo "[INFO] $PRIMARY_RC does not exist. Creating it now..."
    touch "$PRIMARY_RC"
fi

# Inject alias into primary RC file
if grep -q "Slurm Wrapper Custom Alias" "$PRIMARY_RC"; then
    echo "[INFO] Alias already exists in $PRIMARY_RC. Skipping injection."
else
    echo "$ALIAS_BLOCK" >> "$PRIMARY_RC"
    echo "[SUCCESS] Added alias to $PRIMARY_RC"
fi

# Passive injection for the alternate shell *only if it already exists*
ALTERNATE_RC="$HOME/.bashrc"
[[ "$PRIMARY_RC" == "$HOME/.bashrc" ]] && ALTERNATE_RC="$HOME/.zshrc"

ALTERNATE_UPDATED=false
if [ -f "$ALTERNATE_RC" ]; then
    if ! grep -q "Slurm Wrapper Custom Alias" "$ALTERNATE_RC"; then
        echo "$ALIAS_BLOCK" >> "$ALTERNATE_RC"
        echo "[SUCCESS] Secondary mirror added to existing $ALTERNATE_RC"
        ALTERNATE_UPDATED=true
    fi
fi


UPDATE_CMD="source $PRIMARY_RC"
[[ "$ALTERNATE_UPDATED" == true ]] && UPDATE_CMD="$UPDATE_CMD; source $ALTERNATE_RC"
echo "================================="
echo "[DONE] Installation complete!"
echo "Please restart your terminal or run: $UPDATE_CMD"