# Hướng Dẫn Cài Đặt Chi Tiết

## 1. Chuẩn Bị Raspberry Pi

### 1.1 Format và Cài Đặt OS
- Download Raspberry Pi Imager: https://www.raspberrypi.com/software/
- Flash Raspberry Pi OS (Bookworm 64-bit recommended)
- Boot và complete initial setup

### 1.2 Cập Nhật Hệ Thống
```bash
sudo apt update
sudo apt upgrade -y
```

### 1.3 Cài Đặt Dependencies Hệ Thống
```bash
# Python dev headers
sudo apt install -y python3-dev python3-pip python3-venv

# Camera support
sudo apt install -y libatlas-base-dev libjasper-dev libtiff5 libjasper1 libharfbuzz0b libwebp6

# GPIO support
sudo apt install -y python3-rpi.gpio

# I2C tools (for LCD)
sudo apt install -y i2c-tools python3-smbus

# Build tools
sudo apt install -y build-essential cmake
```

### 1.4 Enable Camera & I2C
```bash
sudo raspi-config
# Navigate to: Interface Options
# - Enable Camera
# - Enable I2C
# Then reboot
```

## 2. Clone và Cài Đặt ứng dụng

```bash
# Clone repository
git clone your-repo-url
cd edge_node

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate

# Cài đặt Python packages
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Cấu Hình Firebase

### 3.1 Tạo Firebase Project (nếu chưa có)
1. Truy cập https://console.firebase.google.com/
2. Tạo project mới
3. Tạo Realtime Database
4. Tạo Service Account (Project Settings → Service Accounts)
5. Download JSON key file

### 3.2 Cấu Hình Local
```bash
# Copy template
cp config/firebase-credentials.example.json config/firebase-credentials.json

# Edit với credentials của bạn
nano config/firebase-credentials.json
```

## 4. Cấu Hình MQTT (Optional)

Nếu sử dụng MQTT, cấu hình broker:

```bash
# Edit config/config.py
nano config/config.py
```

Thay đổi:
- `MQTT_BROKER`: địa chỉ broker
- `MQTT_PORT`: port (default 1883)
- Credentials nếu cần

## 5. Kiểm Tra Phần Cứng

### 5.1 Kiểm Tra Camera
```bash
# Pi 4 or newer
libcamera-hello -t 5

# Or
python3 -c "from picamera2 import Picamera2; print('Camera OK')"
```

### 5.2 Kiểm Tra I2C (LCD)
```bash
i2cdetect -y 1
# Tìm địa chỉ 0x27 trong output
```

### 5.3 Kiểm Tra GPIO
```bash
python3 -c "import RPi.GPIO; print('GPIO OK')"
```

## 6. Download Model File

Download `best_square_ocr_pro.pth` và đặt vào thư mục `models/`:

```bash
# Nếu có URL download
wget <model-url> -O models/best_square_ocr_pro.pth

# Hoặc sao chép file từ máy khác
```

## 7. Chạy ứng dụng

### 7.1 Test chạy

```bash
# Activate virtual environment
source venv/bin/activate

# Chạy main app
python3 src/main.py

# Hoặc debug mode
python3 src/main.py --debug
```

### 7.2 Systemd Service (Optional - Auto start)

Tạo file service:
```bash
sudo nano /etc/systemd/system/edge-ocr.service
```

Nội dung:
```ini
[Unit]
Description=Edge Node OCR System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/edge_node
Environment="PATH=/home/pi/edge_node/venv/bin"
ExecStart=/home/pi/edge_node/venv/bin/python3 /home/pi/edge_node/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable edge-ocr.service
sudo systemctl start edge-ocr.service

# Check status
sudo systemctl status edge-ocr.service
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'RPi'"
```bash
# Chỉ có thể cài trên Raspberry Pi thật
# Để phát triển trên máy khác, install mock version:
pip install fake-rpi
```

### "Camera not found"
```bash
# Kiểm tra kết nối physical
# Chạy: raspi-config → Interface Options → Camera
# Reboot
```

### "I2C Address not found"
```bash
# Khi chạy i2cdetect -y 1
# Check wiring
# Thay đổi address trong config/config.py từ 0x27 thành address tìm được
```

### Firebase connection error
```bash
# Kiểm tra JSON file
# Kiểm tra internet
# Kiểm tra Firebase rules (cho phép read/write)
```

## Notes

- Chạy dưới user `pi` để tránh permission issues với GPIO
- Giữ credentials.json an toàn, không commit lên git
- Theo dõi logs: `tail -f /var/log/edge-ocr.log`
