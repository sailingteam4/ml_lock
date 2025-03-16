#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}ML Lock Installer/Updater${NC}"

if ! command -v git &> /dev/null; then
    echo -e "${RED}Git is not installed. Please install git first.${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 is not installed. Please install Python3 first.${NC}"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Pip3 is not installed. Please install pip3 first.${NC}"
    exit 1
fi

install_dir="$HOME/.local/share/ml_lock"
source_dir="$install_dir/source"

if [ -d "$source_dir" ]; then
    echo -e "${BLUE}Existing installation found. Updating...${NC}"
    
    if [ -f "$HOME/.config/ml_lock/config.json" ]; then
        cp "$HOME/.config/ml_lock/config.json" "/tmp/ml_lock_config_backup.json"
    fi
    
    cd "$source_dir"
    
    if ! git diff-index --quiet HEAD --; then
        echo "Local changes detected, stashing them..."
        git stash
        local_changes=true
    fi
    
    git fetch
    current_hash=$(git rev-parse HEAD)
    remote_hash=$(git rev-parse @{u})
    
    if [ "$current_hash" != "$remote_hash" ]; then
        echo "Updates available. Downloading..."
        git pull
        
        if [ "$local_changes" = true ]; then
            echo "Restoring local changes..."
            git stash pop
            
            if git diff --name-only --diff-filter=U | grep -q .; then
                echo -e "${RED}Warning: Conflicts detected. Your local changes have been preserved in stash.${NC}"
                git reset --hard HEAD
                echo "You can find your local changes using 'cd $source_dir && git stash list'"
            fi
        fi
        
        echo -e "${GREEN}Updated to latest version${NC}"
    else
        echo -e "${GREEN}Already at latest version${NC}"
        if [ "$local_changes" = true ]; then
            git stash pop
        fi
    fi

    if [ -f "/tmp/ml_lock_config_backup.json" ]; then
        mv "/tmp/ml_lock_config_backup.json" "$HOME/.config/ml_lock/config.json"
    fi
else
    echo "Performing fresh installation..."
    mkdir -p "$install_dir"
    git clone https://github.com/sailingteam4/ml_lock.git "$source_dir"
fi

echo "Updating dependencies..."
pip3 install --user -r "$source_dir/requirements.txt" --upgrade

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config/ml_lock"
mkdir -p "$source_dir/img"

cat > "$HOME/.local/bin/ml_lock" << 'EOF'
#!/bin/bash
python3 "$HOME/.local/share/ml_lock/source/ml_lock.py" "$@"
EOF

chmod +x "$HOME/.local/bin/ml_lock"
chmod -R 755 "$install_dir"
chmod 700 "$HOME/.config/ml_lock"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
fi

echo -e "${GREEN}Installation/Update complete!${NC}"
echo "You can use ML Lock by running: ml_lock"
echo "To set/change password, run: ml_lock -p"
echo "NOTE: You may need to restart your terminal or run: source ~/.bashrc"
