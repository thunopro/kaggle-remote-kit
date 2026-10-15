#!/usr/bin/env bash
# Cài bộ lệnh kaggle remote. Dùng: ./install.sh [KAGGLE_API_TOKEN]   (token dạng KGAT_...; hoặc nhập khi được hỏi)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
pip install --user --break-system-packages -U kaggle jupytext jupyterlab websocket-client >/dev/null 2>&1 || pip install --user -U kaggle jupytext jupyterlab websocket-client
mkdir -p ~/.local/bin ~/kaggle-work/.kjupyter ~/.kaggle
cp "$HERE"/bin/* ~/.local/bin/ && chmod +x ~/.local/bin/{krun,kjupyter,kwatch,kup,kdown,kls,ktime,kman,kterm}
cp "$HERE"/templates/server.tmpl.py ~/kaggle-work/.kjupyter/
T="${1:-}"
if [ -z "$T" ] && [ ! -f ~/.kaggle/access_token ]; then read -rsp "Dán Kaggle API token (KGAT_...): " T; echo; fi
if [ -n "$T" ]; then printf '%s' "$T" > ~/.kaggle/access_token; chmod 700 ~/.kaggle; chmod 600 ~/.kaggle/access_token; fi
mkdir -p ~/.local/kaggle-wrap && cp "$HERE"/wrap/kaggle ~/.local/kaggle-wrap/ && chmod +x ~/.local/kaggle-wrap/kaggle
grep -q kaggle-wrap ~/.bashrc || echo 'export PATH="$HOME/.local/kaggle-wrap:$PATH:$HOME/.local/bin"' >> ~/.bashrc
[ -f ~/.zshrc ] && ! grep -q kaggle-wrap ~/.zshrc && echo 'export PATH="$HOME/.local/kaggle-wrap:$PATH:$HOME/.local/bin"' >> ~/.zshrc
[ -f ~/.config/fish/config.fish ] && ! grep -q kaggle-wrap ~/.config/fish/config.fish && echo 'fish_add_path -m ~/.local/kaggle-wrap ~/.local/bin' >> ~/.config/fish/config.fish
echo "✅ Xong. Mở terminal mới rồi gõ: kaggle man"
