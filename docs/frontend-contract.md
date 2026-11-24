# 프론트엔드 연동 명세 v1.0

이 패키지는 추천 HTTP API를 새로 만들지 않습니다. `analyze()`가 반환하는 dict 또는 CLI의 UTF-8 JSON이 계약입니다. 프론트는 JSON을 읽어 그대로 표시할 수 있습니다. 운영 전달 위치·스케줄·접근 제어는 팀 합의가 필요합니다. 실제 데이터 및 추정치는 서버 쪽에서 계산하고, 세션 쿠키를 프론트 코드나 결과 JSON에 넣지 마세요.

## 최상위 필드

| 필드 | 타입 | NULL | 의미 |
| --- | --- | --- | --- |
| schema_version | string | 불가 | `1.0` |
| date | string | 불가 | 선택 날짜 YYYY-MM-DD |
| timezone | string | 불가 | Asia/Seoul |
| generated_at | string | 불가 | 계산 시각, 오프셋 포함 ISO 8601 |
| capacity | integer | 허용 | 확인된 선택 범위 전체 정원. 미확인 시 null |
| space_ids | integer[] | 불가 | 분석에 포함한 공간 ID |
| estimate_basis | string | 불가 | registered_participants_proxy: 신청 인원 기반 대리 추정 |
| recommendations | object[] | 불가 | 추천하지 않는 구간도 포함한 하루 전체 |
| issues | string[] | 불가 | 수집 실패·스키마 오류 등의 코드 |
| limitations | string[] | 불가 | 결과 해석상의 한계 |

## 시간대별 필드

| 필드 | 타입 | NULL | 의미 |
| --- | --- | --- | --- |
| start_time | string | 불가 | KST HH:MM |
| end_time | string | 불가 | KST HH:MM, 마지막 구간은 24:00 |
| starts_at / ends_at | string | 불가 | 날짜·오프셋 포함 ISO. 끝 시각은 다음 날일 수 있음 |
| reservation_count | integer | 허용 | 시간대 내 최대 동시 신청 인원, 고유 user_id 기준. 0은 신청 없음, null은 조회 불완전 |
| schedule_count | integer | 불가 | 겹치는 유효 일정 수. 수집 실패 시 전체 수를 보장하지 않음 |
| chat_count | integer | 허용 | 최근 엄격한 전체 인원 제보. 메시지 개수가 아님. 적용 여부와 무관하게 근거로 표시 |
| attendance_count | integer | 허용 | 현재 구간에 한한 최신 동방 전체 버튼 기록 |
| estimated_count | integer | 허용 | 아래 규칙으로 계산한 보수적 신청 기반 추정. 알 수 없으면 null |
| congestion_ratio | number | 허용 | estimated_count / capacity. 1 초과 가능; 클리핑 안 함 |
| congestion_level | string | 허용 | LOW / MEDIUM / HIGH. 근거 또는 정원 없으면 null |
| recommended | boolean | 불가 | LOW + MEDIUM 신뢰도 + 아직 시작하지 않은 시간. 조건 부족이면 false |
| data_source | string[] | 불가 | 계산에 사용한 출처만 기재 |
| confidence | string | 불가 | LOW / MEDIUM. 현 버전은 HIGH를 생성하지 않음 |
| reasons | string[] | 불가 | 계산 근거와 한계 설명 |
| history | object | 불가 | 아래 과거 통계 |

## history 필드

| 필드 | 타입 | NULL | 의미 |
| --- | --- | --- | --- |
| sample_days | integer | 불가 | 완전 보존 기간 안에서 계산 가능한 동일 요일 일수 |
| mean_count | number | 허용 | 일별 시간대 최대 동시 신청 인원의 산술평균 |
| max_count | integer | 허용 | 그 일별 값들의 최대 |
| reservation_frequency | number | 허용 | 일정이 존재한 표본 일수 / 전체 표본 일수 |
| recent_mean | number | 허용 | 최근 최대 4개 동일 요일 표본의 평균 |
| trend_delta | number | 허용 | 최근 4일 평균 - 이전 최대 4일 평균. 이전 표본 없으면 null |

출처 값: `timetable`, `timetable_history`, `attendance`, `chat_explicit_report`. chat_count가 있어도 opt-in이 꺼졌거나 attendance가 우선 적용되면 chat_explicit_report는 출처에 들어가지 않습니다. analytics는 수집되지만 예약 예상치 산식에는 넣지 않습니다.

## 계산·신뢰도 정책

