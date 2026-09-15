import io
import wave
import numpy as np
import sounddevice as sd
from piper import PiperVoice


class Speaker:
    """
    Zet tekst om in gesproken audio met Piper (lokaal, geen internet nodig
    na het downloaden van de stem) en speelt dit direct af.
    """

    def __init__(self, voice_path: str = "en_US-lessac-medium.onnx"):
        print("TTS-stem laden...")
        self.voice = PiperVoice.load(voice_path)
        print("TTS-stem geladen.")

    def speak(self, text: str):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file)

        buffer.seek(0)
        with wave.open(buffer, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            audio_bytes = wav_file.readframes(wav_file.getnframes())

        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        sd.play(audio, sample_rate)
        sd.wait()


if __name__ == "__main__":
    speaker = Speaker()
    speaker.speak("Hello, I am Sarah.")