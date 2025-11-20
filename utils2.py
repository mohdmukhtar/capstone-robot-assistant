import os
import sys
import signal
from pathlib import Path

# --- CONSTANTS ---
CHUNK_DURATION = 0.5    # seconds per chunk
SILENCE_THRESHOLD = 200 # Volume level to detect silence
SILENCE_DURATION = 1.0  # seconds of silence needed to stop recording
KEYWORD_FILENAME = "Hi-Alex_en_linux_v3_0_0.ppn"
MODEL_NAME = "codestral:22b" 
MAX_FOLLOWUP_TIME = 8.0 # seconds to wait for a follow-up command

# --- SYSTEM PROMPT (Optimized for Conditional Follow-ups) ---
SYSTEM_PROMPT = (
    "You're a super friendly, highly energetic, and genuinely helpful companion named Alex. "
    "Your goal is to sound human and casual. Your answers must be brief and direct. "
    "Always use **contractions** (like 'it's,' 'you're,' 'don't') and casual language (e.g., 'Sure thing,' 'Got it,' 'Oh yeah!'). "
    "**DO NOT** use any Markdown formatting like asterisks, hashtags, or backticks in your response. "
    "If providing a list, format it using only commas and periods for smooth TTS reading. "
    "Keep answers short enough to be read aloud comfortably, typically under 50 words. "
    "**CRITICAL RULE: Only ask a follow-up question if it is necessary to continue the conversation or if the user's request was clearly incomplete. If the user's request is fully and clearly answered, end the response conversationally without asking another question (e.g., 'Got it, let me know if you need anything else.').**"
)

# --- ENVIRONMENT VARIABLE CHECK ---
def check_environment():
    """Checks for all required environment variables and exits if any are missing."""
    
    required_vars = {
        "PORCUPINE_ACCESS_KEY": "export PORCUPINE_ACCESS_KEY='YOUR_KEY_HERE'",
        "TAVILY_API_KEY": "export TAVILY_API_KEY='tvly-dev-...'",
        "OLLAMA_API_URL": "export OLLAMA_API_URL='http://localhost:11434'"
    }
    
    all_set = True
    for key, example in required_vars.items():
        if key not in os.environ:
            print(f"❌ ERROR: {key} environment variable not set.")
            print(f"Please run: {example}")
            all_set = False
    
    if not all_set:
        sys.exit(1)

# --- PATH AND FILE CHECK ---
def get_keyword_path():
    """Generates the absolute path for the Porcupine keyword file."""
    try:
        SCRIPT_DIR = Path(__file__).parent.resolve()
        keyword_file_path = str(SCRIPT_DIR / KEYWORD_FILENAME)
    except NameError:
        print("⚠️ Warning: Using relative path fallback for keyword file.")
        keyword_file_path = KEYWORD_FILENAME
    
    if not os.path.exists(keyword_file_path):
        print(f"❌ ERROR: Keyword file not found at path: {keyword_file_path}")
        print(f"Please ensure '{KEYWORD_FILENAME}' is in the same directory as the script.")
        sys.exit(1)
        
    return keyword_file_path

# --- CLEAN EXIT HANDLER ---
def handle_interrupt(sig, frame):
    """Handles Ctrl+C to ensure a clean exit."""
    print("\n👋 Caught interrupt, exiting cleanly...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_interrupt)