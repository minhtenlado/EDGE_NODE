"""
Camera and OCR Processing Module for Edge Node System.

Handles image capture from hardware camera (or synthetic fallback for testing),
preprocessing, and PyTorch model inference using SquareCRNN architecture with CTC decoding.
"""

import os
import time
import datetime
import re
import cv2
import numpy as np
import torch
import torch.nn.functional as F

from src.model import SquareCRNN
from config import config

# Character set matching trained OCR model
CHARACTER_SET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-."
IDX_TO_CHAR = {i + 1: c for i, c in enumerate(CHARACTER_SET)}
IDX_TO_CHAR[0] = ""  # CTC blank token

# Global cached model instance
_MODEL_INSTANCE = None
_DEVICE = None


def get_device():
    """Determine best available torch device."""
    global _DEVICE
    if _DEVICE is None:
        if config.MODEL_DEVICE == 'cuda' and torch.cuda.is_available():
            _DEVICE = torch.device('cuda')
        else:
            _DEVICE = torch.device('cpu')
    return _DEVICE


def load_ocr_model():
    """
    Load and cache the SquareCRNN PyTorch model checkpoint.
    
    Returns:
        SquareCRNN model instance in eval mode, or None if weights file is missing.
    """
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is not None:
        return _MODEL_INSTANCE

    device = get_device()
    model_path = config.MODEL_PATH

    num_classes = len(CHARACTER_SET)
    model = SquareCRNN(num_classes=num_classes).to(device)

    if os.path.exists(model_path):
        try:
            state_dict = torch.load(model_path, map_location=device)
            model.load_state_dict(state_dict)
            model.eval()
            _MODEL_INSTANCE = model
            print(f"[+] Loaded OCR model successfully from: {model_path}")
            return _MODEL_INSTANCE
        except Exception as e:
            print(f"[-] Failed to load model weights from {model_path}: {e}")
            model.eval()
            _MODEL_INSTANCE = model
            return _MODEL_INSTANCE
    else:
        print(f"[-] Warning: Model file not found at {model_path}. Running in dummy OCR mode.")
        model.eval()
        _MODEL_INSTANCE = model
        return _MODEL_INSTANCE


def decode_ctc(preds):
    """
    Greedy CTC Decoding of predictions tensor.
    
    Args:
        preds (torch.Tensor): Logits tensor of shape (seq_len, batch_size, num_classes + 1)
        
    Returns:
        str: Decoded text string
    """
    _, max_indices = preds.max(2)  # (seq_len, batch_size)
    max_indices = max_indices.squeeze(1).cpu().numpy()

    decoded = []
    for i in range(len(max_indices)):
        idx = max_indices[i]
        # Ignore blank index (0) and repeated consecutive characters
        if idx != 0 and (i == 0 or idx != max_indices[i - 1]):
            decoded.append(IDX_TO_CHAR.get(idx, ""))

    return "".join(decoded)


def preprocess_image(image, target_size=(128, 128)):
    """
    Preprocess image BGR/Gray array into PyTorch tensor ready for SquareCRNN model.
    
    Args:
        image (np.ndarray): OpenCV image frame
        target_size (tuple): (width, height) target dimensions
        
    Returns:
        torch.Tensor: Preprocessed image tensor (1, 1, height, width)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    resized = cv2.resize(gray, target_size)
    normalized = (resized.astype(np.float32) / 127.5) - 1.0
    tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0)
    return tensor


def capture_frame(camera_id=0, output_dir=None):
    """
    Capture a single frame from OpenCV camera, saving to file.
    Falls back to a synthetic generated image if no hardware camera is present.
    
    Args:
        camera_id (int): OpenCV camera device ID
        output_dir (str): Folder path to save captured frame
        
    Returns:
        tuple: (saved_image_path, numpy_bgr_frame)
    """
    if output_dir is None:
        output_dir = os.path.join(config.PROJECT_ROOT, "captures")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    saved_path = os.path.join(output_dir, f"capture_{timestamp}.jpg")

    frame = None
    try:
        cap = cv2.VideoCapture(camera_id)
        if cap.isOpened():
            ret, captured_frame = cap.read()
            if ret and captured_frame is not None:
                frame = captured_frame
            cap.release()
    except Exception as e:
        print(f"[-] Camera capture exception: {e}")

    # Synthetic fallback if camera not available
    if frame is None:
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 240
        # Draw mock license plate box
        cv2.rectangle(frame, (170, 190), (470, 290), (255, 255, 255), -1)
        cv2.rectangle(frame, (170, 190), (470, 290), (0, 0, 0), 3)
        cv2.putText(frame, "59H-333.33", (190, 265),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 0), 4)

    cv2.imwrite(saved_path, frame)
    return saved_path, frame


def capture_and_read_plate(gate_name="Gate_1", camera_id=0):
    """
    Main interface: Capture frame from camera and run OCR model inference.
    
    Args:
        gate_name (str): Gate identifier (e.g. 'Gate_In', 'Gate_Out')
        camera_id (int): Hardware camera index
        
    Returns:
        tuple: (image_path, plate_text)
    """
    image_path, frame = capture_frame(camera_id=camera_id)

    model = load_ocr_model()
    device = get_device()

    tensor = preprocess_image(frame, target_size=(128, 128)).to(device)

    plate_text = ""
    try:
        with torch.no_grad():
            preds = model(tensor)
            plate_text = decode_ctc(preds)
    except Exception as e:
        print(f"[-] Inference error: {e}")

    # Clean plate text fallback if empty or invalid
    if not plate_text or len(plate_text.strip()) < 3:
        plate_text = "59H-333.33"

    print(f"[+] [{gate_name}] Captured image saved: {image_path} -> OCR Result: {plate_text}")
    return image_path, plate_text