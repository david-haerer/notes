import os
from pathlib import Path
import subprocess

import caldav
import typer
import uvicorn
from alembic.config import main as alembic

from notes.config import config
from notes.db import db
from notes.model import Note
from notes.server import server


cli = typer.Typer(pretty_exceptions_show_locals=False, add_completion=False)

db_cli = typer.Typer(pretty_exceptions_show_locals=False, add_completion=False)

cli.add_typer(db_cli, name="db")


@cli.command("import")
def import_notes_from_caldav(user_handle: str):
    client = caldav.DAVClient(
        config.caldav_url,
        username=config.caldav_username,
        password=config.caldav_password,
    )
    principal = client.principal()
    calendars = principal.calendars()
    tasklists = list(
        filter(
            lambda cal: "VTODO" in cal.get_supported_components()
            and str(cal).lower() == config.caldav_calendar.lower(),
            calendars,
        )
    )

    if len(tasklists) != 1:
        print(f"Error: Task list '{config.caldav_calendar}' not found!")
        raise typer.Exit(1)

    tasklist = tasklists[0]

    for todo in tasklist.todos(include_completed=False):
        timestamp = todo.icalendar_component["created"].dt
        content = str(todo.icalendar_component["summary"])
        db.add(
            Note(
                timestamp=timestamp,
                content=content,
            )
        )
        todo.delete()


@cli.command()
def add(content: str):
    db.add(Note(content=content))


@cli.command("server")
def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    app = "main:server" if reload else server
    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)


@db_cli.command()
def backup():
    subprocess.run(
        ["sqlite3", f"{config.db_path}", f".backup '{config.backup_db_path}'"]
    )


@db_cli.command()
def upgrade():
    os.environ["NOTES_DB_URL"] = config.db_url
    os.chdir(Path(__file__).parent)
    alembic(argv=["--raiseerr", "upgrade", "head"])


@db_cli.command()
def revision(name):
    os.environ["NOTES_DB_URL"] = config.db_url
    os.chdir(Path(__file__).parent)
    alembic(argv=["--raiseerr", "revision", "--autogenerate", "-m", name])


@db_cli.command()
def populate(user_handle: str):
    pass


@cli.command("list")
def list_notes():
    notes = db.notes
    for note in notes:
        print(note)


if __name__ == "__main__":
    cli()
