import re
import time
import threading
import numpy as np
import sounddevice as sd
import tkinter as tk
from skills.base_skill import BaseSkill


def play_alert_beep(frequency: float = 1000, duration: float = 0.3):
    """Één luide piep, duidelijk hoorbaarder dan de zachte STT-bevestigingspiep."""
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = 0.9 * np.sin(2 * np.pi * frequency * t)
    sd.play(tone, sample_rate)
    sd.wait()


class TimerSkill(BaseSkill):
    """
    Zet een timer met een eigen klein schermpje (countdown, pauze- en
    annuleerknop). Draait in zijn eigen thread, zodat Sarah intussen
    gewoon door blijft luisteren naar nieuwe opdrachten.
    """

    PATTERN = re.compile(r"timer for (\d+)\s*(second|seconds|minute|minutes|hour|hours)")

    def __init__(self, speaker):
        self.speaker = speaker

    def can_handle(self, text: str) -> bool:
        return bool(self.PATTERN.search(text.lower()))

    def handle(self, text: str) -> str:
        match = self.PATTERN.search(text.lower())
        amount = int(match.group(1))
        unit = match.group(2)

        seconds = amount
        if "minute" in unit:
            seconds = amount * 60
        elif "hour" in unit:
            seconds = amount * 3600

        done_message = f"Your {amount} {unit} timer is done."
        title = f"Timer: {amount} {unit}"

        thread = threading.Thread(
            target=lambda: CountdownWindow(seconds, title, done_message, self.speaker).run(),
            daemon=True,
        )
        thread.start()

        return f"Timer set for {amount} {unit}."


class CountdownWindow:
    """
    Generiek aftel-schermpje met pauze- en annuleerknop. Wordt gebruikt
    door zowel TimerSkill als AlarmSkill.
    """

    def __init__(self, seconds, title, done_message, speaker, repeats: int = 4, repeat_gap: float = 1.5):
        self.remaining = seconds
        self.title = title
        self.done_message = done_message
        self.speaker = speaker
        self.paused = False
        self.cancelled = False
        self.repeats = repeats
        self.repeat_gap = repeat_gap

    def run(self):
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry("240x130")
        self.root.attributes("-topmost", True)

        self.label = tk.Label(self.root, text=self._format_time(), font=("Sans", 24))
        self.label.pack(pady=10)

        button_frame = tk.Frame(self.root)
        button_frame.pack()

        self.pause_button = tk.Button(button_frame, text="Pause", command=self._toggle_pause)
        self.pause_button.pack(side="left", padx=5)

        cancel_button = tk.Button(button_frame, text="Cancel", command=self._cancel)
        cancel_button.pack(side="left", padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self._cancel)
        self._tick()
        self.root.mainloop()

    def _format_time(self):
        hours, remainder = divmod(max(self.remaining, 0), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.config(text="Resume" if self.paused else "Pause")

    def _cancel(self):
        self.cancelled = True
        self.root.destroy()

    def _tick(self):
        if self.cancelled:
            return

        if not self.paused:
            self.label.config(text=self._format_time())
            if self.remaining <= 0:
                self.root.destroy()
                self._announce_done()
                return
            self.remaining -= 1

        self.root.after(1000, self._tick)

    def _announce_done(self):
        banner = "=" * 44
        print(f"\n{banner}\n⏰  {self.done_message}\n{banner}\n")

        for i in range(self.repeats):
            if self.cancelled:
                break
            play_alert_beep()
            self.speaker.speak(self.done_message)
            if i < self.repeats - 1:
                time.sleep(self.repeat_gap)