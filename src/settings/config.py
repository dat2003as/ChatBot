import os
from src.utils.env import Env
from src.utils.design_pattern import singleton


@singleton
class AppSettings:
    app_name: str = Env.get("APP_NAME") or ""
    app_version: str = Env.get("APP_VERSION") or "0.0.1"
    app_description: str = Env.get("APP_DESCRIPTION") or ""
    api_host: str = Env.get("API_HOST") or "0.0.0.0"
    api_port: int = 8000  # Env.get("API_PORT") or 8000

    GOOGLE_API_KEY = Env.get("GOOGLE_API_KEY")

    # SQL SERVER
    DB_SERVER = Env.get("DB_SERVER")
    SQL_SERVER_NAME = Env.get("SQL_SERVER_NAME")
    SQL_DATABASE_NAME = Env.get("SQL_DATABASE_NAME")
    SQL_DATABASE_USER = Env.get("SQL_DATABASE_USER")
    SQL_DATABASE_PASSWORD = Env.get("SQL_DATABASE_PASSWORD")


APP_SETTINGS = AppSettings()
