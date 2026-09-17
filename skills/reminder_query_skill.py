import re
import threading
from datetime import datetime
from skills.base_skill import BaseSkill
from memory.reminder_store import ReminderStore
from skills.ui_utils import show_notification

LIST_PHRASES = ["what are my reminders", "list my reminders", "show my reminders", "read my reminders"]
DELETE_PATTERN = re.compile(r"(?:delete|remove|cancel) (?:the )?reminder(?:s)?(?: to| about| for)? (.+)")


class ReminderQuerySkill(BaseSkill):
    """
    Laat bestaande reminders opvragen ('what are my reminders') of
    verwijderen ('delete the reminder to do the dishes'). Moet VOOR
    ReminderSkill in de skills-lijst staan, anders vangt die generiekere
    skill deze zinnen eerst af.
    """

    def __init__(self, reminder_store: ReminderStore = None):
        self.store = reminder_store or ReminderStore()

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        return any(phrase in text for phrase in LIST_PHRASES) or bool(DELETE_PATTERN.search(text))

    def handle(self, text: str) -> str:
        text_lower = text.lower()

        delete_match = DELETE_PATTERN.search(text_lower)
        if delete_match:
            keyword = delete_match.group(1).strip(" .,-")
            reminders = self.store.load()
            remaining = [r for r in reminders if keyword not in r["text"].lower()]
            removed_count = len(reminders) - len(remaining)
            self.store.save(remaining)
            if removed_count:
                return f"Removed {removed_count} reminder(s) about {keyword}."
            return f"I couldn't find a reminder about {keyword}."

        reminders = [r for r in self.store.load() if not r["notified"]]
        if not reminders:
            return "You have no upcoming reminders."

        lines = []
        for r in reminders:
            due = datetime.fromisoformat(r["due_time"])
            lines.append(f"- {r['text']} ({due.strftime('%a %d %b, %H:%M')})")
        message = "\n".join(lines)

        threading.Thread(target=lambda: show_notification("Your Reminders", message), daemon=True).start()

        spoken_list = "; ".join(r["text"] for r in reminders)
        count_word = "reminder" if len(reminders) == 1 else "reminders"
        return f"You have {len(reminders)} {count_word}: {spoken_list}"