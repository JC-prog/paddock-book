from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    aws_region: str = "us-east-1"
    jwt_secret: str
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    cookie_secure: bool = False
    ollama_model: str = "llama3.2"
    ollama_host: str = "http://localhost:11434"
    embedding_provider: str = "bedrock"
    ollama_embedding_model: str = "mxbai-embed-large"
    log_to_file: bool = True
    log_file_path: str = "logs/app.log"
    log_file_max_bytes: int = 10 * 1024 * 1024
    log_file_backup_count: int = 5
