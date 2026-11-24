# 실제 백엔드 API 조사

기준: [고정 커밋](https://github.com/y3rtcn/koss-room-backend/tree/b15935c7b0b6bf65fde0856272e6db8c2c37cc04), 2026-11-24. 아래는 코드의 JSON 생성 계약을 확인한 결과입니다. 운영 서버에서 받은 응답이라고 주장하지 않습니다.

| 실제 GET 경로 | 응답 필드 및 구조 | 활용 |
| --- | --- | --- |
| `/api/accounts/me/` | `id:string, email:string, nickname:string` | 분석 불필요, 미수집 |
| `/api/spaces/` | `spaces:[{id:int,name:string,capacity:int}]` | 활성 공간과 정원 확인; 공간 간 중첩 여부 불명 |
| `/api/schedules/` | `schedules:[{id:int,title:string,creator_id:string,space_id:int,space_name:string,starts_at:ISO,ends_at:ISO,expected_count:int,purpose:string,is_cancelled:bool}]` | 모든 미취소 일정; 날짜 필터와 페이지 없음 |
| `/api/schedules/{id}/participants/` | `schedule_id:int,capacity:int,participant_count:int,participants:[{user_id:string,nickname:string,is_creator:bool}]` | 현재 실제 신청자 목록. capacity는 일정 모집 정원 |
| `/api/attendance/occupancy/` | `current_count:int,revision:int` | 동방 전체 버튼 기록; 서버 관측 시각 없음 |
| `/api/attendance/me/` | `is_inside:bool,active_visit:object|null,current_count:int,revision:int` | 개인 입실 정보는 불필요하여 미수집 |
| `/api/chat/messages/?date=YYYY-MM-DD&limit=100` | `date,timezone,messages,has_more,next_before_id,next_after_id` | 전체 페이지 수집. 최근 페이지부터 before_id로 과거 조회 |
| 메시지 항목 | `id:int,user_id:string,nickname:string,content:string,client_id:UUID,created_at:ISO` | 인원 전용 필드 없음. 일반 대화는 인원으로 변환하지 않음 |
| `/api/analytics/daily/?date=YYYY-MM-DD` | `date,timezone,basis,as_of,observed_seconds,visit_count,unique_users,person_seconds,average_count,peak_count,hourly` | 수집만 함. 예약 통계로 재해석하지 않음 |
| analytics `hourly[]` | `hour:int,observed_seconds:number,average_count:number|null,peak_count:int|null` | 버튼 기록의 0~23시 24개. 미래는 null; 지난 기록 0도 센서 검증된 빈 방은 아님 |

`/api/attendance/` 자체에는 현재 인원 조회 핸들러가 없습니다. 실제 경로는 `/api/attendance/occupancy/`입니다.

모든 기능 GET과 WebSocket은 활성 사용자 Django 세션 쿠키가 필요합니다. Bearer 토큰 방식이 아닙니다. 쓰기는 CSRF 필요하지만 이 패키지는 쓰기·입퇴실·닉네임 변경·일정 변경·메시지 전송을 하지 않습니다.

## 중요한 데이터 의미

`expected_count`는 신청 가능 모집 정원입니다. `join_schedule()`은 현재 신청 수가 이 값 이상이면 막고, `participant_list()`는 이를 `capacity`로 반환합니다. 예상 방문 인원으로 직접 합산하지 않습니다. 작성자는 생성 시 Participation에 포함되므로 별도로 +1 하지 않습니다. 참여 취소는 Participation 삭제이며, 현재 목록에서 이미 빠집니다. 일정 목록은 취소 일정 자체를 제외합니다. 방어적으로 is_cancelled도 검사합니다.

과거 데이터도 현재 신청 상태입니다. 과거 취소 전 인원·모집 완료 시점·변경 이력은 노출되지 않습니다. 조회가 성공했다고 과거 보존 기간이 자동 증명되는 것은 아닙니다. 분석의 history_start는 별도 확인이 필요합니다.

## 채팅 및 실시간 확인 결과

1. 날짜별 메시지 조회 가능, KST 날짜 기준이며 페이지를 모두 읽어야 합니다.
2. 작성 시각 created_at이 포함됩니다.
3. 스키마에 명시적 상주 인원 필드는 없습니다. 실제 메시지 내용은 아직 미확보입니다.
4. `/ws/room/`의 `attendance.updated.data`는 current_count와 revision을 제공합니다. envelope에 event_id, occurred_at이 있습니다.
5. `chat.message.data.message`와 attendance.updated는 구분됩니다. 채팅을 입퇴실 이벤트로 처리하지 않습니다.

연결 직후 connected.data에도 현재 인원이 있습니다. revision 순서로 중복·과거 이벤트를 버립니다. 재연결은 authoritative connected/REST 재조회로 기준을 갱신해야 합니다. 소켓 전달은 최선형이므로 누락 복구를 보장하지 않습니다. 패키지의 realtime 어댑터는 전달받은 이벤트만 처리하며 소켓 연결/재연결 루프는 구현하지 않았습니다. schedule.changed를 받으면 일정/참여자를 다시 수집한 뒤 재계산해야 합니다.

## 코드 근거

- [일정 JSON과 participants](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/schedules/views.py)
- [일정 모집·참여·취소 의미](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/schedules/services.py)
- [공간 정원](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/spaces/views.py)
- [입퇴실 응답](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/attendance/views.py)
- [채팅 조회와 페이지](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/chat/services.py)
- [방문 기반 통계](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/analytics/services.py)
- [세션 인증 검사](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/common/http.py)
- [WebSocket 이벤트 계약](https://github.com/y3rtcn/koss-room-backend/blob/b15935c7b0b6bf65fde0856272e6db8c2c37cc04/docs/api.md)
