#!/usr/bin/env python3
"""Generate iPhone-compatible .ics invites for Secret Riso Club July 2026 events."""

from __future__ import annotations

import uuid
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
INDIVIDUAL_DIR = OUT_DIR / "individual"

# Shared VTIMEZONE blocks for Apple Calendar / iOS
VTIMEZONE_NY = """BEGIN:VTIMEZONE
TZID:America/New_York
X-LIC-LOCATION:America/New_York
BEGIN:DAYLIGHT
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
TZNAME:EDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
TZNAME:EST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE"""

VTIMEZONE_SF = """BEGIN:VTIMEZONE
TZID:America/Los_Angeles
X-LIC-LOCATION:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE"""

VTIMEZONE_CDMX = """BEGIN:VTIMEZONE
TZID:America/Mexico_City
X-LIC-LOCATION:America/Mexico_City
BEGIN:STANDARD
TZOFFSETFROM:-0600
TZOFFSETTO:-0600
TZNAME:CST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE"""


def fold(line: str) -> str:
    """RFC 5545 line folding at 75 octets (ASCII-safe for these strings)."""
    if len(line) <= 75:
        return line
    parts = [line[:75]]
    rest = line[75:]
    while rest:
        parts.append(" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(parts)


def escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def uid() -> str:
    return f"{uuid.uuid4()}@secretrisoclub.calendar"


def vevent_timed(
    *,
    summary: str,
    description: str,
    location: str,
    dtstart: str,
    dtend: str,
    tzid: str,
) -> str:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid()}",
        "DTSTAMP:20260719T000000Z",
        f"DTSTART;TZID={tzid}:{dtstart}",
        f"DTEND;TZID={tzid}:{dtend}",
        f"SUMMARY:{escape_text(summary)}",
        f"DESCRIPTION:{escape_text(description)}",
        f"LOCATION:{escape_text(location)}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "END:VEVENT",
    ]
    return "\r\n".join(fold(line) for line in lines)


def vevent_all_day(
    *,
    summary: str,
    description: str,
    location: str,
    start_date: str,
    end_date_exclusive: str,
) -> str:
    # All-day DTEND is exclusive per RFC 5545
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid()}",
        "DTSTAMP:20260719T000000Z",
        f"DTSTART;VALUE=DATE:{start_date}",
        f"DTEND;VALUE=DATE:{end_date_exclusive}",
        f"SUMMARY:{escape_text(summary)}",
        f"DESCRIPTION:{escape_text(description)}",
        f"LOCATION:{escape_text(location)}",
        "STATUS:CONFIRMED",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]
    return "\r\n".join(fold(line) for line in lines)


def calendar(events: list[str], timezones: list[str], calname: str) -> str:
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Secret Riso Club//July 2026 Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(calname)}",
        "X-WR-TIMEZONE:America/New_York",
    ]
    # Normalize timezone blocks to CRLF for RFC 5545 / iOS Calendar
    tz_blocks = [tz.replace("\r\n", "\n").replace("\n", "\r\n") for tz in timezones]
    parts = header + tz_blocks + events + ["END:VCALENDAR"]
    body = "\r\n".join(parts)
    return body + "\r\n"


