import re
from datetime import date
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

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


templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["date_fr"] = _date_fr
templates.env.filters["highlight"] = _highlight
templates.env.globals.update({
    "app_version": "0.6.0",
    "current_year": date.today().year,
})
