"""
LLM Provider presets for the QA Agent Platform.

Each entry defines:
  name              — human-readable label
  base_url          — API endpoint (None = use SDK default)
  default_model     — recommended model for this provider
  supports_json_mode— whether response_format={"type":"json_object"} is supported
  models            — list of supported model IDs

To add a new provider, append an entry to PROVIDERS and no other code changes are needed.
"""

from typing import Any, Dict, List, Optional

PROVIDERS: Dict[str, Dict[str, Any]] = {
    # ── OpenAI ────────────────────────────────────────────────────────────
    "openai": {
        "name": "OpenAI",
        "base_url": None,                     # SDK default: https://api.openai.com/v1
        "default_model": "gpt-4o",
        "supports_json_mode": True,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1", "gpt-3.5-turbo"],
        "key_env_hint": "OPENAI_API_KEY=sk-...",
        "key_url": "https://platform.openai.com/api-keys",
    },
    # ── GitHub Models (included with GitHub Copilot Pro) ──────────────────
    "github": {
        "name": "GitHub Models / Copilot Pro",
        "base_url": "https://models.inference.ai.azure.com",
        "default_model": "gpt-4o",
        "supports_json_mode": True,
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "Meta-Llama-3.1-70B-Instruct",
            "Meta-Llama-3.1-405B-Instruct",
            "Mistral-large-2407",
            "Mistral-Nemo",
            "AI21-Jamba-1.5-Large",
            "Phi-3.5-MoE-instruct",
        ],
        "key_env_hint": "OPENAI_API_KEY=ghp_... (GitHub classic PAT)",
        "key_url": "https://github.com/settings/tokens",
    },
    # ── Anthropic (Claude) ────────────────────────────────────────────────
    "anthropic": {
        "name": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
        "supports_json_mode": False,          # Uses prompt-level JSON instructions instead
        "models": [
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        "key_env_hint": "OPENAI_API_KEY=sk-ant-...",
        "key_url": "https://console.anthropic.com/account/keys",
    },
    # ── DeepSeek ──────────────────────────────────────────────────────────
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "supports_json_mode": True,
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "key_env_hint": "OPENAI_API_KEY=sk-...",
        "key_url": "https://platform.deepseek.com/api_keys",
    },
    # ── Azure OpenAI ──────────────────────────────────────────────────────
    "azure": {
        "name": "Azure OpenAI",
        "base_url": None,                     # Set OPENAI_BASE_URL to your deployment endpoint
        "default_model": "gpt-4o",
        "supports_json_mode": True,
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-35-turbo"],
        "key_env_hint": "OPENAI_API_KEY=<azure-key>  OPENAI_BASE_URL=https://<resource>.openai.azure.com/openai/deployments/<deployment>/",
        "key_url": "https://portal.azure.com",
    },
    # ── Groq (ultra-fast open-source inference) ───────────────────────────
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "supports_json_mode": True,
        "models": [
            "llama-3.3-70b-versatile",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        "key_env_hint": "OPENAI_API_KEY=gsk_...",
        "key_url": "https://console.groq.com/keys",
    },
    # ── Mistral AI ────────────────────────────────────────────────────────
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
        "supports_json_mode": True,
        "models": [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
            "open-mixtral-8x22b",
            "codestral-latest",
        ],
        "key_env_hint": "OPENAI_API_KEY=...",
        "key_url": "https://console.mistral.ai/api-keys",
    },
    # ── Ollama (local, no API key required) ───────────────────────────────
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.1",
        "supports_json_mode": False,
        "models": ["llama3.1", "llama3", "mistral", "codellama", "phi3", "qwen2.5"],
        "key_env_hint": "OPENAI_API_KEY=ollama  (any non-empty string)",
        "key_url": "https://ollama.ai",
    },
    # ── Google Gemini (OpenAI-compatible endpoint) ────────────────────────
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.0-flash",
        "supports_json_mode": True,
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "key_env_hint": "OPENAI_API_KEY=AIza...",
        "key_url": "https://aistudio.google.com/app/apikey",
    },
}


def get_provider(name: str) -> Dict[str, Any]:
    """Return provider config by name (case-insensitive). Falls back to openai."""
    return PROVIDERS.get(name.lower(), PROVIDERS["openai"])


def resolve_base_url(provider_name: str, override_base_url: Optional[str] = None) -> Optional[str]:
    """Return effective base URL: explicit override > provider preset > None."""
    if override_base_url:
        return override_base_url
    return get_provider(provider_name).get("base_url")


def supports_json_mode(provider_name: str) -> bool:
    """Whether this provider accepts response_format=json_object."""
    return get_provider(provider_name).get("supports_json_mode", True)


def list_providers() -> List[Dict[str, Any]]:
    """Return a summary list suitable for the /providers API endpoint."""
    return [
        {
            "id": pid,
            "name": p["name"],
            "default_model": p["default_model"],
            "models": p["models"],
            "key_url": p["key_url"],
            "key_env_hint": p["key_env_hint"],
        }
        for pid, p in PROVIDERS.items()
    ]
