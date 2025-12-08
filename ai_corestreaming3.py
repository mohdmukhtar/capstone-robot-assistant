import os
import requests
import datetime
import json
import time 
from tavily import TavilyClient

# --- V3 IMPORTS ---
from utils3 import MODEL_NAME, SYSTEM_PROMPT, get_default_users 
from ai_taskhandler3 import llm_nlu_task_parser, handle_task_command 
# ------------------


# --- GLOBAL INITIALIZATION ---
print("Loading Tavily client...")
try:
    TAVILY_CLIENT = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    print("Tavily client loaded.")
except Exception as e:
    print(f"❌ Failed to load Tavily client: {e}")
    TAVILY_CLIENT = None

# --- OLLAMA STREAMING COMMUNICATION ---
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
    
    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        print("❌ OLLAMA_API_URL is empty or not set correctly in the environment.")
        speak_func("Sorry, I couldn't connect to my brain. Please check the Ollama environment variable.")
        return ""
    
    try:
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/chat",
            json={
                "model": MODEL_NAME, 
                "messages": messages,
                "stream": True,
                "options": {"temperature": 0.7},
            },
            stream=True,
            timeout=15
        )
        response.raise_for_status() 

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    for line in chunk.decode('utf-8').splitlines():
                        if line:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            
                            if content:
                                # Streams to console
                                print(content, end="", flush=True)
                                full_assistant_response += content

                            if data.get("done", False):
                                break
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON decoding error in stream: {e}")
                    continue
        
        print() # Newline after streaming finishes
        return full_assistant_response.strip()

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Ollama connection or API error: {e}")
        speak_func("I'm sorry, I couldn't connect to my processing model. Please make sure Ollama is running.")
        return ""
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        return ""


# --- LLM ROUTER (For determining CHAT vs. SEARCH) ---
def route_command(transcript: str, chat_history: list) -> dict:
    """
    Uses Ollama to determine if a command requires a web search or a general chat response,
    using the chat_history to maintain context for generating accurate search queries.
    Returns a structured dictionary: {"action": "SEARCH" or "CHAT", "search_query": "..."}
    """
    ROUTER_SYSTEM_PROMPT = """
    You are a command router. Your task is to analyze the user's current question and the conversation history to determine two things:
    1. If the request requires a real-time web search or can be answered from general knowledge/chat.
    2. If the action is SEARCH, you MUST generate the best possible, context-aware search query based on the history.

    JSON Output Format (MUST output a single JSON object):
    {{
      "action": "SEARCH" or "CHAT",
      "search_query": "The exact, context-aware search query for the SEARCH action (e.g., 'album recommendations for Cara Tivey'), or the user's original question for the CHAT action."
    }}
    
    **CRITICAL RULES:**
    1. Choose "SEARCH" if the question asks for current events, specific facts, or anything that requires up-to-date, external information.
    2. Choose "CHAT" for conversation, roleplay, general knowledge, or simple questions that do not require external facts.
    3. The entire output MUST be the JSON object defined above.
    """
    
    # 1. Build the messages list for the router to use context
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT}
    ]
    # Add history for context
    messages.extend(chat_history)
    messages.append({"role": "user", "content": f"User's current question: '{transcript}'"})
    
    print("🗺️ Routing command via Ollama with full context...")

    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        print("❌ OLLAMA_API_URL is empty. Routing aborted.")
        return {"action": "CHAT", "search_query": transcript}

    try:
        # Using the /api/chat endpoint to properly leverage the 'messages' history
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/chat",
            json={
                "model": MODEL_NAME, 
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512, "num_ctx": 4096},
            },
            timeout=10
        )
        if response.ok:
            # The response from /api/chat (non-streaming) is structured as a message object
            response_text = response.json().get('message', {}).get('content', '').strip()
            
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            
            if start_index != -1 and end_index != -1:
                json_string = response_text[start_index : end_index + 1]
                
                json_string = json_string.replace('```json', '').replace('```', '').strip()
                return json.loads(json_string)
            
            print(f"❌ Failed to extract valid JSON from router: {response_text[:100]}...")
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

