# Quick Start Guide

## 1️⃣ Clone & Setup (5 minutes)

```bash
# Clone repository
git clone <your-repo-url>
cd edge_node

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

## 2️⃣ Configuration (2 minutes)

```bash
# Setup Firebase credentials
cp config/firebase-credentials.example.json config/firebase-credentials.json
# Edit with your actual credentials
nano config/firebase-credentials.json

# (Optional) Setup environment variables
cp .env.example .env
nano .env
```

## 3️⃣ Verify Hardware (5 minutes on Raspberry Pi)

```bash
# Check camera
libcamera-hello -t 5

# Check I2C LCD
i2cdetect -y 1

# Check GPIO
python3 -c "import RPi.GPIO; print('GPIO OK')"
```

## 4️⃣ Download Model (varies)

```bash
# Download best_square_ocr_pro.pth and place in models/ folder
wget <url> -O models/best_square_ocr_pro.pth
```

## 5️⃣ Run Application

```bash
# Regular mode
python3 src/main.py

# Debug mode
python3 src/main.py --debug
```

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| `ImportError: No module named 'RPi'` | Only works on Raspberry Pi |
| Camera not working | Enable Camera via `raspi-config` → Interface Options → Camera |
| I2C not found | Run `i2cdetect -y 1` to find address, update in config |
| Firebase auth error | Check credentials.json, check database rules |

## 📚 Further Reading

- [Full Setup Guide](docs/SETUP.md)
- [API Documentation](docs/API.md)
- [Contributing](CONTRIBUTING.md)

## 🆘 Help

If stuck:
1. Check `/docs/SETUP.md` for detailed instructions
2. Review application logs
3. Open an Issue on GitHub with error details

---

**Ready?** Start with: `python3 src/main.py`
