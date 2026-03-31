import paho.mqtt.client as mqtt
import json
import firebase_admin
from firebase_admin import credentials, db
import datetime
import base64
import os
import time
import threading
import math
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD
import psutil  
import re

# IMPORT THƯ VIỆN CAMERA TỪ FILE camera_ocr.py
try:
    import camera_ocr
except ImportError:
    print("[-] Cảnh báo: Không tìm thấy camera_ocr.py!")

# ==========================================
# 1. CẤU HÌNH PHẦN CỨNG (SERVO & LCD)
# ==========================================
try:
    lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8)
    lcd_lock = threading.Lock()
except Exception as e:
    print(f"[-] Lỗi LCD I2C: {e}")
    lcd = None

SERVO_IN_PIN = 20  
SERVO_OUT_PIN = 21 

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SERVO_IN_PIN, GPIO.OUT)
GPIO.setup(SERVO_OUT_PIN, GPIO.OUT)

pwm_in = GPIO.PWM(SERVO_IN_PIN, 50)
pwm_out = GPIO.PWM(SERVO_OUT_PIN, 50)
pwm_in.start(0)
pwm_out.start(0)

# ==========================================
# 2. CẤU HÌNH FIREBASE
# ==========================================
# Đảm bảo đường dẫn file JSON đúng với máy của bạn
CRED_PATH = "/home/vando/Documents/test1/test-50f9b-firebase-adminsdk-fbsvc-5a694d09eb.json"
AVAILABLE_SLOTS = 3 
CONFIG_PRICE_PER_HOUR = 20000

try:
    cred = credentials.Certificate(CRED_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://test-50f9b-default-rtdb.asia-southeast1.firebasedatabase.app'
        })
    print("[+] Khởi tạo Firebase thành công!")
    
    price = db.reference('config/pricePerHour').get()
    if price: CONFIG_PRICE_PER_HOUR = int(price)
except Exception as e:
    print(f"[-] Lỗi Firebase: {e}")

# ==========================================
# 3. THUẬT TOÁN CHUẨN HÓA VÀ ĐIỀU KHIỂN
# ==========================================
def normalize_plate(plate_str):
    """Lược bỏ mọi ký tự thừa (-, ., khoảng trắng), chỉ giữ lại chữ và số viết hoa"""
    if not plate_str: return ""
    return re.sub(r'[^A-Z0-9]', '', str(plate_str).upper())

def display_lcd(line1, line2):
    if lcd is None: return
    with lcd_lock:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(str(line1).center(16))
        lcd.cursor_pos = (1, 0)
        lcd.write_string(str(line2).center(16))

def update_standby_screen():
    global AVAILABLE_SLOTS
    if AVAILABLE_SLOTS <= 0:
        display_lcd("BAI DA DAY", "QUAY LAI SAU")
    else:
        display_lcd("BAI DO XE IOT", f"CON TRONG: {AVAILABLE_SLOTS} CHO")

def control_gate(pwm_channel, action):
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
        pass

# ==========================================
# 4. LUỒNG XỬ LÝ: XE VÀO & XE RA (TỰ ĐỘNG ĐỒNG BỘ)
# ==========================================
def process_car_in(gate_name):
    global AVAILABLE_SLOTS
    print(f"\n>>> [SỰ KIỆN] Xe tiến vào tại {gate_name}")
    
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

    print(f"[+] Nhận diện (VÀO): {plate_text}")
    clean_ocr_plate = normalize_plate(plate_text) 
    
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        base64_image_data = f"data:image/jpeg;base64,{encoded_string}"

        matched_uid = "Guest"
        display_name = "Khách vãng lai"
        
        users_ref = db.reference('users').get()
        if users_ref and isinstance(users_ref, dict):
            for uid, user_info in users_ref.items():
                if isinstance(user_info, dict):
                    reg_list = []
                    if 'registeredPlates' in user_info:
                        rp = user_info['registeredPlates']
                        if isinstance(rp, dict): reg_list.extend(rp.values())
                        elif isinstance(rp, list): reg_list.extend(rp)
                        else: reg_list.append(str(rp))
                    if 'plate' in user_info:
                        reg_list.append(user_info['plate'])
                        
                    clean_regs = [normalize_plate(p) for p in reg_list]
                    if clean_ocr_plate in clean_regs:
                        matched_uid = uid
                        display_name = user_info.get('fullName', user_info.get('name', 'Khách hàng AIoT'))
                        print(f"[+] Đã tìm thấy chủ xe: {display_name} (UID: {uid})")
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
        
        db.reference('parkingLogs').push(log_data)
        display_lcd("XIN CHAO", plate_text)
        control_gate(pwm_in, "open")
        time.sleep(4) 
        control_gate(pwm_in, "close")
        update_standby_screen() 

    except Exception as e:
        print(f"[-] Lỗi: {e}")