# --- WEB SEARCH TOOL ---
def search_with_tavily(query: str):
    """Performs a web search using Tavily and returns a concise context string."""
    global TAVILY_CLIENT
    if TAVILY_CLIENT is None:
        return "Tavily client is not initialized."
    
    try:
        response = TAVILY_CLIENT.search(query=query, search_depth="basic", max_results=3)
        
        context = []
        for result in response['results']:
            context.append(f"Source: {result['url']}\nContent: {result['content']}")
            
        return "\n---\n".join(context)
        
    except Exception as e:
        print(f"❌ Tavily search failed: {e}")
        return None

# --- LOCAL UTILITIES ---
def check_local_tools(transcript: str, speak_func):
    """Checks for hard-coded exit commands."""
    
    exit_phrases = [
        "stop", 
        "exit conversation", 
        "shut down", 
        "thanks goodbye", 
        "that'll be all", 
        "that will be all", 
        "thank you that'll be all",
        "thank you that will be all"
    ]
    
    if any(phrase in transcript.lower() for phrase in exit_phrases):
        speak_func("Sure thing. Catch you later!")
        return "EXIT_CONVERSATION"

    return "NOT_HANDLED"
    
# --- NEW LOCAL TIME UTILITY ---
def handle_local_time_check(transcript: str, speak_func):
    """
    Checks for common local time or date queries and answers directly.
    Returns: "HANDLED" or "NOT_HANDLED"
    """
    transcript_lower = transcript.lower()
    
    # Check for local time/date queries (must NOT include a known city/region to keep it local)
    is_time_query = ("time" in transcript_lower or "o'clock" in transcript_lower) and not any(city in transcript_lower for city in ["toronto", "new york", "london", "tokyo", "paris", "city", "canada", "us", "uk", "gmt"])
    
    if is_time_query:
        now = datetime.datetime.now()
        # Format for casual speech (e.g., 11:50 AM, stripping leading zero for natural reading)
        current_time = now.strftime("%I:%M %p").lstrip('0')
        
        conversational_response = f"Oh sure! It's currently {current_time} over here."
        
        speak_func(conversational_response)
        
        print(f"⏰ Local Time Check (Hardcoded): {now.strftime('%H:%M:%S')} - Responded: {conversational_response}")

        return "HANDLED"
        
    return "NOT_HANDLED"


# --- NLU USER IDENTITY PARSER (FIXED FOR STRICT JSON OUTPUT) ---
def llm_nlu_user_identity_parser(transcript: str):
    """
    Uses Ollama to determine if the transcript contains a valid user name
    from the default list, typically in response to "Who is speaking?"
    """
    default_users = get_default_users() 
    
    NLU_PROMPT = f"""
You are a User Identity NLU service. Your sole task is to analyze the User Response and output **ONLY** the required JSON object, with absolutely **NO** other commentary, introduction, or conversation.

Available USER NAMES: {', '.join(default_users)}

User Response: "{transcript}"

JSON Output Format (MUST output a single JSON object):
{{
  "identified_user": "Extracted name from the Available USER NAMES list (e.g., Patrick, Surya, Mohamed), or NULL if no valid name is found."
}}

**CRITICAL RULES:**
1. Your entire output MUST be the JSON object defined above.
2. Only return a name if it matches one of the Available USER NAMES.
3. The extracted name must be capitalized (e.g., 'Patrick').
"""
    print("🧠 NLU User Identity Parsing via Ollama...")

    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        print("❌ OLLAMA_API_URL is empty. Identity parsing aborted.")
        return {"identified_user": None}

    try:
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/generate",
            json={
                "model": MODEL_NAME, 
                "prompt": NLU_PROMPT,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512, "num_ctx": 4096},
            },
            timeout=10
        )
        if response.ok:
            # Defensive coding: Use .get('response', '')
            response_text = response.json().get('response', '').strip()
            
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            
            if start_index != -1 and end_index != -1:
                json_string = response_text[start_index : end_index + 1]
                json_string = json_string.replace('```json', '').replace('```', '').strip()
                
                parsed_data = json.loads(json_string)
                user_name = parsed_data.get('identified_user', '').strip().capitalize() or None
                if user_name and user_name in get_default_users():
                     return {"identified_user": user_name}
                return {"identified_user": None}

            print(f"❌ Failed to extract valid JSON from identity NLU: {response_text[:100]}...")
            return {"identified_user": None}
        
        else:
            print(f"⚠️ Ollama Identity NLU returned non-OK status: {response.status_code}")
            return {"identified_user": None}

    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama connection error during Identity NLU parsing: {e}")
        return {"identified_user": None}
    except json.JSONDecodeError:
        print("❌ JSON decode error during Identity NLU parsing.")
        return {"identified_user": None}


