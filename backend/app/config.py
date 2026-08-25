import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Aegis 2.0"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # URLs
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    API_BASE_URL: str = Field(default="http://localhost:8000", env="API_BASE_URL")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./aegis.db", env="DATABASE_URL")
    
    # Redis & Task Queue
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Groq LLM API
    GROQ_API_KEY: str = Field(default="", env="GROQ_API_KEY")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-120b", env="GROQ_MODEL")
    GROQ_ENGINEER_MODEL: str = Field(default="openai/gpt-oss-120b", env="GROQ_ENGINEER_MODEL")
    
    # GitHub App & OAuth
    GITHUB_APP_ID: Optional[str] = Field(default=None, env="GITHUB_APP_ID")
    GITHUB_APP_PRIVATE_KEY: Optional[str] = Field(default=None, env="GITHUB_APP_PRIVATE_KEY")
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None, env="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None, env="GITHUB_CLIENT_SECRET")
    GITHUB_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="GITHUB_WEBHOOK_SECRET")
    
    # Security
    SESSION_SECRET: str = Field(default="aegis-super-secret-session-key-32chars-min", env="SESSION_SECRET")
    
    # Scanner
    SEMGREP_TIMEOUT: int = Field(default=60, env="SEMGREP_TIMEOUT")
    
    # Cloud Deployment Check
    RENDER: Optional[str] = Field(default=None, env="RENDER")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def normalized_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()
