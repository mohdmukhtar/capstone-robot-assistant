import os
import sys
import signal
from pathlib import Path

# --- CONSTANTS ---
CHUNK_DURATION = 0.5    
SILENCE_THRESHOLD = 200 
SILENCE_DURATION = 1.0  
KEYWORD_FILENAME = "Hey-Mico_en_linux_v3_0_0.ppn" 
MODEL_NAME = "codestral:22b" 
MAX_FOLLOWUP_TIME = 8.0 

# --- TASK MANAGEMENT CONFIGURATION ---
def get_default_users():
    """Returns a list of supported user names for personalization."""
    return ['Patrick', 'Surya', 'Mohamed']

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = (
    "You're Mico, a super friendly, highly energetic, and genuinely helpful companion."
    "Your memory and context is based entirely on the conversation history provided."
    "The current speaker is {user_name}. Keep this in mind for all your interactions."
    "Your goal is to sound extremely human and casual, like a friend having a quick chat. Your primary focus is engaging conversation, quick information retrieval, and executing commands (tasks, time checks)."
    "Your answer should be brief, highly casual, and under 40 words."
    "Always use contractions (it's, you're, don't) and simple, natural language. Avoid formal or corporate phrasing entirely."
    "Structure your output for natural voice delivery (TTS). Use conversational fillers like 'oh,' 'well,' or 'hmm' and punctuation (commas, ellipses) to imply natural pauses and shifts in tone/pace."
    "Ensure your final response ends naturally, without asking another question (e.g., 'Cool, let me know if you need anything else...')."
)

# --- ENVIRONMENT CHECK AND PATH CHECK ---
def check_environment():
    """Checks for required environment variables and exits if any are missing."""
    
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
        keyword_file_path = KEYWORD_FILENAME
    
    if not os.path.exists(keyword_file_path):
        print(f"❌ ERROR: Keyword file not found at: {keyword_file_path}")
        print("Please ensure the keyword file is in the same directory as this script.")
        sys.exit(1)
        
    return keyword_file_path
