# KOSS 동방 한산한 시간대 분석 — 데이터 파트

2026-11-24 작성. 기존 백엔드·DB·인증·WebSocket 서버 및 프론트 UI는 변경하지 않았습니다. 별도 Python 3.11+ 패키지이며 런타임 외부 의존성은 없습니다. Windows에서 시간대 데이터가 없으면 `pip install tzdata`가 필요합니다.

## 현재 결과와 제한

- 백엔드 커밋 `b15935c7b0b6bf65fde0856272e6db8c2c37cc04`의 views/services/models/urls 및 API 문서를 직접 확인했습니다.
- GET 수집기, 시간 정규화, 실제 신청자 중복 제거, 통계, 보수적 추천, 채팅 분류, 인원 이벤트 어댑터, JSON 계약 및 테스트를 구현했습니다.
- **운영 서버 응답·로그인 세션·실제 데이터는 확보하지 않았습니다.** 예제는 전부 합성 데이터이며 운영 정확도 검증이나 배포 완료를 의미하지 않습니다.
- 결과는 신청 인원 기반 대리 추정치입니다. 실제 상주 인원으로 검증된 미래 예측 모델이 아닙니다.
- 예약이 없고 다른 근거가 없으면 예상 인원과 혼잡도는 `null`입니다. 빈 방으로 추천하지 않습니다.
- 일치 요일의 과거 완전 보존 기간이 확인되고 4일 이상 표본이 있을 때만 MEDIUM 및 확정 추천을 허용합니다. 현재 입퇴실 기록·채팅만으로는 미래 시간을 추천하지 않습니다.

## 실행

이 폴더로 이동한 뒤 실행합니다. 별도 설치 없이 동작합니다.

```bash
python -m unittest discover -s tests -v
python -m koss_data --date 2026-11-24 --input examples/snapshot.synthetic.json --space-ids 1 --capacity 20 --history-start 2026-10-27 --output result.json
```

명령은 실행 시각 기준으로 분석하므로, 고정 재현 예제는 다음 명령을 사용합니다.

```bash
PYTHONPATH=. python examples/make_demo.py
```

Windows PowerShell에서는 `$env:PYTHONPATH='.'`를 설정하고 `python examples/make_demo.py`를 실행하세요.

실제 수집은 `--input` 대신 `--base-url https://실제백엔드호스트`를 사용합니다. `KOSS_SESSION_COOKIE` 환경 변수에 기존 로그인 흐름에서 얻은 Cookie 헤더 값(예: `sessionid=...`)을 넣으세요. 비밀값을 코드·공유 JSON·Git에 저장하지 마세요. 수집기는 인증을 새로 구현하지 않으며 GET만 사용합니다. 원격 HTTP 및 리다이렉트를 거부합니다.

- `--space-ids`: 해당 분석 범위를 구성하는 실제 공간 ID 목록.
- `--capacity`: 그 범위의 확인된 전체 정원. 생략하면 혼잡도와 추천 여부를 결정하지 않습니다. 공간별 정원을 자동 합산하지 않습니다.
- `--room-scope`: ID 목록이 동방 전체와 정확히 대응할 때만 지정합니다. 입퇴실/전체 인원 채팅을 테이블 하나에 잘못 적용하지 않기 위한 설정입니다.
- `--history-start`: 백엔드 팀이 **누락 없이 과거 일정과 신청자를 보존했다고 확인한 날짜**. 단순 최초 일정 날짜가 아닙니다. 확인 전에는 생략합니다.
- `--slot-minutes`: 기본 60; 1440의 양의 약수만 허용합니다.
- `--use-chat`: 엄격한 명시적 전체 인원 제보의 수치 반영을 선택합니다. 기본 꺼짐. 일반 채팅은 항상 제외합니다.

JSON 파일 모드의 현재 예약은 파일에 담긴 상태입니다. 오래된 파일로 현재 운영 결과를 제공하지 마세요. 실시간 운영에서는 다시 수집한 입력으로 계산해야 합니다.

## 전달 파일

| 파일 | 용도 |
| --- | --- |
| `docs/api-audit.md` | 실제 API 필드·인증·한계·코드 근거 |
| `docs/frontend-contract.md` | 결과 필드 타입·NULL·계산·연동 |
| `docs/backend-requests.md` | 백엔드/팀 확인 및 추가 데이터 요청 |
| `docs/test-results.txt` | 실행한 테스트 결과 |
| `koss_data/client.py` | GET 수집 및 채팅 페이지 처리 |
| `koss_data/core.py` | 정규화·통계·추천 |
| `koss_data/realtime.py` | 기존 클라이언트가 전달한 이벤트 처리 |
| `examples/*.json` | 합성 입력과 24개 구간의 결과 |

HTTP 추천 엔드포인트는 추가하지 않았습니다. 프론트엔드가 Python 함수를 브라우저에서 직접 실행할 수는 없습니다. 개발 중에는 생성 JSON을 사용하고, 운영에서는 별도 데이터 실행 환경이 JSON을 생성·전달할 위치를 팀에서 정해야 합니다. 기존 백엔드에 붙이는 작업은 담당자 합의 후 진행해야 합니다.
