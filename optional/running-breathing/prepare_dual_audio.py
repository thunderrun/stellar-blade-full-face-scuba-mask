"""Prepare supplied PCM recordings, or verify the distributed prepared loops."""
import argparse
import hashlib
import json
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_pcm(path):
    with wave.open(str(path), "rb") as sound:
        if sound.getsampwidth() != 2 or sound.getcomptype() != "NONE":
            raise ValueError(f"Expected uncompressed 16-bit PCM WAV: {path}")
        channels, rate, frames = sound.getnchannels(), sound.getframerate(), sound.getnframes()
        pcm = sound.readframes(frames)
    if channels < 1 or rate < 1 or frames < 1 or len(pcm) != frames * channels * 2:
        raise ValueError(f"Incomplete or empty PCM WAV: {path}")
    return channels, rate, frames, pcm


def verify_loop(path):
    channels, rate, frames, pcm = read_pcm(path)
    frame_bytes = channels * 2
    first = struct.unpack("<" + "h" * channels, pcm[:frame_bytes])
    last = struct.unpack("<" + "h" * channels, pcm[-frame_bytes:])
    return {
        "processed_duration_seconds": frames / rate,
        "sample_rate": rate,
        "channels": channels,
        "bits": 16,
        "output": str(path.resolve()),
        "output_sha256": sha(path),
        "maximum_loop_boundary_jump": max(abs(a - b) for a, b in zip(last, first)) / 32768,
        "passed": True,
    }


def prepare(source, output):
    # Passing a generated loop as its own source must never rewrite the input.
    if source.resolve() == output.resolve():
        raise ValueError("Input and output are the same file; omit that source flag to verify the prepared loop.")
    import numpy as np

    before = sha(source)
    channels, rate, frames, raw = read_pcm(source)
    data = np.frombuffer(raw, dtype="<i2").reshape(-1, channels).astype(np.float64) / 32768
    crossfade = round(rate * 0.15)
    if crossfade < 1 or len(data) <= 2 * crossfade:
        raise ValueError(f"Recording is too short for a 0.15-second loop seam: {source}")
    weight = np.linspace(0, 1, crossfade, endpoint=False)[:, None]
    seam = data[-crossfade:] * (1 - weight) + data[:crossfade] * weight
    processed = np.concatenate([seam, data[crossfade:-crossfade]], axis=0)
    peak = float(np.max(np.abs(processed)))
    gain = min(1.0, 0.98 / peak) if peak else 1.0
    pcm = np.round(np.clip(processed * gain, -1, 0.999969) * 32768).astype("<i2")
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as sound:
        sound.setnchannels(channels)
        sound.setsampwidth(2)
        sound.setframerate(rate)
        sound.writeframes(pcm.tobytes())
    if sha(source) != before:
        raise RuntimeError(f"Source changed during preparation: {source}")
    return {
        "input_mode": "original-recording",
        "source": str(source.resolve()),
        "source_sha256": before,
        "source_unchanged": True,
        "source_duration_seconds": frames / rate,
        "crossfade_seconds": crossfade / rate,
        "applied_gain": gain,
        **verify_loop(output),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="Original running recording (#3); requires NumPy.")
    parser.add_argument("--walk", type=Path, help="Original walking/armed-idle recording (#2); requires NumPy.")
    parser.add_argument("--report", type=Path, default=ROOT / "checks/audio-preparation.json")
    args = parser.parse_args()
    sounds = {}
    for mode, source in (("run", args.run), ("walk", args.walk)):
        output = ROOT / f"source/audio/{mode}_breathing_loop.wav"
        if source is not None:
            sounds[mode] = prepare(source, output)
        else:
            if not output.is_file():
                parser.error(f"Missing prepared {mode} loop: {output}. Supply --{mode} with an original recording.")
            # A prepared loop's original recording cannot be verified from PCM.
            sounds[mode] = {
                "input_mode": "prepared-loop",
                "source": None,
                "source_sha256": None,
                "source_unchanged": None,
                "source_duration_seconds": None,
                "crossfade_seconds": None,
                "applied_gain": None,
                **verify_loop(output),
            }
    report = {"passed": True, "sounds": sounds}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
