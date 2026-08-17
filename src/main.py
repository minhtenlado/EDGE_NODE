"""
Main Orchestration Module for Edge Node System.

Manages MQTT broker events from IoT microcontrollers (ESP32), Firebase Realtime Database
synchronization, GPIO hardware (Servos, LCD screen), system health metrics, and Edge AI OCR workflow.
"""

import os
import sys
import time
import json
import base64
import math
import re
import datetime
import threading
import argparse

import paho.mqtt.client as mqtt
import firebase_admin
from firebase_admin import credentials, db
import psutil

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import config
from src import camera_ocr

# ==========================================
# 1. HARDWARE HARDENING (GPIO & LCD FALLBACKS)
# ==========================================
GPIO_AVAILABLE = False
LCD_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(config.SERVO_IN_PIN, GPIO.OUT)
    GPIO.setup(config.SERVO_OUT_PIN, GPIO.OUT)
    pwm_in = GPIO.PWM(config.SERVO_IN_PIN, config.SERVO_PWM_FREQ)
    pwm_out = GPIO.PWM(config.SERVO_OUT_PIN, config.SERVO_PWM_FREQ)
    pwm_in.start(0)
    pwm_out.start(0)
    GPIO_AVAILABLE = True
    print("[+] GPIO initialized successfully.")
except Exception as e:
    print(f"[-] GPIO hardware unavailable (running mock mode): {e}")
    pwm_in, pwm_out = None, None

try:
    from RPLCD.i2c import CharLCD
    lcd = CharLCD(
        i2c_expander=config.LCD_I2C_EXPANDER,
        address=config.LCD_I2C_ADDRESS,
        port=config.LCD_I2C_PORT,
        cols=config.LCD_COLS,
        rows=config.LCD_ROWS,
        dotsize=config.LCD_DOTSIZE
    )
    lcd_lock = threading.Lock()
    LCD_AVAILABLE = True
    print("[+] I2C LCD display initialized successfully.")
except Exception as e:
    print(f"[-] I2C LCD hardware unavailable (console output mode): {e}")
    lcd = None
    lcd_lock = threading.Lock()

# ==========================================
# 2. STATE & FIREBASE INITIALIZATION
# ==========================================
AVAILABLE_SLOTS = config.AVAILABLE_SLOTS
CONFIG_PRICE_PER_HOUR = 20000

CRED_PATH = config.FIREBASE_CREDENTIALS_PATH

if os.path.exists(CRED_PATH):
    try:
        cred = credentials.Certificate(CRED_PATH)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://test-50f9b-default-rtdb.asia-southeast1.firebasedatabase.app'
            })
        print("[+] Firebase Realtime Database connected successfully!")

        price_ref = db.reference('config/pricePerHour').get()
        if price_ref:
            CONFIG_PRICE_PER_HOUR = int(price_ref)
    except Exception as e:
        print(f"[-] Firebase initialization error: {e}")
else:
    print(f"[-] Warning: Firebase credentials file not found at '{CRED_PATH}'. Running offline mock database mode.")


# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def normalize_plate(plate_str):
    """Clean license plate string by stripping symbols and keeping uppercase alphanumeric characters."""
    if not plate_str:
        return ""
    return re.sub(r'[^A-Z0-9]', '', str(plate_str).upper())


def display_lcd(line1, line2):
    """Write two-line status text to I2C LCD display or console fallback."""
    print(f"[LCD DISPLAY] | Line 1: {line1:<16} | Line 2: {line2:<16}")
    if lcd is None:
        return
    with lcd_lock:
        try:
            lcd.clear()
            lcd.cursor_pos = (0, 0)
            lcd.write_string(str(line1).center(16))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(str(line2).center(16))
        except Exception as e:
            print(f"[-] LCD write exception: {e}")


def update_standby_screen():
    """Update LCD screen with active available slots status."""
    global AVAILABLE_SLOTS
    if AVAILABLE_SLOTS <= 0:
        display_lcd("BAI DA DAY", "QUAY LAI SAU")
    else:
        display_lcd("BAI DO XE IOT", f"CON TRONG: {AVAILABLE_SLOTS} CHO")


