import io
import numpy as np
import cv2
import qrcode
from qrcode.constants import ERROR_CORRECT_H

def generate_qr_png(data):
    img = qrcode.make(data, error_correction=ERROR_CORRECT_H)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def decode_qr(image_bytes):
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return None
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return data or None
