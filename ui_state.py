import socket
import logging
import json

current_custom_text = None

def set_text(text: str):
    global current_custom_text
    current_custom_text = text
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = f"custom:{text}"
        sock.sendto(payload.encode('utf-8'), ("127.0.0.1", 49152))
        sock.close()
        logging.info(f"[UI_STATE] Sent custom text via UDP: {text}")
    except Exception as e:
        logging.warning(f"[UI_STATE] Failed to send custom text: {e}")

def send_json(data: dict):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = json.dumps(data)
        sock.sendto(payload.encode('utf-8'), ("127.0.0.1", 49152))
        sock.close()
        logging.info(f"[UI_STATE] Sent JSON data via UDP: {data.get('type')}")
    except Exception as e:
        logging.warning(f"[UI_STATE] Failed to send JSON data: {e}")


