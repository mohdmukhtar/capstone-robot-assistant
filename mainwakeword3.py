import pvporcupine
import pyaudio
import struct
import sys
import io
import os
import time 
import numpy as np 

# Imports specific names needed from utils
from utils3 import check_environment, get_keyword_path, KEYWORD_FILENAME, MAX_FOLLOWUP_TIME

# Imports the functions and the derived audio constants from stt_tts.py
from stt_tts3 import record_command, transcribe_audio, speak, SAMPLE_RATE, CHUNK_SIZE 
from ai_corestreaming3 import process_command 


def main():
    
    # 1. INITIAL SETUP
    check_environment()
    keyword_file_path = get_keyword_path()

    # 2. PORCUPINE INITIALIZATION
    try:
        porcupine = pvporcupine.create(
            access_key=os.environ["PORCUPINE_ACCESS_KEY"],
            keyword_paths=[keyword_file_path],
            sensitivities=[0.7],
        )
    except Exception as e:
        print(f"❌ Porcupine initialization failed: {e}")
        print("Is your ACCESS_KEY correct? Is the keyword file valid?")
        sys.exit(1)
        
    pa = pyaudio.PyAudio()
    print(f"\n👂 Listening for wake word ('{KEYWORD_FILENAME.split('_')[0].replace('-', ' ')}')...")
    
    # STATE VARIABLES
    conversation_mode = False
    chat_history = [] 
    # V3 STATE VARIABLE: Tracks the currently identified user
    current_user = None 
    last_activity_time = time.time()
    
    # 3. MAIN LOOP
    try:
        while True:
            # --- WAKE WORD DETECTION ---
            if not conversation_mode:
                audio_stream = pa.open(
                    rate=porcupine.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=porcupine.frame_length
                )
                
                while True:
                    pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                    
                    if porcupine.process(pcm) >= 0:
                        print(f"\n📢 Wake word detected! Entering conversation mode.")
                        conversation_mode = True
                        last_activity_time = time.time()
                        break
                
                audio_stream.close()

            # --- CONVERSATION MODE ---
            if conversation_mode:
                # 3a. CHECK FOR TIMEOUT
                if time.time() - last_activity_time > MAX_FOLLOWUP_TIME:
                    conversation_mode = False
                    current_user = None # Reset user state after timeout
                    chat_history = []   # Clear memory
                    print(f"\n💤 Timeout. Resetting user. Listening for wake word ('{KEYWORD_FILENAME.split('_')[0].replace('-', ' ')}')...")
                    continue
                
                # 3b. USER IDENTIFICATION PROMPT (V2-like flow)
                if current_user is None:
                    speak("Hello. Who is speaking?")
                    
                # 3c. RECORD USER COMMAND
                print(f"\n🎤 Listening for command (User: {current_user if current_user else 'Unknown'})...")
                
                raw_audio_io = record_command(pa)
                if raw_audio_io:
                    
                    # Transcribe and process
                    try:
                        transcript = transcribe_audio(raw_audio_io, SAMPLE_RATE) 
                        
                        if transcript:
                            
                            # process_command now takes and may update current_user
                            result, user_identified = process_command(
                                transcript, 
                                speak, 
                                chat_history, 
                                current_user
                            ) 

                            if user_identified:
                                current_user = user_identified # Update state if successful

                            last_activity_time = time.time() 
                            
                            if result == "EXIT_CONVERSATION":
                                conversation_mode = False
                                current_user = None # Reset user state on explicit exit
                                chat_history = []   # Clear memory
                                print(f"\n👂 Listening for wake word ('{KEYWORD_FILENAME.split('_')[0].replace('-', ' ')}')...")
                            
                            elif result == "CONTINUE_CONVERSATION":
                                pass
                            
                        else:
                            print("🤐 No transcribable speech detected.")
                            
                    except Exception as e:
                        print(f"❌ Error during transcription/processing: {e}")
                        
    except KeyboardInterrupt:
        pass 
    finally:
        print("Cleaning up...")
        if pa:
            pa.terminate()
        if porcupine:
            porcupine.delete()

if __name__ == "__main__":
    main()