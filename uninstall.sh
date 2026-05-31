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


# Remove alias from primary RC file
ALIAS_BLOCK=$(cat <<EOF

# >>> Slurm Wrapper Custom Alias >>>
alias sbatch='python $TARGET_PATH /usr/bin/sbatch'
# <<< Slurm Wrapper Custom Alias <<<
EOF
)

# Remove alias from primary RC file
if grep -q "Slurm Wrapper Custom Alias" "$HOME/.bashrc"; then
    sed -i.bak "/# >>> Slurm Wrapper Custom Alias >>>/,/# <<< Slurm Wrapper Custom Alias <<</d" "$HOME/.bashrc"
    echo "[SUCCESS] Removed alias from $HOME/.bashrc"
    BASHRC_UPDATED=true
fi

if grep -q "Slurm Wrapper Custom Alias" "$HOME/.zshrc"; then
    sed -i.bak "/# >>> Slurm Wrapper Custom Alias >>>/,/# <<< Slurm Wrapper Custom Alias <<</d" "$HOME/.zshrc"
    echo "[SUCCESS] Removed alias from $HOME/.zshrc"
    ZSHRC_UPDATED=true
fi

UPDATE_CMD=""
[[ "$ZSHRC_UPDATED" == true ]] && UPDATE_CMD="source $HOME/.zshrc"
[[ "$BASHRC_UPDATED" == true ]] && UPDATE_CMD="$UPDATE_CMD; source $HOME/.bashrc"
UPDATE_CMD=$(echo "$UPDATE_CMD" | sed 's/^; //') # Remove leading semicolon if exists

echo "================================="
echo "[DONE] Uninstallation complete!"
[[ -n "$UPDATE_CMD" ]] && echo "Please run: $UPDATE_CMD"