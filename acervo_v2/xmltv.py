from __future__ import annotations

import hashlib
import io
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from acervo_v2.importers import PARSER_VERSION, stable_id


def parse_xmltv_datetime(value: str, default_timezone=timezone.utc):
    match = re.match(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:\s*([+-])(\d{2})(\d{2}))?", value or "")
    if not match:
        return None
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    sign, oh, om = match.groups()[6:]
    offset = timedelta(hours=int(oh or 0), minutes=int(om or 0))
    if sign == "-":
        offset = -offset
    try:
        return datetime(year, month, day, hour, minute, second,
                        tzinfo=timezone(offset) if sign else default_timezone)
    except ValueError:
        return None


def parse_xmltv(payload: bytes | str, source_id: str, source_ref: str = "input.xml",
                default_timezone=timezone.utc):
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    provenance = {
        "source_id": source_id, "source_ref": source_ref, "method": "xmltv",
        "parser_version": PARSER_VERSION,
        "collected_at": (datetime.fromtimestamp(int(os.environ["SOURCE_DATE_EPOCH"]), timezone.utc)
                         .replace(microsecond=0).isoformat().replace("+00:00", "Z")
                         if os.environ.get("SOURCE_DATE_EPOCH", "").isdigit() else None),
        "collection_time_known": os.environ.get("SOURCE_DATE_EPOCH", "").isdigit(),
        "input_sha256": hashlib.sha256(raw).hexdigest(), "confidence": 1.0,
    }
    channels, programmes, quarantine = [], [], []
    stack = []
    try:
        for event, elem in ET.iterparse(io.BytesIO(raw), events=("start", "end")):
            tag = elem.tag.rsplit("}", 1)[-1]
            if event == "start":
                stack.append(elem)
                continue
            parent = stack[-2] if len(stack) > 1 else None
            if tag == "channel":
                ident = str(elem.attrib.get("id") or "").strip()
                names = [" ".join(child.text.split()) for child in elem
                         if child.tag.rsplit("}", 1)[-1] == "display-name" and child.text and child.text.strip()]
                if ident:
                    channels.append({"id": ident, "display_names": list(dict.fromkeys(names)),
                                     "source_id": source_id, "provenance": [provenance],
                                     "raw": dict(elem.attrib)})
                else:
                    quarantine.append({"domain": "epg", "reason": "channel_missing_id", "raw": dict(elem.attrib)})
                elem.clear()
                if parent is not None:
                    parent.remove(elem)
            elif tag == "programme":
                start_raw, stop_raw = elem.attrib.get("start", ""), elem.attrib.get("stop", "")
                start = parse_xmltv_datetime(start_raw, default_timezone)
                stop = parse_xmltv_datetime(stop_raw, default_timezone)
                title = next((" ".join(child.text.split()) for child in elem
                              if child.tag.rsplit("}", 1)[-1] == "title" and child.text and child.text.strip()), "")
                description = next((" ".join(child.text.split()) for child in elem
                                    if child.tag.rsplit("}", 1)[-1] == "desc" and child.text and child.text.strip()), None)
                channel_id = str(elem.attrib.get("channel") or "").strip()
                if not start or not stop or stop <= start or not channel_id or not title:
                    quarantine.append({"domain": "epg", "reason": "invalid_programme",
                                       "raw": {"attributes": dict(elem.attrib), "title": title,
                                               "start": start_raw, "stop": stop_raw}})
                else:
                    key = channel_id + "|" + start.isoformat() + "|" + title
                    programmes.append({"id": stable_id("epgprogram", source_id, key),
                                        "epg_channel_id": channel_id, "title": title,
                                        "description": description, "start": start.isoformat(),
                                        "stop": stop.isoformat(), "source_id": source_id,
                                        "provenance": [provenance],
                                        "raw": {"attributes": dict(elem.attrib),
                                                "start": start_raw, "stop": stop_raw}})
                elem.clear()
                if parent is not None:
                    parent.remove(elem)
            elif parent is not None and parent.tag.rsplit("}", 1)[-1] in {"channel", "programme"}:
                # Keep child text until its enclosing record has been parsed.
                pass
            else:
                elem.clear()
            stack.pop()
    except ET.ParseError as exc:
        raise ValueError("invalid XMLTV document: " + str(exc)) from exc
    if not channels:
        quarantine.append({"domain": "epg", "reason": "no_xmltv_channels"})
    return channels, programmes, quarantine
