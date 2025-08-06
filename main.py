# main.py
import asyncio
import json
import re

import services.excel_service as db_service
import services.rag_service as rag # Re-enabled for post-validation queries
from services.audio_service import AudioService
from services.ai_service import AiService
from utils.conversation_logger import ConversationLogger

# --- Initialization ---
audio = AudioService()
ai_service = AiService()
logger = ConversationLogger(log_directory="customer_calls")
# Re-enable RAG setup
rag.setup_rag_from_file("data/faq.txt")


# --- 1. PROMPTS ---

# Prompt to use BEFORE a tracking ID has been validated
ID_EXTRACTION_PROMPT = """
Your only task is to extract a parcel tracking ID from the user's text.
A tracking ID looks like 'TRK' followed by numbers (e.g., 'TRK1001').
- If a tracking ID is present, respond with ONLY the ID (e.g., "TRK1001").
- If no tracking ID is found, respond with the single word "NONE".

User's Text: "{user_text}"
Your Response:
"""

# Prompt to use AFTER a tracking ID has been validated
POST_VALIDATION_PROMPT = """
You are a function-calling AI model for a validated user. The user's tracking ID is {tracking_id}.
Analyze the user's new query and decide which tool to use.

**Available Tools:**
1. `get_parcel_status`: Use this if the user asks for the status or location of their parcel again.
2. `faq_lookup`: Use this for general questions about policies, returns, cancellations, etc.
3. `end_call`: Use this if the user says "goodbye", "thank you", or indicates the conversation is over.
4. `no_tool`: Use this for conversational filler that doesn't require a tool.

**RULES:**
- The user is ONLY allowed to ask about tracking ID {tracking_id}. If they mention a different ID, tell them you can only discuss {tracking_id} in this session.
- Your response MUST be a single, raw JSON object.

**Examples:**
User Query: "Where is it now?"
Your Action: {{"tool_to_use": "get_parcel_status", "parameters": {{}}}}

User Query: "What is the return policy for this item?"
Your Action: {{"tool_to_use": "faq_lookup", "parameters": {{"query": "return policy"}}}}

User Query: "Okay, thank you, goodbye."
Your Action: {{"tool_to_use": "end_call", "parameters": {{}}}}

User Query: "Okay, can you check TRK5555 for me?"
Your Action: {{"tool_to_use": "deny_new_id", "parameters": {{"response": "I can only provide information for tracking ID {tracking_id} in this call. Would you like to know its current status or something else?"}}}}

**Current User Query:**
"{user_query}"

**Your Action:**
"""

# Generic prompt to generate the final human-readable response
FINAL_RESPONSE_PROMPT = """
You are a helpful customer service assistant. Convert the 'Information Found' into a single, direct sentence.

**RULES:**
- Be direct. DO NOT add conversational filler like 'Of course'.
- If the information is parcel data, state the key facts.
- If the information is from an FAQ, state the answer.
- If the information is an error or a denial message, state it politely.

**Information Found:**
"{information}"

**Your Direct Response:**
"""

# --- 2. HELPER FUNCTIONS ---

def clean_and_parse_json(json_string: str) -> dict:
    start_index = json_string.find('{')
    end_index = json_string.rfind('}')
    if start_index != -1 and end_index != -1:
        json_part = json_string[start_index : end_index + 1]
        try: return json.loads(json_part)
        except json.JSONDecodeError: return {}
    return {}

async def generate_and_speak_response(text_en: str):
    """Generates a spoken response in English and Tamil."""
    print(f"🤖 Assistant (en): {text_en}")
    logger.add_entry("Assistant (en)", text_en)

    response_ta = await ai_service.translate_text(text=text_en)
    print(f"🤖 Assistant (ta): {response_ta}")
    logger.add_entry("Assistant (ta)", response_ta)

    await ai_service.speak_elevenlabs(text=response_ta)

async def handle_single_call():
    """Manages a single, stateful user call session from start to finish."""
    print("\n-------------------- NEW CALL SIMULATION --------------------")
    
    # Session State
    session_state = "AWAITING_ID"
    locked_tracking_id = None
    max_attempts = 3
    attempts = 0

    # Proactive Welcome
    await generate_and_speak_response("Welcome to Parcel Pal support. Please state your tracking ID to begin.")
    
    while True: # The conversation now loops until an end condition
        audio_data = await audio.record_full_utterance()
        if not audio_data: continue

        user_query_en = await ai_service.transcribe_audio_buffer(audio_data)
        if not user_query_en or len(user_query_en.strip()) < 3:
            print("INFO: Transcription too short or empty. Listening again.")
            continue
            
        print(f"👤 You (en): {user_query_en}")
        logger.add_entry("Customer (en)", user_query_en)

        # --- STATE MACHINE LOGIC ---
        
        if session_state == "AWAITING_ID":
            prompt = ID_EXTRACTION_PROMPT.format(user_text=user_query_en)
            extracted_id = (await ai_service.process_llm_query(prompt)).strip()
            
            if extracted_id.upper() != "NONE" and extracted_id.startswith("TRK"):
                status_info = db_service.get_parcel_status(extracted_id)
                if status_info:
                    locked_tracking_id = extracted_id
                    session_state = "ID_VALIDATED"
                    info_for_prompt = f"Data for tracking ID {locked_tracking_id}: {json.dumps(status_info)}"
                    final_prompt = FINAL_RESPONSE_PROMPT.format(information=info_for_prompt)
                    response_en = await ai_service.process_llm_query(final_prompt)
                    await generate_and_speak_response(f"Thank you. I have located parcel {locked_tracking_id}. {response_en} How else can I help you?")
                else:
                    await generate_and_speak_response(f"Sorry, I couldn't find any information for tracking ID {extracted_id}. Please try another ID.")
            else:
                attempts += 1
                if attempts >= max_attempts:
                    await generate_and_speak_response("I'm having trouble understanding. Please call back later. Goodbye.")
                    return # End call
                await generate_and_speak_response("I'm sorry, I couldn't find a tracking ID. Please clearly state your tracking ID.")

        elif session_state == "ID_VALIDATED":
            prompt = POST_VALIDATION_PROMPT.format(tracking_id=locked_tracking_id, user_query=user_query_en)
            action_json_str = await ai_service.process_llm_query(prompt)
            action = clean_and_parse_json(action_json_str)

            tool = action.get("tool_to_use")
            params = action.get("parameters", {})
            information = ""

            if tool == "get_parcel_status":
                status_info = db_service.get_parcel_status(locked_tracking_id)
                information = f"Data for tracking ID {locked_tracking_id}: {json.dumps(status_info)}"
            elif tool == "faq_lookup":
                information = rag.query_rag(params.get("query", user_query_en))
            elif tool == "deny_new_id":
                information = params.get("response", "You are not authorised to view other details")
            elif tool == "end_call":
                await generate_and_speak_response("Thank you for calling Parcel Pal. Goodbye!")
                return # End call
            else: # no_tool or fallback
                information = "You should ask only about the parcel"

            final_prompt = FINAL_RESPONSE_PROMPT.format(information=information)
            response_en = await ai_service.process_llm_query(final_prompt)
            await generate_and_speak_response(response_en)


async def main_loop():
    """Waits for user input to start a new call session."""
    print("\n--- Parcel Pal Stateful IVR Assistant ---")
    while True:
        await handle_single_call()
        logger.save_log()
        input("\n--- Call Ended. Press Enter to simulate a new call or Ctrl+C to exit. ---")
        logger.__init__(log_directory="customer_calls") # Reset logger for the new call


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nShutting down Parcel Pal. Goodbye!")
    finally:
        audio.shutdown()