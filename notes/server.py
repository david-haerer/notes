from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from notes.config import config
from notes.db import db
from notes.model import Note, User
from notes.utils import render_timestamp


server = FastAPI(openapi_url=None)

server.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

server.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["render_timestamp"] = render_timestamp

session = {}


def get_user_id(session_id: Annotated[UUID | None, Cookie()] = None) -> UUID | None:
    if session_id not in session:
        return None
    return session[session_id]["user_id"]


def require_user_id(session_id: Annotated[UUID | None, Cookie()] = None) -> UUID:
    user_id = get_user_id(session_id)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required!",
        )
    return user_id


@server.get("/callbacks/github")
async def github_callback(code: str):
    access_token = httpx.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": config.github_client_id,
            "client_secret": config.github_client_secret,
            "code": code,
        },
        headers={
            "Accept": "application/json",
        },
    ).json()["access_token"]

    github = httpx.get(
        "https://api.github.com/user",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    ).json()

    with db.session as db_session:
        user = db.get_user_by_github_id(db_session, github["id"])
        session_id = uuid4()

        if user is None:
            user = db.add(
                db_session,
                User(
                    name=github["name"],
                    github_id=github["id"],
                    github_login=github["login"],
                ),
            )

        session[session_id] = {"user_id": user.id}
        response = RedirectResponse("/")
        response.set_cookie(key="session_id", value=session_id)
        return response


@server.get("/logout")
async def get_logout(
    response: Response, session_id: Annotated[str | None, Cookie()] = None
):
    response = RedirectResponse("/")
    response.delete_cookie("session_id")
    session.pop(session_id, None)
    return response


@server.get("/", response_class=HTMLResponse)
async def get_index(
    request: Request, user_id: Annotated[User | None, Depends(get_user_id)]
):
    with db.session as db_session:
        user = db.get_user_by_id(db_session, user_id)
        notes = db.get_notes(db_session)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "notes": notes,
                "client_id": config.github_client_id,
                "user": user,
            },
        )


@server.post("/add", response_class=HTMLResponse)
def post_note(
    request: Request,
    user_id: Annotated[User, Depends(require_user_id)],
    content: Annotated[str, Form()],
):
    with db.session as db_session:
        user = db.get_user_by_id(db_session, user_id)
        db.add(
            db_session,
            Note(
                author_id=user_id,
                content=content,
            ),
        )
        notes = db.get_notes(db_session)
        return templates.TemplateResponse(
            "partials/notes.html",
            {
                "request": request,
                "notes": notes,
                "user": user,
            },
        )


@server.delete("/delete/{note_id}", response_class=HTMLResponse)
def delete_note(
    request: Request, note_id: UUID, user_id: Annotated[User, Depends(require_user_id)]
):
    with db.session as db_session:
        note = db.get_note_by_id(db_session, note_id)

        if note is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note does not exist!",
            )

        if user_id != note.author_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Only the author can delete the note!",
            )

        db.delete(db_session, note)
        user = db.get_user_by_id(db_session, user_id)
        notes = db.get_notes(db_session)
        return templates.TemplateResponse(
            "partials/notes.html",
            {
                "request": request,
                "notes": notes,
                "user": user,
            },
        )
