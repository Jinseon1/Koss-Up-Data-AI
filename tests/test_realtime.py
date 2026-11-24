import unittest
from koss_data.realtime import apply_attendance_event

class Realtime(unittest.TestCase):
    def test_revision_order_duplicates_and_reconnect(self):
        s={}
        def event(rev):
            return dict(type='attendance.updated',occurred_at='2026-11-24T10:00:00+09:00',data=dict(current_count=3,revision=rev))
        now='2026-11-24T10:01:00+09:00'
        self.assertTrue(apply_attendance_event(s,event(2),received_at=now))
        self.assertFalse(apply_attendance_event(s,event(1),received_at=now))
        self.assertFalse(apply_attendance_event(s,event(2),received_at=now))
        self.assertTrue(apply_attendance_event(s,dict(type='connected',data=dict(current_count=1,revision=1)),received_at=now,reconnect=True))
    def test_chat_event_is_not_occupancy(self):
        self.assertFalse(apply_attendance_event({},dict(type='chat.message'),received_at='2026-11-24T10:00:00+09:00'))
