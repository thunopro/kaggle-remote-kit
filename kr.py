#!/usr/bin/env python3
"""Kaggle Remote Kit — chạy Jupyter / notebook trên GPU Kaggle từ máy local (Linux, macOS, Windows). Gõ: kaggle man"""
import os, sys, json, time, subprocess, shutil, tempfile, base64, zipfile, secrets, re, platform, urllib.request, urllib.parse
from pathlib import Path

IS_WIN = os.name == "nt"
STATE = Path.home() / ".kaggle-remote"
SLUG = "kaggle-remote-jupyter"
URL_FILE, TOPIC_FILE, PID_FILE, GDRIVE_ID_FILE = STATE / "last_url", STATE / "topic", STATE / "watcher.pid", STATE / "gdrive_id"

MAN = """\
╔════════════════ KAGGLE REMOTE – CÁC LỆNH ════════════════╗
 Phiên Jupyter trên GPU Kaggle (dùng với VS Code / Web Lab)
  kaggle on [--cpu] [--comp slug] [--data user/ds]   Bật Jupyter trên Kaggle, in link + copy vào clipboard
                      (--comp/--data gắn competition/dataset vào /kaggle/input, lặp lại được)
  kaggle off          Tắt phiên (tự động đồng bộ lên Drive trước khi dừng)
  kaggle status       Đang ON/OFF, link hiện tại
  kaggle url          In lại link (và copy lại)
  kaggle time         Quota GPU/TPU còn lại + thời gian phiên đã chạy

 Lưu trữ vĩnh viễn với Google Drive:
  kaggle gdrive [link|id|off]  Liên kết / xem trạng thái / huỷ Google Drive
  kaggle sync [up|down]        Đồng bộ ngay lập tức (up=lưu lên Drive, down=kéo về)
  - Thư mục /kaggle/working/drive/ tự động gắn với folder Google Drive của bạn
  - Tự động kéo dữ liệu về khi bật (kaggle on)
  - Tự động đẩy dữ liệu lên Drive mỗi 60 giây và khi tắt (kaggle off)

 File giữa máy bạn <-> Kaggle (cần kaggle on)
  kaggle up [-d thư_mục_đích] <file|dir>...  Upload (nhiều file/thư mục → nén zip, 1 lần, giải nén bên Kaggle)
  kaggle ls [thư_mục]          Xem file trên Kaggle
  kaggle down <file|dir> [đích=.]  Tải từ Kaggle về máy
  kaggle rm <đường_dẫn|glob>...  Xoá file/thư mục trên Kaggle (vd: kaggle rm '*.jpg' test)
  kaggle terminal              Terminal ngay trên Kaggle (ls, cd, unzip, nvidia-smi, pip... thoát: exit)

 Chạy cả notebook 1 lần (không tương tác)
  kaggle run <thư_mục> [--cpu] Push train.ipynb/train.py, đợi xong, tải output về <thư_mục>/output

 Lệnh Kaggle gốc vẫn dùng bình thường
  kaggle kernels|datasets|competitions|models ...
  kaggle man          Hiện bảng này

 Cách dùng với VS Code & Web Lab
  1. kaggle gdrive <link_folder> (cấu hình Drive 1 lần, xem README)
  2. kaggle on   3. Mở link Web hoặc VS Code (Existing Jupyter Server)
  4. Mọi file/folder lưu trong thư mục `drive/` sẽ KHÔNG BAO GIỜ MẤT (lưu vĩnh viễn trên Drive)
  Quota: GPU 30h/tuần, TPU 20h/tuần; mỗi phiên tối đa ~12h.
╚══════════════════════════════════════════════════════════╝"""

