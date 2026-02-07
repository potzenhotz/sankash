"""Settings page state management."""

import reflex as rx

from sankash.services import llm_service
from sankash.services import settings_service
from sankash.state.base import BaseState


class SettingsState(BaseState):
    """State for the settings page."""

    state_auto_setters = True

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    saving: bool = False
    success_message: str = ""
    error: str = ""
    ollama_status: str = ""  # "connected" / "unreachable" / ""

    def load_settings(self) -> None:
        """Load settings from DB, falling back to defaults."""
        self.error = ""
        self.success_message = ""
        try:
            self.ollama_base_url = settings_service.get_setting(
                self.db_path, "ollama_base_url", "http://localhost:11434"
            )
            self.ollama_model = settings_service.get_setting(
                self.db_path, "ollama_model", "llama3.2"
            )
        except Exception as e:
            self.error = f"Failed to load settings: {e}"

    def save_settings(self) -> None:
        """Write current values to DB."""
        self.saving = True
        self.error = ""
        self.success_message = ""
        try:
            settings_service.set_setting(
                self.db_path, "ollama_base_url", self.ollama_base_url.strip()
            )
            settings_service.set_setting(
                self.db_path, "ollama_model", self.ollama_model.strip()
            )
            self.success_message = "Settings saved"
        except Exception as e:
            self.error = f"Failed to save settings: {e}"
        finally:
            self.saving = False

    def test_ollama_connection(self) -> None:
        """Ping Ollama and update status."""
        self.ollama_status = ""
        self.error = ""
        try:
            if llm_service.check_ollama_available(self.ollama_base_url.strip()):
                self.ollama_status = "connected"
            else:
                self.ollama_status = "unreachable"
        except Exception:
            self.ollama_status = "unreachable"
