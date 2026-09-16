import re
from skills.base_skill import BaseSkill


def normalize(text: str) -> str:
    """
    Verwijdert leestekens die Whisper soms toevoegt (komma's, punten) en
    overbodige spaties, zodat regex-matching in skills niet struikelt
    over dingen als 'play, don't...' i.p.v. 'play don't...'.
    """
    text = re.sub(r"[,.!?]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class Orchestrator:
    """
    Houdt een lijst van skills bij en kiest, op basis van can_handle(),
    welke skill een binnenkomende tekst mag afhandelen.
    """

    def __init__(self, skills: list[BaseSkill]):
        self.skills = skills

    def handle_input(self, text: str) -> str:
        text = normalize(text)

        for skill in self.skills:
            if skill.can_handle(text):
                return skill.handle(text)

        return "Sorry bro that's not yet in my vocabulary"#"Sorry, I dont know that yet."