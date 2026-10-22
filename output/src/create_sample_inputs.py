"""Generate sample customer audio inputs for batch evaluation testing."""
import os
import wave
import struct
import math
from pathlib import Path

SAMPLE_DIR = Path("sample_inputs")
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

test_clips = [
    {
        "name": "clip_01_greeting.wav",
        "text": "Hello, mujhe order ke baare mein help chahiye."
    },
    {
        "name": "clip_02_order_id.wav",
        "text": "Order number hai 8978 2837."
    },
    {
        "name": "clip_03_verification.wav",
        "text": "Last four digits 4533 hain."
    },
    {
        "name": "clip_04_refund_query.wav",
        "text": "Aur refund kitne din mein aayega?"
    },
    {
        "name": "clip_05_unsupported.wav",
        "text": "Can I schedule a delivery at midnight?"
    }
]

def make_tone_wav(filename: Path, duration: float = 2.0, freq: float = 440.0):
    sample_rate = 16000
    total_samples = int(sample_rate * duration)
    with wave.open(str(filename), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            sample = int(0.3 * math.sin(2.0 * math.pi * freq * t) * 32767.0)
            data.extend(struct.pack('<h', sample))
        wf.writeframes(data)

print(f"Creating sample test audio clips in {SAMPLE_DIR.resolve()}...")
for idx, clip in enumerate(test_clips, 1):
    wav_path = SAMPLE_DIR / clip["name"]
    txt_path = SAMPLE_DIR / (Path(clip["name"]).stem + ".txt")
    make_tone_wav(wav_path, duration=2.5, freq=300.0 + idx * 70.0)
    txt_path.write_text(clip["text"], encoding="utf-8")
    print(f"Created: {wav_path.name} with transcript: '{clip['text']}'")

print("Done generating sample inputs.")
