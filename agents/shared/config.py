from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Google AI
    google_api_key: str

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: str

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_password: str = ""

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    # Sarvam AI
    sarvam_api_key: str
    sarvam_tts_url: str = "https://api.sarvam.ai/text-to-speech"

    # External APIs
    serper_api_key: str

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    max_concurrent_calls: int = 10
    call_timeout_seconds: int = 300

    # Webhooks
    webhook_base_url: str = "http://localhost:8000"


settings = Settings()
