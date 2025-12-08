import os
import requests
import datetime
import json
import re
# Import from the utils file to get necessary configs
from utils3 import MODEL_NAME, get_default_users 
import database3 as db # Assuming your database module is named database3


# --- OLLAMA RESPONSE GENERATOR FOR TASKS (CRITICAL DATE FIX) ---
def llm_generate_task_response(intent: str, user_name: str, task_data: dict, speak_func):
    """
    Uses Ollama to generate both a structured text output (for screen/reporting) and 
    a conversational speech response (for TTS).
    """
    
    # 1. Prepare a specialized prompt for conversational output
    task_data_json = json.dumps(task_data)
    
    # Get today's date for accurate LLM calendar anchoring
    today_date = datetime.date.today().strftime('%Y-%m-%d')

    # --- ENHANCED PROMPT FOR CONVERSATIONAL SPEECH ---
    RESPONSE_PROMPT = f"""
    You are Alex, a super friendly and casual assistant. Your goal is to generate two distinct outputs in a single JSON block: 
    1. A formal, structured text output for display/reporting (required for ALL intents).
    2. A conversational, human-like speech output for smooth TTS reading (required for ALL intents).

    **SYSTEM CONTEXT:**
    - Today's Date: {today_date}
    - Intent: {intent}
    - User: {user_name}
    - Data: {task_data_json}

    **CRITICAL STYLING RULES for Conversational Speech:**
    1. Be **highly** friendly, energetic, and use contractions (e.g., "you've got", "it's done"). **Your tone should feel lively and casual.**
    2. Responses must be brief and directly convey the outcome.
    3. **CRITICAL FORMATTING RULE:** Do not use Markdown formatting (asterisks, hashtags, backticks) **AND ABSOLUTELY DO NOT USE ANY QUOTATION MARKS (', ")** in the conversational speech.
    4. Speak directly to the user (use 'you').
    5. **CRITICAL GREETING RULE:** For intents ADD_TASK, COMPLETE_TASK, and RESCHEDULE_TASK, **start directly with the confirmation**. Do not use an opening greeting like 'Hey [User]' or 'Got it [User]'.

    6. **CRITICAL DATE RULE (ULTIMATE FIX: STRICT LITERAL DATES):** You MUST refer to dates based on the current intent:
       * **IF INTENT IS ADD_TASK or RESCHEDULE_TASK (USER REQUESTED CHANGE):** You **MUST** state the new date **explicitly** using the Month, Day, and Year from the data (e.g., 'due on February 13th, 2025' or 'due on 2026-01-17'). **ABSOLUTELY FORBIDDEN** to use relative terms like "tomorrow," "next week," or "next Sunday." State the full, literal date clearly.
       * **IF INTENT IS LIST_TASKS:** Follow the "Future Proximity Check" rules below.
       
       * **FUTURE PROXIMITY CHECK (FOR LIST_TASKS ONLY):**
         * IF DUE TODAY: Use "due today."
         * IF DUE TOMORROW: Use "due tomorrow."
         * IF DUE LATER (more than one day away): State the month and day number (e.g., 'due on January 13th').
       * **PAST DATES (ALL INTENTS):** State clearly that the task **was due** on a specific past day (e.g., 'which was due last Tuesday, November 11th').

    **JSON Output Format (MUST output a single JSON object):**
    {{
      "structured_text": "A clear, multi-line, non-conversational summary for reporting. Use the format: ACTION: [ACTION NAME]\\nDetails: [Relevant data].",
      "conversational_speech": "The friendly, casual response ready for speaking."
    }}

    **RESPONSE SCENARIOS:**

    # 1. LIST_TASKS
    - Data has a list of 'reminders' (task, date, id). **THE LIST IS ALREADY SORTED BY DUE DATE (SOONEST FIRST).**
    - 'structured_text': Must list all tasks clearly, using the explicit dates from the Data. Format: 'ACTION: LISTED TASKS\\n[Task description] (Due: [YYYY-MM-DD or date phrase])\\n[Next task description]...' Use the exact date if provided. Use '\\n' for new lines. **DO NOT USE NUMBERING.**
    - 'conversational_speech': Use a friendly opener, list tasks casually, strictly following the CRITICAL DATE RULE. **MUST END** with the question: 'Do you want to add, complete, or reschedule any of these?'

    # 2. ADD_TASK
    - Data contains 'task' and 'due_date'.
    - 'structured_text': Format: 'ACTION: ADDED TASK\\nTask: [task]\\nDue: [due_date]'.
    - 'conversational_speech': Confirm the task was added, strictly following the CRITICAL DATE RULE (which mandates a literal date). **MUST END** with the follow-up question: 'Anything else you want to remove, add, or move around?'

    # 3. COMPLETE_TASK
    - Data contains 'task_description' and 'success'.
    - 'structured_text': If success is True: 'ACTION: COMPLETED TASK\\nTask: [task_description]'. If False: 'ACTION: FAILED TO COMPLETE TASK\\nKeywords: [keywords]'.
    - 'conversational_speech': If successful, confirm the completion and **MUST END** with the follow-up question: 'Anything else you want to remove, add, or move around?'. If failed, explain the failure and use a generic closing.
    
    # 4. RESCHEDULE_TASK
    - Data contains 'task_description', 'new_date', 'current_date', and 'success'.
    - 'structured_text': If success is True: 'ACTION: RESCHEDULED TASK\\nTask: [task_description]\\nOld Due: [current_date]\\nNew Due: [new_date]'. If False: 'ACTION: FAILED TO RESCHEDULE TASK\\nKeywords: [keywords]'.
    - 'conversational_speech': If successful, confirm the rescheduling, strictly following the CRITICAL DATE RULE (which mandates a literal date). **MUST END** with the follow-up question: 'Anything else you want to remove, add, or move around?'. If failed, explain the failure and use a generic closing.

    Generate the response based on the Task Data and Scenarios.
    """
    
    print(f"🧠 Generating conversational response for {intent}...")
    OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "").strip()
    if not OLLAMA_URL:
        speak_func("I can't talk right now. The Ollama API URL is missing.")
        return

    try:
        response = requests.post(
            OLLAMA_URL.rstrip('/') + "/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": RESPONSE_PROMPT,
                "stream": False,
                "options": {"temperature": 0.5, "num_predict": 512, "num_ctx": 4096},
            },
            timeout=15
        )
        if response.ok:
            response_text = response.json().get('response', '').strip()
            
            # Extract JSON block
            start_index = response_text.find('{')
            end_index = response_text.rfind('}')
            
            if start_index != -1 and end_index != -1:
                json_string = response_text[start_index : end_index + 1]
                json_string = json_string.replace('```json', '').replace('```', '').replace('```text', '').strip()
                
                try:
                    parsed_response = json.loads(json_string)
                    structured_text = parsed_response.get("structured_text")
                    conversational_speech = parsed_response.get("conversational_speech", "Oops, I forgot what I was supposed to say.")
                    
                    if structured_text:
                        print(f"--- Structured Report Output for {intent} ---\n{structured_text}\n---------------------------------------------")

                    speak_func(conversational_speech)
                
                except json.JSONDecodeError:
                    print(f"❌ JSON Decode Error in Task Response Generator. Raw response was: {response_text[:200]}...")
                    speak_func("I successfully processed that, but I had a little trouble generating a perfect response.")

            else:
                 print(f"❌ Failed to extract JSON from task generator. Raw response was: {response_text[:200]}...")
                 speak_func("I successfully processed that, but I had a little trouble generating a perfect response.")

        else:
            speak_func(f"Uh oh, my internal brain had a problem generating a {intent} response.")

    except requests.exceptions.RequestException:
        speak_func("I'm having trouble connecting to my response generator right now.")
    except Exception as e:
        print(f"❌ Response generation failed: {e}")
        speak_func("Oops, something went wrong while I was trying to talk about your tasks.")