SERVER_PY = '''import subprocess, time, re, urllib.request, os, base64
TOKEN="__TOKEN__"; TOPIC="__TOPIC__"; GDRIVE_B64="__GDRIVE_B64__"
subprocess.run("pip -q install jupyterlab 2>&1 | tail -1", shell=True)

# Cấu hình Google Drive nếu có
if GDRIVE_B64 and not GDRIVE_B64.startswith("__"):
    try:
        cdir = os.path.expanduser("~/.config/rclone")
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "rclone.conf"), "wb") as f:
            f.write(base64.b64decode(GDRIVE_B64))
        subprocess.run("curl -s https://rclone.org/install.sh | bash > /dev/null 2>&1", shell=True)
        os.makedirs("/kaggle/working/drive", exist_ok=True)
        subprocess.run("rclone copy gdrive: /kaggle/working/drive --update -q", shell=True)
    except Exception as e:
        print("GDrive setup err:", e)

subprocess.run("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /tmp/cf && chmod +x /tmp/cf", shell=True, check=True)
subprocess.Popen(f"jupyter lab --no-browser --allow-root --ip=127.0.0.1 --port=8899 --ServerApp.token={TOKEN} --ServerApp.allow_origin='*' --ServerApp.disable_check_xsrf=True --notebook-dir=/kaggle/working > /tmp/jl.log 2>&1", shell=True)
time.sleep(8)
subprocess.Popen("/tmp/cf tunnel --no-autoupdate --url http://127.0.0.1:8899 > /tmp/cf.log 2>&1", shell=True)
url=None
for _ in range(60):
    time.sleep(2)
    m = re.search(r"https://[a-z0-9-]+\\.trycloudflare\\.com", open("/tmp/cf.log").read())
    if m: url=m.group(0); break
print("URL:", url)
urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=f"{url}/?token={TOKEN}".encode()))

def sync_gdrive():
    try:
        if os.path.exists("/kaggle/working/drive"):
            subprocess.run("rclone copy /kaggle/working/drive gdrive: --update -q", shell=True, timeout=120)
            subprocess.run("rclone copy /kaggle/working gdrive:notebooks_backup --include '*.ipynb' --include '*.py' --max-depth 1 -q", shell=True, timeout=60)
    except Exception: pass

def ctl():
    try: return urllib.request.urlopen(f"https://ntfy.sh/{TOPIC}-ctl/raw?poll=1&since=10m", timeout=20).read().decode().split()
    except Exception: return ["hb"]

for step in range(11*60*2+30):
    time.sleep(30)
    if step % 2 == 0:
        sync_gdrive()
    m = ctl()
    if not m or m[-1] == "stop": break

sync_gdrive()
print("Stopped")
'''

# ---------- tiện ích ----------
def die(msg): sys.exit(msg)

def real_kaggle(args, capture=False):
    code = "import sys; from kaggle.cli import main; sys.argv[0]='kaggle'; main()"
    return subprocess.run([sys.executable, "-c", code, *args], capture_output=capture, text=True)

def username():
    out = real_kaggle(["config", "view"], capture=True).stdout
    m = re.search(r"username:\s*(\S+)", out)
    return m.group(1) if m else die("Chưa cấu hình token Kaggle (~/.kaggle/access_token)")

