from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    database_url_sync: str

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    cors_allowed_origins: str = "http://localhost:5173"

    upload_dir: str = "./uploads"
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    image_url_prefix: str = "/tour-images"

    # Public site origin used to build success/cancel URLs handed to the
    # payment provider. Override per environment.
    public_site_origin: str = "http://localhost:5173"

    # Booking lookup endpoint rate limit (per IP per minute). Tunable.
    booking_lookup_rate_limit_per_minute: int = 5

    # Background job sweep interval for cancelling expired pending bookings.
    booking_ttl_sweep_interval_seconds: int = 300
    booking_ttl_minutes: int = 30

    # Shell-mode payment provider: auto-fire a fake "succeeded" webhook a
    # few seconds after each checkout session is created, so the happy path
    # is testable end-to-end. Disable to test the cancel/abandon path.
    # Has no effect once a real payment provider is wired.
    payment_shell_auto_success: bool = True
    payment_shell_auto_success_delay_seconds: float = 4.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()
