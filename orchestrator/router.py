from skills.base_skill import BaseSkill


class Orchestrator:
    """
    Houdt een lijst van skills bij en kiest, op basis van can_handle(),
    welke skill een binnenkomende tekst mag afhandelen.
    """

    def __init__(self, skills: list[BaseSkill]):
        self.skills = skills

    def handle_input(self, text: str) -> str:
        for skill in self.skills:
            if skill.can_handle(text):
                return skill.handle(text)

        # Geen enkele skill kon dit aan.
        # Vanaf Fase 5 komt hier de LLM-fallback in plaats van deze zin.
        return "Sorry bro that's not yet in my vocabulary"#"Sorry, I dont know that yet."