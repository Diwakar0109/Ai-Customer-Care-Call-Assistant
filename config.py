# config.py
import os
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY") # This is now critical
# SARVAM_API_TTS is no longer used.

if not SARVAM_API_KEY:
    raise ValueError("SARVAM_API_KEY not found in .env file.")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file.")
if not ELEVEN_API_KEY:
    raise ValueError("ELEVEN_API_KEY not found in .env file.")