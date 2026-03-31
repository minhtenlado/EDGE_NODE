"""
Configuration settings for Edge Node OCR System
"""
import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# ==========================================
# FIREBASE CONFIGURATION
# ==========================================
FIREBASE_CREDENTIALS_PATH = os.getenv(
    'FIREBASE_CREDENTIALS_PATH',
    str(PROJECT_ROOT / 'config' / 'firebase-credentials.json')
)

# ==========================================
# MQTT CONFIGURATION
# ==========================================
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')

# MQTT Topics
MQTT_TOPIC_OCR_INPUT = 'edge/ocr/input'
MQTT_TOPIC_OCR_OUTPUT = 'edge/ocr/output'
MQTT_TOPIC_STATUS = 'edge/status'

# ==========================================
# GPIO CONFIGURATION (Raspberry Pi)
# ==========================================
GPIO_MODE = 'BCM'  # Broadcom SOC channel numbering

# Servo Motors
SERVO_IN_PIN = 20   # Input servo GPIO pin
SERVO_OUT_PIN = 21  # Output servo GPIO pin
SERVO_PWM_FREQ = 50  # PWM frequency in Hz

# ==========================================
# LCD CONFIGURATION
# ==========================================
LCD_I2C_EXPANDER = 'PCF8574'
LCD_I2C_ADDRESS = 0x27
LCD_I2C_PORT = 1
LCD_COLS = 16
LCD_ROWS = 2
LCD_DOTSIZE = 8

# ==========================================
# MODEL CONFIGURATION
# ==========================================
MODEL_PATH = str(PROJECT_ROOT / 'models' / 'best_square_ocr_pro.pth')
MODEL_DEVICE = 'cuda'  # 'cuda' or 'cpu'
MODEL_INPUT_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 0.7

# ==========================================
# APPLICATION CONFIGURATION
# ==========================================
AVAILABLE_SLOTS = 3
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
DEBUG_MODE = False

# ==========================================
# CAMERA CONFIGURATION
# ==========================================
CAMERA_ID = 0  # Default camera
CAMERA_RESOLUTION = (640, 480)
CAMERA_FPS = 30

# ==========================================
# TIMING CONFIGURATION
# ==========================================
INFERENCE_TIMEOUT = 30  # seconds
MQTT_RECONNECT_INTERVAL = 5  # seconds
FIREBASE_SYNC_INTERVAL = 10  # seconds
