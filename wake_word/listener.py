import time
import sounddevice as sd
import numpy as np
from openwakeword.model import Model


class WakeWordListener:
    """
    Luistert continu naar de microfoon en checkt elk klein stukje audio
    op het wake word. Heel licht: dit mag continu op de achtergrond draaien.
    """

    def __init__(self, wakeword: str = "hey_jarvis", threshold: float = 0.5,
                 cooldown_seconds: float = 1.5, warmup_chunks: int = 20):
        self.model = Model(wakeword_models=[wakeword], inference_framework="onnx")
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.warmup_chunks = warmup_chunks  # ~20 chunks * 80ms = ~1.6 sec genegeerd na opstarten
        self.last_trigger_time = 0.0
        self.sample_rate = 16000
        self.chunk_size = 1280

    def wait_for_wakeword(self) -> str:
        """
        Blokkeert tot het wake word gehoord wordt, en geeft dan de naam
        van het gedetecteerde wake word terug.
        """
        with sd.InputStream(channels=1, samplerate=self.sample_rate,
                             dtype="int16", blocksize=self.chunk_size) as stream:
            chunks_seen = 0
            while True:
                audio_chunk, _ = stream.read(self.chunk_size)
                audio_chunk = audio_chunk.flatten()
                prediction = self.model.predict(audio_chunk)
                chunks_seen += 1

                if chunks_seen <= self.warmup_chunks:
                    continue  # buffer nog aan het vullen, scores nog niet betrouwbaar

                for wakeword_name, score in prediction.items():
                    now = time.time()
                    if score > self.threshold and (now - self.last_trigger_time) > self.cooldown_seconds:
                        self.last_trigger_time = now
                        return wakeword_name


if __name__ == "__main__":
    listener = WakeWordListener(wakeword="hey_jarvis")
    print("Sarah luistert... (Ctrl+C om te stoppen)")
    while True:
        detected = listener.wait_for_wakeword()
        print(f"Wake word gedetecteerd: {detected}")