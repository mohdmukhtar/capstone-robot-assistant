import io
import pyaudio
import struct
import time
import numpy as np 
import os
import whisper 
import wave

# Imports for gTTS and Pygame
from gtts import gTTS
import pygame

from utils3 import SILENCE_THRESHOLD, SILENCE_DURATION, CHUNK_DURATION

# --- AUDIO CONSTANTS ---
SAMPLE_RATE = 16000 
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION) 
SILENCE_CHUNKS = int(SILENCE_DURATION / CHUNK_DURATION)

# --- GLOBAL INITIALIZATION ---
print("Loading Whisper Model...")
try:
    WHISPER_MODEL = whisper.load_model("base") 
except Exception as e:
    print(f"❌ Could not load Whisper model: {e}")
    WHISPER_MODEL = None

# --- TTS INITIALIZATION ---
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
        
        # Save the audio to a temporary file
        tts.save(temp_file)
        
        # Load and play the audio using Pygame
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # Wait until the audio is done playing
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
        # Clean up the temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    except Exception as e:
        print(f"❌ TTS failed: {e}")

# --- SPEECH TO TEXT (STT) ---
def record_command(pa_instance: pyaudio.PyAudio) -> io.BytesIO:
    """
    Records audio by opening a temporary PyAudio stream until silence is detected.
    
    Note: It requires pa_instance (the PyAudio object) to be passed so it can open 
    and close its own stream internally.
    """
    audio_frames = []
    silence_counter = 0
    speaking = False
    
    print("Recording...")

    raw_audio = io.BytesIO()
    
    # --- FIX: Open the stream inside the function using the passed PyAudio instance ---
    stream = pa_instance.open(
        rate=SAMPLE_RATE,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )
    # --------------------------------------------------------------------------------
    
    try:
        while True:
            try:
                # Read a chunk of audio using the internally opened stream
                chunk_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                
                # Convert raw 16-bit data to numpy array for volume analysis
                frame_data = np.frombuffer(chunk_data, dtype=np.int16)
                volume = np.abs(frame_data).mean()
                
                # Start/Stop logic
                if volume > SILENCE_THRESHOLD:
                    silence_counter = 0
                    speaking = True
                    raw_audio.write(chunk_data)
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
        
    finally:
        # Crucial: Close the stream before exiting the function
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
        
    finally:
        # 3. Clean up temporary file
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            
    return transcript
