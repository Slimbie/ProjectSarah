from wake_word.listener import WakeWordListener
from stt.transcriber import Transcriber
from orchestrator.router import Orchestrator
from skills.time_skill import TimeSkill
from tts.speaker import Speaker
from skills.llm_skill import LlmSkill
from skills.app_skill import AppSkill
from skills.search_skill import SearchSkill
from skills.media_skill import MediaSkill




def main():
    listener = WakeWordListener(wakeword="hey_jarvis")
    transcriber = Transcriber()
    orchestrator = Orchestrator(skills=[TimeSkill(), AppSkill(), MediaSkill(), SearchSkill(), LlmSkill()])
    speaker = Speaker()
    
    
    print("Sarah is actief en luistert op de achtergrond... (Ctrl+C om te stoppen)")

    while True:
        listener.wait_for_wakeword()
        print("Wake word gehoord!")

        text = transcriber.transcribe()
        if not text:
            print("Niks verstaan, terug naar luisteren.")
            speaker.speak("I didn't hear you.")
            continue

        print(f"Jij zei: {text}")
        response = orchestrator.handle_input(text)
        print(f"Sarah: {response}")
        speaker.speak(response)


if __name__ == "__main__":
    main()