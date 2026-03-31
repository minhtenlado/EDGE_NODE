# Edge Node OCR System

Hệ thống nhận diện ký tự quang học (OCR) chạy trên Raspberry Pi với kết nối Firebase và MQTT cho ứng dụng IoT.

## Mô tả Dự án

Ứng dụng này chạy trên Raspberry Pi để:
- Nhận ảnh từ camera
- Sử dụng deep learning model để nhận diện ký tự (OCR)
- Gửi dữ liệu qua MQTT
- Lưu trữ dữ liệu lên Firebase
- Điều khiển servo motor và LCD cho phản hồi người dùng

## Yêu cầu Hệ thống

- Raspberry Pi (4 hoặc 5)
- Python 3.8+
- Camera module hoặc USB camera
- LCD 16x2 với i2c expander PCF8574
- 2 Servo motors (GPIO pins 20, 21)
- Kết nối internet

## Cài đặt

### 1. Clone dự án
```bash
git clone <repository-url>
cd edge_node
```

### 2. Tạo virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình Firebase
```bash
# Sao chép file template
cp config/firebase-credentials.example.json config/firebase-credentials.json

# Chỉnh sửa với credentials thực của bạn
nano config/firebase-credentials.json
```

### 5. Cấu hình ứng dụng
Chỉnh sửa các thông số trong `config/config.py`:
- Firebase credentials path
- MQTT broker settings
- GPIO pins
- Model path

## Cấu Trúc Dự Án

```
edge_node/
├── src/                          # Source code
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── model.py                 # Model definition
│   └── camera_ocr.py            # Camera & OCR processing
├── models/                       # Trained models
│   └── .gitkeep
├── config/                       # Configuration
│   ├── config.py                # Configuration settings
│   └── firebase-credentials.example.json
├── docs/                         # Documentation
│   ├── SETUP.md                 # Setup guide
│   └── API.md                   # API documentation
├── requirements.txt              # Python dependencies
├── .gitignore                   # Git ignore file
└── README.md                    # This file
```

## Sử dụng

```bash
# Chạy ứng dụng chính
python src/main.py

# Chạy với verbose logging
python src/main.py --debug
```

## Các Module

### `model.py`
Định nghĩa ResNet-based OCR model với attention mechanism đối với nhận diện ký tự.

### `camera_ocr.py`
Xử lý camera input, preprocessing ảnh, và gọi model để nhận diện.

### `main.py`
Chương trình chính điều phối:
- Quản lý kết nối Firebase
- Xử lý MQTT messages
- Điều khiển GPIO (servo, LCD)
- Xử lý camera input và inference

## Tính Năng

- ✅ Real-time OCR từ camera
- ✅ Deep learning model (PyTorch)
- ✅ Firebase integration
- ✅ MQTT communication
- ✅ LCD display feedback
- ✅ Hardware control (Servo motors)
- ✅ System monitoring

## Troubleshooting

### Lỗi LCD I2C
```
[-] Lỗi LCD I2C: ...
```
- Kiểm tra địa chỉ I2C: `i2cdetect -y 1`
- Kiểm tra kết nối dây
- Thay đổi address trong config nếu cần

### Lỗi Firebase
- Đảm bảo file credentials.json đúng
- Kiểm tra kết nối internet
- Xem logs để chi tiết

### Lỗi Camera
- Kiểm tra kết nối camera
- Test với: `libcamera-hello` (Pi 4+) hoặc `raspistill`

## Dependencies

Xem [requirements.txt](requirements.txt) để danh sách đầy đủ.

## License

MIT License

## Tác giả

Your Name / Your Organization

## Hỗ Trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra phần Troubleshooting
2. Xem logs chi tiết
3. Mở GitHub Issues

## Changelog

### v1.0.0
- Initial release
- OCR functionality
- Firebase integration
- MQTT support
