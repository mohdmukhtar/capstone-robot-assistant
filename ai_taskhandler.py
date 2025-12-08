import os
import requests
import datetime
import json
import database3 as db
from utils3 import MODEL_NAME, get_default_users 


# --- OLLAMA RESPONSE GENERATOR FOR TASKS ---
def llm_generate_task_response(intent: str, user_name: str, task_data: dict, speak_func):
    """
    Uses Ollama to generate a conversational, friendly response based on the
    successful or failed outcome of a task command.
    """
    
    # 1. Prepare a specialized prompt for conversational output
    task_data_json = json.dumps(task_data)
    
    RESPONSE_PROMPT = f"""
    You are Alex, a super friendly and casual assistant. Your goal is to deliver the result of a task command in a conversational, human-like manner, suitable for smooth TTS reading.

    **CRITICAL STYLING RULES:**
    1. Be friendly, energetic, and use contractions (e.g., "you've got", "it's done").
    2. Your response must be brief and directly convey the outcome of the command.
    3. Do not use Markdown formatting (asterisks, hashtags, backticks).
    4. Speak directly to the user (use 'you').

    **TASK DATA:**
    - Intent: {intent}
    - User: {user_name}
    - Data: {task_data_json}

    **RESPONSE SCENARIOS:**

    # 1. LIST_TASKS
    - Data has a list of 'reminders' (task, date, id) or is empty.
    - If empty: Respond with a brief, happy phrase that the user is caught up. (e.g., "Hey, you're totally caught up, nice job!")
    - If tasks exist: Use a friendly opener (e.g., "Oh yeah for sure, here's what you've got...") and list the tasks casually. Mention the total count. Separate each task with a comma and a period. (e.g., "...first, finish the robot arm coding, that's due tomorrow, second, call the manager, that's due next week.")

    # 2. ADD_TASK
    - Data contains 'task' and 'due_date' (which may be NULL).
    - Respond with a brief confirmation that the task was successfully added. (e.g., "Got it! I've added that task for you, super easy.")

    # 3. COMPLETE_TASK
    - Data contains 'task_description' and 'success' (True/False).
    - If success is True: Confirm the task is marked as done, referring to it by a keyword. (e.g., "All set! The server logs task is officially done.")
    - If success is False: State clearly that the task wasn't found. (e.g., "Hmm, I couldn't actually find a task matching those keywords.")
    
    # 4. RESCHEDULE_TASK
    - Data contains 'task_description', 'new_date', 'current_date', and 'success' (True/False).
    - If success is True: Confirm the task is rescheduled and mention the new date. (e.g., "Done deal. I've moved the server logs task to December 1st for you.")
    - If success is False: State clearly that the task wasn't found.

    Generate the response based on the Task Data and Scenarios.
    """
    
    print(f"🧠 Generating conversational response for {intent}...")
    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        speak_func("I can't talk right now. The Ollama API URL is missing.")
        return

    try:
        # Use a low temperature for reliable, conversational style 
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/generate",
            json={
                "model": MODEL_NAME, # TASK_MODEL_NAME could be used here if you change it later
                "prompt": RESPONSE_PROMPT,
                "stream": False,
                "options": {"temperature": 0.5, "num_predict": 512, "num_ctx": 4096},
            },
            timeout=15
        )
        if response.ok:
            response_text = response.json()['response'].strip()
            # Clean up potential LLM code block wrappers
            final_response = response_text.replace('```json', '').replace('```', '').replace('```text', '').strip()
            speak_func(final_response)
        else:
            speak_func(f"Uh oh, my internal brain had a problem generating a {intent} response.")

    except requests.exceptions.RequestException:
        speak_func("I'm having trouble connecting to my response generator right now.")
    except Exception as e:
        print(f"❌ Response generation failed: {e}")
        speak_func("Oops, something went wrong while I was trying to talk about your tasks.")


