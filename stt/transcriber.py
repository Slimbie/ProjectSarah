import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


class Transcriber:
    """
    Neemt audio op vanaf het moment dat spraak gedetecteerd wordt, en stopt
    zodra het even stilte hoort (of na een maximale duur). Wordt pas
    aangeroepen NA een wake word trigger, dus mag zwaarder zijn dan de
    wake word listener.
    """

    def __init__(
        self,
        model_size: str = "base",
        silence_duration: float = 1.2,
        max_wait_for_speech: float = 4.0,
        max_record_seconds: float = 12.0,
    ):
        print("STT-model laden (bij eerste keer wordt het ook gedownload, kan even duren)...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("STT-model geladen.")

        self.sample_rate = 16000
        self.chunk_size = 1280  # ~80ms per stukje, zelfde stijl als de wake word listener
        self.silence_threshold = 0.02  # wordt elke keer opnieuw bepaald door calibrate_silence_threshold()
        self.silence_duration = silence_duration
        self.max_wait_for_speech = max_wait_for_speech
        self.max_record_seconds = max_record_seconds

    def play_beep(self):
        """Korte piep als signaal dat je nu mag spreken. Placeholder tot Fase 4 (TTS)."""
        duration = 0.15
        freq = 880
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        tone = 0.3 * np.sin(2 * np.pi * freq * t)
        sd.play(tone, self.sample_rate)
        sd.wait()

    def _rms(self, audio_chunk: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2)))

    def calibrate_silence_threshold(self, duration: float = 1.0, margin: float = 3.0) -> float:
        """
        Meet heel even de achtergrondruis (blijf stil) en stelt de
        stilte-drempel in op een marge daarboven. Voorkomt dat een vaste,
        geraden waarde niet past bij jouw microfoon/omgeving.
        """
        print("Kalibreren... (blijf even stil)")
        samples = sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate,
                          channels=1, dtype="float32")
        sd.wait()
        ambient_rms = self._rms(samples.flatten())
        threshold = max(ambient_rms * margin, 0.003)  # ondergrens tegen extreem stille ruimtes
        print(f"Achtergrondruis: {ambient_rms:.5f} -> drempel ingesteld op: {threshold:.5f}")
        return threshold

    def record_audio(self) -> np.ndarray:
        print("Luisteren...")
        recorded_chunks = []
        speech_started = False
        silence_start = None
        wait_start = time.time()
        record_start = None

        with sd.InputStream(channels=1, samplerate=self.sample_rate,
                             dtype="float32", blocksize=self.chunk_size) as stream:
            while True:
                chunk, _ = stream.read(self.chunk_size)
                chunk = chunk.flatten()
                volume = self._rms(chunk)
                now = time.time()

                if not speech_started:
                    if volume > self.silence_threshold:
                        speech_started = True
                        record_start = now
                        recorded_chunks.append(chunk)
                    elif now - wait_start > self.max_wait_for_speech:
                        print("Geen spraak gedetecteerd, gestopt met luisteren.")
                        break
                else:
                    recorded_chunks.append(chunk)

                    if volume > self.silence_threshold:
                        silence_start = None
                    else:
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start > self.silence_duration:
                            break

                    if now - record_start > self.max_record_seconds:
                        print("Maximale opnametijd bereikt.")
                        break

        if not recorded_chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(recorded_chunks)

    def transcribe(self) -> str:
        self.silence_threshold = self.calibrate_silence_threshold()
        self.play_beep()
        audio = self.record_audio()
        if audio.size == 0:
            return ""
        segments, _ = self.model.transcribe(audio, language="en")
        text = " ".join(segment.text for segment in segments).strip()
        return text


if __name__ == "__main__":
    transcriber = Transcriber()
    result = transcriber.transcribe()
    print(f"Getranscribeerd: {result}")