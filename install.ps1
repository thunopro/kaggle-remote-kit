# Cài trên Windows (PowerShell). Dùng:  .\install.ps1 [-Token KGAT_...]   (không truyền thì được hỏi)
# Yêu cầu: Python 3.8+ (python.org, tick "Add to PATH")
param([string]$Token = "")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m pip install --user -q -U kaggle websocket-client
$kr = Join-Path $env:USERPROFILE ".kaggle-remote"
$wrap = Join-Path $env:USERPROFILE ".kaggle-remote\bin"
New-Item -ItemType Directory -Force $kr, $wrap, (Join-Path $env:USERPROFILE ".kaggle") | Out-Null
Copy-Item "$here\kr.py" $kr -Force
Copy-Item "$here\wrap\kaggle.cmd" $wrap -Force
$tokFile = Join-Path $env:USERPROFILE ".kaggle\access_token"
if (-not $Token -and -not (Test-Path $tokFile)) {
  $sec = Read-Host "Dán Kaggle API token (KGAT_...)" -AsSecureString
  $Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
}
if ($Token) { [IO.File]::WriteAllText($tokFile, $Token) }
$p = [Environment]::GetEnvironmentVariable("Path", "User")
if ($p -notlike "*$wrap*") { [Environment]::SetEnvironmentVariable("Path", "$wrap;$p", "User") }
Write-Host "Xong. Mở cửa sổ PowerShell/CMD MỚI rồi gõ: kaggle man"
Write-Host "💡 Tuỳ chọn: Gõ 'kaggle gdrive <link_folder>' để liên kết Google Drive lưu trữ vĩnh viễn (xem README.md)."
