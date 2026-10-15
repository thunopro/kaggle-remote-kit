#!/usr/bin/env bash
# Cài trên Linux / macOS. Dùng: ./install.sh [KAGGLE_API_TOKEN]   (token KGAT_...; không truyền thì được hỏi)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PIP="python3 -m pip install --user -q -U kaggle websocket-client"
$PIP 2>/dev/null || $PIP --break-system-packages
mkdir -p ~/.kaggle-remote ~/.local/kaggle-wrap ~/.kaggle
cp "$HERE/kr.py" ~/.kaggle-remote/ && cp "$HERE/wrap/kaggle" ~/.local/kaggle-wrap/ && chmod +x ~/.local/kaggle-wrap/kaggle
T="${1:-}"
if [ -z "$T" ] && [ ! -f ~/.kaggle/access_token ]; then read -rsp "Dán Kaggle API token (KGAT_...): " T; echo; fi
if [ -n "$T" ]; then printf '%s' "$T" > ~/.kaggle/access_token; chmod 700 ~/.kaggle; chmod 600 ~/.kaggle/access_token; fi
LINE='export PATH="$HOME/.local/kaggle-wrap:$PATH"'
for rc in ~/.bashrc ~/.zshrc; do [ -f "$rc" ] && ! grep -q kaggle-wrap "$rc" && echo "$LINE" >> "$rc"; done
[ -f ~/.config/fish/config.fish ] && ! grep -q kaggle-wrap ~/.config/fish/config.fish && echo 'fish_add_path -m ~/.local/kaggle-wrap' >> ~/.config/fish/config.fish
# dọn bản cũ (bash scripts v1.x)
for f in krun kjupyter kwatch kup kdown kls ktime kman kterm; do rm -f ~/.local/bin/$f; done
echo "✅ Xong. Mở terminal mới rồi gõ: kaggle man"
echo "💡 Tuỳ chọn: Gõ 'kaggle gdrive <link_folder>' để liên kết Google Drive lưu trữ vĩnh viễn (xem README.md)."