def process_car_out(gate_name):
    print(f"\n>>> [SỰ KIỆN] Xe tiến ra tại {gate_name}")
    
    image_path, plate_text = camera_ocr.capture_and_read_plate(gate_name, 2)

    if not plate_text:
        display_lcd("KHONG NHAN DIEN", "VUI LONG THU LAI")
        time.sleep(3)
        update_standby_screen()
        return

    print(f"[+] Nhận diện (RA): {plate_text}")
    clean_ocr_out = normalize_plate(plate_text)
    
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
                    except:
                        time_in = datetime.datetime.now()
                        
                    duration_hours = (datetime.datetime.now() - time_in).total_seconds() / 3600.0
                    fee = math.ceil(duration_hours) * CONFIG_PRICE_PER_HOUR 
                    if fee == 0: fee = CONFIG_PRICE_PER_HOUR 

                    uid = log_data.get('matchedUid', 'Guest')
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # KIỂM TRA AUTO-PAY
                    if uid != "Guest":
                        user_ref = db.reference(f'users/{uid}')
                        balance = user_ref.child('balance').get()
                        if balance is None: balance = 0
                        balance = int(balance)

                        if balance >= fee:
                            # 1. Trừ tiền ví
                            new_balance = balance - fee
                            user_ref.child('balance').set(new_balance)

                            # 2. Tạo lịch sử giao dịch
                            trans_data = {
                                "fee": -fee,
                                "plate": f"Thu phí tự động: {plate_text}",
                                "timeIn": int(time.time() * 1000),
                                "status": "Thành công"
                            }
                            db.reference(f'transactions/{uid}').push(trans_data)

                            # 3. Cập nhật Firebase và Mở cổng ngay lập tức
                            logs_ref.child(key).update({
                                "fee": fee,
                                "gateOut": gate_name,
                                "exitTime": current_time,
                                "isPaid": True,
                                "status": "Completed"
                            })

                            print(f"[$$$] TỰ ĐỘNG THANH TOÁN THÀNH CÔNG CHO TÀI KHOẢN {uid} (-{fee} VND)")
                            display_lcd("THANH TOAN XONG", f"DA TRU: {fee} VND")
                            
                            control_gate(pwm_out, "open")
                            time.sleep(4)
                            control_gate(pwm_out, "close")
                            update_standby_screen()
                            found = True
                            break
                        else:
                            print(f"[-] Ví {uid} không đủ tiền ({balance} < {fee}). Yêu cầu quét mã...")
                            logs_ref.child(key).update({"fee": fee, "gateOut": gate_name})
                            display_lcd("SO DU KHONG DU", f"PHI: {fee} VND")
                            found = True
                            break
                    else:
                        logs_ref.child(key).update({"fee": fee, "gateOut": gate_name})
                        print(f"[-] Khách vãng lai. Yêu cầu thu thủ công: {fee} VND")
                        display_lcd("VUI LONG T.TOAN", f"PHI: {fee} VND")
                        found = True
                        break 
        
        if not found:
            display_lcd("LOI BIEN SO", "CHUA DANG KY VAO")
            time.sleep(3)
            update_standby_screen() 

    except Exception as e:
        print(f"[-] Lỗi: {e}")

# ==========================================
# 5. LISTENER: LẮNG NGHE THANH TOÁN QR (DỰ PHÒNG)
# ==========================================
def firebase_payment_listener(event):
    if event.path == '/': return 
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
            print(f"\n[$$$] XÁC NHẬN ĐÃ NHẬN TIỀN TỪ APP/WEB -> MỞ CỔNG!")
            display_lcd("THANH TOAN XONG", "TAM BIET QUY KHACH")
            control_gate(pwm_out, "open")
            time.sleep(4)
            control_gate(pwm_out, "close")
            update_standby_screen()
            db.reference(f'parkingLogs/{log_key}').update({"status": "Completed"})
    except Exception as e:
        pass

# ==========================================
# 6. ĐỒNG BỘ CHỖ TRỐNG VÀ GIÁM SÁT PI
# ==========================================
def update_slots_to_firebase(slots_data):
    global AVAILABLE_SLOTS
    try:
        empty_count = sum(1 for i in range(1, 4) if slots_data.get(f"slot_{i}"))
        AVAILABLE_SLOTS = empty_count 
        update_standby_screen()
        
        firebase_slots = {}
        for i in range(1, 4):
            status = "Empty" if slots_data.get(f"slot_{i}") else "Occupied"
            firebase_slots[f"slot_{i}"] = {
                "status": status, 
                "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        db.reference('slots').set(firebase_slots) 
    except Exception as e: pass

def monitor_pi_health():
    while True:
        try:
            temp_str = os.popen("vcgencmd measure_temp").readline()
            temp = float(temp_str.replace("temp=", "").replace("'C\n", "")) if temp_str else 0.0
            ram = psutil.virtual_memory()
            db.reference('SystemHealth').set({
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
                "ram_percent": ram.percent,
                "ram_used_mb": round(ram.used / (1024 * 1024), 2),
                "temperature_c": temp,
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception: pass
        time.sleep(15) 

# ==========================================
# 7. MQTT LẮNG NGHE ESP32
# ==========================================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Đã kết nối. Chờ xe vào/ra...")
        client.subscribe("parking/gate/status")
        client.subscribe("parking/slots/status")
        update_standby_screen()
    else:
        print(f"[MQTT] Lỗi kết nối: {rc}")

def on_message(client, userdata, msg):
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
            
    except Exception as e: pass

# ==========================================
# MAIN ENTRY POINT
# ==========================================
if __name__ == "__main__":
    control_gate(pwm_in, "close")
    control_gate(pwm_out, "close")

    threading.Thread(target=monitor_pi_health, daemon=True).start()
    db.reference('parkingLogs').listen(firebase_payment_listener)

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client() 
        
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"⏳ Hệ thống đang khởi động...")
    try:
        client.connect("127.0.0.1", 1883, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[!] Đã dừng chương trình.")
    finally:
        pwm_in.stop()
        pwm_out.stop()
        GPIO.cleanup()
        if lcd: lcd.clear()