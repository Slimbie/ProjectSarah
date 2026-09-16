import re
import threading
from datetime import datetime, timedelta
from skills.base_skill import BaseSkill
from skills.timer_skill import CountdownWindow


class AlarmSkill(BaseSkill):
    """
    Zet een alarm op een specifiek tijdstip (bv. 'set an alarm for 7:30 am',
    'put an alarm up for 11 pm'). Hergebruikt hetzelfde aftel-schermpje
    als TimerSkill.
    """

    PATTERN = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)")

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        return "alarm" in text and bool(self.PATTERN.search(text))

    def __init__(self, speaker):
        self.speaker = speaker

    def handle(self, text: str) -> str:
        match = self.PATTERN.search(text.lower())
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)

        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        now = datetime.now()
        alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if alarm_time <= now:
            alarm_time += timedelta(days=1)

        seconds = int((alarm_time - now).total_seconds())
        time_str = alarm_time.strftime("%H:%M")

        thread = threading.Thread(
            target=lambda: CountdownWindow(
                seconds,
                f"Alarm: {time_str}",
                f"It's {time_str}, your alarm is going off.",
                self.speaker,
            ).run(),
            daemon=True,
        )
        thread.start()

        return f"Alarm set for {time_str}."