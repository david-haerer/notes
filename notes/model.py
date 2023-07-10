from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from notes.utils import render_timestamp


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    handle: Optional[str]
    name: str
    notes: list["Note"] = Relationship(back_populates="author")
    github_id: Optional[int]
    github_login: Optional[str]
    
    @property
    def link(self):
        if self.handle:
            return f"/@{self.handle}"
        return f"/user/{self.id}"


class Note(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, primary_key=True)
    content: str
    author_id: UUID = Field(foreign_key="user.id")
    author: User = Relationship(back_populates="notes")

    def __str__(self):
        timestamp = render_timestamp(self.timestamp)
        return f"{timestamp}\n{self.content}\n"
