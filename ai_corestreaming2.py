import os
import requests
import datetime
import json
import time 
from tavily import TavilyClient

# Update imports to use the new file names and paths
from utils2 import MODEL_NAME, SYSTEM_PROMPT 
from database2 import get_user_reminders, add_reminder, mark_reminder_completed, get_user_name_by_id

# --- GLOBAL INITIALIZATION ---
print("Loading Tavily client...")
try:
    TAVILY_CLIENT = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    print("Tavily client loaded.")
except Exception as e:
    print(f"❌ Failed to load Tavily client: {e}")
    TAVILY_CLIENT = None

# --- OLLAMA STREAMING COMMUNICATION (Unchanged) ---
def send_to_ollama(prompt: str, speak_func, chat_history: list):
    """
    Sends a chat prompt to Ollama with streaming enabled, using chat_history
    to maintain context. Returns the full assistant response text.
    """
    
    # 1. Build the messages list using history
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages.extend(chat_history) 
    messages.append({"role": "user", "content": prompt}) 
    
    print(f"🤖 Sending to Ollama (Streaming): {prompt}")
    
    full_assistant_response = ""
    
    # Robust URL handling
    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        print("❌ OLLAMA_API_URL is empty or not set correctly in the environment.")
        speak_func("Sorry, I couldn't connect to my brain. The API address is missing.")
        return ""

    try:
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/chat",
            json={
                "model": MODEL_NAME, 
                "messages": messages, 
                "stream": True 
            },
            stream=True, 
            timeout=60
        )
        
        response.raise_for_status() 

        buffer = ""
        print("🧠 Ollama response starting...")
        
        # --- Streaming and Buffering Logic ---
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    chunk_data = json.loads(line)
                    
                    if 'message' in chunk_data and 'content' in chunk_data['message']:
                        content = chunk_data['message']['content']
                        buffer += content
                        
                        # --- Buffering Logic for Smooth TTS ---
                        if content.endswith(('.', '!', '?')) and len(buffer.split()) > 2:
                            speak_func(buffer)
                            full_assistant_response += buffer
                            buffer = ""
                        
                        elif len(buffer) > 100 and ' ' in buffer:
                            break_index = max(buffer.rfind('.'), buffer.rfind('!'), buffer.rfind('?'))
                            
                            if break_index > 0 and break_index < len(buffer) - 10:
                                chunk_to_speak = buffer[:break_index + 1]
                                buffer = buffer[break_index + 1:].lstrip()
                                speak_func(chunk_to_speak)
                                full_assistant_response += chunk_to_speak

                    if chunk_data.get('done'):
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error on chunk: {e}, line: {line[:50]}...")
                    continue

        # Speak any remaining content in the buffer
        if buffer.strip():
            speak_func(buffer.strip())
            full_assistant_response += buffer.strip()
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to Ollama or request failed: {e}")
        speak_func("Sorry, I couldn't connect to my brain. Is Ollama running?")
        
    return full_assistant_response 


# --- TAVILY SEARCH TOOL (Unchanged) ---
def search_with_tavily(query: str):
    """Executes a search query using the Tavily API."""
    if not TAVILY_CLIENT:
        return None
        
    print(f"🛠️ Searching Tavily for: {query}")
    try:
        response = TAVILY_CLIENT.search(query, search_depth="basic")
        results = response.get("results", [])[:3]
        
        context = ""
        for result in results:
            context += f"URL: {result.get('url', 'N/A')}\nContent: {result.get('content', 'N/A')}\n\n"
            
        return context
        
    except Exception as e:
        print(f"❌ Tavily search failed: {e}")
        return None

