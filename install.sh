#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

TARGET_DIR="$HOME/.local/bin"
TARGET_PATH="$TARGET_DIR/sbatch"
ENV_SCRIPT="$TARGET_DIR/env"

echo "=== Sbatch Wrapper Installer ==="

# Create directory if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    echo "[INFO] Creating $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
fi

# Download wrapper script
echo "[INFO] Downloading wrapper..."
curl -sSL "https://raw.githubusercontent.com/Archiel19/compute-accounting/main/sbatch_wrapper.py" -o "$TARGET_PATH"
chmod +x "$TARGET_PATH"
echo "[INFO] Saved wrapper to $TARGET_PATH"

# Create env script if it doesn't exist
if [ ! -f "$ENV_SCRIPT" ]; then
    echo "[INFO] Creating $ENV_SCRIPT..."
    cat > "$ENV_SCRIPT" << 'EOF'
#!/bin/sh
# add binaries to PATH if they aren't added yet
# affix colons on either side of $PATH to simplify matching
case ":${PATH}:" in
    *:"$HOME/.local/bin":*)
        ;;
    *)
        # Prepending path in case a system-installed binary needs to be overridden
        export PATH="$HOME/.local/bin:$PATH"
        ;;
esac
EOF
    chmod +x "$ENV_SCRIPT"
    echo "[INFO] Saved env script to $ENV_SCRIPT"
else
    echo "[INFO] $ENV_SCRIPT already exists, skipping creation"
fi

# Update shell configuration files
echo "[INFO] Updating shell configuration files..."

# Check if ~/.local/bin is already in PATH
if echo ":${PATH}:" | grep -q ":$HOME/.local/bin:"; then
    echo "[INFO] $HOME/.local/bin is already in PATH"
else
    # Function to add env script sourcing to config files
    # Arguments: config_file, force (optional, default: false)
    # If force=true, creates file if it doesn't exist; if false, only modifies existing files
    add_to_config() {
        local config_file="$1"
        local force="${2:-false}"
        local source_line=". \"\$HOME/.local/bin/env\""
        
        if [ "$force" = true ] || [ -f "$config_file" ]; then
            # Check if already sourced to avoid duplicates
            if [ -f "$config_file" ] && grep -q "\.local/bin/env" "$config_file"; then
                echo "[INFO] $config_file already sources the env script"
            else
                echo "[INFO] Adding env script to $config_file"
                echo "" >> "$config_file"
                echo "$source_line" >> "$config_file"
            fi
        fi
    }
    
    # Update shell config files based on available shells
    if command -v bash >/dev/null 2>&1; then
        add_to_config "$HOME/.bashrc" true
        add_to_config "$HOME/.bash_profile"
    fi
    
    if command -v zsh >/dev/null 2>&1; then
        add_to_config "$HOME/.zshenv" true
    fi
    
    # Always create/update .profile (works for POSIX shells)
    add_to_config "$HOME/.profile" true
fi

echo "================================="
echo "[DONE] Installation complete!"
echo "[INFO] Run: . \"\$HOME/.local/bin/env\" to update your PATH in the current shell"