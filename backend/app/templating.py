import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

_PARIS = ZoneInfo("Europe/Paris")

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _date_fr(d: date) -> str:
    return f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]} {d.year}"


def _highlight(text: str | None, search: str | None) -> Markup:
    if not text:
        return Markup("")
    escaped = str(escape(text))
    if not search or not search.strip():
        return Markup(escaped)
    pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
    result = pattern.sub(
        lambda m: f'<mark class="bg-yellow-100 text-yellow-800 rounded px-0.5">{m.group()}</mark>',
        escaped,
    )
    return Markup(result)


def _dt_paris(dt: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    if not dt:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(_PARIS)
    return dt.strftime(fmt)


templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["date_fr"] = _date_fr
templates.env.filters["highlight"] = _highlight
templates.env.filters["dt_paris"] = _dt_paris
app_version = "1.5.2"

templates.env.globals.update({
    "app_version": app_version,
    "current_year": date.today().year,
})


def render(request: Request, template: str, ctx: dict | None = None) -> HTMLResponse:
    user = getattr(request.state, "user", None)
    return templates.TemplateResponse(request, template, {"current_user": user, **(ctx or {})})
