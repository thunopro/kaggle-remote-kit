# Kaggle Remote Kit

Viết code ở máy mình (VS Code / Jupyter), **bấm Run Cell như bình thường nhưng chạy bằng GPU Kaggle** (T4 x2). Hỗ trợ **Linux, macOS, Windows**.

## Cài đặt

Lấy API token: kaggle.com → Settings → API → Create New Token (dạng `KGAT_...`). **Không bao giờ commit token.**
Yêu cầu: Python 3.8+, VS Code + extension Jupyter, tài khoản Kaggle đã xác minh số điện thoại (để bật internet).

**Linux / macOS**
```bash
git clone git@github.com:thunopro/kaggle-remote-kit.git && cd kaggle-remote-kit
./install.sh            # hỏi token, lưu vào ~/.kaggle/access_token
# mở terminal mới
```

**Windows (PowerShell)**
```powershell
git clone git@github.com:thunopro/kaggle-remote-kit.git; cd kaggle-remote-kit
powershell -ExecutionPolicy Bypass -File .\install.ps1     # hỏi token, lưu vào %USERPROFILE%\.kaggle\access_token
# mở cửa sổ PowerShell/CMD mới
```
Gõ `kaggle man` để kiểm tra.

> Windows: bản này viết theo cùng mã nguồn Python và chưa được test trên máy Windows thật. Gặp lỗi thì mở issue.

## Cách dùng với VS Code
1. `kaggle on` — đợi 1–3 phút, link được in ra và copy vào clipboard
2. Mở `.ipynb` → **Select Kernel → Existing Jupyter Server → Ctrl+V → Enter → python3**
3. `kaggle up train.csv` — đưa dữ liệu local lên Kaggle (code chạy bên Kaggle nên không thấy file local)
4. Bấm **Run Cell**, code chạy trên GPU Kaggle
5. `kaggle down model.pth` — tải kết quả về máy
6. `kaggle off` (hoặc đóng VS Code, sẽ tự tắt)

## Danh sách lệnh
| Lệnh | Chức năng |
|---|---|
| `kaggle on [--cpu]` | Bật Jupyter trên Kaggle, in link + copy clipboard |
| `kaggle off` | Tắt phiên |
| `kaggle status` / `kaggle url` | Trạng thái / in lại link |
| `kaggle time` | Quota GPU/TPU còn lại + thời gian phiên |
| `kaggle up [-d dir] <file\|dir>...` | Upload (nhiều file/thư mục: nén zip → upload 1 lần → giải nén bên Kaggle, giữ cấu trúc) |
| `kaggle ls [dir]` | Liệt kê file trên Kaggle |
| `kaggle down <file\|dir> [đích]` | Tải từ Kaggle về |
| `kaggle rm <path\|glob>...` | Xoá file/thư mục trên Kaggle |
| `kaggle terminal` | Terminal tương tác ngay trên Kaggle (ls, unzip, nvidia-smi...) |
| `kaggle run <thư mục> [--cpu]` | Chạy cả `train.ipynb`/`train.py` (`# %%` chia cell) một lần, tải output về `<thư mục>/output` |
| `kaggle man` | Bảng hướng dẫn |
| `kaggle kernels/datasets/...` | Lệnh Kaggle CLI gốc (chuyển tiếp) |

## Cơ chế
- `kaggle on` push một notebook private lên Kaggle, chạy JupyterLab + Cloudflare quick tunnel. Link gửi về máy qua topic ngẫu nhiên trên `ntfy.sh`; Jupyter được bảo vệ bằng token ngẫu nhiên.
- Một tiến trình nền trên máy gửi heartbeat mỗi 60s khi VS Code còn mở. VS Code tắt (~2 phút) hoặc mất heartbeat >10 phút → phiên Kaggle tự dừng, không phí quota.
- Toàn bộ logic nằm trong một file `kr.py` (chỉ dùng thư viện chuẩn + `kaggle` + `websocket-client`); `wrap/kaggle` (Linux/macOS) và `wrap/kaggle.cmd` (Windows) chỉ gọi file này, lệnh lạ thì chuyển cho Kaggle CLI gốc.

## Lưu ý
- Quota: GPU 30h/tuần, TPU 20h/tuần, mỗi phiên tối đa ~12h.
- `/kaggle/working` bị xoá khi tắt phiên → `kaggle down` trước.
- Link đổi mỗi lần bật → chọn lại kernel trong VS Code. Ai có link là điều khiển được phiên, đừng chia sẻ.
- Trạng thái lưu ở `~/.kaggle-remote/`.
- Nút xoá trên giao diện JupyterLab báo lỗi `send2trash` (máy Kaggle không có thùng rác) → dùng `kaggle rm`.
