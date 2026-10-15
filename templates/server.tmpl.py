# %%
import subprocess, time, re, os, urllib.request
TOKEN="__TOKEN__"; TOPIC="__TOPIC__"
subprocess.run("pip -q install jupyterlab 2>&1 | tail -1", shell=True)
subprocess.run("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /tmp/cf && chmod +x /tmp/cf", shell=True, check=True)
subprocess.Popen(f"jupyter lab --no-browser --allow-root --ip=127.0.0.1 --port=8899 --ServerApp.token={TOKEN} --ServerApp.allow_origin='*' --ServerApp.disable_check_xsrf=True --notebook-dir=/kaggle/working > /tmp/jl.log 2>&1", shell=True)
time.sleep(8)
cf = subprocess.Popen("/tmp/cf tunnel --no-autoupdate --url http://127.0.0.1:8899 > /tmp/cf.log 2>&1", shell=True)
url=None
for _ in range(60):
    time.sleep(2)
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open("/tmp/cf.log").read())
    if m: url=m.group(0); break
print("URL:", url)
urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=f"{url}/?token={TOKEN}".encode()))
# tự dừng khi nhận "stop" hoặc mất heartbeat từ máy bạn > 10 phút
def ctl():
    try: return urllib.request.urlopen(f"https://ntfy.sh/{TOPIC}-ctl/raw?poll=1&since=10m", timeout=20).read().decode().split()
    except Exception: return ["hb"]  # lỗi mạng tạm thời: không dừng
for _ in range(11*60*2+30):
    time.sleep(30)
    m = ctl()
    if not m or m[-1] == "stop": break
print("Stopped")
