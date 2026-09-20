import subprocess
from skills.base_skill import BaseSkill


class AppSkill(BaseSkill):
    """
    Opent programma's op basis van een naam-naar-commando mapping.
    Voeg zelf gerust meer apps toe aan APP_COMMANDS hieronder.
    """

    APP_COMMANDS = {
        "firefox": "firefox",
        "browser": "google-chrome",
        "terminal": "terminal",
        "files": "files",
        "file manager": "files",
        "calculator": "gnome-calculator",
        "text editor": "gedit",
        "spotify": "spotify",
        "vlc": "vlc",
        "video player": "vlc",
        "visual studio code": "code",
        "code": "code",
        "Rhythmbox": "rhythmbox",
        "whatsapp": "whatsapp-desktop-linux",
        "google": "google-chrome",
        "chrome": "google-chrome",
        "appstore": "App-Center",
        "app center": "app-center",
        "resources":"Resources",
        "settings":"Settings",
        "Trash":"Trash",
        "music":"spotify",
        "weather": "gnome-weather",
        "weather app": "gnome-weather",
        
    }

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        if "open" not in text:
            return False
        return any(app_name in text for app_name in self.APP_COMMANDS)

    def handle(self, text: str) -> str:
        text = text.lower()
        for app_name, command in self.APP_COMMANDS.items():
            if app_name in text:
                try:
                    subprocess.Popen([command])
                    return f"Opening {app_name}."
                except FileNotFoundError:
                    return f"I couldn't find {app_name} on this system."
        return "I don't know which app you mean."