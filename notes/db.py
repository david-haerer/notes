from sqlmodel import (
    Session,
    create_engine,
    select,
)
from notes.config import config
from notes.model import User, Note


class DB:
    def __init__(self):
        self.engine = create_engine(config.db_url)
    
    @property
    def session(self):
        return Session(self.engine)
    
    def add(self, session, item: Note | User):
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    def delete(self, session, item: Note | User):
        session.delete(item)
        session.commit()
    
    def get_users(self, session):
        statement = select(User)
        results = session.exec(statement)
        users = results.all()
        return users
    
    def get_user_by_id(self, session, user_id):
        if user_id is None:
            return None
        statement = select(User).where(User.id == user_id)
        results = session.exec(statement)
        user = results.one()
        return user

    def get_user_by_github_id(self, session, github_id):
        statement = select(User).where(User.github_id == github_id)
        results = session.exec(statement)
        user = results.one()
        return user
    
    def get_notes(self, session):
        statement = select(Note)
        results = session.exec(statement)
        notes = results.all()
        return reversed(notes)
    
    def get_note_by_id(self, session, note_id):
        if note_id is None:
            return None
        statement = select(Note).where(Note.id == note_id)
        results = session.exec(statement)
        note = results.first()
        return note



db = DB()
