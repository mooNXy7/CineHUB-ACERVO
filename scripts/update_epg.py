#!/usr/bin/env python3
"""Refresh EPG source health and map XMLTV IDs onto the shared channel catalog."""
import concurrent.futures
import datetime as dt
import io
import json
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPG_DIR = ROOT / "catalog/epg"
CHANNELS_FILE = ROOT / "catalog/channels/channels.json"
SOURCES_FILE = EPG_DIR / "sources.json"
MAP_FILE = EPG_DIR / "channel-map.json"
HEALTH_FILE = EPG_DIR / "health.json"
XMLTV_INDEX_FILE = EPG_DIR / "xmltv-channels.json"
USER_AGENT = "CineHUB-ACERVO-EPG/1.0 (+https://github.com/mooNXy7/CineHUB-ACERVO)"
MAX_BYTES = 100 * 1024 * 1024
TIMEOUT = 45


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalise(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"^[a-z]{2}\s*[-|]\s*", "", value)
    value = re.sub(r"\b(?:hd|sd|fhd|uhd|4k|br)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def get_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,text/html,*/*"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        status = getattr(response, "status", 200)
        content_type = response.headers.get("Content-Type", "")
        chunks, size = [], 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("response exceeds 100 MiB safety limit")
            chunks.append(chunk)
        if not 200 <= status < 300:
            raise ValueError("HTTP status " + str(status))
        return b"".join(chunks), status, content_type


def parse_xmltv_date(value):
    match = re.match(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:\s*([+-])(\d{2})(\d{2}))?", value or "")
    if not match:
        return None
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    sign, oh, om = match.groups()[6:]
    offset = dt.timedelta(hours=int(oh or 0), minutes=int(om or 0))
    if sign == "-":
        offset = -offset
    try:
        return dt.datetime(year, month, day, hour, minute, second, tzinfo=dt.timezone(offset))
    except ValueError:
        return None


def parse_xmltv(payload, now=None):
    """Validate XMLTV with bounded-memory iterparse and count programmes in the 78h window."""
    now = now or dt.datetime.now(dt.timezone.utc)
    start_window = now - dt.timedelta(hours=6)
    end_window = now + dt.timedelta(hours=72)
    channels, programme_count, window_count = [], 0, 0
    stack = []
    for event, elem in ET.iterparse(io.BytesIO(payload), events=("start", "end")):
        tag = elem.tag.rsplit("}", 1)[-1]
        if event == "start":
            stack.append(elem)
            continue
        if tag == "channel":
            ident = elem.attrib.get("id", "").strip()
            names = []
            for child in elem:
                if child.tag.rsplit("}", 1)[-1] == "display-name" and child.text:
                    name = " ".join(child.text.split())
                    if name and name not in names:
                        names.append(name)
            if ident:
                channels.append({"id": ident, "display_names": names})
        elif tag == "programme":
            programme_count += 1
            begin = parse_xmltv_date(elem.attrib.get("start", ""))
            stop = parse_xmltv_date(elem.attrib.get("stop", ""))
            if begin and stop and stop > start_window and begin < end_window:
                window_count += 1
        if len(stack) > 1:
            parent = stack[-2]
            # Keep display-name children until their enclosing channel closes.
            if not (tag == "display-name" and parent.tag.rsplit("}", 1)[-1] == "channel"):
                parent.remove(elem)
        if tag != "display-name":
            elem.clear()
        stack.pop()
    if not channels:
        raise ValueError("valid XML parsed, but no XMLTV channels were found")
    return channels, programme_count, window_count


def probe_html(url):
    payload, status, content_type = get_url(url)
    html = payload.decode("utf-8", errors="replace")
    if not re.search(r"<(?:li|article|div)\b", html, re.I):
        raise ValueError("HTTP succeeded but no recognizable schedule markup was found")
    return {"http_status": status, "content_type": content_type, "bytes": len(payload), "schedule_markup": True}


def pluto_id(text):
    match = re.search(r"(?:plu-|images\.pluto\.tv/channels/)([0-9a-f]{24})", str(text or ""), re.I)
    return match.group(1).lower() if match else None


def main():
    sources_doc = read_json(SOURCES_FILE, {})
    map_doc = read_json(MAP_FILE, {})
    old_health = read_json(HEALTH_FILE, {"schema_version": 1, "sources": {}})
    old_indexes = read_json(XMLTV_INDEX_FILE, {"schema_version": 1, "sources": {}})
    health_by_id = old_health.get("sources", {})
    index_by_id = old_indexes.get("sources", {})
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    xmltv_sources = [s for s in sources_doc.get("sources", []) if s.get("enabled") and s.get("format") == "xmltv"]
    html_sources = [s for s in sources_doc.get("sources", []) if s.get("enabled") and s.get("format") == "html"]
    tasks = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for source in xmltv_sources:
            tasks[pool.submit(get_url, source["url"])] = ("xmltv", source)
        for source in html_sources:
            tasks[pool.submit(probe_html, source["probe_url"])] = ("html", source)
        for future in concurrent.futures.as_completed(tasks):
            kind, source = tasks[future]
            sid = source["id"]
            previous = health_by_id.get(sid, {})
            entry = {
                "source_id": sid, "checked_at": now, "priority": source.get("priority"),
                "url": source.get("url") or source.get("probe_url"),
                "last_success_at": previous.get("last_success_at"),
                "consecutive_failures": int(previous.get("consecutive_failures", 0)),
            }
            try:
                if kind == "xmltv":
                    payload, status, content_type = future.result()
                    channels, programmes, window_programmes = parse_xmltv(payload)
                    entry.update({
                        "status": "healthy", "http_status": status, "content_type": content_type,
                        "bytes": len(payload), "channel_count": len(channels),
                        "programme_count_total": programmes, "programme_count_window_78h": window_programmes,
                        "last_success_at": now, "consecutive_failures": 0, "error": None,
                    })
                    index_by_id[sid] = {"source_id": sid, "fetched_at": now, "channel_count": len(channels), "channels": channels}
                else:
                    entry.update(future.result())
                    entry.update({"status": "healthy", "last_success_at": now, "consecutive_failures": 0, "error": None})
            except Exception as exc:
                entry.update({
                    "status": "unavailable",
                    "consecutive_failures": int(previous.get("consecutive_failures", 0)) + 1,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                })
                print(f"WARNING: EPG source {sid} failed: {entry['error']}; preserving last known-good index")
            health_by_id[sid] = entry

    write_json(XMLTV_INDEX_FILE, {
        "schema_version": 1, "generated_at": now,
        "window_hours": {"past": 6, "future": 72}, "sources": index_by_id,
    })

    channel_doc = read_json(CHANNELS_FILE, {})
    channels = channel_doc.get("channels", [])
    aliases = map_doc.get("xmltv_aliases", {})
    aliases_norm = {normalise(k): [normalise(x) for x in v] for k, v in aliases.items()}
    by_source_names = {}
    for source in xmltv_sources:
        sid = source["id"]
        index = index_by_id.get(sid, {})
        name_to_ids = {}
        for record in index.get("channels", []):
            ident = record.get("id", "")
            for name in record.get("display_names", []):
                name_to_ids.setdefault(normalise(name), []).append(ident)
        by_source_names[sid] = name_to_ids

    updated = 0
    for channel in channels:
        name = str(channel.get("name", "")).strip()
        if not name:
            continue
        current_sources = []
        pid = pluto_id(" ".join([
            str(channel.get("logo_url") or ""),
            " ".join(str(x.get("url", "")) for x in channel.get("sources", []) if isinstance(x, dict)),
        ]))
        for source in xmltv_sources:
            sid = source["id"]
            if sid == "pluto-br-xmltv":
                if not pid:
                    continue
                matches = [x["id"] for x in index_by_id.get(sid, {}).get("channels", []) if pid in x.get("id", "").lower()]
                if matches:
                    current_sources.append({"source_id": sid, "channel_id": matches[0], "priority": source["priority"], "match": "pluto_id"})
                continue
            name_to_ids = by_source_names.get(sid, {})
            keys = [normalise(name), *aliases_norm.get(normalise(name), [])]
            ids = list(dict.fromkeys(ident for key in keys for ident in name_to_ids.get(key, [])))
            if ids:
                for ident in ids:
                    current_sources.append({"source_id": sid, "channel_id": ident, "priority": source["priority"], "match": "exact_or_alias"})
        current_sources.sort(key=lambda x: (x["priority"], x["channel_id"]))
        if current_sources:
            # Keep all exact feed variants for adapters that can merge them; epg_id is the preferred legacy field.
            channel["epg_sources"] = current_sources
            channel["epg_id"] = current_sources[0]["channel_id"]
            updated += 1
    if updated:
        channel_doc["generated_at"] = now
        write_json(CHANNELS_FILE, channel_doc)
    xmltv_ids = {s["id"] for s in xmltv_sources}
    overall = "healthy" if any(health_by_id.get(sid, {}).get("status") == "healthy" for sid in xmltv_ids) else "degraded"
    write_json(HEALTH_FILE, {
        "schema_version": 1, "generated_at": now, "overall_status": overall,
        "matched_channel_records": updated, "sources": health_by_id,
    })
    print(f"EPG: {overall}; {updated} channel records mapped; statuses=" +
          str({k: v.get("status") for k, v in health_by_id.items()}))


if __name__ == "__main__":
    main()
