#!/usr/bin/env python3
"""Parse HTML schedule pages into normalized programme records.

This module deliberately performs no network access and writes no catalog files.
Callers must fetch pages safely and decide how parsed schedules are published.
"""
from __future__ import annotations

import datetime as dt
import html
import re
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
from typing import Any

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def _programme(start: dt.datetime, title: str, genre: str = "") -> dict[str, Any]:
    return {
        "start": start.astimezone(SAO_PAULO).isoformat(),
        "title": title,
        "genre": genre or None,
    }


def _finish_intervals(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort, drop duplicate start/title pairs, and end at the next start."""
    parsed: list[tuple[dt.datetime, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item["start"], item["title"].casefold())
        if key in seen:
            continue
        seen.add(key)
        parsed.append((dt.datetime.fromisoformat(item["start"]), item))
    parsed.sort(key=lambda pair: pair[0])
    result = []
    for index, (start, item) in enumerate(parsed):
        end = parsed[index + 1][0] if index + 1 < len(parsed) else start + dt.timedelta(hours=1)
        if end <= start:
            continue
        record = dict(item)
        record["end"] = end.isoformat()
        result.append(record)
    return result


class _MeuGuiaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, Any]] = []
        self.items: list[dict[str, str]] = []
        self.active_li: dict[str, str] | None = None
        self.capture: tuple[str, list[str]] | None = None
        self.date_text = ""

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
        return set(dict(attrs).get("class", "").split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = self._classes(attrs)
        if tag == "li":
            self.active_li = {"time": "", "title": "", "genre": "", "date": self.date_text}
        if "subheader" in classes and self.capture is None:
            self.capture = ("date", [])
        elif self.active_li is not None and tag in {"span", "div", "p"} and "time" in classes:
            self.capture = ("time", [])
        elif self.active_li is not None and tag == "h2":
            self.capture = ("title", [])
        elif self.active_li is not None and tag == "h3":
            self.capture = ("genre", [])
        self.stack.append({"tag": tag, "classes": classes, "attrs": attr})

    def handle_data(self, data: str) -> None:
        if self.capture is not None:
            self.capture[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture is not None and self.stack and self.stack[-1]["tag"] == tag:
            field, chunks = self.capture
            value = _text(" ".join(chunks))
            if field == "date":
                self.date_text = value
            elif self.active_li is not None:
                self.active_li[field] = value
            self.capture = None
        if tag == "li" and self.active_li is not None:
            if self.active_li.get("time") and self.active_li.get("title"):
                self.items.append(self.active_li)
            self.active_li = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break


def _date_from_header(value: str, reference_date: dt.date) -> dt.date | None:
    match = re.search(r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?\b", value or "")
    if not match:
        if re.search(r"hoje|today", value or "", re.I):
            return reference_date
        if re.search(r"amanh[ãa]|tomorrow", value or "", re.I):
            return reference_date + dt.timedelta(days=1)
        return None
    day, month = int(match.group(1)), int(match.group(2))
    year = int(match.group(3) or reference_date.year)
    try:
        result = dt.date(year, month, day)
    except ValueError:
        return None
    if not match.group(3) and result < reference_date - dt.timedelta(days=180):
        try:
            result = result.replace(year=year + 1)
        except ValueError:
            return None
    return result


def parse_meuguia(html_document: str, reference_date: dt.date | None = None) -> list[dict[str, Any]]:
    """Parse MeuGuia li entries containing a date header, time, h2 title and optional h3 genre."""
    parser = _MeuGuiaParser()
    parser.feed(html_document or "")
    parser.close()
    reference_date = reference_date or dt.datetime.now(SAO_PAULO).date()
    current_date = reference_date
    output = []
    for item in parser.items:
        date = _date_from_header(item.get("date", ""), reference_date) or current_date
        time_match = re.search(r"\b(\d{1,2}):(\d{2})\b", item.get("time", ""))
        if not time_match:
            continue
        try:
            start = dt.datetime.combine(
                date,
                dt.time(int(time_match.group(1)), int(time_match.group(2))),
                tzinfo=SAO_PAULO,
            )
        except ValueError:
            continue
        title = _text(item.get("title", ""))
        if not title:
            continue
        output.append(_programme(start, title, _text(item.get("genre", ""))))
        current_date = date
    return _finish_intervals(output)


class _GuiaDeTvParser(HTMLParser):
    """Read data-dt schedule markers and their associated /programa/ title links."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pending_start: dt.datetime | None = None
        self.capture_anchor = False
        self.anchor_href = ""
        self.anchor_text: list[str] = []
        self.records: list[tuple[dt.datetime, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        raw_dt = attr.get("data-dt", "")
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?", raw_dt)
        if match:
            try:
                self.pending_start = dt.datetime(
                    *map(int, match.groups()[:5]),
                    int(match.group(6) or 0),
                    tzinfo=SAO_PAULO,
                )
            except ValueError:
                self.pending_start = None
        if tag == "a":
            self.anchor_href = attr.get("href", "")
            self.capture_anchor = "/programa/" in self.anchor_href
            self.anchor_text = []

    def handle_data(self, data: str) -> None:
        if self.capture_anchor:
            self.anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            title = _text(" ".join(self.anchor_text))
            if self.capture_anchor and self.pending_start and title:
                self.records.append((self.pending_start, title))
                self.pending_start = None
            self.capture_anchor = False
            self.anchor_href = ""
            self.anchor_text = []


def parse_guiadetv(html_document: str) -> list[dict[str, Any]]:
    """Parse GuiaDeTv data-dt markers and following /programa/ links."""
    parser = _GuiaDeTvParser()
    parser.feed(html_document or "")
    parser.close()
    return _finish_intervals([
        _programme(start, title) for start, title in parser.records if title
    ])


if __name__ == "__main__":
    raise SystemExit("Import parse_meuguia/parse_guiadetv from a controlled updater; no network or writes occur here.")
