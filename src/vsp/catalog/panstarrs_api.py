"""
PanSTARRS catalog API client (MAST DR1/DR2).

Thin wrapper around the MAST PanSTARRS REST endpoints. Replaces three
near-identical copies that lived in the original ``DR2API_queries.py``,
``DR2API_que.py``, and ``PanAPIQuery.py`` files.

The public entry points are :func:`ps1cone`, :func:`ps1search`,
:func:`ps1metadata`, :func:`mastQuery`, and :func:`resolve`.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Iterable, Optional, Tuple
from urllib.parse import quote as urlencode

import http.client as httplib

import requests
from astropy.table import Table

logger = logging.getLogger(__name__)

DEFAULT_BASEURL = "https://catalogs.mast.stsci.edu/api/v0.1/panstarrs"


def ps1cone(
    ra: float,
    dec: float,
    radius: float,
    table: str = "mean",
    release: str = "dr2",
    format: str = "csv",
    columns: Optional[Iterable[str]] = None,
    baseurl: str = DEFAULT_BASEURL,
    verbose: bool = False,
    **kw,
) -> str:
    """Cone search of the PanSTARRS catalog.

    Parameters
    ----------
    ra, dec
        J2000 RA/Dec in degrees.
    radius
        Cone radius in degrees (must be <= 0.5).
    table
        ``mean``, ``stack``, or ``detection``.
    release
        ``dr1`` or ``dr2``.
    format
        ``csv``, ``votable``, or ``json``.
    columns
        Optional column whitelist.
    **kw
        Additional query parameters, e.g. ``nDetections.min=2``.
    """
    data = dict(kw)
    data["ra"] = ra
    data["dec"] = dec
    data["radius"] = radius
    return ps1search(
        table=table, release=release, format=format, columns=columns,
        baseurl=baseurl, verbose=verbose, **data,
    )


def ps1search(
    table: str = "mean",
    release: str = "dr2",
    format: str = "csv",
    columns: Optional[Iterable[str]] = None,
    baseurl: str = DEFAULT_BASEURL,
    verbose: bool = False,
    **kw,
) -> str:
    """General catalog search; ``ps1cone`` is the cone-shaped specialization."""
    data = dict(kw)
    if not data:
        raise ValueError("You must specify some parameters for search")
    checklegal(table, release)
    if format not in ("csv", "votable", "json"):
        raise ValueError(f"Bad value for format: {format!r}")
    url = f"{baseurl}/{release}/{table}.{format}"
    if columns:
        valid = {c.lower() for c in ps1metadata(table, release)["name"]}
        bad = [c for c in columns if c.lower().strip() not in valid]
        if bad:
            raise ValueError(f"Some columns not found in table: {', '.join(bad)}")
        data["columns"] = "[{}]".format(",".join(columns))

    r = requests.get(url, params=data)
    if verbose:
        logger.info("PanSTARRS GET %s", r.url)
    r.raise_for_status()
    return r.json() if format == "json" else r.text


def checklegal(table: str, release: str) -> None:
    """Raise ``ValueError`` if the (table, release) combo isn't supported."""
    releaselist = ("dr1", "dr2")
    if release not in releaselist:
        raise ValueError(f"Bad value for release ({release!r}); expected one of {releaselist}")
    if release == "dr1":
        tablelist = ("mean", "stack")
    else:
        tablelist = ("mean", "stack", "detection")
    if table not in tablelist:
        raise ValueError(f"Bad value for table ({table!r}); expected one of {tablelist}")


def ps1metadata(
    table: str = "mean",
    release: str = "dr2",
    baseurl: str = DEFAULT_BASEURL,
) -> Table:
    """Return the metadata table (column names + types) for ``release/table``."""
    checklegal(table, release)
    url = f"{baseurl}/{release}/{table}/metadata"
    r = requests.get(url)
    r.raise_for_status()
    v = r.json()
    return Table(
        rows=[(x["name"], x["type"], x["description"]) for x in v],
        names=("name", "type", "description"),
    )


def mastQuery(request: dict) -> Tuple[list, str]:
    """Issue a MAST API request (used by :func:`resolve`)."""
    server = "mast.stsci.edu"
    version = ".".join(map(str, sys.version_info[:3]))
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "User-agent": f"python-requests/{version}",
    }
    request_string = urlencode(json.dumps(request))
    conn = httplib.HTTPSConnection(server)
    conn.request("POST", "/api/v0/invoke", "request=" + request_string, headers)
    resp = conn.getresponse()
    head = resp.getheaders()
    content = resp.read().decode("utf-8")
    conn.close()
    return head, content


def resolve(name: str) -> Tuple[float, float]:
    """Resolve an object name to (RA, Dec) via MAST's name lookup."""
    request = {
        "service": "Mast.Name.Lookup",
        "params": {"input": name, "format": "json"},
    }
    _, payload = mastQuery(request)
    obj = json.loads(payload)
    try:
        ra = obj["resolvedCoordinate"][0]["ra"]
        dec = obj["resolvedCoordinate"][0]["decl"]
    except IndexError as exc:
        raise ValueError(f"Unknown object {name!r}") from exc
    return ra, dec
