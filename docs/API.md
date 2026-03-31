# API Documentation

## MQTT Topics

### Input Topics

#### `edge/ocr/input`
Gửi hình ảnh hoặc lệnh OCR

Payload:
```json
{
  "image": "base64_encoded_image",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "unique_request_id"
}
```

### Output Topics

#### `edge/ocr/output`
Kết quả nhận diện OCR

Payload:
```json
{
  "request_id": "unique_request_id",
  "text": "Recognized text here",
  "confidence": 0.95,
  "processing_time_ms": 245,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### `edge/status`
Trạng thái hệ thống

Payload:
```json
{
  "status": "running",
  "uptime_seconds": 3600,
  "temperature": 45.5,
  "memory_usage_percent": 45.2,
  "last_ocr_time_ms": 245,
  "total_ocr_count": 1050,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Firebase Database Structure

```
database_root/
├── devices/
│   └── {device_id}/
│       ├── status: "online/offline"
│       ├── last_seen: "timestamp"
│       ├── config: {...}
│       └── ocr_history/
│           └── {ocr_id}/
│               ├── image_url: "URL"
│               ├── result_text: "text"
│               ├── confidence: 0.95
│               └── timestamp: "timestamp"
└── ocr_results/
    └── {timestamp}/
        ├── device_id: "id"
        ├── text: "recognized text"
        └── confidence: 0.95
```

## Model Configuration

### Input
- Image size: 224x224 pixels
- Format: RGB
- Normalization: ImageNet standard

### Output
- Predicted text: String
- Confidence score: Float 0.0-1.0
- Processing time: milliseconds

## GPIO Interface

### Pin Configuration

```python
SERVO_IN_PIN = 20   # Input servo control
SERVO_OUT_PIN = 21  # Output servo control
PWM_FREQUENCY = 50  # Hz
```

### Servo Control

```python
pwm_in.ChangeDutyCycle(5)   # 0-10 duty cycle
pwm_out.ChangeDutyCycle(5)
```

## LCD Display Control

### I2C Configuration
- Expander: PCF8574
- Address: 0x27
- Rows: 2, Cols: 16

### Display Updates

```python
from RPLCD.i2c import CharLCD

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    port=1,
    cols=16,
    rows=2
)

lcd.write_string("Processing...")
```

## Logging

### Log Levels
- DEBUG: 10
- INFO: 20
- WARNING: 30
- ERROR: 40

### Log Format
```
[TIMESTAMP] [LEVEL] [MODULE] Message
2024-01-01 12:00:00,123 INFO main OCR processing started
```

## Error Codes

| Code | Message | Solution |
|------|---------|----------|
| E001 | Camera not found | Check camera connection |
| E002 | Model file not found | Download model to models/ folder |
| E003 | Firebase auth failed | Check credentials.json |
| E004 | MQTT connection failed | Check broker address/port |
| E005 | GPIO initialization failed | Run as sudo or correct pins |
| E006 | I2C device not found | Check LCD wiring and address |

## Rate Limiting

- OCR requests: max 10 per minute per device
- Status updates: every 10 seconds
- Firebase sync: every 10 seconds

## Performance Metrics

- Average OCR time: 200-300ms
- Confidence threshold: 0.7
- Memory usage: ~500MB
- CPU usage: 60-80% during processing
