# Kaggle Remote Kit

Viết code ở máy mình (VS Code / Jupyter), chạy bằng GPU Kaggle (T4 x2) chỉ với vài lệnh terminal.

## Cài đặt
```bash
git clone git@github.com:thunopro/kaggle-remote-kit.git && cd kaggle-remote-kit
./install.sh            # sẽ hỏi Kaggle API token (KGAT_...), lưu vào ~/.kaggle/access_token
source ~/.bashrc
```
Lấy token: kaggle.com → Settings → API → Create New Token. **Không bao giờ commit token.**
Yêu cầu: Linux, Python 3, `curl`, `openssl`, tài khoản Kaggle đã xác minh số điện thoại (để bật internet), VS Code + extension Jupyter.

## Cách dùng với VS Code
1. `kaggle on` — đợi 1–3 phút, link được in ra và copy vào clipboard
2. Mở file `.ipynb` → **Select Kernel → Existing Jupyter Server → Ctrl+V → Enter → python3**
3. `kaggle up train.csv` — đưa dữ liệu local lên Kaggle (code chạy bên Kaggle nên không thấy file local)
4. Bấm **Run Cell** như bình thường, code chạy trên GPU Kaggle
5. `kaggle down model.pth` — tải kết quả về máy
6. `kaggle off` (hoặc đóng VS Code, sẽ tự tắt)

## Danh sách lệnh
| Lệnh | Chức năng |
|---|---|
| `kaggle on [--cpu]` | Bật Jupyter trên Kaggle, in link + copy clipboard |
| `kaggle off` | Tắt phiên |
| `kaggle status` | Đang ON/OFF |
| `kaggle url` | In lại link |
| `kaggle time` | Quota GPU/TPU còn lại + thời gian phiên |
| `kaggle up <file\|dir>` | Upload lên `/kaggle/working` |
| `kaggle ls [dir]` | Liệt kê file trên Kaggle |
| `kaggle down <file\|dir> [đích]` | Tải từ Kaggle về |
| `kaggle run <thư mục> [--cpu]` | Chạy cả `train.ipynb`/`train.py` một lần, tải output về `<thư mục>/output` |
| `kaggle man` | Bảng hướng dẫn |
| `kaggle kernels/datasets/...` | Lệnh Kaggle CLI gốc |

## Cơ chế
- `kaggle on` push một notebook private lên Kaggle, chạy JupyterLab + Cloudflare quick tunnel. Link gửi về máy qua topic ngẫu nhiên trên `ntfy.sh`; Jupyter được bảo vệ bằng token ngẫu nhiên.
- `kwatch` chạy ngầm trên máy, gửi heartbeat mỗi 60s khi VS Code còn mở. VS Code tắt (~2 phút) hoặc mất heartbeat >10 phút → phiên Kaggle tự dừng, không phí quota.

## Lưu ý
- Quota: GPU 30h/tuần, TPU 20h/tuần, mỗi phiên tối đa ~12h.
- `/kaggle/working` bị xoá khi tắt phiên → `kaggle down` trước.
- Link đổi mỗi lần bật → chọn lại kernel trong VS Code. Ai có link là điều khiển được phiên, đừng chia sẻ.
- `kaggle` là wrapper script (bash/zsh/fish đều dùng được), lệnh không phải của kit sẽ chuyển cho Kaggle CLI gốc.
