# services/ai_service.py
import asyncio
import io
import re
import wave
from typing import AsyncGenerator

from sarvamai import AsyncSarvamAI
from groq import AsyncGroq
from elevenlabs.client import AsyncElevenLabs
import pyaudio

from config import SARVAM_API_KEY, GROQ_API_KEY, ELEVEN_API_KEY

class AiService:
    """
    A service orchestrating a multilingual AI pipeline.
    - Uses reliable buffer-based STT (Sarvam).
    - Uses fast logic layer (Groq).
    - Uses reliable translation (Sarvam).
    - Uses high-quality, reliable non-streaming TTS (ElevenLabs).
    """

    def __init__(self):
        self.sarvam_client = AsyncSarvamAI(api_subscription_key=SARVAM_API_KEY)
        self.groq_client = AsyncGroq(api_key=GROQ_API_KEY)
        self.eleven_client = AsyncElevenLabs(api_key=ELEVEN_API_KEY)
        print("AI Services initialized (Sarvam STT/Translate, Groq LLM, ElevenLabs TTS).")

    async def transcribe_audio_buffer(self, audio_data: bytes) -> str:
        if not audio_data: return ""
        buffer = io.BytesIO()
        try:
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_data)
            buffer.seek(0)
            response = await self.sarvam_client.speech_to_text.translate(
                file=buffer, model="saaras:v2.5", prompt="A customer is talking."
            )
            return response.transcript.strip()
        except Exception as e:
            print(f"❌ Error during STT processing: {e}")
            return ""

    async def process_llm_query(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant", messages=messages, max_tokens=200, temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error during Groq LLM processing: {e}")
            return "{}"

    async def translate_text(self, text: str, source_lang: str = "en-IN", target_lang: str = "ta-IN") -> str:
        if not text: return ""
        try:
            response = await self.sarvam_client.text.translate(
                input=text, source_language_code=source_lang, target_language_code=target_lang
            )
            return response.translated_text
        except Exception as e:
            print(f"❌ Translation Error: {e}")
            return "Error translating text."

    async def speak_elevenlabs(self, text: str):
        """
        Generates audio for the given text using the modern ElevenLabs API
        and plays it back using PyAudio.
        """
        print(f"🗣️  Assistant (speaking via ElevenLabs): {text}")
        try:
            # --- THE FINAL FIX: Replace "Serena" with your actual Voice ID ---
            # For example, Rachel's ID is "21m00Tcm4TlvDq8ikWAM"
            # PASTE YOUR COPIED VOICE ID HERE:
            YOUR_VOICE_ID = "izSi63MW0URDnszWlZMX" # Replace with your ID from VoiceLab

            audio_stream_generator = self.eleven_client.text_to_speech.convert(
                voice_id=YOUR_VOICE_ID,
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="pcm_16000"
            )

            audio_chunks = []
            async for chunk in audio_stream_generator:
                if chunk:
                    audio_chunks.append(chunk)

            if audio_chunks:
                audio_data = b"".join(audio_chunks)
                
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=16000,
                                output=True)
                
                stream.write(audio_data)

                stream.stop_stream()
                stream.close()
                p.terminate()
                print("Audio playback finished.")
            else:
                print("TTS returned no audio data.")

        except Exception as e:
            print(f"❌ ElevenLabs TTS Error: {e}")

