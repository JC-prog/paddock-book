from typing import Literal

from pydantic import BaseModel, ConfigDict


class LogDestinationSetting(BaseModel):
    # Strict, not Pydantic's default lenient coercion — "yes"/"1"/etc.
    # should be rejected as non-boolean (422), per contracts/admin-api.md,
    # not silently coerced to true.
    model_config = ConfigDict(strict=True)

    log_to_file: bool


ChatProvider = Literal["ollama", "bedrock", "openai_compatible"]


class ChatProviderSettingsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    active_provider: ChatProvider
    ollama_model_override: str | None
    bedrock_model: str | None
    openai_compatible_base_url: str | None
    openai_compatible_model: str | None
    # Never the key's value (FR-011) — only whether one is saved.
    openai_compatible_api_key_set: bool


class ChatProviderSettingsUpdate(BaseModel):
    # Partial update (contracts/admin-api.md): every field is optional;
    # an omitted field leaves its previously stored value untouched.
    model_config = ConfigDict(strict=True)

    active_provider: ChatProvider | None = None
    ollama_model_override: str | None = None
    bedrock_model: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str | None = None
