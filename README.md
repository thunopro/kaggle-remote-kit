# Kaggle Remote Kit

Viết code ở máy mình (VS Code / Jupyter), **bấm Run Cell như bình thường nhưng chạy bằng GPU Kaggle** (T4 x2). Hỗ trợ **Linux, macOS, Windows**.

---

## Cài đặt

1. **Lấy API token Kaggle**: vào [kaggle.com](https://www.kaggle.com) → Settings → API → **Create New Token** (token dạng `KGAT_...`).  
   *(Lưu ý: Không bao giờ chia sẻ hay commit token này lên GitHub).*
2. **Yêu cầu**: Python 3.8+, VS Code + extension Jupyter, tài khoản Kaggle đã xác minh số điện thoại (để bật internet trên notebook).

### Linux / macOS
```bash
git clone git@github.com:thunopro/kaggle-remote-kit.git && cd kaggle-remote-kit
./install.sh            # hỏi token, lưu an toàn vào ~/.kaggle/access_token
# mở terminal mới
```

### Windows (PowerShell)
```powershell
git clone git@github.com:thunopro/kaggle-remote-kit.git; cd kaggle-remote-kit
powershell -ExecutionPolicy Bypass -File .\install.ps1     # hỏi token, lưu an toàn vào %USERPROFILE%\.kaggle\access_token
# mở cửa sổ PowerShell/CMD mới
```
Gõ `kaggle man` để kiểm tra.

---

## Cách dùng với VS Code

1. `kaggle on` — đợi 1–3 phút, link được in ra và tự động copy vào clipboard.
2. Mở file `.ipynb` trong VS Code → **Select Kernel → Existing Jupyter Server → Ctrl+V (dán link) → Enter → chọn kernel python3**.
3. `kaggle up train.csv` — đưa dữ liệu từ máy lên Kaggle (hoặc dùng `--data`/`--comp` để gắn dataset Kaggle vào `/kaggle/input`).
4. Bấm **Run Cell**, code chạy trực tiếp trên GPU Kaggle.
5. `kaggle down model.pth` — tải kết quả/checkpoint về máy.
6. `kaggle off` để tắt phiên khi xong (hoặc chỉ cần tắt VS Code, hệ thống sẽ tự dừng an toàn).

---

## ☁️ Lưu trữ vĩnh viễn với Google Drive (Không lo mất dữ liệu)

Mặc định khi phiên Kaggle tắt hoặc timeout (sau 12h), toàn bộ thư mục `/kaggle/working` trên Kaggle sẽ bị xoá sạch. Để không bao giờ bị mất model weights, checkpoints, logs hay dataset tải dở, bạn có thể **liên kết một thư mục Google Drive riêng của bạn**:

- Khi bật phiên (`kaggle on`), dữ liệu trong Drive tự động kéo về `/kaggle/working/drive/`.
- Định kỳ mỗi 60 giây và khi tắt phiên (`kaggle off`), dữ liệu được tự động đồng bộ 2 chiều lên Drive.
- Tự động sao lưu cả code notebook (`.ipynb`, `.py`) vào thư mục `notebooks_backup` trên Drive.

### Hướng dẫn kết nối Google Drive cá nhân (chỉ làm 1 lần):

#### Bước 1: Cài đặt `rclone` trên máy tính
- **Linux**: `curl https://rclone.org/install.sh | sudo bash`
- **macOS**: `brew install rclone`
- **Windows**: Tải file cài từ [rclone.org/downloads](https://rclone.org/downloads/) hoặc chạy PowerShell: `winget install Rclone.Rclone`

#### Bước 2: Cấp quyền tài khoản Google cho rclone
Mở terminal trên máy của bạn và chạy:
```bash
rclone config
```
Làm theo các bước sau:
1. Gõ `n` (New remote).
2. Đặt tên: `gdrive` (hoặc tên bất kỳ bạn thích).
3. Mục loại lưu trữ (Storage type): gõ `drive` (hoặc số tương ứng với Google Drive).
4. `client_id` và `client_secret`: bấm **Enter** để trống (dùng mặc định).
5. `scope`: chọn `1` (Full access: quyền đọc/ghi vào Drive của bạn).
6. `service_account_file`: bấm **Enter** để trống.
7. `Edit advanced config`: gõ `n`.
8. `Use web browser to automatically authenticate`: gõ `y`.
9. Trình duyệt tự động mở lên: **Đăng nhập Google** → bấm **Allow (Cho phép)** cấp quyền cho rclone.
10. Quay lại terminal: gõ `y` để xác nhận lưu cấu hình, rồi gõ `q` để thoát.

#### Bước 3: Tạo thư mục trên Google Drive và liên kết
1. Mở [Google Drive](https://drive.google.com) trên trình duyệt, tạo một thư mục riêng để chứa code/data Kaggle (ví dụ: `kaggle_drive`).
2. Mở thư mục đó ra, nhìn lên thanh địa chỉ trình duyệt, copy toàn bộ đường link (hoặc mã ID ở cuối):
   - Link dạng: `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j...`
3. Chạy lệnh liên kết:
   ```bash
   kaggle gdrive https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j...
   ```
   *(Hoặc chỉ cần truyền ID: `kaggle gdrive 1a2b3c4d5e6f7g8h9i0j...`)*

#### Bước 4: Tận hưởng!
Giờ mỗi khi bạn gõ `kaggle on`, thư mục `/kaggle/working/drive/` sẽ tự động kết nối với folder Google Drive của bạn:
- Mọi model, checkpoint, dataset bạn lưu trong thư mục `drive/` sẽ **lưu vĩnh viễn trên Google Drive**.
- Muốn đồng bộ ngay lập tức: gõ `kaggle sync up` (đẩy lên Drive) hoặc `kaggle sync down` (kéo về).
- Muốn xem trạng thái: gõ `kaggle gdrive`.
- Muốn huỷ liên kết: gõ `kaggle gdrive off`.

---

## Danh sách lệnh

| Lệnh | Chức năng |
|---|---|
| `kaggle on [--cpu] [--comp slug] [--data user/ds]` | Bật Jupyter trên GPU Kaggle, in link + copy clipboard. Có thể gắn competition hoặc dataset vào `/kaggle/input`. |
| `kaggle off` | Tắt phiên (tự động đồng bộ toàn bộ thư mục `drive/` lên Google Drive trước khi dừng). |
| `kaggle gdrive [link\|id\|off]` | Liên kết thư mục Google Drive cá nhân, xem trạng thái hoặc huỷ liên kết. |
| `kaggle sync [up\|down]` | Đồng bộ thủ công dữ liệu giữa Kaggle và Google Drive ngay lập tức (`up` = đẩy lên, `down` = kéo về). |
| `kaggle status` / `kaggle url` | Kiểm tra trạng thái ON/OFF / in lại link web + copy clipboard. |
| `kaggle time` | Xem quota GPU/TPU còn lại trong tuần + thời gian phiên hiện tại đã chạy. |
| `kaggle up [-d dir] <file\|dir>...` | Upload nhanh file/folder từ máy lên Kaggle (tự động nén zip → tải lên 1 lần → giải nén bên Kaggle). |
| `kaggle ls [dir]` | Liệt kê danh sách file đang có trên Kaggle. |
| `kaggle down <file\|dir> [đích]` | Tải file hoặc thư mục từ Kaggle về máy local. |
| `kaggle rm <path\|glob>...` | Xoá file/thư mục trên Kaggle (hỗ trợ wildcard như `'*.pth'`). |
| `kaggle terminal` | Mở Terminal tương tác trực tiếp bên trong Kaggle (chạy lệnh bash, nvidia-smi, pip install...). |
| `kaggle run <thư mục> [--cpu]` | Chạy batch cả file `train.ipynb`/`train.py` một lần không cần mở VS Code, tự tải output về khi xong. |
| `kaggle man` | Xem bảng trợ giúp các lệnh. |
| `kaggle kernels\|datasets\|...` | Chuyển tiếp các lệnh Kaggle CLI gốc. |

---

## 🔒 Bảo mật & Quyền riêng tư (Security)

- **API Token Kaggle (`KGAT_...`)**: Được lưu ở `~/.kaggle/access_token` trên máy cá nhân với quyền đọc hạn chế (`chmod 600`), không bao giờ bị đẩy lên GitHub.
- **Google Drive Access Token**: Lưu ở `rclone.conf` trên máy của bạn. Khi khởi động phiên Kaggle, kit chỉ chuyển token tạm thời với phạm vi bị khoá cứng vào đúng thư mục bạn đã chỉ định (`root_folder_id`). Kaggle **không thể** truy cập các thư mục cá nhân khác ngoài Drive của bạn.
- Tất cả các file cấu hình, token và key đều được khai báo trong `.gitignore` để ngăn chặn rủi ro vô tình commit dữ liệu riêng tư.

---

## Cơ chế hoạt động

- `kaggle on` đẩy một notebook private lên Kaggle, khởi động server JupyterLab và tạo Cloudflare quick tunnel. Link truy cập gửi an toàn về máy qua topic ngẫu nhiên trên `ntfy.sh`; Jupyter được bảo vệ bằng token ngẫu nhiên.
- Một watcher nền trên máy gửi heartbeat mỗi 60s khi VS Code còn mở. Khi đóng VS Code hoặc mất kết nối >10 phút, phiên Kaggle sẽ tự động đồng bộ dữ liệu và dừng lại để tiết kiệm quota 30h/tuần.
- Toàn bộ logic gói gọn trong `kr.py`, không cần setup server phức tạp.