def control_gate(pwm_channel, action):
    """Operate barrier servo motor gate open/close duty cycles."""
    print(f"[GATE CONTROL] Action: {action.upper()}")
    if not GPIO_AVAILABLE or pwm_channel is None:
        return
    try:
        if action == "open":
            pwm_channel.ChangeDutyCycle(7.5)
            time.sleep(0.5)
            pwm_channel.ChangeDutyCycle(0)
        elif action == "close":
            pwm_channel.ChangeDutyCycle(2.5)
            time.sleep(0.5)
            pwm_channel.ChangeDutyCycle(0)
    except Exception as e:
        print(f"[-] Gate control error: {e}")


# ==========================================
# 4. PARKING WORKFLOW: CAR IN & CAR OUT
# ==========================================
def process_car_in(gate_name):
    """Process incoming vehicle event: capture image, run OCR, query user, push log, open entry gate."""
    global AVAILABLE_SLOTS
    print(f"\n>>> [EVENT] Car entering at {gate_name}")

    if AVAILABLE_SLOTS <= 0:
        display_lcd("BAI DA DAY", "VUI LONG QUAY LAI")
        time.sleep(3)
        update_standby_screen()
        return

    image_path, plate_text = camera_ocr.capture_and_read_plate(gate_name, 0)

    if not image_path or not plate_text:
        display_lcd("KHONG NHAN DIEN", "VUI LONG THU LAI")
        time.sleep(3)
        update_standby_screen()
        return

    print(f"[+] Recognized Entry Plate: {plate_text}")
    clean_ocr_plate = normalize_plate(plate_text)

    try:
        base64_image_data = ""
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            base64_image_data = f"data:image/jpeg;base64,{encoded_string}"

        matched_uid = "Guest"
        display_name = "Khách vãng lai"

        if firebase_admin._apps:
            users_ref = db.reference('users').get()
            if users_ref and isinstance(users_ref, dict):
                for uid, user_info in users_ref.items():
                    if isinstance(user_info, dict):
                        reg_list = []
                        if 'registeredPlates' in user_info:
                            rp = user_info['registeredPlates']
                            if isinstance(rp, dict):
                                reg_list.extend(rp.values())
                            elif isinstance(rp, list):
                                reg_list.extend(rp)
                            else:
                                reg_list.append(str(rp))
                        if 'plate' in user_info:
                            reg_list.append(user_info['plate'])

                        clean_regs = [normalize_plate(p) for p in reg_list]
                        if clean_ocr_plate in clean_regs:
                            matched_uid = uid
                            display_name = user_info.get('fullName', user_info.get('name', 'Khách hàng AIoT'))
                            print(f"[+] Vehicle Owner Matched: {display_name} (UID: {uid})")
                            break

        log_data = {
            "plate": plate_text,
            "normalizedPlate": clean_ocr_plate,
            "imageBase64": base64_image_data,
            "entryTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Parked",
            "fee": 0,
            "matchedUid": matched_uid,
            "display_name": display_name,
            "gateIn": gate_name,
            "isPaid": False
        }

        if firebase_admin._apps:
            db.reference('parkingLogs').push(log_data)

        display_lcd("XIN CHAO", plate_text)
        control_gate(pwm_in, "open")
        time.sleep(4)
        control_gate(pwm_in, "close")
        update_standby_screen()

    except Exception as e:
        print(f"[-] process_car_in Error: {e}")


