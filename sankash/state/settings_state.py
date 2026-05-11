"""Settings page state management."""

import reflex as rx

from sankash.services import llm_service
from sankash.services import settings_service
from sankash.state.base import BaseState


class SettingsState(BaseState):
    """State for the settings page."""

    state_auto_setters = True

    # Provider selection
    llm_provider: str = "ollama"  # ollama | openrouter | apfel | openai_compatible

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # OpenAI-compatible settings (used by openrouter, apfel, openai_compatible)
    openai_base_url: str = "https://openrouter.ai/api"
    openai_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    openai_api_key: str = ""

    saving: bool = False
    success_message: str = ""
    error: str = ""
    ollama_status: str = ""  # "connected" / "unreachable" / ""

    def load_settings(self) -> None:
        """Load settings from DB, falling back to defaults."""
        self.error = ""
        self.success_message = ""
        try:
            self.llm_provider = settings_service.get_setting(
                self.data_dir, "llm_provider", "ollama"
            )
            self.ollama_base_url = settings_service.get_setting(
                self.data_dir, "ollama_base_url", "http://localhost:11434"
            )
            self.ollama_model = settings_service.get_setting(
                self.data_dir, "ollama_model", "llama3.2"
            )
            self.openai_base_url = settings_service.get_setting(
                self.data_dir, "openai_base_url", "https://openrouter.ai/api"
            )
            self.openai_model = settings_service.get_setting(
                self.data_dir, "openai_model", "meta-llama/llama-3.1-8b-instruct:free"
            )
            self.openai_api_key = settings_service.get_setting(
                self.data_dir, "openai_api_key", ""
            )
        except Exception as e:
            self.error = f"Failed to load settings: {e}"

    def select_provider(self, provider: str) -> None:
        """Switch provider and apply default values for the new provider."""
        self.llm_provider = provider
        preset = llm_service.PROVIDER_PRESETS.get(provider, {})
        if provider == "ollama":
            if not self.ollama_base_url or self.ollama_base_url == "http://localhost:11434":
                self.ollama_base_url = preset.get("default_base_url", "http://localhost:11434")
            if not self.ollama_model or self.ollama_model == "llama3.2":
                self.ollama_model = preset.get("default_model", "llama3.2")
        else:
            if not self.openai_base_url or self.openai_base_url in (
                p.get("default_base_url", "") for p in llm_service.PROVIDER_PRESETS.values()
            ):
                self.openai_base_url = preset.get("default_base_url", "")
            if not self.openai_model or self.openai_model in (
                p.get("default_model", "") for p in llm_service.PROVIDER_PRESETS.values()
            ):
                self.openai_model = preset.get("default_model", "")

    def save_settings(self) -> None:
        """Write current values to DB."""
        self.saving = True
        self.error = ""
        self.success_message = ""
        try:
            settings_service.set_setting(
                self.data_dir, "llm_provider", self.llm_provider.strip()
            )
            settings_service.set_setting(
                self.data_dir, "ollama_base_url", self.ollama_base_url.strip()
            )
            settings_service.set_setting(
                self.data_dir, "ollama_model", self.ollama_model.strip()
            )
            settings_service.set_setting(
                self.data_dir, "openai_base_url", self.openai_base_url.strip()
            )
            settings_service.set_setting(
                self.data_dir, "openai_model", self.openai_model.strip()
            )
            settings_service.set_setting(
                self.data_dir, "openai_api_key", self.openai_api_key.strip()
            )
            self.success_message = "Settings saved"
        except Exception as e:
            self.error = f"Failed to save settings: {e}"
        finally:
            self.saving = False

    def test_ollama_connection(self) -> None:
        """Ping the configured LLM provider and update status."""
        self.ollama_status = ""
        self.error = ""
        try:
            if self.llm_provider == "ollama":
                available = llm_service.check_provider_available(
                    "ollama", self.ollama_base_url.strip()
                )
            else:
                available = llm_service.check_provider_available(
                    self.llm_provider,
                    self.openai_base_url.strip(),
                    self.openai_api_key.strip() or None,
                )

            self.ollama_status = "connected" if available else "unreachable"
        except Exception:
            self.ollama_status = "unreachable"