# --- PRIMARY COMMAND PROCESSOR (MAIN ENTRY POINT) ---
def process_command(transcript: str, speak_func, chat_history: list, current_user: str):
    """
    Processes the command, using chat_history, and returns a state flag and the
    newly identified user name (or the existing one).
    Returns: (result_flag: str, new_user: str or None)
    """
    
    # 1. --- Check for Local Tools and Exit Commands ---
    local_result = check_local_tools(transcript, speak_func)
    
    if local_result == "EXIT_CONVERSATION":
        return "EXIT_CONVERSATION", None

    # 2. --- USER IDENTIFICATION FLOW ---
    if current_user is None:
        identity_data = llm_nlu_user_identity_parser(transcript)
        identified_user = identity_data.get("identified_user")
        
        if identified_user:
            speak_func(f"Got it. Hi {identified_user}. How can I help you?")
            return "CONTINUE_CONVERSATION", identified_user
        else:
            print("⚠️ User name not recognized. Proceeding with general command.")
            
    # 3. --- QUICK LOCAL UTILITY CHECK (Time/Date) ---
    local_time_result = handle_local_time_check(transcript, speak_func)
    if local_time_result == "HANDLED":
        return "CONTINUE_CONVERSATION", current_user

    # 4. --- NLU Task Routing/Handling (via dedicated module) ---
    nlu_data = llm_nlu_task_parser(transcript, default_user=current_user)
    if nlu_data.get("intent") != "NONE":
        is_handled = handle_task_command(nlu_data, speak_func)
        if is_handled:
            return "CONTINUE_CONVERSATION", current_user

    # 5. --- Go straight to LLM Router (for chat/search) ---
    # PASS CHAT HISTORY to route_command to enable context-aware search query generation
    router_result = route_command(transcript, chat_history) 
    
    action = router_result.get("action", "CHAT").upper()
    search_query = router_result.get("search_query", transcript) 
    
    # 6. --- EXECUTION Logic ---
    assistant_response = "" 

    if action == "SEARCH":
        print(f"🛠️ Executing Search for: {search_query}")
        
        context = search_with_tavily(search_query) 
        
        if not context:
            speak_func("Sorry, I had a problem searching the web.")
            return "CONTINUE_CONVERSATION", current_user

        augmented_prompt = f"""
Use the following search results to answer the user's question.
Provide a concise answer based *only* on the context provided. Do not invent information.

---[SEARCH RESULTS]---
{context}
---[END OF RESULTS]---

# User Context: The user currently speaking is {current_user} (or None if not identified).
User's Question: {transcript}
"""
        assistant_response = send_to_ollama(augmented_prompt, speak_func, chat_history) 

    # --- Default: Regular Chat ---
    else:
        print("🧠 Execution: Regular chat/memory response.")
        assistant_response = send_to_ollama(transcript, speak_func, chat_history) 
    
    # --- Speak the response and handle failure ---
    if assistant_response:
        speak_func(assistant_response)
    else:
        speak_func("I'm sorry, I failed to generate a complete answer for that question.")
    
    # 7. LOG THE CONVERSATION HISTORY (Memory logging)
    if assistant_response:
        chat_history.append({"role": "user", "content": transcript})
        chat_history.append({"role": "assistant", "content": assistant_response})
        
        # Keep history manageable (last 10 turns)
        if len(chat_history) > 10:
            chat_history = chat_history[-10:] 
            
    return "CONTINUE_CONVERSATION", current_user
