from datetime import datetime
from pathlib import Path

from pydantic import BaseSettings


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
    def db_path(self):
        path = self.data_path / "notes.db"
        return path.resolve()
    
    @property
    def backup_db_path(self):
        now = datetime.utcnow().isoformat()
        path = self.data_path / f"notes__{now}.db"
        return path.resolve()

    @property
    def db_url(self):
        return f"sqlite:///{self.db_path}"

    @property
    def json_path(self):
        return self.data_path / "notes.json"


config = Config()
