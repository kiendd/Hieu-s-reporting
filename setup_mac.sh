#!/bin/bash
# Tạo file "Chay Bao Cao.app" để double-click chạy tool trên Mac.
# Chạy script này 1 lần sau khi tải tool về.
#
# Cách chạy:
#   1. Mở Terminal
#   2. Kéo thả file này vào Terminal
#   3. Nhấn Enter

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$DIR/Chay Bao Cao.app"

echo "Đang cài thư viện Python..."
pip3 install -r "$DIR/requirements.txt" --quiet

echo "Đang tạo launcher app..."
osacompile -o "$APP" -e "
tell application \"Finder\"
    set myPath to POSIX path of (container of (path to me) as alias)
end tell
tell application \"Terminal\"
    activate
    do script \"cd \" & quoted form of myPath & \" && streamlit run app.py\"
end tell
"

echo ""
echo "Hoàn tất! Double-click \"Chay Bao Cao.app\" để khởi động."
