import os
import wave
import imageio_ffmpeg
import numpy as np
from google.cloud import storage

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
OUTPUT_DIR = "/config/.gemini/antigravity/brain/749a82c6-08df-4376-a5eb-84f300041b92"
INPUT_VIDEO = os.path.join(OUTPUT_DIR, "fitcoach_demo.webm")
LOFI_AUDIO = os.path.join(OUTPUT_DIR, "lofi_track.wav")
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "fitcoach_demo_lofi.mp4")
OUTPUT_WEBM = os.path.join(OUTPUT_DIR, "fitcoach_demo_lofi.webm")

STORAGE_BUCKET_NAME = "fitcoach-ai-media-qwiklabs-gcp-03-6fec44d0cd84"
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-6fec44d0cd84"


def generate_lofi_track(duration_sec=35.0, sample_rate=44100):
    """Synthesizes a warm, upbeat lo-fi background track with Rhodes chords, kick/snare beat, and vinyl crackle."""
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    
    bpm = 85.0
    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * 4

    # 1. Warm Rhodes / Electric Piano Chords (Cmaj7 -> Am7 -> Dm7 -> G7)
    chords = [
        [261.63, 329.63, 392.00, 493.88],  # Cmaj7
        [220.00, 261.63, 329.63, 392.00],  # Am7
        [293.66, 349.23, 440.00, 523.25],  # Dm7
        [196.00, 246.94, 293.66, 349.23],  # G7
    ]

    piano_signal = np.zeros(num_samples)
    for i, sample_t in enumerate(t):
        bar_idx = int(sample_t / bar_duration) % len(chords)
        chord_freqs = chords[bar_idx]
        bar_progress = (sample_t % bar_duration) / bar_duration
        
        # Soft decay envelope for each chord bar
        envelope = np.exp(-1.5 * bar_progress)
        tremolo = 1.0 + 0.08 * np.sin(2 * np.pi * 5.0 * sample_t)  # 5Hz lo-fi tremolo
        
        val = 0.0
        for freq in chord_freqs:
            # Fundamental + warm 2nd harmonic
            val += np.sin(2 * np.pi * freq * sample_t)
            val += 0.3 * np.sin(2 * np.pi * freq * 2.0 * sample_t)
            val += 0.1 * np.sin(2 * np.pi * freq * 3.0 * sample_t)
        
        piano_signal[i] = val * envelope * tremolo * 0.15

    # 2. Upbeat Lo-Fi Beat (Kick on 1 & 3, Snare/Clap on 2 & 4, Hi-Hats on 8ths)
    beat_signal = np.zeros(num_samples)
    for sample_i in range(num_samples):
        sample_t = t[sample_i]
        beat_num = (sample_t % bar_duration) / beat_duration  # 0.0 to 4.0
        beat_frac = beat_num % 1.0
        sub_beat = (sample_t % (beat_duration / 2.0)) / (beat_duration / 2.0)
        
        # Kick Drum (Beat 1 & 3)
        if (beat_num < 0.25 or (beat_num >= 2.0 and beat_num < 2.25)) and beat_frac < 0.25:
            time_since_kick = beat_frac * beat_duration
            kick_env = np.exp(-20.0 * time_since_kick)
            kick_freq = 120.0 * np.exp(-30.0 * time_since_kick)
            beat_signal[sample_i] += 0.4 * np.sin(2 * np.pi * kick_freq * time_since_kick) * kick_env

        # Snare / Soft Clap (Beat 2 & 4)
        if ((beat_num >= 1.0 and beat_num < 1.25) or (beat_num >= 3.0 and beat_num < 3.25)) and beat_frac < 0.2:
            time_since_snare = beat_frac * beat_duration
            snare_env = np.exp(-25.0 * time_since_snare)
            noise = (np.random.rand() * 2.0 - 1.0)
            beat_signal[sample_i] += 0.25 * noise * snare_env

        # Hi-Hats (8th notes)
        if sub_beat < 0.15:
            time_since_hat = sub_beat * (beat_duration / 2.0)
            hat_env = np.exp(-60.0 * time_since_hat)
            hat_noise = (np.random.rand() * 2.0 - 1.0)
            beat_signal[sample_i] += 0.08 * hat_noise * hat_env

    # 3. Vinyl Crackle Noise
    vinyl_noise = (np.random.rand(num_samples) * 2.0 - 1.0) * 0.015
    pop_mask = np.random.rand(num_samples) > 0.9995
    vinyl_noise[pop_mask] += (np.random.rand(np.sum(pop_mask)) * 2.0 - 1.0) * 0.15

    # Mix and normalize
    full_track = piano_signal + beat_signal + vinyl_noise
    max_val = np.max(np.abs(full_track))
    if max_val > 0:
        full_track = (full_track / max_val) * 0.8  # Normalize to -2dB peak

    # Convert to 16-bit PCM integer wave
    audio_int16 = (full_track * 32767).astype(np.int16)
    
    with wave.open(LOFI_AUDIO, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    
    print(f"Synthesized lo-fi audio track saved to: {LOFI_AUDIO}")


def merge_audio_video():
    """Merges video and lo-fi audio track using imageio_ffmpeg binary."""
    print("Merging video and audio into WebM with ffmpeg...")
    cmd_webm = [
        FFMPEG_EXE,
        "-y",
        "-i", INPUT_VIDEO,
        "-i", LOFI_AUDIO,
        "-c:v", "copy",
        "-c:a", "libopus",
        "-shortest",
        OUTPUT_WEBM,
    ]
    os.system(" ".join([f'"{c}"' for c in cmd_webm]))
    print(f"Output WebM video created: {OUTPUT_WEBM}")

    print("Converting to MP4 with ffmpeg...")
    cmd_mp4 = [
        FFMPEG_EXE,
        "-y",
        "-i", INPUT_VIDEO,
        "-i", LOFI_AUDIO,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        OUTPUT_VIDEO,
    ]
    os.system(" ".join([f'"{c}"' for c in cmd_mp4]))
    print(f"Output MP4 video created: {OUTPUT_VIDEO}")

    # Upload to Cloud Storage
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)

    blob_webm = bucket.blob("fitcoach_demo_lofi.webm")
    with open(OUTPUT_WEBM, "rb") as f:
        blob_webm.upload_from_file(f, content_type="video/webm")

    blob_mp4 = bucket.blob("fitcoach_demo_lofi.mp4")
    with open(OUTPUT_VIDEO, "rb") as f:
        blob_mp4.upload_from_file(f, content_type="video/mp4")

    print("Uploaded lo-fi demo video to Cloud Storage:")
    print(f"WebM URL: https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/fitcoach_demo_lofi.webm")
    print(f"MP4 URL: https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/fitcoach_demo_lofi.mp4")


if __name__ == "__main__":
    generate_lofi_track()
    merge_audio_video()
