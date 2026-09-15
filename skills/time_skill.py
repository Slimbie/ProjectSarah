from datetime import datetime
from skills.base_skill import BaseSkill


class TimeSkill(BaseSkill):
    """Simpele skill die vraagt over de tijd beantwoordt."""

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        return "what time" in text or "time is it" in text

    def handle(self, text: str) -> str:
        now = datetime.now().strftime("%H:%M")
        return f"It is now {now}."