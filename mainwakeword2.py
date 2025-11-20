import sys
import os
import pvporcupine
import pyaudio
import struct
import io
import time 
import numpy as np



# Imports specific names needed from utils
from utils2 import check_environment, get_keyword_path, KEYWORD_FILENAME, MAX_FOLLOWUP_TIME

# Imports the functions and the derived audio constants from stt_tts.py
from stt_tts2 import record_command, transcribe_audio, speak, SAMPLE_RATE, CHUNK_SIZE 
from ai_corestreaming2 import process_command 
from database2 import get_user_id_by_name, get_user_name_by_id # NEW IMPORT

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
    current_user_id = None # <-- NEW STATE VARIABLE
    current_user_name = None # <-- NEW STATE VARIABLE

    # 3. MAIN LOOP
    try:
        while True:
            # --- WAKE WORD DETECTION BLOCK ---
            if not conversation_mode:
                chat_history.clear() 
                current_user_id = None # Reset user ID
                
                stream = None 
                try:
                    stream = pa.open(
                        rate=porcupine.sample_rate,
                        channels=1,
                        format=pyaudio.paInt16,
                        input=True,
                        frames_per_buffer=porcupine.frame_length,
                        input_device_index=None
                    )
                    
                    while not conversation_mode:
                        pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                        pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
                        
                        if porcupine.process(pcm_unpacked) >= 0:
                            print("✅ Wake word detected!")
                            speak("Yes?") 
                            
                            # --- NEW USER RECOGNITION BLOCK (Input based) ---
                            print("\n--- Awaiting User Identification ---")
                            
                            while current_user_id is None:
                                user_name_input = input("👤 Please enter your name (must be in database): ")
                                
                                if user_name_input.lower() in ('exit', 'quit'):
                                    speak("Okay, going quiet.")
                                    break 
                                    
                                current_user_id = get_user_id_by_name(user_name_input)
                                
                                if current_user_id is None:
                                    print(f"❌ User '{user_name_input}' not found. Please try again or type 'exit'.")
                                    speak("I don't recognize that name. Could you say your name again?")
                                else:
                                    # Get the capitalized/clean name back from the database
                                    current_user_name = get_user_name_by_id(current_user_id) 
                                
                            if current_user_id is None:
                                # Break out of the conversation mode check if user exits prompt
                                continue 
                                
                            speak(f"Hello, {current_user_name}. How can I help you?")
                            # --- END NEW USER RECOGNITION BLOCK ---

                            conversation_mode = True
                            break 
                            
                except Exception as e:
                    print(f"❌ PyAudio Error during wake word detection: {e}")
                    time.sleep(1) 
                    continue 
                    
                finally:
                    if stream and stream.is_active():
                         stream.stop_stream()
                         stream.close()

            # --- CONTINUOUS CONVERSATION/COMMAND BLOCK ---
            if conversation_mode:
                last_activity_time = time.time()
                
                while conversation_mode:
                    # Check for Inactivity Timeout
                    if time.time() - last_activity_time > MAX_FOLLOWUP_TIME:
                        print(f"💤 Inactivity timeout ({MAX_FOLLOWUP_TIME}s). Returning to wake-word mode.")
                        speak("I'm going quiet now. Say the wake word when you need me.")
                        conversation_mode = False
                        current_user_id = None # Final reset
                        break 
                        
                    # Start command recording (Volume-based, auto-stop)
                    raw_audio_io = record_command(pa, SAMPLE_RATE, CHUNK_SIZE)
                    
                    # Check for recording length (to ignore short microphone bumps)
                    raw_audio_io.seek(0, io.SEEK_END)
                    size_in_bytes = raw_audio_io.tell()
                    raw_audio_io.seek(0)
                    
                    num_samples = size_in_bytes // 2 
                    
                    if num_samples < SAMPLE_RATE * 0.5:
                        print("⏱️ Recording too short, ignoring.")
                        continue
                    
                    # Transcribe and process
                    try:
                        transcript = transcribe_audio(raw_audio_io, SAMPLE_RATE) 
                        
                        if transcript:
                            
                            # PASS THE USER ID TO THE PROCESSOR
                            result = process_command(transcript, speak, chat_history, current_user_id) 
                            
                            last_activity_time = time.time() 
                            
                            if result == "EXIT_CONVERSATION":
                                conversation_mode = False
                                print(f"\n👂 Listening for wake word ('{KEYWORD_FILENAME.split('_')[0].replace('-', ' ')}')...")
                                current_user_id = None # Final reset
                            
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
