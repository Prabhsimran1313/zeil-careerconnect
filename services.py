import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
TZ = ZoneInfo('Pacific/Auckland')
SESSION_TYPES = ['Technical Mock Interview', 'Behavioural Mock Interview', 'Career Guidance']


@contextmanager
def connection():
    path = Path(os.getenv('CAREERCONNECT_DB', str(ROOT / 'data' / 'careerconnect.db')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS workspaces
        (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bookings (id TEXT PRIMARY KEY, owner TEXT NOT NULL,
        mentor INTEGER NOT NULL, slot TEXT NOT NULL, payload TEXT NOT NULL,
        UNIQUE(mentor, slot));''')
    try:
        with db:
            yield db
    finally:
        db.close()


def save_workspace(owner, payload):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO workspaces VALUES (?,?)', (owner, json.dumps(payload)))


def load_workspace(owner):
    with connection() as db:
        row = db.execute('SELECT payload FROM workspaces WHERE id=?', (owner,)).fetchone()
    return json.loads(row['payload']) if row else None


def load_mentors():
    return json.loads((ROOT / 'mentors.json').read_text(encoding='utf-8'))


ALIASES = {'etl': ['etl', 'data pipeline', 'data pipelines', 'extract transform', 'data migration'],
    'plm': ['plm', 'teamcenter', 'epdm', 'product lifecycle', 'cad', 'metadata'],
    'machine learning': ['machine learning', 'ml', 'artificial intelligence'],
    'llms': ['llms', 'llm', 'large language models', 'generative ai'],
    'data visualisation': ['data visualisation', 'data visualization', 'dashboards'],
    'stakeholder management': ['stakeholder management', 'stakeholders', 'cross-functional']}


def concepts(text):
    text = text.lower()
    def contains(term):
        return re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text) is not None
    known = {s.lower() for m in load_mentors() for s in m['skills']}
    found = {s for s in known if contains(s)}
    for canonical, aliases in ALIASES.items():
        if any(contains(alias) for alias in aliases):
            found.add(canonical)
    return found


def match_mentor(mentor, priorities):
    matched = concepts(' '.join(priorities)) & concepts(' '.join(mentor['skills']))
    return len(matched), sorted(matched)


def available_slots(mentor, now=None):
    now = now or datetime.now(TZ)
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    slots = []
    with connection() as db:
        reserved = {r['slot'] for r in db.execute('SELECT slot FROM bookings WHERE mentor=?', (mentor['id'],))}
    for offset in range(15):
        day = (now + timedelta(days=offset)).date()
        for template in mentor['slots']:
            weekday, hour, period = template.split()
            if weekdays[day.weekday()] == weekday:
                h = int(hour) % 12 + (12 if period == 'PM' else 0)
                slot = datetime(day.year, day.month, day.day, h, tzinfo=TZ)
                if slot > now and slot.isoformat() not in reserved:
                    slots.append(slot.isoformat())
    return sorted(slots)


def book_session(owner, mentor, slot, session_type, role):
    if session_type not in SESSION_TYPES or slot not in available_slots(mentor):
        raise ValueError('This slot is no longer available. Choose another time.')
    booking = dict(id=str(uuid4()), mentor_name=mentor['name'], mentor_id=mentor['id'],
        slot=slot, session_type=session_type, role=role, price_nzd=mentor['price_nzd'], duration=30)
    try:
        with connection() as db:
            db.execute('INSERT INTO bookings VALUES (?,?,?,?,?)',
                (booking['id'], owner, mentor['id'], slot, json.dumps(booking)))
    except sqlite3.IntegrityError as exc:
        raise ValueError('That time was just reserved. Choose another slot.') from exc
    return booking


def bookings_for(owner):
    with connection() as db:
        return [json.loads(r['payload']) for r in db.execute(
            'SELECT payload FROM bookings WHERE owner=? ORDER BY slot', (owner,))]


def cancel_booking(owner, booking_id):
    with connection() as db:
        db.execute('DELETE FROM bookings WHERE owner=? AND id=?', (owner, booking_id))


def calendar_event(booking):
    start = datetime.fromisoformat(booking['slot'])
    def utc(dt):
        return dt.astimezone(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')
    return '\r\n'.join(['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//CareerConnect//Demo//EN',
        'BEGIN:VEVENT', f"UID:{booking['id']}@careerconnect.demo", f'DTSTAMP:{utc(datetime.now(TZ))}',
        f'DTSTART:{utc(start)}', f'DTEND:{utc(start + timedelta(minutes=30))}',
        f"SUMMARY:Demo mentorship with {booking['mentor_name']}",
        'DESCRIPTION:Simulated booking. No actual interview or payment is arranged.',
        'END:VEVENT', 'END:VCALENDAR', ''])
