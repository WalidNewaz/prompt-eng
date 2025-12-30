from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"

    # Tool server
    tool_base_url: str = "http://127.0.0.1:8001/v1/tools"

    class Config:
        env_file = ".env"
        env_prefix = "APP_"


settings = Settings()
