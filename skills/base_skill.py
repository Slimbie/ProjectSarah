from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """
    Elke skill (bv. tijd opvragen, app openen, LLM-vraag) erft van deze klasse
    en implementeert de twee methodes hieronder.
    """

    @abstractmethod
    def can_handle(self, text: str) -> bool:
        """
        Geeft True terug als deze skill de gegeven tekst kan afhandelen.
        Wordt door de orchestrator gebruikt om de juiste skill te kiezen.
        """
        raise NotImplementedError

    @abstractmethod
    def handle(self, text: str) -> str:
        """
        Voert de skill daadwerkelijk uit en geeft het antwoord terug als tekst
        (dat antwoord wordt later door de TTS-laag uitgesproken).
        """
        raise NotImplementedError