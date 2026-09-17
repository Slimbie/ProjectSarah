import json
from pathlib import Path
from datetime import datetime


class ReminderStore:
    """
    Persistente opslag voor reminders/agenda-items, als JSON-bestand.
    Weet niks over spraak of skills - puur lezen/schrijven van data.
    """

    def __init__(self, file_path: str = "memory/reminders.json"):
        self.file_path = Path(file_path)

    def load(self) -> list:
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def save(self, reminders: list):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(reminders, f, ensure_ascii=False, indent=2)

    def add(self, text: str, due_time: datetime):
        reminders = self.load()
        reminders.append({
            "text": text,
            "due_time": due_time.isoformat(),
            "notified": False,
        })
        self.save(reminders)

    def get_due(self, now: datetime) -> list:
        reminders = self.load()
        return [r for r in reminders
                if not r["notified"] and datetime.fromisoformat(r["due_time"]) <= now]

    def mark_notified(self, text: str, due_time_iso: str):
        reminders = self.load()
        for r in reminders:
            if r["text"] == text and r["due_time"] == due_time_iso:
                r["notified"] = True
        self.save(reminders)