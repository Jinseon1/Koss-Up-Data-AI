"""GET-only collector for backend commit b15935c7. Session stays in memory."""
from datetime import datetime
import json
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlencode, urlsplit
from .core import KST, instant


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, base_url, session_cookie, *, timeout=15):
        parsed = urlsplit(base_url)
        if (parsed.scheme not in ('http', 'https') or not parsed.netloc
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/')):
            raise ValueError('Base URL must be an origin')
        if parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('Remote backend requires HTTPS')
        if not session_cookie or any(c in session_cookie for c in '\r\n'):
            raise ValueError('Valid session cookie required')
        self.base = base_url.rstrip('/')
        self.cookie = session_cookie
        self.timeout = timeout

    def get(self, path, **query):
        if not path.startswith('/api/') or '?' in path:
            raise ValueError('Only known API paths')
        url = self.base + path + ('?' + urlencode(query) if query else '')
        req = Request(url, headers={'Cookie': self.cookie, 'Accept': 'application/json'}, method='GET')
        # Never follow a login/cross-origin redirect with session credentials.
        with build_opener(NoRedirect()).open(req, timeout=self.timeout) as response:
            result = json.load(response)
        if not isinstance(result, dict) or 'error' in result:
            raise ValueError('Invalid API response')
        return result

    def collect(self, day, *, space_ids):
        # Required collections fail closed; optional data degrades explicitly.
        spaces = self.get('/api/spaces/')['spaces']
        schedules = self.get('/api/schedules/')['schedules']
        if not isinstance(spaces, list) or not isinstance(schedules, list):
            raise ValueError('Invalid API collection')
        snapshot = dict(spaces=spaces, schedules=schedules, participants={}, messages=[], issues=[])
        for row in schedules:
            if row['is_cancelled'] or row['space_id'] not in space_ids:
                continue
            try:
                snapshot['participants'][str(row['id'])] = self.get(f"/api/schedules/{int(row['id'])}/participants/")
            except Exception:
                snapshot['issues'].append(f"participants_fetch_failed:{row['id']}")
        try:
            before = datetime.now(KST)
            snapshot['attendance'] = self.get('/api/attendance/occupancy/')
            # Conservative collection start, since response has no server timestamp.
            snapshot['attendance']['observed_at'] = before.isoformat()
        except Exception:
            snapshot['issues'].append('attendance_fetch_failed')
        try:
            cursor, cursors, messages = None, set(), {}
            while True:
                query = dict(date=day, limit=100)
                if cursor is not None:
                    query['before_id'] = cursor
                page = self.get('/api/chat/messages/', **query)
                if page['date'] != day or type(page['has_more']) is not bool:
                    raise ValueError('Invalid chat page')
                for m in page['messages']:
                    if instant(m['created_at']).date().isoformat() != day:
                        raise ValueError('Wrong message date')
                    if m['id'] in messages and messages[m['id']] != m:
                        raise ValueError('Conflicting message')
                    messages[m['id']] = m
                if not page['has_more']:
                    break
                nxt = page['next_before_id']
                if type(nxt) is not int or nxt <= 0 or nxt in cursors or (cursor is not None and nxt >= cursor):
                    raise ValueError('Invalid pagination cursor')
                cursors.add(nxt)
                cursor = nxt
            snapshot['messages'] = sorted(messages.values(), key=lambda m: m['id'])
        except Exception:
            snapshot['issues'].append('chat_fetch_failed')
        try:
            snapshot['analytics'] = self.get('/api/analytics/daily/', date=day)
        except Exception:
            snapshot['issues'].append('analytics_fetch_failed')
        snapshot['collected_at'] = datetime.now(KST).isoformat()
        return snapshot
