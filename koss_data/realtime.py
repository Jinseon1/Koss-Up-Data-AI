"""Optional adapter for events delivered by an existing WebSocket client.
No socket/server or authentication implementation is introduced here.
"""
from .core import integer, instant


def apply_attendance_event(snapshot, event, *, received_at, reconnect=False):
    if event.get('type') not in ('connected', 'attendance.updated'):
        return False
    data = event['data']
    revision = integer(data['revision'])
    count = integer(data['current_count'])
    received = instant(received_at)
    if event['type'] == 'attendance.updated':
        occurred = instant(event['occurred_at'])
        if occurred > received:
            return False
        observed_at = occurred.isoformat()
    else:
        observed_at = received.isoformat()
    old = snapshot.get('attendance')
    if old and not reconnect and revision <= old['revision']:
        return False
    snapshot['attendance'] = dict(current_count=count, revision=revision, observed_at=observed_at)
    return True
