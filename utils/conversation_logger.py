# utils/conversation_logger.py
# A reusable, self-contained module for logging conversations.

import datetime
import os

class ConversationLogger:
    """
    Manages the logging of a conversation by tracking speaker entries
    and saving the final transcript to a uniquely named file.
    """
    def __init__(self, log_directory: str = "conversation_logs"):
        """
        Initializes the ConversationLogger.

        Args:
            log_directory (str): The directory where log files will be saved.
                                 It will be created if it doesn't exist.
        """
        self.log_directory = log_directory
        self.transcript = []
        self.session_start_time = datetime.datetime.now()
        
        # Generate a unique filename for this session
        timestamp_str = self.session_start_time.strftime("%Y-%m-%d_%H-%M-%S")
        self.filename = f"conversation_{timestamp_str}.txt"
        self.filepath = os.path.join(self.log_directory, self.filename)
        
        # Ensure the log directory exists
        os.makedirs(self.log_directory, exist_ok=True)
        
        print(f"📝 ConversationLogger initialized. Log will be saved to '{self.filepath}'")

    def add_entry(self, speaker: str, text: str):
        """
        Adds a new entry to the conversation transcript.

        Args:
            speaker (str): The identifier of the speaker (e.g., 'Customer', 'Assistant').
            text (str): The transcribed text spoken by the speaker.
        """
        if not text or not text.strip():
            return
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        clean_text = text.strip()
        
        entry = {
            "speaker": speaker,
            "text": clean_text,
            "timestamp": timestamp
        }
        self.transcript.append(entry)
        
        # Provide immediate feedback in the console for clarity
        print(f"LOGGED: [{timestamp}] {speaker}: {clean_text}")

    def save_log(self):
        """
        Saves the complete conversation transcript to the designated file.
        """
        if not self.transcript:
            print("INFO: No conversation to save.")
            return

        print(f"\n💾 Saving final transcript to '{self.filepath}'...")
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(f"--- Conversation Log ---\n")
                f.write(f"Session Date: {self.session_start_time.strftime('%Y-%m-%d')}\n")
                f.write(f"Session Start Time: {self.session_start_time.strftime('%H:%M:%S')}\n")
                f.write("-" * 26 + "\n\n")

                for entry in self.transcript:
                    line = f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}\n"
                    f.write(line)
            
            print(f"✅ Transcript saved successfully.")
        except IOError as e:
            print(f"❌ CRITICAL ERROR: Could not write log file to '{self.filepath}'. Reason: {e}")