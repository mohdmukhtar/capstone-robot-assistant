import io
import pyaudio
import struct
import time
import numpy as np 
import os
import whisper 
import wave

# Update imports to use the new file name
from utils2 import SILENCE_THRESHOLD, SILENCE_DURATION, CHUNK_DURATION 

# Imports for gTTS and Pygame
from gtts import gTTS
import pygame

# --- AUDIO CONSTANTS AND CALCULATIONS (Made Local) ---
SAMPLE_RATE = 16000 
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION) 
SILENCE_CHUNKS = int(SILENCE_DURATION / CHUNK_DURATION)

# --- GLOBAL INITIALIZATION ---
# Load Whisper Model (Choose a model size, "base" is recommended for local CPU)
print("Loading Whisper Model...")
try:
    WHISPER_MODEL = whisper.load_model("base") 
    print("Whisper model loaded.")
except Exception as e:
    print(f"❌ Could not load Whisper model: {e}")
    WHISPER_MODEL = None

# TTS INITIALIZATION: Initialize Pygame Mixer for audio playback
pygame.mixer.init()

# --- TEXT TO SPEECH (TTS) ---
def speak(text):
    """
    Speaks the given text using gTTS (Requires Internet).
    This function is NON-BLOCKING once the audio is loaded.
    """
    print(f"🗣️ Speaking: {text}")
    
    try:
        # Create a gTTS object
        tts = gTTS(text=text, lang='en', slow=False)
        temp_file = "temp_tts.mp3"
        
        # Save audio to a temporary file
        tts.save(temp_file)
        
        # Load and play the audio using Pygame
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # Wait until playback finishes (blocking call to ensure audio completes)
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
        # Clean up
        os.remove(temp_file)
        
    except Exception as e:
        print(f"❌ gTTS/Pygame playback failed (Do you have internet access?): {e}")


# --- SPEECH TO TEXT (STT) ---
def record_command(pa, sample_rate, chunk_size):
    """
    Records audio until silence is detected using amplitude threshold.
    """
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size,
        input_device_index=None
    )
    
    raw_audio = io.BytesIO()
    silence_counter = 0
    speaking = False
    
    print("🎙️ Listening for command (Volume activated)...")
    
    while True:
        try:
            data = stream.read(chunk_size, exception_on_overflow=False)
            raw_audio.write(data)

            # --- Volume Check (Amplitude based) ---
            audio_data = np.frombuffer(data, dtype=np.int16)
            volume = np.max(np.abs(audio_data))
            
            if volume > SILENCE_THRESHOLD:
                silence_counter = 0
                if not speaking:
                    speaking = True # Start recording only after first speech
            else:
                if speaking:
                    silence_counter += 1
            
            # --- Stop Condition ---
            if speaking and silence_counter >= SILENCE_CHUNKS:
                print("🔇 Silence detected, stopping recording.")
                break
                
        except IOError as e:
            if e.errno == pyaudio.paInputOverflowed:
                continue
            else:
                raise
        
    stream.stop_stream()
    stream.close()
    
    return raw_audio

def transcribe_audio(audio_io, sample_rate):
    """
    Transcribes the recorded audio buffer using the loaded Whisper model.
    """
    global WHISPER_MODEL

    if WHISPER_MODEL is None:
        print("❌ Whisper model is not loaded. Cannot transcribe.")
        return ""
    
    # 1. Save audio data to a temporary WAV file for Whisper
    temp_wav_path = "temp_recording.wav"
    audio_io.seek(0)
    
    with wave.open(temp_wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit audio
        wf.setframerate(sample_rate)
        wf.writeframes(audio_io.read())

    # 2. Run Whisper transcription
    try:
        result = WHISPER_MODEL.transcribe(temp_wav_path)
        transcript = result["text"].strip()
        print(f"👂 Transcript: {transcript}")
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        transcript = ""
        
    # 3. Clean up
    os.remove(temp_wav_path)

    return transcript
