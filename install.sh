#!/usr/bin/env bash
# Cài bộ lệnh kaggle remote. Dùng: ./install.sh [KAGGLE_API_TOKEN]   (token dạng KGAT_...; hoặc nhập khi được hỏi)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
pip install --user --break-system-packages -U kaggle jupytext jupyterlab >/dev/null 2>&1 || pip install --user -U kaggle jupytext jupyterlab
mkdir -p ~/.local/bin ~/kaggle-work/.kjupyter ~/.kaggle
cp "$HERE"/bin/* ~/.local/bin/ && chmod +x ~/.local/bin/{krun,kjupyter,kwatch,kup,kdown,kls,ktime,kman}
cp "$HERE"/templates/server.tmpl.py ~/kaggle-work/.kjupyter/
T="${1:-}"
if [ -z "$T" ] && [ ! -f ~/.kaggle/access_token ]; then read -rsp "Dán Kaggle API token (KGAT_...): " T; echo; fi
if [ -n "$T" ]; then printf '%s' "$T" > ~/.kaggle/access_token; chmod 700 ~/.kaggle; chmod 600 ~/.kaggle/access_token; fi
grep -q '.local/bin' ~/.bashrc || echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
if ! grep -q '^kaggle()' ~/.bashrc; then
cat >> ~/.bashrc <<'B'
# kaggle on|off|status|url|time|up|ls|down|run|man = lệnh tự làm; còn lại chuyển cho Kaggle CLI thật (gõ: kaggle man)
kaggle() { case "$1" in
  on) shift; kjupyter "$@";; off|status) kjupyter "$1";;
  url) cat ~/kaggle-work/.kjupyter/last_url 2>/dev/null | tee >(xclip -selection clipboard 2>/dev/null); echo;;
  time) ktime;; up) shift; kup "$@";; ls) shift; kls "$@";; down) shift; kdown "$@";;
  run) shift; krun "$@";; man) kman;; *) command kaggle "$@";; esac; }
B
fi
echo "✅ Xong. Mở terminal mới rồi gõ: kaggle man"
