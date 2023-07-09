# -- IMPORTS --


import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional
from uuid import UUID, uuid4

import caldav
import httpx
import typer
import uvicorn
from fastapi import Cookie, Depends, FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware







# -- CONFIG --


def get_config():
    data_path = os.getenv("DATA_PATH")
    if not data_path:
        raise EnvironmentError("Environment variable 'DATA_PATH' must be set!")
    notes_data_path = Path(data_path) / "notes.json"
    users_data_path = Path(data_path) / "users.json"
    db_path = (Path(data_path) / "notes.db").resolve()
    db_url = f"sqlite:///{db_path}"

    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    if not github_client_id:
        raise EnvironmentError("Environment variable 'GITHUB_CLIENT_ID' must be set!")

    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if not github_client_secret:
        raise EnvironmentError(
            "Environment variable 'GITHUB_CLIENT_SECRET' must be set!"
        )

    return {
        "DB_URL": db_url,
        "NOTES_DATA_PATH": notes_data_path,
        "USERS_DATA_PATH": users_data_path,
        "GITHUB_CLIENT_ID": github_client_id,
        "GITHUB_CLIENT_SECRET": github_client_secret,
    }


config = get_config()

CALDAV_URL = os.getenv("CALDAV_URL")
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME")
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD")
CALDAV_CALENDAR = "Notizen"


# -- MODEL --


class Note(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    timestamp: datetime
    content: str


engine = create_engine(config["DB_URL"])
SQLModel.metadata.create_all(engine)


# -- DB --


def load():
    if not config["NOTES_DATA_PATH"].is_file():
        return []
    with open(config["NOTES_DATA_PATH"], "r", encoding="utf-8") as file:
        notes = json.load(file)
    notes.sort(key=lambda note: -int(note["timestamp"]))
    for note in notes:
        note["timestamp"] = int(note["timestamp"])
    return notes


def save(notes):
    notes.sort(key=lambda note: -int(note["timestamp"]))
    with open(config["NOTES_DATA_PATH"], mode="wt", encoding="utf-8") as file:
        json.dump(notes, file, indent=4, ensure_ascii=False)


# -- CLI --


cli = typer.Typer(pretty_exceptions_show_locals=False, add_completion=False)


@cli.command("import")
def import_notes_from_caldav():
    if None in (CALDAV_URL, CALDAV_USERNAME, CALDAV_PASSWORD):
        print(
            "Error: 'CALDAV_URL', 'CALDAV_USERNAME' and 'CALDAV_PASSWORD' must be defined!"
        )
        raise typer.Exit(1)

    client = caldav.DAVClient(
        CALDAV_URL, username=CALDAV_USERNAME, password=CALDAV_PASSWORD
    )
    principal = client.principal()
    calendars = principal.calendars()
    tasklists = list(
        filter(
            lambda cal: "VTODO" in cal.get_supported_components()
            and str(cal).lower() == CALDAV_CALENDAR.lower(),
            calendars,
        )
    )

    if len(tasklists) != 1:
        print(f"Error: Task list '{CALDAV_CALENDAR}' not found!")
        raise typer.Exit(1)

    tasklist = tasklists[0]

    notes = load()

    for todo in tasklist.todos(include_completed=False):
        timestamp = int(todo.icalendar_component["created"].dt.timestamp())
        notes.append(
            {
                "timestamp": timestamp,
                "content": str(todo.icalendar_component["summary"]),
            }
        )
        todo.delete()

    save(notes)


@cli.command()
def add(content: str):
    timestamp = int(datetime.now().timestamp())
    notes = load()
    notes.append(
        {
            "content": content,
            "timestamp": timestamp,
        }
    )
    save(notes)
    return notes


@cli.command()
def server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    app = "main:server" if reload else server
    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload)


@cli.command()
def populate():
    notes = load()
    with Session(engine) as session:
        for note in notes:
            session.add(Note(
                timestamp=datetime.fromtimestamp(int(note["timestamp"])),
                content=note["content"],
            ))
        session.commit()


# -- SERVER --


server = FastAPI(openapi_url=None)
server.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
server.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
session = {}


def get_user(session_id: Annotated[str | None, Cookie()] = None):
    if session_id not in session:
        return None
    return session[session_id]["user"]["login"]


@server.get("/", response_class=HTMLResponse)
async def get_index(request: Request, user: Annotated[str | None, Depends(get_user)]):
    notes = load()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "notes": notes,
            "client_id": config["GITHUB_CLIENT_ID"],
            "user": user,
        },
    )


@server.get("/callback")
async def get_index(code: str):
    access_token = httpx.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": config["GITHUB_CLIENT_ID"],
            "client_secret": config["GITHUB_CLIENT_SECRET"],
            "code": code,
        },
        headers={
            "Accept": "application/json",
        },
    ).json()["access_token"]

    user = httpx.get(
        "https://api.github.com/user",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    ).json()
    session_id = uuid4()

    session[session_id] = {
        "access_token": access_token,
        "user": user
    }

    response = RedirectResponse("/")
    response.set_cookie(key="session_id", value=session_id)
    return response


@server.get("/logout")
async def get_logout(response: Response, session_id: Annotated[str | None, Cookie()] = None):
    response = RedirectResponse("/")
    response.delete_cookie("session_id")
    session.pop(session_id, None)
    return response



@server.post("/add", response_class=HTMLResponse)
def post_note(request: Request, content: Annotated[str, Form()]):
    notes = add(content)
    return templates.TemplateResponse(
        "partials/notes.html", {"request": request, "notes": notes}
    )


@server.delete("/delete/{timestamp}", response_class=HTMLResponse)
def delete_note(request: Request, timestamp: int):
    notes = load()
    notes = list(filter(lambda note: note["timestamp"] != timestamp, notes))
    save(notes)
    return templates.TemplateResponse(
        "partials/notes.html", {"request": request, "notes": notes}
    )


# -- TEMPLATES --


def render_timestamp(timestamp):
    return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M")


templates.env.filters["render_timestamp"] = render_timestamp


# -- MAIN --


if __name__ == "__main__":
    cli()
