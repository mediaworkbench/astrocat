"""City search for birth places, from GeoNames cities1000 (CC BY 4.0, https://www.geonames.org/)."""

import csv
import io
import sys
import unicodedata
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from urllib.request import urlopen

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from astrocat.db import Place, PlaceName

GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"
MAX_NAME_LENGTH = 80


def normalize(name: str) -> str:
    """Lowercase, accents removed, ß → ss: "München" → "munchen", "Múnich" → "munich"."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def _searchable_names(name: str, ascii_name: str, alternate: str) -> set[str]:
    names = {normalize(name), normalize(ascii_name)}
    for alt in alternate.split(","):
        norm = normalize(alt)
        # Only Latin-script names: the app's languages are EN/ES/DE.
        if norm and len(norm) <= MAX_NAME_LENGTH and norm.isascii():
            names.add(norm)
    names.discard("")
    return names


def parse_geonames(lines: Iterable[str]) -> Iterator[tuple[Place, set[str]]]:
    """Rows of the GeoNames "geoname" table format (tab-separated, 19 columns)."""
    for row in csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE):
        if len(row) < 18 or not row[17]:
            continue
        place = Place(
            id=int(row[0]),
            name=row[1][:200],
            country_code=row[8][:2],
            latitude=float(row[4]),
            longitude=float(row[5]),
            timezone=row[17],
            population=int(row[14] or 0),
        )
        yield place, _searchable_names(row[1], row[2], row[3])


def _open_lines(source: str | Path | None) -> Iterator[str]:
    if source is None or str(source).startswith(("http://", "https://")):
        url = str(source or GEONAMES_URL)
        print(f"Downloading {url} …", file=sys.stderr)
        with urlopen(url, timeout=120) as response:  # one-time admin download, not at runtime
            data = response.read()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            member = next(n for n in archive.namelist() if n.endswith(".txt"))
            with archive.open(member) as f:
                yield from io.TextIOWrapper(f, encoding="utf-8")
        return
    with open(source, encoding="utf-8") as f:
        yield from f


def import_places(db: Session, source: str | Path | None = None, batch_size: int = 5000) -> int:
    """Replace all places with the given file (default: download cities1000). Returns the count."""
    db.execute(delete(PlaceName))
    db.execute(delete(Place))
    count = 0
    places: list[Place] = []
    names: list[dict] = []
    for place, searchable in parse_geonames(_open_lines(source)):
        places.append(place)
        names.extend({"place_id": place.id, "name_norm": n} for n in searchable)
        if len(places) >= batch_size:
            count += _flush(db, places, names)
    count += _flush(db, places, names)
    db.commit()
    return count


def _flush(db: Session, places: list[Place], names: list[dict]) -> int:
    n = len(places)
    if n:
        db.add_all(places)
        db.flush()
        db.execute(PlaceName.__table__.insert(), names)
        places.clear()
        names.clear()
    return n


def search_places(db: Session, query: str, limit: int = 10) -> list[Place]:
    """Places whose name (or an alternate name) starts with `query`, biggest first."""
    q = normalize(query)
    if len(q) < 2:
        return []
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    matching = (
        select(PlaceName.place_id).where(PlaceName.name_norm.like(f"{escaped}%", escape="\\")).distinct().subquery()
    )
    stmt = (
        select(Place)
        .join(matching, matching.c.place_id == Place.id)
        .order_by(Place.population.desc(), Place.name)
        .limit(limit)
    )
    return list(db.scalars(stmt))


def place_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Place)) or 0