EVENTS: list[dict] = [
    {
        "slug": "01-book-swap",
        "summary": "Book Swap - Secret Riso Club",
        "description": "Bring a book or zine to trade and swap!\n\nSecret Riso Club Calendar - July Events & Workshops",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260708T160000",
        "dtend": "20260708T190000",
        "tz": "ny",
    },
    {
        "slug": "02-touch-designer-workshop-jul8",
        "summary": "Touch Designer Workshop (Session 1 of 2) - Secret Riso Club",
        "description": "Learn Touch Designer and create your own file for riso! This is a two-session workshop.\n\nSession 1 of 2 (also July 11).",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260708T180000",
        "dtend": "20260708T210000",
        "tz": "ny",
    },
    {
        "slug": "03-west-side-festival",
        "summary": "West Side Festival - Secret Riso Club",
        "description": "Live tote bag screenprinting at Poster House.",
        "location": "Poster House, Manhattan",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260710T120000",
        "dtend": "20260710T170000",
        "tz": "ny",
    },
    {
        "slug": "04-touch-designer-workshop-jul11",
        "summary": "Touch Designer Workshop (Session 2 of 2) - Secret Riso Club",
        "description": "Learn Touch Designer and create your own file for riso! This is a two-session workshop.\n\nSession 2 of 2 (also July 8).",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260711T180000",
        "dtend": "20260711T210000",
        "tz": "ny",
    },
    {
        "slug": "05-riso-102-jul13",
        "summary": "Riso 102 (Session 1 of 2) - Secret Riso Club",
        "description": "Riso 102 is the perfect class for those who have already taken 101 or have prior Riso experience.\n\nSession 1 of 2 (also July 20).",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260713T180000",
        "dtend": "20260713T210000",
        "tz": "ny",
    },
    {
        "slug": "06-riso-101-jul15",
        "summary": "Riso 101 - Secret Riso Club",
        "description": "Learn the basics of Riso, no experience needed.",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260715T183000",
        "dtend": "20260715T213000",
        "tz": "ny",
    },
    {
        "slug": "07-club-kids",
        "summary": "Club Kids - Secret Riso Club",
        "description": "A riso workshop for kids, hosted by Citation Needed.",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260718T110000",
        "dtend": "20260718T130000",
        "tz": "ny",
    },
    {
        "slug": "08-zurdo-book-launch",
        "summary": "Zurdo..! Book Launch - Secret Riso Club",
        "description": "Join us for a night of readings and the book launch for Zurdo..!, a sci-fi novella by Nat Pyper.",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260718T180000",
        "dtend": "20260718T210000",
        "tz": "ny",
    },
    {
        "slug": "09-riso-102-jul20",
        "summary": "Riso 102 (Session 2 of 2) - Secret Riso Club",
        "description": "Riso 102 is the perfect class for those who have already taken 101 or have prior Riso experience.\n\nSession 2 of 2 (also July 13).",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260720T180000",
        "dtend": "20260720T210000",
        "tz": "ny",
    },
    {
        "slug": "10-sf-art-book-fair",
        "summary": "San Francisco Art Book Fair - Secret Riso Club",
        "description": "Minnesota Street Project Foundation presents. Visit us at Table A16.\n\nMulti-day fair (times not listed on flyer).",
        "location": "San Francisco, CA",
        "type": "allday",
        "start_date": "20260723",
        "end_date_exclusive": "20260727",
        "tz": "sf",
    },
    {
        "slug": "11-riso-101-jul25",
        "summary": "Riso 101 - Secret Riso Club",
        "description": "Learn the basics of Riso, no experience needed.",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260725T183000",
        "dtend": "20260725T213000",
        "tz": "ny",
    },
    {
        "slug": "12-interactive-poems-workshop",
        "summary": "Interactive Poems Workshop - Secret Riso Club",
        "description": "Learn four paper-engineering techniques to create interactive layouts for text and images using folding, hosted by Extra Credit.",
        "location": "SRC, Brooklyn",
        "type": "timed",
        "tzid": "America/New_York",
        "dtstart": "20260726T130000",
        "dtend": "20260726T170000",
        "tz": "ny",
    },
    {
        "slug": "13-hardcore-art-book-fair",
        "summary": "Hardcore Art Book Fair - Secret Riso Club",
        "description": "Look forward to SRC table and programming!\n\nMulti-day fair (times not listed on flyer).",
        "location": "CDMX (Mexico City)",
        "type": "allday",
        "start_date": "20260730",
        "end_date_exclusive": "20260803",
        "tz": "cdmx",
    },
]

TZ_BLOCKS = {
    "ny": VTIMEZONE_NY,
    "sf": VTIMEZONE_SF,
    "cdmx": VTIMEZONE_CDMX,
}


def build_vevent(event: dict) -> str:
    if event["type"] == "timed":
        return vevent_timed(
            summary=event["summary"],
            description=event["description"],
            location=event["location"],
            dtstart=event["dtstart"],
            dtend=event["dtend"],
            tzid=event["tzid"],
        )
    return vevent_all_day(
        summary=event["summary"],
        description=event["description"],
        location=event["location"],
        start_date=event["start_date"],
        end_date_exclusive=event["end_date_exclusive"],
    )


def main() -> None:
    INDIVIDUAL_DIR.mkdir(parents=True, exist_ok=True)

    vevents: list[str] = []
    for event in EVENTS:
        vevent = build_vevent(event)
        vevents.append(vevent)
        tz = TZ_BLOCKS[event["tz"]]
        ics = calendar([vevent], [tz], event["summary"])
        path = INDIVIDUAL_DIR / f"{event['slug']}.ics"
        path.write_bytes(ics.encode("utf-8"))
        print(f"Wrote {path.name}")

    all_ics = calendar(
        vevents,
        [VTIMEZONE_NY, VTIMEZONE_SF, VTIMEZONE_CDMX],
        "Secret Riso Club - July 2026",
    )
    all_path = OUT_DIR / "secret-riso-club-july-2026.ics"
    all_path.write_bytes(all_ics.encode("utf-8"))
    print(f"Wrote {all_path.name} ({len(EVENTS)} events)")


if __name__ == "__main__":
    main()
