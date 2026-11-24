"""Synthetic fixtures only. No API data or personal identifiers."""
import json
from pathlib import Path
from koss_data import analyze

s = dict(spaces=[dict(id=1,name='가상 테이블',capacity=20)],schedules=[],participants={})
for i,md in enumerate(['10-27','11-03','11-10','11-17','11-24'],1):
    s['schedules'].append(dict(id=i,space_id=1,starts_at=f'2026-{md}T10:00:00+09:00',ends_at=f'2026-{md}T11:00:00+09:00',expected_count=8,is_cancelled=False))
    s['participants'][str(i)]=dict(schedule_id=i,capacity=8,participant_count=2,participants=[dict(user_id='synthetic-A'),dict(user_id='synthetic-B')])
root=Path(__file__).parent
(root/'snapshot.synthetic.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
r=analyze(s,'2026-11-24',capacity=20,space_ids=[1],history_start='2026-10-27',now='2026-11-24T08:00:00+09:00')
(root/'result.synthetic.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
