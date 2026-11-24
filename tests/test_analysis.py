import unittest
from koss_data import analyze, Config
from koss_data.core import chat_evidence, instant
from koss_data.client import Client

NOW='2026-11-24T08:00:00+09:00'

def row(i=1,start='2026-11-24T10:00:00+09:00',end='2026-11-24T11:00:00+09:00',**kw):
    return dict(id=i,space_id=1,starts_at=start,ends_at=end,expected_count=30,is_cancelled=False,**kw)

def snap(rows=(),users=None):
    users=users or {r['id']:['a','b'] for r in rows}
    return dict(spaces=[dict(id=1,capacity=20)],schedules=list(rows),participants={str(i):dict(schedule_id=i,capacity=30,participant_count=len(u),participants=[dict(user_id=v) for v in u]) for i,u in users.items()})

def run(s,**kw):
    return analyze(s,'2026-11-24',capacity=20,space_ids=[1],now=kw.pop('now',NOW),**kw)

class Analysis(unittest.TestCase):
    def test_timetable_proxy(self):
        r=run(snap([row()]))['recommendations'][10]
        self.assertEqual(r['estimated_count'],2); self.assertEqual(r['confidence'],'LOW'); self.assertFalse(r['recommended'])
    def test_no_reservation_not_empty(self):
        r=run(snap())['recommendations'][10]
        self.assertEqual(r['reservation_count'],0); self.assertIsNone(r['estimated_count']); self.assertIsNone(r['congestion_level'])
    def test_missing_schedules(self):
        s=snap(); s['schedules']=None
        self.assertIsNone(run(s)['recommendations'][10]['reservation_count'])
    def test_duplicates_and_cancelled(self):
        a,b,c=row(),row(2),row(3); c['is_cancelled']=True
        self.assertEqual(run(snap([a,a,b,c],{1:['a','b'],2:['b','c'],3:['d']}))['recommendations'][10]['reservation_count'],3)
    def test_sequential_not_summed(self):
        a=row(end='2026-11-24T10:30:00+09:00'); b=row(2,start='2026-11-24T10:30:00+09:00')
        self.assertEqual(run(snap([a,b],{1:['a','b'],2:['c','d']}))['recommendations'][10]['reservation_count'],2)
    def test_leave(self):
        self.assertEqual(run(snap([row()],{1:['a']}))['recommendations'][10]['reservation_count'],1)
    def test_missing_participants(self):
        s=snap([row()]); s['participants']={}
        r=run(s)['recommendations']; self.assertIsNone(r[10]['reservation_count']); self.assertEqual(r[11]['reservation_count'],0)
    def test_general_chat_rejected(self):
        ms=[dict(id=i,created_at=NOW,content=t) for i,t in enumerate(['많아요','내일 3명','우리 3명','지금 동방 전체 인원은 3명입니다?','10시에 3명'])]
        self.assertIsNone(chat_evidence(ms,instant(NOW),Config()))
    def test_chat_opt_in_and_stale(self):
        s=snap([row()]); s['messages']=[dict(id=1,created_at='2026-11-24T10:02:00+09:00',content='지금 동방 전체 인원은 5명입니다')]*2
        r=run(s,room_scope=True,now='2026-11-24T10:05:00+09:00',config=Config(use_chat=True))['recommendations'][10]
        self.assertEqual(r['estimated_count'],5); self.assertEqual(r['confidence'],'LOW')
        self.assertIsNone(run(s,room_scope=True,now='2026-11-24T11:05:00+09:00')['recommendations'][11]['chat_count'])
        self.assertEqual(run(s,room_scope=True,now='2026-11-24T10:05:00+09:00')['recommendations'][10]['estimated_count'],2)
    def test_attendance_precedence_and_scope(self):
        s=snap([row()]); s['attendance']=dict(current_count=7,revision=1,observed_at='2026-11-24T10:03:00+09:00')
        s['messages']=[dict(id=1,created_at='2026-11-24T10:04:00+09:00',content='지금 동방 전체 인원은 9명입니다')]
        r=run(s,room_scope=True,now='2026-11-24T10:05:00+09:00',config=Config(use_chat=True))['recommendations']
        self.assertEqual(r[10]['estimated_count'],7); self.assertIsNone(r[11]['attendance_count'])
        self.assertIsNone(run(s,now='2026-11-24T10:05:00+09:00')['recommendations'][10]['attendance_count'])
    def test_history_requires_coverage(self):
        rows=[row(i,f'2026-{md}T10:00:00+09:00',f'2026-{md}T11:00:00+09:00') for i,md in enumerate(['10-27','11-03','11-10','11-17'],1)]
        s=snap(rows); r=run(s,history_start='2026-10-27')['recommendations'][10]
        self.assertEqual(r['history']['sample_days'],4); self.assertTrue(r['recommended']); self.assertEqual(r['estimated_count'],2)
        self.assertIsNone(run(s)['recommendations'][10]['estimated_count'])
    def test_timezone_slot_and_midnight(self):
        r=run(snap([row(start='2026-11-23T15:00:00Z',end='2026-11-23T16:00:00Z')]),config=Config(slot_minutes=30))['recommendations']
        self.assertEqual(len(r),48); self.assertEqual(r[0]['reservation_count'],2); self.assertEqual(r[-1]['end_time'],'24:00')
    def test_thresholds(self):
        for n,lv in [(6,'LOW'),(7,'MEDIUM'),(12,'MEDIUM'),(13,'HIGH')]:
            self.assertEqual(run(snap([row()],{1:list(map(str,range(n)))}))['recommendations'][10]['congestion_level'],lv)
    def test_conflicting_duplicate(self):
        a=row(); b=dict(a,expected_count=3)
        with self.assertRaises(ValueError): run(snap([a,b]))
    def test_naive_time_unknown(self):
        self.assertIsNone(run(snap([row(start='2026-11-24T10:00:00')]))['recommendations'][10]['reservation_count'])
    def test_config(self):
        for m in [0,-1,17]:
            with self.assertRaises(ValueError): Config(slot_minutes=m)

class Collector(unittest.TestCase):
    def fake(self,fail=False):
        class Fake(Client):
            def __init__(self): self.calls=[]
            def get(self,path,**q):
                self.calls.append((path,q))
                if path=='/api/spaces/': return dict(spaces=[dict(id=1,capacity=20)])
                if path=='/api/schedules/': return dict(schedules=[row()])
                if 'participants' in path:
                    if fail: raise OSError()
                    return snap([row()])['participants']['1']
                if 'occupancy' in path: return dict(current_count=2,revision=1)
                if 'analytics' in path: return dict(hourly=[])
                if fail: raise OSError()
                old='before_id' in q
                return dict(date='2026-11-24',messages=[dict(id=1 if old else 2,created_at=NOW,content='hi')],has_more=not old,next_before_id=None if old else 2)
        return Fake()
    def test_pagination(self):
        c=self.fake(); s=c.collect('2026-11-24',space_ids=[1]); self.assertEqual([m['id'] for m in s['messages']],[1,2])
        self.assertEqual(c.calls[-2][1].get('before_id'),2)
    def test_degradation(self):
        s=self.fake(True).collect('2026-11-24',space_ids=[1]); self.assertIn('chat_fetch_failed',s['issues']); self.assertIsNone(run(s)['recommendations'][10]['estimated_count'])
    def test_origin(self):
        for origin in ['http://example.com','https://example.com/path','https://a:b@example.com']:
            with self.assertRaises(ValueError): Client(origin,'sessionid=x')

if __name__=='__main__': unittest.main()
