
from pydantic import BaseSettings
from pathlib import Path


class Config(BaseSettings):
    data_path: Path

    github_client_id: str
    github_client_secret: str

    caldav_url: str
    caldav_username: str
    caldav_password: str
    caldav_calendar: str

    class Config:
        env_file = Path().absolute() / ".env"
        env_file_encoding = "utf-8"
        # secrets_dir = "/run/secrets"

    @property
    def db_url(self):
        db_path = self.data_path / "notes.db"
        return f"sqlite:///{db_path.resolve()}"

    @property
    def json_path(self):
        return self.data_path / "notes.json"


config = Config()
