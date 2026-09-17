import re
from datetime import datetime, timedelta
from skills.base_skill import BaseSkill
from memory.reminder_store import ReminderStore

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

LEAD_IN_PHRASES = [
    r"can you remind me to", r"remind me to", r"set a reminder to",
    r"set a reminder for", r"can you remember to",
    r"put this in my agenda to", r"put this in my agenda",
    r"put a reminder to", r"add to my agenda to", r"add to my agenda",
]


def extract_due_time(text: str, now: datetime = None):
    """
    Zoekt gerichte, expliciete tijdsaanduidingen (geen vrije-tekst gok-search
    zoals dateparser deed, om valse matches te voorkomen). Geeft
    (due_time, [gevonden tekstdelen]) terug, of (None, []) als niks matcht.
    """
    now = now or datetime.now()
    text_lower = text.lower()
    matched_phrases = []

    # "in X minutes/hours/days" - meest expliciet, dus voorrang
    m = re.search(r"\bin (\d+)\s*(minute|minutes|hour|hours|day|days)\b", text_lower)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        if "minute" in unit:
            delta = timedelta(minutes=amount)
        elif "hour" in unit:
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)
        return now + delta, [m.group(0)]

    due_date = None
    due_time_of_day = None

    if re.search(r"\btomorrow\b", text_lower):
        due_date = (now + timedelta(days=1)).date()
        matched_phrases.append("tomorrow")

    m = re.search(r"\b(?:next|on)\s+(" + "|".join(WEEKDAYS) + r")\b", text_lower)
    if m:
        target_day = WEEKDAYS.index(m.group(1))
        days_ahead = (target_day - now.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7  # "next X" is altijd de KOMENDE, niet vandaag
        due_date = (now + timedelta(days=days_ahead)).date()
        matched_phrases.append(m.group(0))

    if due_date is None and re.search(r"\btoday\b", text_lower):
        due_date = now.date()
        matched_phrases.append("today")

    m = re.search(r"\bat (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        meridiem = m.group(3)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        due_time_of_day = (hour, minute)
        matched_phrases.append(m.group(0))

    if due_date is None and due_time_of_day is None:
        return None, []

    if due_date is None:
        due_date = now.date()

    if due_time_of_day:
        hour, minute = due_time_of_day
        due = datetime.combine(due_date, datetime.min.time()).replace(hour=hour, minute=minute)
        if due <= now:
            due += timedelta(days=1)
        return due, matched_phrases

    # Alleen een dag genoemd, geen tijdstip:
    if due_date == now.date():
        # "today" zonder tijd -> kort heads-up over 5 minuten, i.p.v. onmerkbaar om 00:00
        return now + timedelta(minutes=5), matched_phrases

    due = datetime.combine(due_date, datetime.min.time())
    return due, matched_phrases


class ReminderSkill(BaseSkill):
    """
    Herkent reminder/agenda-verzoeken mét een expliciet tijdstip in
    dezelfde zin, en slaat de rest op als de taak.
    """

    def __init__(self, reminder_store: ReminderStore = None):
        self.store = reminder_store or ReminderStore()

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        return "remind" in text or "reminder" in text or "agenda" in text

    def handle(self, text: str) -> str:
        due_time, matched_phrases = extract_due_time(text)
        if due_time is None:
            return "When should I remind you? Please include a day, date, or time."

        task = text.lower()
        for phrase in matched_phrases:
            task = task.replace(phrase, "")
        for phrase in LEAD_IN_PHRASES:
            task = re.sub(phrase, "", task)
        task = re.sub(r"\s+", " ", task).strip(" .,-")

        if not task:
            task = "your reminder"

        self.store.add(task, due_time)
        formatted = due_time.strftime("%A %d %B, %H:%M")
        return f"I'll remind you to {task} on {formatted}."