# --- NLU TASK PARSER (IMPROVED KEYWORD EXTRACTION & INTENT PRIORITY) ---
def llm_nlu_task_parser(transcript: str, default_user: str = None):
    """
    Uses Ollama to parse the user's request into a structured JSON object 
    for task management, optionally defaulting the user.
    """
    default_users = get_default_users() 
    
    default_user_for_prompt = default_user if default_user else 'Patrick'
    
    NLU_PROMPT = f"""
You are a robust Natural Language Understanding (NLU) service for task management. Your primary goal is to **STRICTLY** and **ONLY** identify requests that involve scheduling, remembering, or completing a future action.

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
  "keywords": "A concise, lower-cased keyword phrase containing **1-2 short, unique words** for matching tasks (e.g., '%speech%', '%assembly%') for LIST_TASKS/COMPLETE_TASK/RESCHEDULE_TASK, or NULL if intent is ADD_TASK or NONE. **MUST** include the percent symbols. **PRIORITIZE SHORT, UNIQUE TERMS OVER LONG PHRASES.**"
}}

**CRITICAL RULES:**
1. The 'user_name' key MUST be filled with a capitalized name from the list.
2. **STRICT TASK DEFINITION:** A task MUST contain explicit verbs or phrases related to *remembering, scheduling, or completing an action.* **If the request is about scheduling or rescheduling a task (e.g., 'Can I reschedule the standard parts task to...'), the intent MUST be RESCHEDULE_TASK, not NONE.**
    * **Examples of tasks:** 'Remind me to call John,' 'Add a meeting to my list,' 'I need to check the server logs.'
    * **Examples of NON-TASKS (set intent to NONE):** 'What's the time?', 'What's the best way to make a smoothie?', 'Who is Nelson Mandela?', 'I need a good NUC computer model.'
3. If the request is a question seeking information or general knowledge, set intent to NONE.
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
            response_text = response.json().get('response', '').strip()
            
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
        

# --- V3 TASK HANDLER (NO CHANGE NEEDED HERE, RELIES ON NLU/RESPONSE FIXES) ---
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
        return True 
    
    task_data = {} # Data package to send to the LLM response generator

    # --- ADD TASK ---
    if intent == "ADD_TASK":
        task = nlu_data.get("task_description")
        due_date_str = nlu_data.get("due_date")
        
        if not task:
            speak_func(f"Oh, I need a task description for {user_name} before I can add it.")
            return True
        
        # NOTE: Date parsing must occur before db.add_reminder. Since we cannot add 
        # a resolver, the raw string is used, relying on the DB/LLM to handle the format.
        db.add_reminder(user_id, task, due_date_str)
        task_data = {"task": task, "due_date": due_date_str}
        
    # --- RESCHEDULE TASK ---
    elif intent == "RESCHEDULE_TASK":
        keywords = nlu_data.get("keywords")
        new_date = nlu_data.get("due_date")

        if not keywords or not new_date:
            speak_func(f"I need both a task keyword and a new date to reschedule for {user_name}. What should I change?")
            return True
            
        # NOTE: Date parsing must occur before db.update_reminder_due_date. 
        # The raw string is used here.
        
        reminder = db.get_reminder_by_keywords(user_id, keywords)
        
        if reminder:
            task_description, current_date, reminder_id = reminder
            db.update_reminder_due_date(reminder_id, new_date) 
            task_data = {
                "success": True, 
                "task_description": task_description, 
                "current_date": current_date, 
                "new_date": new_date # Use the potentially raw/unresolved date for LLM
            }
        else:
            task_data = {"success": False, "keywords": keywords.strip('%')}

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
            task_data = {"success": False, "keywords": keywords.strip('%')}
            
    # --- Generate the Conversational TTS Response ---
    llm_generate_task_response(intent, user_name, task_data, speak_func)
    
    return True