def copy_clip(text):
    cmds = [["clip"]] if IS_WIN else [["pbcopy"]] if sys.platform == "darwin" else [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-b"]]
    for c in cmds:
        if shutil.which(c[0]):
            try: subprocess.run(c, input=text.encode(), timeout=5); return True
            except Exception: pass
    return False

def http(url, data=None, method=None, headers=None, timeout=60):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    return urllib.request.urlopen(r, timeout=timeout).read()

def ntfy_post(topic, msg):
    try: http(f"https://ntfy.sh/{topic}", msg.encode(), timeout=10)
    except Exception: pass

def ntfy_last(topic):
    try: lines = http(f"https://ntfy.sh/{topic}/raw?poll=1", timeout=15).decode().split()
    except Exception: return ""
    return lines[-1] if lines else ""

def session():
    if not URL_FILE.exists(): die("Chưa bật phiên. Gõ: kaggle on")
    base, tok = URL_FILE.read_text().strip().split("/?token=")
    return base, tok

def api(path, method="GET", body=None, timeout=600):
    base, tok = session()
    h = {"Authorization": f"token {tok}", "Content-Type": "application/json"}
    return http(base + path, None if body is None else json.dumps(body).encode(), method, h, timeout)

# ---------- notebook ----------
def nb_json(code_text, split=True):
    chunks = re.split(r"(?m)^# %%.*\n", code_text) if split else [code_text]
    cells = [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": c.strip("\n").splitlines(True)} for c in chunks if c.strip()]
    return {"cells": cells, "nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}}

def write_meta(d, title_slug, gpu, data=(), comp=()):
    meta = {"id": f"{username()}/{title_slug}", "title": title_slug, "code_file": "train.ipynb", "language": "python", "kernel_type": "notebook",
            "is_private": True, "enable_gpu": gpu, "enable_internet": True, "dataset_sources": list(data), "competition_sources": list(comp), "kernel_sources": []}
    (Path(d) / "kernel-metadata.json").write_text(json.dumps(meta))
    return meta["id"]

# ---------- watcher ----------
def vscode_running():
    try:
        if IS_WIN: return "Code.exe" in subprocess.run(["tasklist", "/FI", "IMAGENAME eq Code.exe", "/NH"], capture_output=True, text=True).stdout
        name = "Electron" if sys.platform == "darwin" else "code"
        return subprocess.run(["pgrep", "-x", name], capture_output=True).returncode == 0
    except Exception: return True

def watch(topic):
    seen, miss, start = False, 0, time.time()
    while True:
        if vscode_running(): seen, miss = True, 0
        else: miss += 1
        if (seen and miss >= 2) or (not seen and time.time() - start > 600): break
        ntfy_post(topic + "-ctl", "hb"); time.sleep(60)
    ntfy_post(topic + "-ctl", "stop"); PID_FILE.unlink(missing_ok=True)

# ---------- google drive (rclone) ----------
def parse_gdrive_id(text):
    m = re.search(r"folders/([a-zA-Z0-9_-]+)", text)
    if m: return m.group(1)
    m2 = re.search(r"id=([a-zA-Z0-9_-]+)", text)
    if m2: return m2.group(1)
    clean = text.strip()
    if re.match(r"^[a-zA-Z0-9_-]{15,}$", clean):
        return clean
    return None

def get_gdrive_folder_id():
    env_id = os.environ.get("KAGGLE_GDRIVE_ID") or os.environ.get("KAGGLE_REMOTE_GDRIVE_ID")
    if env_id: return env_id.strip()
    if GDRIVE_ID_FILE.exists():
        return GDRIVE_ID_FILE.read_text().strip()
    return ""

def find_rclone_conf_path():
    paths = [Path.home() / ".config" / "rclone" / "rclone.conf"]
    if IS_WIN:
        appdata = os.environ.get("APPDATA")
        if appdata: paths.insert(0, Path(appdata) / "rclone" / "rclone.conf")
        paths.append(Path.home() / "AppData" / "Roaming" / "rclone" / "rclone.conf")
    for p in paths:
        if p.exists(): return p
    if shutil.which("rclone"):
        try:
            out = subprocess.run(["rclone", "config", "file"], capture_output=True, text=True, timeout=5).stdout
            for line in out.splitlines():
                line = line.strip()
                if line.endswith("rclone.conf") and os.path.exists(line): return Path(line)
        except Exception: pass
    return None

def find_rclone_conf_and_remote():
    p = find_rclone_conf_path()
    if not p or not p.exists(): return None, None
    try:
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(p)
        if "gdrive" in cfg and cfg["gdrive"].get("type") == "drive" and "token" in cfg["gdrive"]:
            return p, "gdrive"
        for s in cfg.sections():
            if cfg[s].get("type") == "drive" and "token" in cfg[s]:
                return p, s
    except Exception: pass
    return p, None

def get_gdrive_conf():
    fid = get_gdrive_folder_id()
    if not fid: return ""
    p, rem = find_rclone_conf_and_remote()
    if not p or not rem: return ""
    try:
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(p)
        sec = cfg[rem]
        conf = f"[gdrive]\ntype = drive\nscope = drive\nroot_folder_id = {fid}\ntoken = {sec['token']}\n"
        return base64.b64encode(conf.encode()).decode()
    except Exception: pass
    return ""

def cmd_gdrive(args):
    if not args:
        cur = get_gdrive_folder_id()
        p, rem = find_rclone_conf_and_remote()
        print("== Trạng thái Google Drive ==")
        if cur:
            print(f"📁 Folder ID đang liên kết: {cur}")
            print(f"🔗 Link: https://drive.google.com/drive/folders/{cur}")
        else:
            print("📁 Chưa liên kết Google Drive folder nào.")
        if rem:
            print(f"☁️ Remote rclone tìm thấy: [{rem}]")
        else:
            print("⚠️ Chưa tìm thấy remote Google Drive trong cấu hình rclone.")
        print("\nCách dùng:")
        print("  kaggle gdrive <link_folder_hoặc_id>    Liên kết thư mục Google Drive")
        print("  kaggle gdrive off                     Huỷ liên kết Google Drive")
        print("  kaggle sync [up|down]                 Đồng bộ ngay lập tức (khi đang ON)")
        return

    sub = args[0].strip()
    if sub in ("off", "unlink", "rm", "disable", "stop"):
        GDRIVE_ID_FILE.unlink(missing_ok=True)
        print("✓ Đã huỷ liên kết Google Drive.")
        return

    fid = parse_gdrive_id(sub)
    if not fid:
        die("❌ Không nhận diện được Folder ID hoặc URL Google Drive.\nVí dụ hợp lệ: https://drive.google.com/drive/folders/1a2b3c4d... hoặc 1a2b3c4d...")

    STATE.mkdir(exist_ok=True)
    GDRIVE_ID_FILE.write_text(fid)
    print(f"✅ Đã liên kết Google Drive Folder ID: {fid}")
    print(f"🔗 Link: https://drive.google.com/drive/folders/{fid}")

    p, rem = find_rclone_conf_and_remote()
    if rem:
        print(f"✓ Đã phát hiện remote rclone: [{rem}].")
        print("✨ Sẵn sàng! Khi gõ 'kaggle on', thư mục /kaggle/working/drive/ sẽ tự động đồng bộ 2 chiều với Google Drive của bạn.")
    else:
        print("\n⚠️ Lưu ý: Chưa tìm thấy cấu hình Google Drive bằng rclone trên máy bạn!")
        print("Để hoàn tất:")
        print("  1. Cài rclone: https://rclone.org (Linux: curl https://rclone.org/install.sh | sudo bash)")
        print("  2. Chạy 'rclone config' tạo remote kiểu 'drive' (xem hướng dẫn chi tiết trong README.md)")

# ---------- lệnh ----------
def cmd_off(quiet=False):
    if URL_FILE.exists() and get_gdrive_folder_id():
        try:
            if not quiet: print("💾 Đang đồng bộ dữ liệu lên Google Drive trước khi tắt...", flush=True)
            remote_exec("import subprocess; subprocess.run('rclone copy /kaggle/working/drive gdrive: --update -q; rclone copy /kaggle/working gdrive:notebooks_backup --include \"*.ipynb\" --include \"*.py\" --max-depth 1 -q', shell=True, timeout=60)")
            if not quiet: print("✓ Đã lưu an toàn lên Google Drive!")
        except Exception: pass
    if TOPIC_FILE.exists(): ntfy_post(TOPIC_FILE.read_text().strip() + "-ctl", "stop")
    if PID_FILE.exists():
        try: os.kill(int(PID_FILE.read_text()), 15)
        except Exception: pass
    for f in (PID_FILE, URL_FILE): f.unlink(missing_ok=True)
    if not quiet: print("🛑 Đã gửi lệnh tắt, Kaggle sẽ dừng trong ≤30 giây.")

def cmd_on(args):
    gpu = "--cpu" not in args
    data, comp = [], []
    for i, a in enumerate(args):
        if a == "--data" and i + 1 < len(args): data.append(args[i + 1])
        if a == "--comp" and i + 1 < len(args): comp.append(args[i + 1])
    STATE.mkdir(exist_ok=True)
    if TOPIC_FILE.exists(): cmd_off(quiet=True)
    token, topic = secrets.token_hex(16), "kj-" + secrets.token_hex(12)
    TOPIC_FILE.write_text(topic)
    kw = {"creationflags": 0x00000008 | 0x00000200} if IS_WIN else {"start_new_session": True}
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "_watch", topic], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    PID_FILE.write_text(str(p.pid))
    d = tempfile.mkdtemp()
    gconf = get_gdrive_conf()
    code = SERVER_PY.replace("__TOKEN__", token).replace("__TOPIC__", topic).replace("__GDRIVE_B64__", gconf)
    Path(d, "train.ipynb").write_text(json.dumps(nb_json(code, split=False)))
    kid = write_meta(d, SLUG, gpu, data, comp)
    if real_kaggle(["kernels", "push", "-p", d]).returncode: cmd_off(True); die("Push lên Kaggle thất bại")
    print("⏳ Đợi Kaggle khởi động (1-3 phút)...", flush=True)
    if gconf:
        print("☁️ Google Drive: Đã kích hoạt lưu trữ vĩnh viễn (/kaggle/working/drive/)")
    elif get_gdrive_folder_id():
        print("⚠️ Google Drive: Đã cài Folder ID nhưng chưa tìm thấy token rclone trên máy. Phiên chạy không có Drive.")
    for _ in range(90):
        u = ntfy_last(topic)
        if u: break
        time.sleep(5)
    else:
        cmd_off(True); die(f"Không nhận được URL, xem https://www.kaggle.com/code/{kid}")
    URL_FILE.write_text(u)
    ok = copy_clip(u)
    print(f"\n✅ Jupyter trên Kaggle: {u}")
    print("   " + ("Link đã được copy vào clipboard. " if ok else "") + "VS Code: Select Kernel → Existing Jupyter Server → Ctrl+V → Enter.")
    if gconf:
        print("📁 Thư mục /kaggle/working/drive/ sẽ tự động đồng bộ về Google Drive.")

def cmd_status():
    if not URL_FILE.exists(): return print("OFF")
    print("ON:", URL_FILE.read_text().strip()); real_kaggle(["kernels", "status", f"{username()}/{SLUG}"])

def cmd_url():
    u = URL_FILE.read_text().strip() if URL_FILE.exists() else ""
    print(u or "OFF"); u and copy_clip(u)

def cmd_time():
    print("== Quota Kaggle (reset hàng tuần) ==", flush=True); real_kaggle(["quota"])
    print()
    if URL_FILE.exists(): print(f"== Phiên đang chạy ==\nBật từ: {time.strftime('%H:%M %d/%m', time.localtime(URL_FILE.stat().st_mtime))} (~{int((time.time()-URL_FILE.stat().st_mtime)/60)} phút)")
    else: print("Không có phiên nào đang bật.")

def upload(path, remote):
    size, n, i, CH = os.path.getsize(path), 0, 0, 24 << 20
    with open(path, "rb") as f:
        while True:
            d = f.read(CH); n += len(d); i += 1; last = n >= size
            api(f"/api/contents/{urllib.parse.quote(remote)}", "PUT", {"type": "file", "format": "base64", "name": os.path.basename(remote), "chunk": -1 if last else i, "content": base64.b64encode(d).decode()})
            print(f"\r  {os.path.basename(path)}: {n*100//max(size,1)}%", end="", flush=True)
            if last: break
    print()

def remote_exec(code):
    import websocket
    base, tok = session()
    kid = json.loads(api("/api/kernels", "POST", {}))["id"]
    ws = websocket.create_connection(base.replace("https", "wss") + f"/api/kernels/{kid}/channels?token={tok}", timeout=600)
    ws.send(json.dumps({"header": {"msg_id": "1", "username": "", "session": "kr", "msg_type": "execute_request", "version": "5.3"}, "parent_header": {}, "metadata": {}, "channel": "shell", "buffers": [],
        "content": {"code": code, "silent": False, "store_history": False, "user_expressions": {}, "allow_stdin": False, "stop_on_error": True}}))
    err = None
    while True:
        m = json.loads(ws.recv())
        if m["parent_header"].get("msg_id") != "1": continue
        if m["msg_type"] == "error": err = "\n".join(m["content"]["traceback"])
        if m["msg_type"] == "status" and m["content"]["execution_state"] == "idle": break
    ws.close(); api(f"/api/kernels/{kid}", "DELETE")
    if err: die("Lỗi bên Kaggle:\n" + err)

def cmd_up(args):
    if not args: die("Dùng: kaggle up [-d thư_mục_đích] <file|dir>...")
    rd = ""
    if args[0] == "-d": rd, args = args[1].strip("/"), args[2:]
    paths = [a.rstrip("/\\") for a in args]
    if len(paths) == 1 and not rd and os.path.isfile(paths[0]):
        upload(paths[0], os.path.basename(paths[0])); return print(f"  ✓ /kaggle/working/{os.path.basename(paths[0])}")
    name = "kup_bundle"; z = os.path.join(tempfile.mkdtemp(), name + ".zip"); cnt = 0
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        for p in paths:
            if os.path.isdir(p):
                top = os.path.basename(os.path.abspath(p))
                for root, _, fs in os.walk(p):
                    for fn in fs:
                        fp = os.path.join(root, fn); arc = "/".join(x for x in (rd, top, *Path(os.path.relpath(fp, p)).parts) if x); zf.write(fp, arc); cnt += 1
            elif os.path.exists(p): zf.write(p, "/".join(x for x in (rd, os.path.basename(p)) if x)); cnt += 1
            else: die(f"Không thấy: {p}")
    print(f"{cnt} file → zip {os.path.getsize(z)/1e6:.1f} MB → /kaggle/working/{rd}")
    upload(z, name + ".zip")
    remote_exec(f"import zipfile,os\nzipfile.ZipFile('/kaggle/working/{name}.zip').extractall('/kaggle/working')\nos.remove('/kaggle/working/{name}.zip')")
    os.remove(z); print("  ✓ xong")

def cmd_rm(pats):
    if not pats or any(x.startswith("/") or ".." in x for x in pats): die("Dùng: kaggle rm <đường dẫn tương đối|glob>... (chỉ trong /kaggle/working)")
    remote_exec("import glob,os,shutil\nfor pat in %r:\n    for f in glob.glob(os.path.join('/kaggle/working',pat)):\n        shutil.rmtree(f) if os.path.isdir(f) else os.remove(f)" % pats)
    print("✓ đã xoá:", " ".join(pats))

def cmd_ls(args):
    p = urllib.parse.quote(args[0].strip("/")) if args else ""
    for c in json.loads(api(f"/api/contents/{p}", timeout=60))["content"]:
        print(f"{(c['size'] or 0)/1e6:9.2f} MB  {c['name']}{'/' if c['type']=='directory' else ''}")

def cmd_down(args):
    if not args: die("Dùng: kaggle down <file|dir> [thư mục đích]")
    dest = args[1] if len(args) > 1 else "."
    def get(p, dest):
        q = urllib.parse.quote(p)
        m = json.loads(api(f"/api/contents/{q}?content=0"))
        if m["type"] == "directory":
            for c in json.loads(api(f"/api/contents/{q}"))["content"]: get(c["path"], os.path.join(dest, os.path.basename(p)))
            return
        os.makedirs(dest, exist_ok=True); out = os.path.join(dest, os.path.basename(p))
        open(out, "wb").write(base64.b64decode(json.loads(api(f"/api/contents/{q}?content=1&format=base64"))["content"])); print("✓", out)
    p = args[0].replace("\\", "/").lstrip("/")
    get(p[len("kaggle/working/"):] if p.startswith("kaggle/working/") else p, dest)

def cmd_run(args):
    if not args: die("Dùng: kaggle run <thư_mục> [--cpu]")
    d = Path(args[0]).resolve(); gpu = "--cpu" not in args
    nb, py = d / "train.ipynb", d / "train.py"
    if not nb.exists():
        if not py.exists(): die("Thiếu train.ipynb (hoặc train.py)")
        nb.write_text(json.dumps(nb_json(py.read_text(encoding="utf-8"))))
    slug = re.sub(r"[^a-z0-9-]", "-", d.name.lower())
    if len(slug) < 5: slug += "-nb"
    kid = write_meta(d, slug, gpu)
    if real_kaggle(["kernels", "push", "-p", str(d)]).returncode: die("Push thất bại")
    print("⏳ Đang chạy trên Kaggle...")
    while True:
        s = real_kaggle(["kernels", "status", kid], capture=True).stdout.strip(); print(s)
        if any(x in s for x in ("COMPLETE", "ERROR", "CANCEL")): break
        time.sleep(20)
    real_kaggle(["kernels", "output", kid, "-p", str(d / "output")]); print(f"✅ Output ở: {d/'output'}")

def cmd_sync(args):
    if not get_gdrive_folder_id():
        die("Chưa liên kết Google Drive. Gõ: kaggle gdrive <link_folder_hoặc_id>")
    direction = args[0] if args else "up"
    print(f"🔄 Đang đồng bộ {'lên' if direction in ('up','push') else 'về'} Google Drive...", flush=True)
    if direction in ("up", "push"):
        c = "import subprocess\nout = subprocess.run('rclone copy /kaggle/working/drive gdrive: --update -v 2>&1; rclone copy /kaggle/working gdrive:notebooks_backup --include \"*.ipynb\" --include \"*.py\" --max-depth 1 -v 2>&1', shell=True, capture_output=True, text=True)\nprint(out.stdout)"
    elif direction in ("down", "pull"):
        c = "import subprocess\nout = subprocess.run('rclone copy gdrive: /kaggle/working/drive --update -v 2>&1', shell=True, capture_output=True, text=True)\nprint(out.stdout)"
    else: die("Dùng: kaggle sync [up|down]")
    import websocket
    base, tok = session()
    kid = json.loads(api("/api/kernels", "POST", {}))["id"]
    ws = websocket.create_connection(base.replace("https", "wss") + f"/api/kernels/{kid}/channels?token={tok}", timeout=600)
    ws.send(json.dumps({"header": {"msg_id": "1", "username": "", "session": "kr", "msg_type": "execute_request", "version": "5.3"}, "parent_header": {}, "metadata": {}, "channel": "shell", "buffers": [],
        "content": {"code": c, "silent": False, "store_history": False, "user_expressions": {}, "allow_stdin": False, "stop_on_error": True}}))
    err = None
    while True:
        m = json.loads(ws.recv())
        if m["parent_header"].get("msg_id") != "1": continue
        if m["msg_type"] == "stream": sys.stdout.write(m["content"]["text"]); sys.stdout.flush()
        if m["msg_type"] == "error": err = "\n".join(m["content"]["traceback"])
        if m["msg_type"] == "status" and m["content"]["execution_state"] == "idle": break
    ws.close(); api(f"/api/kernels/{kid}", "DELETE")
    if err: die("Lỗi bên Kaggle:\n" + err)
    print("✅ Hoàn tất đồng bộ!")

# ---------- terminal tương tác trên Kaggle ----------
def cmd_terminal():
    import websocket, threading, shutil as sh
    base, tok = session()
    name = json.loads(api("/api/terminals", "POST", {}, 30))["name"]
    ws = websocket.create_connection(base.replace("https", "wss") + f"/terminals/websocket/{name}?token={tok}", timeout=None)
    last = [None]
    def resize():
        s = sh.get_terminal_size()
        if s != last[0]: last[0] = s; ws.send(json.dumps(["set_size", s.lines, s.columns, 0, 0]))
    resize(); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ws.send(json.dumps(["stdin", "cd /kaggle/working && clear && echo '☁  Kaggle terminal — /kaggle/working (thoát: exit)'\r"]))
    done = threading.Event()
    def reader():
        try:
            while True:
                m = json.loads(ws.recv())
                if m[0] == "stdout": sys.stdout.write(m[1]); sys.stdout.flush()
                elif m[0] == "disconnect": break
        except Exception: pass
        done.set()
    threading.Thread(target=reader, daemon=True).start()
    send = lambda s: ws.send(json.dumps(["stdin", s]))
    try:
        if IS_WIN:
            import msvcrt; os.system("")
            keys = {"H": "\x1b[A", "P": "\x1b[B", "K": "\x1b[D", "M": "\x1b[C", "G": "\x1b[H", "O": "\x1b[F", "S": "\x1b[3~"}
            while not done.is_set():
                resize()
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    send(keys.get(msvcrt.getwch(), "") if ch in "\x00\xe0" else ch)
                else: time.sleep(0.02)
        else:
            import tty, termios, select
            fd = sys.stdin.fileno(); old = termios.tcgetattr(fd); tty.setraw(fd)
            try:
                while not done.is_set():
                    resize()
                    if select.select([fd], [], [], 0.2)[0]:
                        d = os.read(fd, 4096)
                        if not d: break
                        send(d.decode(errors="ignore"))
            finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
    finally:
        try: ws.close()
        except Exception: pass
        try: api(f"/api/terminals/{name}", "DELETE", timeout=10)
        except Exception: pass
        print("\n[đã thoát Kaggle terminal]")

def main():
    a = sys.argv[1:]; c = a[0] if a else ""; r = a[1:]
    if c == "on": cmd_on(r)
    elif c == "off": cmd_off()
    elif c == "status": cmd_status()
    elif c == "url": cmd_url()
    elif c == "time": cmd_time()
    elif c == "up": cmd_up(r)
    elif c == "rm": cmd_rm(r)
    elif c == "ls": cmd_ls(r)
    elif c == "down": cmd_down(r)
    elif c == "run": cmd_run(r)
    elif c == "sync": cmd_sync(r)
    elif c in ("gdrive", "drive"): cmd_gdrive(r)
    elif c in ("terminal", "term", "sh"): cmd_terminal()
    elif c == "man": print(MAN)
    elif c == "_watch": watch(r[0])
    else: sys.exit(real_kaggle(a).returncode)

if __name__ == "__main__":
    main()
