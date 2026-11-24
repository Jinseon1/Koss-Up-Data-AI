import argparse
import json
import os
from pathlib import Path
from .core import analyze, Config
from .client import Client


def main():
    p = argparse.ArgumentParser(description='KOSS data analysis; GET-only backend access')
    p.add_argument('--date', required=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument('--input', help='Normalized collector snapshot JSON')
    src.add_argument('--base-url', help='Backend origin; session from KOSS_SESSION_COOKIE env')
    p.add_argument('--space-ids', required=True, help='Comma-separated nonoverlapping scope')
    p.add_argument('--capacity', type=int, help='Confirmed capacity for the selected scope')
    p.add_argument('--room-scope', action='store_true', help='Selected IDs represent the entire room')
    p.add_argument('--history-start', help='Confirmed start of complete retained schedule data')
    p.add_argument('--slot-minutes', type=int, default=60)
    p.add_argument('--use-chat', action='store_true', help='Opt in to unverified strict explicit reports')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    try:
        ids = [int(v) for v in args.space_ids.split(',')]
        if args.input:
            snapshot = json.loads(Path(args.input).read_text(encoding='utf-8'))
        else:
            snapshot = Client(args.base_url, os.environ.get('KOSS_SESSION_COOKIE', '')).collect(args.date, space_ids=ids)
        result = analyze(snapshot, args.date, capacity=args.capacity, space_ids=ids,
                         room_scope=args.room_scope, history_start=args.history_start,
                         config=Config(slot_minutes=args.slot_minutes, use_chat=args.use_chat))
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        p.exit(1, '분석 실패: 입력 스키마, API 접근 권한, 날짜 및 설정을 확인하세요. 세부 인증 정보는 출력하지 않습니다.\n')


if __name__ == '__main__':
    main()