def process_car_out(gate_name):
    """Process exiting vehicle event: capture image, calculate fee, execute auto-payment, open exit gate."""
    print(f"\n>>> [EVENT] Car exiting at {gate_name}")

    image_path, plate_text = camera_ocr.capture_and_read_plate(gate_name, 2)

    if not plate_text:
        display_lcd("KHONG NHAN DIEN", "VUI LONG THU LAI")
        time.sleep(3)
        update_standby_screen()
        return

    print(f"[+] Recognized Exit Plate: {plate_text}")
    clean_ocr_out = normalize_plate(plate_text)

    if not firebase_admin._apps:
        display_lcd("THANH TOAN XONG", f"PLATE: {plate_text}")
        control_gate(pwm_out, "open")
        time.sleep(4)
        control_gate(pwm_out, "close")
        update_standby_screen()
        return

    try:
        logs_ref = db.reference('parkingLogs')
        matching_logs = logs_ref.order_by_child('normalizedPlate').equal_to(clean_ocr_out).get()

        if not matching_logs:
            active_logs = logs_ref.order_by_child('status').equal_to('Parked').get()
            if active_logs:
                for k, v in active_logs.items():
                    if normalize_plate(v.get('plate', '')) == clean_ocr_out:
                        matching_logs = {k: v}
                        break

        found = False
        if matching_logs:
            for key, log_data in matching_logs.items():
                status = log_data.get('status')

                if status in ['Left', 'Paid', 'Completed']:
                    display_lcd("DA THANH TOAN", "TAM BIET QUY KHACH")
                    logs_ref.child(key).update({"status": "Completed"})
                    control_gate(pwm_out, "open")
                    time.sleep(4)
                    control_gate(pwm_out, "close")
                    update_standby_screen()
                    found = True
                    break

                elif status == 'Parked':
                    time_in_str = log_data.get('entryTime', log_data.get('timeIn'))
                    try:
                        time_in = datetime.datetime.strptime(time_in_str, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        time_in = datetime.datetime.now()

                    duration_hours = (datetime.datetime.now() - time_in).total_seconds() / 3600.0
                    fee = math.ceil(duration_hours) * CONFIG_PRICE_PER_HOUR
                    if fee == 0:
                        fee = CONFIG_PRICE_PER_HOUR

                    uid = log_data.get('matchedUid', 'Guest')
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if uid != "Guest":
                        user_ref = db.reference(f'users/{uid}')
                        balance = user_ref.child('balance').get()
                        if balance is None:
                            balance = 0
                        balance = int(balance)

                        if balance >= fee:
                            new_balance = balance - fee
                            user_ref.child('balance').set(new_balance)

                            trans_data = {
                                "fee": -fee,
                                "plate": f"Thu phí tự động: {plate_text}",
                                "timeIn": int(time.time() * 1000),
                                "status": "Thành công"
                            }
                            db.reference(f'transactions/{uid}').push(trans_data)

                            logs_ref.child(key).update({
                                "fee": fee,
                                "gateOut": gate_name,
                                "exitTime": current_time,
                                "isPaid": True,
                                "status": "Completed"
                            })

                            print(f"[$$$] AUTO-PAYMENT SUCCESSFUL FOR USER {uid} (-{fee} VND)")
                            display_lcd("THANH TOAN XONG", f"DA TRU: {fee} VND")

                            control_gate(pwm_out, "open")
                            time.sleep(4)
                            control_gate(pwm_out, "close")
                            update_standby_screen()
                            found = True
                            break
                        else:
                            print(f"[-] Wallet balance insufficient ({balance} < {fee}). Prompt QR code payment.")
                            logs_ref.child(key).update({"fee": fee, "gateOut": gate_name})
                            display_lcd("SO DU KHONG DU", f"PHI: {fee} VND")
                            found = True
                            break
                    else:
                        logs_ref.child(key).update({"fee": fee, "gateOut": gate_name})
                        print(f"[-] Guest user. Manual payment required: {fee} VND")
                        display_lcd("VUI LONG T.TOAN", f"PHI: {fee} VND")
                        found = True
                        break

        if not found:
            display_lcd("LOI BIEN SO", "CHUA DANG KY VAO")
            time.sleep(3)
            update_standby_screen()

    except Exception as e:
        print(f"[-] process_car_out Error: {e}")


# ==========================================
# 5. FIREBASE & SYSTEM HEALTH MONITORING
# ==========================================
def firebase_payment_listener(event):
    """Listen for mobile app payment status updates on Firebase database."""
    if event.path == '/':
        return
    try:
        data = event.data
        path = event.path
        should_open = False
        log_key = None

        if isinstance(data, dict):
            if data.get('status') == 'Left':
                should_open = True
                log_key = path.split('/')[1] if len(path.split('/')) > 1 else list(data.keys())[0]
        elif isinstance(data, str) and path.endswith('/status'):
            if data == 'Left':
                should_open = True
                log_key = path.split('/')[1]

        if should_open and log_key:
            print(f"\n[$$$] WEB/APP PAYMENT CONFIRMED -> OPENING EXIT GATE!")
            display_lcd("THANH TOAN XONG", "TAM BIET QUY KHACH")
            control_gate(pwm_out, "open")
            time.sleep(4)
            control_gate(pwm_out, "close")
            update_standby_screen()
            if firebase_admin._apps:
                db.reference(f'parkingLogs/{log_key}').update({"status": "Completed"})
    except Exception as e:
        print(f"[-] Payment listener error: {e}")


def update_slots_to_firebase(slots_data):
    """Synchronize parking slot ultrasonic sensor states from ESP32 to Firebase."""
    global AVAILABLE_SLOTS
    try:
        empty_count = sum(1 for i in range(1, 4) if slots_data.get(f"slot_{i}"))
        AVAILABLE_SLOTS = empty_count
        update_standby_screen()

        if firebase_admin._apps:
            firebase_slots = {}
            for i in range(1, 4):
                status = "Empty" if slots_data.get(f"slot_{i}") else "Occupied"
                firebase_slots[f"slot_{i}"] = {
                    "status": status,
                    "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            db.reference('slots').set(firebase_slots)
    except Exception as e:
        print(f"[-] Slots sync error: {e}")


def monitor_pi_health():
    """Periodically publish CPU, RAM, and SoC temperature telemetry to Firebase."""
    while True:
        try:
            temp = 0.0
            if hasattr(os, 'popen'):
                temp_str = os.popen("vcgencmd measure_temp 2>/dev/null").readline()
                if temp_str and "temp=" in temp_str:
                    temp = float(temp_str.replace("temp=", "").replace("'C\n", "").strip())

            ram = psutil.virtual_memory()
            health_data = {
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
                "ram_percent": ram.percent,
                "ram_used_mb": round(ram.used / (1024 * 1024), 2),
                "temperature_c": temp,
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            if firebase_admin._apps:
                db.reference('SystemHealth').set(health_data)
        except Exception:
            pass
        time.sleep(15)


# ==========================================
# 6. MQTT SUBSCRIBER CALLBACKS
# ==========================================
def on_connect(client, userdata, flags, rc):
    """Callback when connecting to MQTT Broker."""
    if rc == 0:
        print(f"[MQTT] Connected successfully to broker. Listening for gate/slot events...")
        client.subscribe("parking/gate/status")
        client.subscribe("parking/slots/status")
        update_standby_screen()
    else:
        print(f"[MQTT] Connection failed with response code: {rc}")


def on_message(client, userdata, msg):
    """Callback when receiving MQTT messages from ESP32 sensors."""
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        if msg.topic == "parking/gate/status":
            action = data.get("action")
            gate = data.get("gate", "Gate_1")

            if action == "car_in":
                threading.Thread(target=process_car_in, args=(gate,), daemon=True).start()
            elif action == "car_out":
                threading.Thread(target=process_car_out, args=(gate,), daemon=True).start()

        elif msg.topic == "parking/slots/status":
            threading.Thread(target=update_slots_to_firebase, args=(data,), daemon=True).start()

    except Exception as e:
        print(f"[-] MQTT message processing error: {e}")


# ==========================================
# MAIN ENTRYPOINT
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Edge Node OCR Parking System")
    parser.add_argument("--broker", type=str, default=config.MQTT_BROKER, help="MQTT Broker host")
    parser.add_argument("--port", type=int, default=config.MQTT_PORT, help="MQTT Broker port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    control_gate(pwm_in, "close")
    control_gate(pwm_out, "close")

    threading.Thread(target=monitor_pi_health, daemon=True).start()

    if firebase_admin._apps:
        try:
            db.reference('parkingLogs').listen(firebase_payment_listener)
        except Exception as e:
            print(f"[-] Firebase listener setup error: {e}")

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"⏳ Starting Edge Node system (Broker: {args.broker}:{args.port})...")
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[!] Application interrupted by user.")
    except Exception as e:
        print(f"[-] MQTT Client exception: {e}")
    finally:
        if GPIO_AVAILABLE and pwm_in and pwm_out:
            pwm_in.stop()
            pwm_out.stop()
            GPIO.cleanup()
        if lcd:
            try:
                lcd.clear()
            except Exception:
                pass


if __name__ == "__main__":
    main()