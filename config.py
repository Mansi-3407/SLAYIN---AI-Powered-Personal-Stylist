"""Central configuration for SLAYIN.

All settings are loaded from environment variables / `.env`.
All filesystem paths are resolved relative to the project root.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "SLAYIN"
    app_env: str = "development"
    debug: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- Database ---
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'slayin.db').as_posix()}"

    # --- Gemini ---
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_image_model: str = "gemini-2.5-flash-image"

    # --- AI models ---
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    device: str = "cpu"

    # --- Uploads ---
    max_upload_mb: int = 10
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # --- Logging ---
    log_level: str = "INFO"

    # --- Paths ---
    data_dir: Path = BASE_DIR / "data"
    deepfashion_dir: Path = BASE_DIR / "data" / "raw" / "deep-fashion"
    user_images_dir: Path = BASE_DIR / "data" / "raw" / "user_images"
    wardrobe_dir: Path = BASE_DIR / "data" / "user_data" / "wardrobe"
    preferences_dir: Path = BASE_DIR / "data" / "user_data" / "preferences"
    history_dir: Path = BASE_DIR / "data" / "user_data" / "history"
    embeddings_dir: Path = BASE_DIR / "data" / "processed" / "embeddings"
    encoded_features_dir: Path = BASE_DIR / "data" / "processed" / "encoded_features"
    pretrained_models_dir: Path = BASE_DIR / "models" / "pretrained"
    saved_models_dir: Path = BASE_DIR / "models" / "saved_models"
    model_configs_dir: Path = BASE_DIR / "models" / "model_configs"
    logs_dir: Path = BASE_DIR / "logs"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
