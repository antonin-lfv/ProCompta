from datetime import date
from pathlib import Path

from fastapi.templating import Jinja2Templates

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _date_fr(d: date) -> str:
    return f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]} {d.year}"


templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["date_fr"] = _date_fr
templates.env.globals.update({
    "app_version": "0.3.0",
    "current_year": date.today().year,
})
