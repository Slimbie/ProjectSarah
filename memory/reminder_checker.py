import time
import threading
from datetime import datetime
from memory.reminder_store import ReminderStore
from skills.ui_utils import show_notification


class ReminderChecker:
    """
    Draait continu op de achtergrond en checkt periodiek of er reminders
    zijn verlopen - onafhankelijk van de wake word listener, dus een
    reminder gaat ook af als er niemand 'hey jarvis' zegt.
    """

    def __init__(self, speaker, store: ReminderStore = None, check_interval: int = 20):
        self.speaker = speaker
        self.store = store or ReminderStore()
        self.check_interval = check_interval

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        while True:
            now = datetime.now()
            for reminder in self.store.get_due(now):
                threading.Thread(
                    target=lambda r=reminder: show_notification("Reminder", r["text"]),
                    daemon=True,
                ).start()
                self.speaker.speak(f"Reminder: {reminder['text']}")
                self.store.mark_notified(reminder["text"], reminder["due_time"])
            time.sleep(self.check_interval)