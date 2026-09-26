import subprocess
from pathlib import Path
from datetime import datetime
from skills.base_skill import BaseSkill


class SystemSkill(BaseSkill):
    """
    Basis systeembeheer: volume, mute, schermhelderheid, batterijstatus,
    wifi aan/uit, screenshot, dark/light mode, en energie-profiel.
    """

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        checks = [
            "volume" in text,
            "mute" in text or "unmute" in text,
            "brightness" in text or "dim" in text or "brighten" in text,
            "battery" in text,
            "wifi" in text and any(w in text for w in ["on", "off", "enable", "disable"]),
            "screenshot" in text,
            "dark mode" in text or "light mode" in text,
            "power mode" in text or "power profile" in text or "battery saver" in text or "power saver" in text,
            "performance mode" in text,
        ]
        return any(checks)

    def handle(self, text: str) -> str:
        text = text.lower()

        if "volume" in text:
            return self._handle_volume(text)
        if "mute" in text or "unmute" in text:
            return self._handle_mute(text)
        if "brightness" in text or "dim" in text or "brighten" in text:
            return self._handle_brightness(text)
        if "battery" in text and "saver" not in text:
            return self._handle_battery()
        if "wifi" in text:
            return self._handle_wifi(text)
        if "screenshot" in text:
            return self._handle_screenshot()
        if "dark mode" in text or "light mode" in text:
            return self._handle_theme(text)
        if any(kw in text for kw in ["power mode", "power profile", "battery saver", "power saver", "performance mode"]):
            return self._handle_power_profile(text)

        return "I couldn't do that."

    def _run(self, command: list) -> bool:
        try:
            subprocess.run(command, check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def _handle_volume(self, text: str) -> str:
        if "unmute" in text:
            return self._handle_mute(text)
        if "mute" in text or ("off" in text and "on" not in text):
            ok = self._run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1"])
            return "Volume muted." if ok else "I couldn't mute the volume."
        if "on" in text and "off" not in text and not any(w in text for w in ["up", "down", "increase", "decrease"]):
            ok = self._run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"])
            return "Volume unmuted." if ok else "I couldn't unmute the volume."
        if any(w in text for w in ["up", "increase", "raise"]):
            ok = self._run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%+"])
            return "Volume increased." if ok else "I couldn't change the volume."
        if any(w in text for w in ["down", "decrease", "lower"]):
            ok = self._run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"])
            return "Volume decreased." if ok else "I couldn't change the volume."
        return "Should I turn the volume up or down?"

    def _handle_mute(self, text: str) -> str:
        if "unmute" in text:
            ok = self._run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"])
            return "Unmuted." if ok else "I couldn't unmute."
        ok = self._run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1"])
        return "Muted." if ok else "I couldn't mute."

    def _handle_brightness(self, text: str) -> str:
        if "dim" in text or any(w in text for w in ["down", "decrease"]):
            ok = self._run(["brightnessctl", "set", "10%-"])
            return "Brightness decreased." if ok else "I couldn't change the brightness. Check permissions (video group) or that brightnessctl is installed."
        if "brighten" in text or any(w in text for w in ["up", "increase"]):
            ok = self._run(["brightnessctl", "set", "10%+"])
            return "Brightness increased." if ok else "I couldn't change the brightness. Check permissions (video group) or that brightnessctl is installed."
        return "Should I increase or decrease the brightness?"

    def _handle_battery(self) -> str:
        try:
            devices = subprocess.run(["upower", "-e"], capture_output=True, text=True, check=True)
            battery_device = next((line for line in devices.stdout.splitlines() if "BAT" in line), None)
            if not battery_device:
                return "I couldn't find a battery on this system."

            info = subprocess.run(["upower", "-i", battery_device], capture_output=True, text=True, check=True)
            percentage, state = "unknown", "unknown"
            for line in info.stdout.splitlines():
                if "percentage" in line:
                    percentage = line.split(":")[-1].strip()
                if line.strip().startswith("state"):
                    state = line.split(":")[-1].strip()

            return f"Battery is at {percentage} and {state}."
        except (FileNotFoundError, subprocess.CalledProcessError):
            return "I couldn't check the battery status."

    def _handle_wifi(self, text: str) -> str:
        if any(w in text for w in ["off", "disable"]):
            ok = self._run(["nmcli", "radio", "wifi", "off"])
            return "Wifi turned off." if ok else "I couldn't turn off wifi."
        ok = self._run(["nmcli", "radio", "wifi", "on"])
        return "Wifi turned on." if ok else "I couldn't turn on wifi."

    def _handle_screenshot(self) -> str:
        screenshots_dir = Path.home() / "Pictures" / "Screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        filename = screenshots_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        ok = self._run(["gnome-screenshot", "-f", str(filename)])
        return "Screenshot saved." if ok else "I couldn't take a screenshot. Is gnome-screenshot installed?"

    def _handle_theme(self, text: str) -> str:
        if "dark" in text:
            ok = self._run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark"])
            return "Dark mode enabled." if ok else "I couldn't switch to dark mode."
        ok = self._run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-light"])
        return "Light mode enabled." if ok else "I couldn't switch to light mode."

    def _handle_power_profile(self, text: str) -> str:
        if any(kw in text for kw in ["saver", "saving", "battery"]):
            profile = "power-saver"
        elif "performance" in text:
            profile = "performance"
        else:
            profile = "balanced"

        ok = self._run(["powerprofilesctl", "set", profile])
        readable = profile.replace("-", " ")
        return f"Switched to {readable} mode." if ok else f"I couldn't switch power mode. Is power-profiles-daemon installed?"