1. 모든 시간은 Asia/Seoul로 정규화합니다. 구간은 `[시작, 종료)`입니다. 종료 시각이 다음 일정 시작과 같으면 동시 인원으로 합하지 않습니다.
2. 각 순간 겹치는 일정 참여자의 user_id 합집합 크기를 구하고, 구간 안에서 가장 큰 값을 reservation_count로 삼습니다. 일정 ID 중복은 제거하고 상충 중복은 계산을 실패시킵니다. 참여자 미확보 일정이 겹치는 구간은 unknown입니다.
3. 모집 정원 expected_count는 인원으로 계산하지 않습니다. 취소 일정은 제외하고 현재 참여자 목록에서 빠진 사람도 계산하지 않습니다.
4. 과거 통계는 history_start 이후, 선택 날짜와 오늘 중 이른 날짜 미만의 동일 요일만 사용합니다. 완전 보존 기간이 확인되지 않으면 과거 통계 사용을 꺼둡니다. 관측된 기간 안의 무예약 날짜만 신청자 0 표본으로 포함합니다.
5. 과거 표본이 기본 4일 이상일 때 `max(현재 신청 인원, ceil(동일 요일 평균))`을 사용합니다. 표본이 부족하면 양수인 현재 신청 인원만 사용합니다. 4일 기준은 운영상 최소 표본 정책이며 통계적으로 입증된 정확도 기준이 아닙니다.
6. 현재/과거 모두 신청 0이고 다른 양수 근거가 없으면 estimated_count는 null입니다. 데이터 부족을 낮은 혼잡도로 바꾸지 않습니다.
7. 전체 방 분석에서 현재 진행 중인 구간에만 최근 15분 이내 attendance를 적용합니다. REST에 서버 시각이 없어 요청 시작을 observed_at으로 기록합니다. `max(기본 추정, 버튼 인원)`이며 합산하지 않습니다. 15분은 설정 가능한 만료 정책입니다. 열린 방문의 실제 체류 여부는 검증되지 않았습니다.
8. 채팅은 메시지 전체가 `지금 동방 전체 인원은 N명입니다` 형식일 때만 제보 후보입니다. `.` 또는 `!` 한 개를 허용합니다. 질문·미래 계획·부분 집단·혼잡하다는 표현은 제외합니다. ID 중복 제거 후 최근 15분 내 가장 최신 후보를 선택합니다. 자유 자연어의 모든 명시적 표현을 이해하는 기능은 아닙니다. 특정 과거/미래 시각의 인원 표현은 안전하게 제외합니다.
9. 채팅 수치 반영은 기본 꺼짐입니다. 켜면 현재 구간에서 attendance가 없을 때만 기본 추정과 큰 값을 택합니다. 제보가 많아도 진위가 입증되지는 않습니다. 수치 반영 시 항상 LOW입니다.
10. 신뢰도 MEDIUM은 현재 예약 조회가 완전하고 과거 표본이 4일 이상이며 양수 예상치를 계산한 경우입니다. 나머지는 LOW입니다. 실제 방문 대비 정확도 의미가 아니라 **신청 기반 계산 근거의 충족 정도**입니다. 현재 attendance 보정도 실제 신고 완전성이 불명하므로 LOW입니다.
11. `ratio <= .30` LOW, `.30 < ratio <= .60` MEDIUM, `.60 < ratio` HIGH입니다. Config로 변경 가능합니다. 정원 초과는 LOW 신뢰도로 내려 추천하지 않습니다.
12. 추천은 위의 신뢰도 조건을 만족하는 LOW 구간 전부입니다. 임의 top-k, 순위 가중치, 예측 모델은 사용하지 않습니다. 결과가 전부 false여도 정상입니다.

## 표시·운영 권장

- estimated_count=null은 `정보 부족`, confidence=LOW는 `낮은 신뢰도`로 표시합니다. null을 0으로 치환하지 마세요.
- 표시는 `예약 신청 기반 예상 2명`처럼 추정 기준을 포함하세요. 실제 인원 보장 문구는 피하세요.
- recommended=false는 혼잡하다는 뜻이 아닙니다. 시간 경과나 근거 부족일 수도 있습니다.
- 전체 24개 구간은 그대로 제공하며 운영 시간 정보는 아직 없습니다. 실제 방문 가능 시간을 제한하려면 팀에서 운영 시간을 확인해야 합니다.
- 기존 WebSocket의 schedule.changed에서는 데이터를 다시 읽고, attendance.updated는 어댑터에 전달할 수 있습니다. 연결 복구 시 REST 재조회가 필요합니다. 이 패키지는 자동 주기 수집/배포/구독을 실행하지 않습니다.
- 여러 API 요청은 하나의 DB 스냅샷이 아닙니다. 수집 중 변경 경쟁 가능성을 limitations로 이해하고 갱신하세요.

## Python 호출 예

```python
from koss_data import analyze, Config
result = analyze(snapshot, '2026-11-24', capacity=20, space_ids=[1],
                 room_scope=True, history_start=None,
                 config=Config(slot_minutes=60))
```

snapshot은 Client.collect()의 반환값입니다. spaces/schedules는 각각 백엔드 배열이며 participants는 일정 ID 문자열을 키로 하는 participants API 원본 객체입니다. 선택 항목은 messages 배열, attendance 객체(current_count/revision/observed_at), analytics 객체, issues 배열입니다. API 실패를 빈 schedules 배열로 바꾸지 마세요. 알 수 없음은 schedules=null로 전달하거나 요청을 실패시키세요.

예제 입력과 출력은 examples 폴더에 있습니다. `result.synthetic.json`은 고정 시각 2026-11-24 08:00 KST에서 생성한 가상 결과입니다.
