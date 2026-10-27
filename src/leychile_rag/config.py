from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    database_url: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    leychile_xml_base: str = "https://www.leychile.cl/Consulta/obtxml"
    # Dimensión de text-embedding-3-small
    embedding_dim: int = 1536


settings = Settings()
