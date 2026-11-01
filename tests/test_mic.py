"""
Live microphone diagnostic tool for Zenith
Tests all connected microphones and displays real-time input levels.
"""
import sounddevice as sd
import numpy as np
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

print("=" * 60)
print("🎙️ Zenith Microphone Diagnostic Test")
print("=" * 60)

devices = sd.query_devices()
default_in, default_out = sd.default.device
print(f"[*] Windows Default Input Device Index: {default_in} ({devices[default_in]['name']})")
print(f"[*] Windows Default Output Device Index: {default_out} ({devices[default_out]['name']})")
print("\nScanning available input devices:")

input_devices = []
for idx, d in enumerate(devices):
    if d['max_input_channels'] > 0 and d['hostapi'] in (0, 1):  # MME or DirectSound
        input_devices.append((idx, d['name']))
        marker = " <-- DEFAULT" if idx == default_in else ""
        print(f"  [{idx}] {d['name']}{marker}")

print("\n" + "=" * 60)
print("Listening for 5 seconds... PLEASE SPEAK INTO YOUR MIC NOW!")
print("=" * 60)

for idx, name in input_devices:
    try:
        data = sd.rec(int(24000 * 2), samplerate=24000, channels=1, dtype='int16', device=idx)
        sd.wait()
        peak = int(np.max(np.abs(data)))
        rms = float(np.sqrt(np.mean(data.astype(float)**2)))
        
        bars = min(50, int(peak / 200))
        bar_str = "█" * bars
        
        status = "🟢 ACTIVE / HEARD YOU!" if peak > 500 else "🔴 SILENT / MUTED (No signal)"
        print(f"\nDevice [{idx}] {name}:")
        print(f"  Peak Amplitude: {peak} | RMS: {rms:.1f}")
        print(f"  Meter: [{bar_str:<50}] {status}")
    except Exception as e:
        print(f"\nDevice [{idx}] {name}: Error {e}")

print("\n" + "=" * 60)
print("Diagnostic Complete.")
