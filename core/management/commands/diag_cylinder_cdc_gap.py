"""특정 용기번호의 CDC 최신 이벤트와 스냅샷 상태를 비교하는 진단 커맨드

문제 상황:
- 원본(Oracle/CHAR) trailing spaces 또는 CDC/싱크 지연으로 인해
  cy_cylinder_current(스냅샷)과 fcms_cdc(소스) 간 불일치가 발생할 수 있다.

사용:
  python manage.py diag_cylinder_cdc_gap --cylinder ENKE5843
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "용기번호 기준으로 fcms_cdc 최신 상태(tr_latest_cylinder_statuses)와 cy_cylinder_current 스냅샷을 비교"

    def add_arguments(self, parser):
        parser.add_argument("--cylinder", required=True, help="용기번호 (공백 없이 입력 권장)")

    def handle(self, *args, **options):
        cylinder = (options["cylinder"] or "").strip()
        if not cylinder:
            self.stdout.write(self.style.ERROR("용기번호가 비어있습니다."))
            return

        with connection.cursor() as cursor:
            # 1) fcms_cdc 최신 상태 (trim 기준)
            cursor.execute(
                """
                SELECT
                    RTRIM(ls."CYLINDER_NO") as cylinder_no,
                    ls."MOVE_DATE",
                    ls."CONDITION_CODE",
                    ls."POSITION_USER_NAME",
                    ls."MOVE_REPORT_NO"
                FROM "fcms_cdc"."tr_latest_cylinder_statuses" ls
                WHERE RTRIM(ls."CYLINDER_NO") = %s
                """,
                [cylinder],
            )
            src = cursor.fetchone()

            # 2) 스냅샷 상태
            cursor.execute(
                """
                SELECT
                    RTRIM(cylinder_no) as cylinder_no,
                    last_event_at,
                    condition_code,
                    dashboard_location,
                    move_date,
                    source_updated_at,
                    snapshot_updated_at
                FROM cy_cylinder_current
                WHERE RTRIM(cylinder_no) = %s
                ORDER BY snapshot_updated_at DESC
                LIMIT 1
                """,
                [cylinder],
            )
            snap = cursor.fetchone()

        self.stdout.write("\n=== CDC 최신 상태 (fcms_cdc.tr_latest_cylinder_statuses) ===")
        if src:
            self.stdout.write(
                f"- cylinder_no={src[0]} | move_date={src[1]} | condition_code={src[2]} | location={src[3]} | move_report_no={src[4]}"
            )
        else:
            self.stdout.write(self.style.WARNING("- (없음) tr_latest_cylinder_statuses에서 해당 용기번호를 찾지 못했습니다."))

        self.stdout.write("\n=== 스냅샷 (cy_cylinder_current) ===")
        if snap:
            self.stdout.write(
                f"- cylinder_no={snap[0]} | last_event_at={snap[1]} | condition_code={snap[2]} | location={snap[3]} | move_date={snap[4]} | source_updated_at={snap[5]} | snapshot_updated_at={snap[6]}"
            )
        else:
            self.stdout.write(self.style.WARNING("- (없음) cy_cylinder_current에서 해당 용기번호를 찾지 못했습니다."))

        self.stdout.write("\n=== 판정 ===")
        if not src and not snap:
            self.stdout.write(self.style.WARNING("소스/스냅샷 모두 없음: 용기번호가 틀렸거나 CDC 싱크가 멈춘 상태일 수 있습니다."))
            return

        if src and snap:
            # move_date 기준 비교
            if snap[1] and src[1] and snap[1] >= src[1]:
                self.stdout.write(self.style.SUCCESS("스냅샷이 최신(또는 동일)입니다."))
            elif snap[1] and src[1] and snap[1] < src[1]:
                self.stdout.write(self.style.WARNING("스냅샷이 뒤처져 있습니다. sync_cylinder_snapshot/sync_cylinder_current 실행 및 CDC 지연 확인이 필요합니다."))
            else:
                self.stdout.write(self.style.WARNING("move_date가 한쪽에 NULL입니다. 조인/소스 데이터 품질 또는 VIEW 정의를 확인하세요."))
        else:
            self.stdout.write(self.style.WARNING("한쪽만 존재: CDC 싱크 또는 스냅샷 적재 경로를 확인하세요."))




