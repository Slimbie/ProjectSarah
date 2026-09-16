import re
from skills.browser_utils import open_incognito
from skills.base_skill import BaseSkill


class SearchSkill(BaseSkill):
    """
    Opent een Google-zoekopdracht in de standaardbrowser wanneer de gebruiker
    vraagt om iets op te zoeken. Vangt geen antwoorden terug, opent puur de
    zoekpagina - het daadwerkelijk uitlezen van resultaten is een latere stap.
    """

    TRIGGER_PATTERNS = [
        r"search for (.+)",
        r"search (.+)",
        r"google (.+)",
        r"look up (.+)",
    ]

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        return any(re.search(pattern, text) for pattern in self.TRIGGER_PATTERNS)

    def handle(self, text: str) -> str:
        text = text.lower()
        query = None
        for pattern in self.TRIGGER_PATTERNS:
            match = re.search(pattern, text)
            if match:
                query = match.group(1).strip().rstrip(".?!")
                break

        if not query:
            return "What would you like me to search for?"

        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        open_incognito(url)
        return f"Here's what I found for {query}."