# --- NLU TASK PARSER (UNMODIFIED) ---
def llm_nlu_task_parser(transcript: str, default_user: str = None):
    # ... (Keep this function EXACTLY as it was in the previous step) ...
    """
    Uses Ollama to parse the user's request into a structured JSON object 
    for task management, optionally defaulting the user.
    """
    default_users = get_default_users() 
    
    # If a user is known, use them as the primary default
    default_user_for_prompt = default_user if default_user else 'Patrick'
    
    NLU_PROMPT = f"""
You are a robust Natural Language Understanding (NLU) service for task management.

Available USER NAMES: {', '.join(default_users)}
Currently Active User (default if no name specified): {default_user_for_prompt}
Today's Date: {datetime.date.today().strftime('%Y-%m-%d')}

Question: "{transcript}"

JSON Output Format (MUST output a single JSON object):
{{
  "intent": "ADD_TASK" or "LIST_TASKS" or "COMPLETE_TASK" or "RESCHEDULE_TASK" or "NONE",
  "user_name": "Extracted name from the Available USER NAMES list (e.g., Patrick), or use the ACTIVE user '{default_user_for_prompt}' if the request is ambiguous (e.g., 'my task').",
  "task_description": "The full, extracted description of the task for ADD_TASK, or NULL otherwise.",
  "due_date": "The extracted or inferred date (e.g., '2025-11-27', 'tomorrow', 'next Tuesday') for ADD_TASK or RESCHEDULE_TASK, or NULL if not specified. Use YYYY-MM-DD format if possible, otherwise use the phrase.",
  "keywords": "A concise, lower-cased keyword phrase containing **1-3 main words** for matching tasks (e.g., '%server logs%', '%call manager%') for LIST_TASKS/COMPLETE_TASK/RESCHEDULE_TASK, or NULL if intent is ADD_TASK or NONE. **MUST** include the percent symbols."
}}

**CRITICAL RULES:**
1. The 'user_name' key MUST be filled with a capitalized name from the list.
2. If the request is not clearly a task/reminder, set intent to NONE.
"""
    print(f"🧠 NLU Task Parsing via Ollama (Default User: {default_user_for_prompt})...")
    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        return {"intent": "NONE"}

    try:
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/generate",
            json={
                "model": MODEL_NAME, 
                "prompt": NLU_PROMPT,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512, "num_ctx": 4096},
            },
            timeout=15
        )
        if response.ok:
            response_text = response.json()['response'].strip()
            
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            
            if start_index != -1 and end_index != -1:
                json_string = response_text[start_index : end_index + 1]
                json_string = json_string.replace('```json', '').replace('```', '').strip()
                
                parsed_data = json.loads(json_string)
                parsed_data['user_name'] = parsed_data.get('user_name', '').strip().capitalize() or default_user_for_prompt
                return parsed_data

            return {"intent": "NONE"}
        
        else:
            return {"intent": "NONE"}

    except requests.exceptions.RequestException:
        return {"intent": "NONE"}
    except json.JSONDecodeError:
        return {"intent": "NONE"}
        

# --- V3 TASK HANDLER (MODIFIED TO USE LLM FOR RESPONSE) ---
def handle_task_command(nlu_data, speak_func):
    """
    Executes the task management based on the NLU output and database functions.
    Delegates final conversational response generation to llm_generate_task_response.
    """
    intent = nlu_data.get("intent", "NONE")
    user_name = nlu_data.get("user_name") 
    
    if intent == "NONE":
        return False
        
    user_id = db.get_user_id_by_name(user_name)

    if not user_id:
        speak_func(f"Well, I can't seem to find a user named {user_name} in my system. Sorry.")
        return True # Handled, but failed internally
    
    task_data = {} # Data package to send to the LLM response generator

    # --- ADD TASK ---
    if intent == "ADD_TASK":
        task = nlu_data.get("task_description")
        due_date_str = nlu_data.get("due_date")
        
        if not task:
            speak_func(f"Oh, I need a task description for {user_name} before I can add it.")
            return True
        
        db.add_reminder(user_id, task, due_date_str)
        task_data = {"task": task, "due_date": due_date_str}
        
    # --- RESCHEDULE TASK ---
    elif intent == "RESCHEDULE_TASK":
        keywords = nlu_data.get("keywords")
        new_date = nlu_data.get("due_date")

        if not keywords or not new_date:
            speak_func(f"I need both a task keyword and a new date to reschedule for {user_name}. What should I change?")
            return True
            
        reminder = db.get_reminder_by_keywords(user_id, keywords)
        
        if reminder:
            task_description, current_date, reminder_id = reminder
            db.update_reminder_due_date(reminder_id, new_date)
            task_data = {
                "success": True, 
                "task_description": task_description, 
                "current_date": current_date, 
                "new_date": new_date
            }
        else:
            task_data = {"success": False, "keywords": keywords}

    # --- LIST TASKS ---
    elif intent == "LIST_TASKS":
        reminders = db.get_user_reminders(user_id)
        task_data = {"reminders": reminders}
        
    # --- COMPLETE TASK ---
    elif intent == "COMPLETE_TASK":
        keywords = nlu_data.get("keywords")
        
        if not keywords:
            speak_func(f"I need to know which task to mark complete for {user_name}. Can you give me a keyword?")
            return True
            
        reminder = db.get_reminder_by_keywords(user_id, keywords)
        
        if reminder:
            task_description, _, reminder_id = reminder
            db.mark_reminder_completed(reminder_id)
            task_data = {"success": True, "task_description": task_description}
        else:
            task_data = {"success": False, "keywords": keywords}
            
    # --- Generate the Conversational TTS Response ---
    llm_generate_task_response(intent, user_name, task_data, speak_func)
    
    return True
    