# --- LLM ROUTER (Unchanged) ---
def route_command(transcript: str):
    """Uses Ollama to decide if the command needs a web search or regular chat."""
    
    ROUTER_PROMPT = f"""
You are a highly analytical AI router. Your task is to analyze the user's question and determine the appropriate action.
You MUST output a single JSON object.
Question: "{transcript}"
JSON Output Format:
{{
  "action": "CHAT" or "SEARCH",
  "search_query": "The concise search query if action is SEARCH, otherwise empty string"
}}
"""
    print("🧠 Routing command via Ollama...")

    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        return {"action": "CHAT", "search_query": transcript}

    try:
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/generate",
            json={
                "model": MODEL_NAME, 
                "prompt": ROUTER_PROMPT,
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=10
        )
        if response.ok:
            response_text = response.json()['response'].strip()
            
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            if start_index != -1 and end_index != -1:
                json_string = response_text[start_index : end_index + 1]
                return json.loads(json_string)

            return {"action": "CHAT", "search_query": transcript}
        
        else:
            print(f"⚠️ Ollama router returned non-OK status: {response.status_code}")
            return {"action": "CHAT", "search_query": transcript}

    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama connection error during routing: {e}")
        return {"action": "CHAT", "search_query": transcript}
    except json.JSONDecodeError:
        print("❌ JSON decode error during routing.")
        return {"action": "CHAT", "search_query": transcript}


# --- LOCAL TOOL HANDLER (Unchanged) ---
def check_local_tools(transcript: str, speak_func):
    """
    Checks if the transcript matches a local, non-LLM tool command.
    """
    transcript_lower = transcript.lower()

    # Tool 1: Conversation Exit - Matches "Nothing else. Thank you." flow
    if "stop listening" in transcript_lower or "thank you" in transcript_lower or "that's all" in transcript_lower or "nothing else" in transcript_lower:
        speak_func("You got it. I'm going back to quiet listening now.")
        return {"action": "EXIT_CONVERSATION"}

    # Tool 2: Python datetime (Local Tool)
    if "what time is it" in transcript_lower:
        print("🧠 Decision: Local time query.")
        now = datetime.datetime.now().strftime("%-I:%M %p") 
        speak_func(f"Oh, sure thing! It's {now} right now.")
        return {"action": "LOCAL_HANDLED", "response_spoken": True}

    return {"action": "CONTINUE"}


# --- NEW REMINDER TOOL HANDLER ---
def handle_reminders(transcript: str, speak_func, user_id: int):
    """
    Uses the LLM to process the transcript and execute a database action.
    """
    
    # Get the user's name for a personalized prompt
    USER_NAME = get_user_name_by_id(user_id) 

    REMINDER_PROMPT = f"""
You are an intelligent assistant connected to a reminder database tool. Your task is to analyze the user's request and output a single JSON object to manage their reminders.

Current User: {USER_NAME} (ID: {user_id})
Today's Date: {datetime.date.today()}

The JSON Output Format MUST include the 'action' key:
{{
  "action": "ADD_REMINDER", "VIEW_REMINDERS", "COMPLETE_REMINDER", or "ANSWER"
  "description": "The exact reminder text to be added (if action is ADD_REMINDER), otherwise null.",
  "reminder_id": "The ID of the reminder to complete (if action is COMPLETE_REMINDER), otherwise null.",
  "question": "A friendly conversational response or question if action is ANSWER, otherwise null."
}}

If the user is asking to add a reminder, set action to ADD_REMINDER.
If the user is asking to view their reminders, set action to VIEW_REMINDERS.
If the user is asking to complete or clear a reminder, set action to COMPLETE_REMINDER.
If the user is just asking a general question about reminders (e.g., 'What are reminders?'), set action to ANSWER.

User Request: "{transcript}"
"""
    
    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        return {"action": "ANSWER", "question": "Sorry, I can't access the database tool right now because my brain isn't connected."}
    
    try:
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/generate",
            json={
                "model": MODEL_NAME, 
                "prompt": REMINDER_PROMPT,
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=10
        )
        if response.ok:
            response_text = response.json()['response'].strip()
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            if start_index != -1 and end_index != -1:
                json_string = response_text[start_index : end_index + 1]
                return json.loads(json_string)

            return {"action": "ANSWER", "question": "I had a hard time understanding what you wanted to do with the reminders."}
            
        return {"action": "ANSWER", "question": "My router failed to process the reminder request."}

    except Exception as e:
        print(f"❌ Error during reminder routing: {e}")
        return {"action": "ANSWER", "question": "I can't talk to my reminder system right now. Maybe try again?"}


