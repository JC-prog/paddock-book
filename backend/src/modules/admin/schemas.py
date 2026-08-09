from pydantic import BaseModel, ConfigDict


class LogDestinationSetting(BaseModel):
    # Strict, not Pydantic's default lenient coercion — "yes"/"1"/etc.
    # should be rejected as non-boolean (422), per contracts/admin-api.md,
    # not silently coerced to true.
    model_config = ConfigDict(strict=True)

    log_to_file: bool
