# services/audio_service.py
import pyaudio
import webrtcvad
import collections
import asyncio

class AudioService:
    """
    A service for capturing a single, complete utterance from the microphone using VAD.
    """
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    FRAME_DURATION_MS = 30
    CHUNK_SIZE = int(RATE * FRAME_DURATION_MS / 1000)
    VAD_AGGRESSIVENESS = 3
    SILENCE_LIMIT_S = 1.2
    PRE_SPEECH_PADDING_S = 0.5

    def __init__(self):
        print("Initializing Audio Service with smart VAD...")
        self.vad = webrtcvad.Vad(self.VAD_AGGRESSIVENESS)
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
            input=True, frames_per_buffer=self.CHUNK_SIZE
        )
        print("🎤 Audio Service is ready and listening.")

    async def record_full_utterance(self) -> bytes:
        """
        Listens to the microphone, records a full utterance, and returns the raw audio data.
        """
        loop = asyncio.get_running_loop()
        
        num_padding_frames = int(self.PRE_SPEECH_PADDING_S * 1000 / self.FRAME_DURATION_MS)
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        
        triggered = False
        recorded_frames = bytearray()
        num_silent_frames_after_speech = 0
        max_silent_frames = int(self.SILENCE_LIMIT_S * 1000 / self.FRAME_DURATION_MS)

        print("\nListening for your query...")
        while True:
            frame = await loop.run_in_executor(None, self.stream.read, self.CHUNK_SIZE)
            
            is_speech = self.vad.is_speech(frame, self.RATE)

            if not triggered:
                ring_buffer.append(frame)
                if is_speech:
                    print("🟢 Speech detected, recording...")
                    triggered = True
                    recorded_frames.extend(b''.join(list(ring_buffer)))
                    ring_buffer.clear()
            else:
                recorded_frames.extend(frame)
                if not is_speech:
                    num_silent_frames_after_speech += 1
                else:
                    num_silent_frames_after_speech = 0

                if num_silent_frames_after_speech > max_silent_frames:
                    print("🔴 Silence detected, processing utterance...")
                    return bytes(recorded_frames)
            
    def shutdown(self):
        print("Shutting down Audio Service...")
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        if self.pa:
            self.pa.terminate()