# --- PRIMARY COMMAND PROCESSOR (Modified) ---
def process_command(transcript: str, speak_func, chat_history: list, user_id: int):
    """Processes the command, using chat_history and user_id, and returns a state flag."""
    
    # 1. --- Check for Local Tools and Exit Commands ---
    local_result = check_local_tools(transcript, speak_func)
    
    if local_result["action"] == "EXIT_CONVERSATION":
        chat_history.clear() 
        return "EXIT_CONVERSATION"
        
    if local_result["action"] == "LOCAL_HANDLED":
        return "CONTINUE_CONVERSATION"

    # 2. --- NEW: Check for Reminder Tool ---
    if "reminder" in transcript.lower() or "task" in transcript.lower() or "to do" in transcript.lower() or "list" in transcript.lower():
        print("🛠️ Decision: Reminder Tool activated.")
        tool_result = handle_reminders(transcript, speak_func, user_id)
        
        # --- Execute Reminder Action ---
        if tool_result["action"] == "ADD_REMINDER":
            description = tool_result.get("description")
            if description:
                add_reminder(user_id=user_id, description=description)
                speak_func(f"Got it. I added ' {description} ' to your list.")
            else:
                speak_func("I need a description to add a reminder. What should I remind you about?")
            return "CONTINUE_CONVERSATION"

        elif tool_result["action"] == "VIEW_REMINDERS":
            reminders = get_user_reminders(user_id=user_id)
            if reminders:
                # Format reminders for voice output
                reminder_list = [f"Task {i+1}, {desc}. Due {due if due else 'sometime'}" for i, (desc, due, r_id) in enumerate(reminders)]
                
                speak_func(f"Sure, you have {len(reminders)} pending tasks. They are: {', '.join(reminder_list)}")
                speak_func("I've also displayed them on the screen.")
                
            else:
                speak_func("Awesome! You don't have any pending reminders.")
            return "CONTINUE_CONVERSATION"

        elif tool_result["action"] == "COMPLETE_REMINDER":
            # For this prototype, we'll tell the user how to do it manually
            speak_func("I can mark a reminder complete, but I need the task ID displayed on the screen. Please tell me the ID of the task you want to clear.")
            # In a GUI system, the LLM would ask "Which reminder ID should I complete?"
            return "CONTINUE_CONVERSATION"
            
        elif tool_result["action"] == "ANSWER":
            # If the LLM didn't choose an action, it gives a conversational answer
            speak_func(tool_result.get("question", "I'm not sure how to handle that reminder request."))
            return "CONTINUE_CONVERSATION"


    # 3. --- LLM Router (Only for non-reminder, non-local questions) ---
    router_result = route_command(transcript)
    
    if router_result is None or not isinstance(router_result, dict):
        router_result = {"action": "CHAT", "search_query": transcript}
        
    action = router_result.get("action", "CHAT").upper()
    search_query = router_result.get("search_query", transcript) 
    
    # 4. --- EXECUTION Logic (Unchanged) ---
    assistant_response = "" 

    if action == "SEARCH":
        # ... (Search logic remains the same) ...
        print(f"🛠️ Executing Search for: {search_query}")
        
        context = search_with_tavily(search_query) 
        
        if not context:
            speak_func("Sorry, I had a problem searching the web.")
            return "CONTINUE_CONVERSATION"

        augmented_prompt = f"""
Use the following search results to answer the user's question.
Provide a concise answer based *only* on the context provided. Do not invent information.

---[SEARCH RESULTS]---
{context}
---[END OF RESULTS]---

User's Question: {transcript}
"""
        assistant_response = send_to_ollama(augmented_prompt, speak_func, chat_history) 

    # --- Default: Regular Chat ---
    else:
        print("🧠 Execution: Regular chat/memory response.")
        assistant_response = send_to_ollama(transcript, speak_func, chat_history) 
    
    # 5. LOG THE CONVERSATION HISTORY (Memory logging)
    if assistant_response:
        chat_history.append({"role": "user", "content": transcript})
        chat_history.append({"role": "assistant", "content": assistant_response})
        
        # Keep history manageable (last 10 turns)
        if len(chat_history) > 10:
            chat_history[:] = chat_history[-10:]
            
    return "CONTINUE_CONVERSATION"
