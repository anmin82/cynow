"""
상태 이력(tr_cylinder_status_histories) 조회용 Repository
- 이동코드 분류: 제공된 코드 집합을 기본값으로 두되, 실제 테이블에 존재하는 코드만 사용
- 중량: tr_move_report_details 의 FILLING_WEIGHT, CYLINDER_WEIGHT로 gross/tare/net 계산
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from django.db import connection

from core.utils.status_mapper import map_condition_code_to_status
from core.utils.view_helper import parse_valve_spec, extract_valve_type


class HistoryRepository:
    """
    tr_cylinder_status_histories + tr_move_report_details + cy_cylinder_current 조합 조회
    """

    # 기본 이동코드 분류 (실제 존재하는 코드와 교집합만 사용)
    DEFAULT_MOVE_CODE_SETS = {
        "ship": ["60"],  # 출하만 카운트
        "inbound": ["10"],  # 입하만 카운트
        "charge": ["22"],  # 충전 실적 등록만 카운트
        "maintenance_out": ["11", "24", "26", "27", "28", "29"],  # 정비 출고
        "maintenance_in": ["12", "23", "25"],  # 정비 입고
    }

    _cached_available_move_codes: Optional[set] = None

    @classmethod
    def _ensure_datetime(cls, value: date) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.combine(value, datetime.min.time())

    @classmethod
    def get_available_move_codes(cls) -> set:
        """tr_cylinder_status_histories에 실제 존재하는 MOVE_CODE 집합"""
        if cls._cached_available_move_codes is not None:
            return cls._cached_available_move_codes

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT TRIM(h."MOVE_CODE")
                FROM "fcms_cdc"."tr_cylinder_status_histories" h
                WHERE h."MOVE_CODE" IS NOT NULL
                """
            )
            codes = {row[0] for row in cursor.fetchall() if row and row[0]}

        cls._cached_available_move_codes = codes
        return codes

    @classmethod
    def get_move_code_sets(cls) -> Dict[str, List[str]]:
        """기본 분류와 실제 존재 코드의 교집합을 반환"""
        available = cls.get_available_move_codes()
        result: Dict[str, List[str]] = {}
        for key, codes in cls.DEFAULT_MOVE_CODE_SETS.items():
            result[key] = [c for c in codes if c in available]
        return result

    @classmethod
    def get_cylinder_type_options(cls) -> List[Dict]:
        """
        이력과 연결 가능한 용기종류 옵션 (dashboard 기준 키)
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    c.cylinder_type_key,
                    MIN(c.dashboard_gas_name) AS gas_name,
                    MIN(c.dashboard_capacity) AS capacity,
                    MIN(NULLIF(RTRIM(c.dashboard_valve_group_name), '')) AS valve_group_name,
                    MIN(NULLIF(RTRIM(c.dashboard_valve_spec_name), '')) AS valve_spec_name,
                    MIN(COALESCE(NULLIF(RTRIM(c.dashboard_valve_group_name), ''), NULLIF(RTRIM(c.dashboard_valve_spec_name), ''))) AS valve_display,
                    MIN(c.dashboard_cylinder_spec_name) AS cylinder_display,
                    MIN(c.dashboard_enduser) AS enduser
                FROM cy_cylinder_current c
                WHERE c.cylinder_type_key IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM cy_hidden_cylinder_type h
                      WHERE h.cylinder_type_key = c.cylinder_type_key
                  )
                GROUP BY c.cylinder_type_key
                ORDER BY MIN(c.dashboard_gas_name), MIN(c.dashboard_capacity) NULLS LAST, MIN(COALESCE(NULLIF(RTRIM(c.dashboard_valve_group_name), ''), NULLIF(RTRIM(c.dashboard_valve_spec_name), ''))), MIN(c.dashboard_enduser)
                """
            )
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        results = [dict(zip(cols, row)) for row in rows]

        # 대시보드 카드처럼 읽기 쉬운 표기(예: COS / CGA330 / 47L)
        for r in results:
            # 밸브 식별 보강: 그룹명이 있으면 "그룹명(밸브코드)" 형태로 표시
            valve_group = (r.get("valve_group_name") or "").strip()
            valve_raw = (r.get("valve_spec_name") or "").strip()
            valve_code = (extract_valve_type(valve_raw) or "").strip()
            if valve_group:
                r["valve_display"] = f"{valve_group} ({valve_code})" if valve_code else valve_group
            else:
                r["valve_display"] = valve_code or (r.get("valve_display") or "")

            gas_name = (r.get("gas_name") or "").strip()
            capacity = (str(r.get("capacity") or "")).strip()
            valve_display = (r.get("valve_display") or "").strip()
            cylinder_display = (r.get("cylinder_display") or "").strip()
            enduser = (r.get("enduser") or "").strip()

            # 누락값이 있으면 사용자가 식별할 수 있게 '미상'을 명시적으로 표시
            missing_core = False
            if not gas_name:
                gas_name = "가스미상"
                missing_core = True
            if not capacity:
                capacity = "용량미상"
                missing_core = True
            if not valve_display:
                valve_display = "밸브미상"
            if not cylinder_display:
                cylinder_display = "용기미상"

            label = f"{gas_name} / {capacity} / {valve_display} / {cylinder_display}"
            if enduser:
                label = f"{label} / {enduser}"
            # 핵심 정보(가스/용량)가 누락된 항목은 키 일부를 함께 보여줘서 선택 실수를 방지
            if missing_core and r.get("cylinder_type_key"):
                label = f"{label}  [key:{str(r['cylinder_type_key'])[:8]}]"
            r["display_label"] = label

        # history 페이지의 "용기종류" 옵션은 대시보드 카드처럼 속성 기준으로 묶어준다.
        # (대시보드에서 여러 cylinder_type_key가 한 카드로 합쳐질 수 있어,
        #  key 기준으로 그대로 보여주면 옵션 수가 불필요하게 늘어난다.)
        grouped: Dict[str, Dict] = {}
        for r in results:
            gas_name = (r.get("gas_name") or "").strip()
            capacity = (str(r.get("capacity") or "")).strip()
            valve_display = (r.get("valve_display") or "").strip()
            cylinder_display = (r.get("cylinder_display") or "").strip()
            enduser = (r.get("enduser") or "").strip()
            group_key = f"{gas_name}|{capacity}|{valve_display}|{cylinder_display}|{enduser}"

            k = (r.get("cylinder_type_key") or "").strip()
            if group_key not in grouped:
                base = dict(r)
                base["cylinder_type_keys"] = [k] if k else []
                grouped[group_key] = base
            else:
                if k:
                    grouped[group_key].setdefault("cylinder_type_keys", []).append(k)
                # 대표 키는 deterministic 하게 가장 작은 값을 유지 (선택/URL 안정화)
                cur = (grouped[group_key].get("cylinder_type_key") or "").strip()
                if k and (not cur or k < cur):
                    grouped[group_key]["cylinder_type_key"] = k

        grouped_list: List[Dict] = []
        for g in grouped.values():
            keys = sorted({x for x in (g.get("cylinder_type_keys") or []) if x})
            g["cylinder_type_keys"] = keys
            # display_label은 기존 라벨 유지 (속성 동일 그룹이므로 동일한 값)
            grouped_list.append(g)

        grouped_list.sort(
            key=lambda x: (
                (x.get("gas_name") or ""),
                str(x.get("capacity") or ""),
                (x.get("valve_display") or ""),
                (x.get("enduser") or ""),
            )
        )
        return grouped_list

    @classmethod
    def get_move_code_options(cls, only_codes: Optional[List[str]] = None) -> Dict[str, str]:
        """
        MOVE_CODE -> 이동명 매핑을 ma_parameters에서 가져온다.
        - ma_parameters 스키마: TYPE, KEY1..3, VALUE1..4, SORT
        - TYPE 값은 환경마다 다를 수 있어, KEY1(=MOVE_CODE) 기준으로 후보를 찾고 가장 우선 후보를 선택한다.
        """
        codes = only_codes or sorted(cls.get_available_move_codes())
        if not codes:
            return {}

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p."TYPE" AS type,
                    TRIM(p."KEY1") AS code,
                    p."VALUE2" AS value2,
                    p."VALUE1" AS value1,
                    p."VALUE3" AS value3,
                    p."SORT" AS sort
                FROM "fcms_cdc"."ma_parameters" p
                WHERE TRIM(p."KEY1") = ANY(%s)
                  AND (p."KEY2" IS NULL OR TRIM(p."KEY2") = '')
                  AND (p."KEY3" IS NULL OR TRIM(p."KEY3") = '')
                ORDER BY p."TYPE" ASC, p."SORT" ASC NULLS LAST
                """,
                [codes],
            )
            rows = cursor.fetchall()

        result: Dict[str, str] = {c: c for c in codes}  # fallback = code
        for _type, code, v2, v1, v3, _sort in rows:
            if not code:
                continue
            if result.get(code) != code:
                continue  # already chosen
            name = (v2 or v1 or v3 or "").strip() if isinstance((v2 or v1 or v3), str) else (v2 or v1 or v3)
            if name:
                result[code] = name
        return result

    @classmethod
    def _build_filters(
        cls,
        filters: Optional[Dict],
        params: List,
    ) -> str:
        conditions = []
        if not filters:
            return ""

        if filters.get("cylinder_no"):
            conditions.append('RTRIM(h."CYLINDER_NO") = RTRIM(%s)')
            params.append(filters["cylinder_no"])
        if filters.get("move_code"):
            conditions.append('h."MOVE_CODE" = %s')
            params.append(filters["move_code"])
        if filters.get("condition_code"):
            conditions.append('h."CONDITION_CODE" = %s')
            params.append(filters["condition_code"])
        if filters.get("program_id"):
            conditions.append('h."PROGRAM_ID" = %s')
            params.append(filters["program_id"])
        if filters.get("location_code"):
            conditions.append('h."LOCATION_CODE" = %s')
            params.append(filters["location_code"])
        if filters.get("position_user_name"):
            conditions.append('h."POSITION_USER_NAME" ILIKE %s')
            params.append(f"%{filters['position_user_name']}%")
        if filters.get("move_report_no"):
            conditions.append('RTRIM(h."MOVE_REPORT_NO") = RTRIM(%s)')
            params.append(filters["move_report_no"])
        if filters.get("gas_name"):
            conditions.append("c.dashboard_gas_name = %s")
            params.append(filters["gas_name"])
        # 대시보드 카드 기준으로 여러 키가 묶일 수 있으므로, IN 필터를 지원한다.
        if filters.get("cylinder_type_keys"):
            keys = [k for k in (filters.get("cylinder_type_keys") or []) if k]
            if keys:
                if connection.vendor == "postgresql":
                    conditions.append("c.cylinder_type_key = ANY(%s)")
                    params.append(keys)
                else:
                    placeholders = ", ".join(["%s"] * len(keys))
                    conditions.append(f"c.cylinder_type_key IN ({placeholders})")
                    params.extend(keys)
        elif filters.get("cylinder_type_key"):
            conditions.append("c.cylinder_type_key = %s")
            params.append(filters["cylinder_type_key"])

        if conditions:
            return " AND " + " AND ".join(conditions)
        return ""

    @classmethod
    def fetch_history(
        cls,
        start_date,
        end_date,
        filters: Optional[Dict] = None,
        limit: int = 300,
        offset: int = 0,
    ) -> List[Dict]:
        """
        상태 이력 리스트 조회 (기간 + 필터)
        """
        params: List = [
            cls._ensure_datetime(start_date),
            cls._ensure_datetime(end_date) + timedelta(days=1),  # 끝일 포함
        ]

        where = cls._build_filters(filters, params)

        params.extend([limit, offset])

        query = f"""
            SELECT
                h."CYLINDER_NO" AS cylinder_no,
                h."MOVE_DATE" AS move_date,
                h."MOVE_CODE" AS move_code,
                h."CONDITION_CODE" AS condition_code,
                h."LOCATION_CODE" AS location_code,
                h."POSITION_USER_NAME" AS position_user_name,
                h."LOCATION_USER_NAME" AS location_user_name,
                h."MOVE_REPORT_NO" AS move_report_no,
                h."MOVE_REPORT_BRANCH" AS move_report_branch,
                h."MOVE_STAFF_NAME" AS move_staff_name,
                h."REMARKS" AS remarks,
                h."MANUFACTURE_LOT_HEADER" AS manufacture_lot_header,
                h."MANUFACTURE_LOT_NO" AS manufacture_lot_no,
                h."MANUFACTURE_LOT_BRANCH" AS manufacture_lot_branch,
                h."FILLING_LOT_HEADER" AS filling_lot_header,
                h."FILLING_LOT_NO" AS filling_lot_no,
                h."FILLING_LOT_BRANCH" AS filling_lot_branch,
                h."FILLING_WEIGHT" AS filling_weight_hist,
                h."PROGRAM_ID" AS program_id,
                h."ADD_DATETIME" AS created_at,
                c.cylinder_type_key,
                c.dashboard_gas_name AS gas_name,
                c.dashboard_capacity AS capacity,
                COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name) AS valve_spec,
                c.dashboard_cylinder_spec_name AS cylinder_spec,
                c.dashboard_enduser AS enduser,
                c.dashboard_location AS dashboard_location,
                d."CYLINDER_WEIGHT" AS cylinder_weight,
                d."FILLING_WEIGHT" AS filling_weight_detail
            FROM "fcms_cdc"."tr_cylinder_status_histories" h
            LEFT JOIN cy_cylinder_current c
                ON RTRIM(h."CYLINDER_NO") = RTRIM(c.cylinder_no)
            LEFT JOIN "fcms_cdc"."tr_move_report_details" d
                ON RTRIM(h."CYLINDER_NO") = RTRIM(d."CYLINDER_NO")
               AND h."MOVE_REPORT_NO" IS NOT NULL
               AND RTRIM(h."MOVE_REPORT_NO") = RTRIM(d."MOVE_REPORT_NO")
            WHERE h."MOVE_DATE" >= %s
              AND h."MOVE_DATE" < %s
              {where}
            ORDER BY h."MOVE_DATE" DESC, h."CYLINDER_NO"
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        results: List[Dict] = []
        for row in rows:
            data = dict(zip(columns, row))
            # LOT 문자열
            def _compose_lot(header, no, branch):
                if not (header or no or branch):
                    return None
                return f"{header or ''}{no or ''}{('-' + branch) if branch else ''}"

            manufacture_lot = _compose_lot(
                data.pop("manufacture_lot_header", None),
                data.pop("manufacture_lot_no", None),
                data.pop("manufacture_lot_branch", None),
            )
            filling_lot = _compose_lot(
                data.pop("filling_lot_header", None),
                data.pop("filling_lot_no", None),
                data.pop("filling_lot_branch", None),
            )

            # 중량 계산
            filling_weight = data.pop("filling_weight_detail", None)
            if filling_weight is None:
                filling_weight = data.pop("filling_weight_hist", None)
            cylinder_weight = data.pop("cylinder_weight", None)

            gross_weight = None
            net_weight = filling_weight
            tare_weight = cylinder_weight
            try:
                gross_weight = (filling_weight or 0) + (cylinder_weight or 0)
            except Exception:
                gross_weight = None

            data.update(
                {
                    "manufacture_lot": manufacture_lot,
                    "filling_lot": filling_lot,
                    "net_weight": net_weight,
                    "tare_weight": tare_weight,
                    "gross_weight": gross_weight,
                    "standard_status": map_condition_code_to_status(
                        data.get("condition_code")
                    ),
                }
            )
            results.append(data)

        return results

    @classmethod
    def get_period_summary(
        cls,
        period: str,
        start_date,
        end_date,
        code_sets: Dict[str, List[str]],
        cylinder_type_key: Optional[str] = None,
    ) -> List[Dict]:
        """
        기간별(week/month) 이동유형 집계
        """
        params = [
            period,
            code_sets.get("ship") or ["__none__"],
            code_sets.get("inbound") or ["__none__"],
            code_sets.get("charge") or ["__none__"],
            code_sets.get("maintenance_out") or ["__none__"],
            code_sets.get("maintenance_in") or ["__none__"],
            cls._ensure_datetime(start_date),
            cls._ensure_datetime(end_date) + timedelta(days=1),
        ]
        type_where = ""
        if cylinder_type_key:
            type_where = " AND c.cylinder_type_key = %s"
            params.append(cylinder_type_key)

        query = f"""
            SELECT 
                date_trunc(%s, h."MOVE_DATE") AS bucket,
                c.cylinder_type_key,
                COUNT(DISTINCT (h."CYLINDER_NO", h."HISTORY_SEQ")) FILTER (WHERE h."MOVE_CODE" = ANY(%s)) AS ship_cnt,
                COUNT(DISTINCT (h."CYLINDER_NO", h."HISTORY_SEQ")) FILTER (WHERE h."MOVE_CODE" = ANY(%s)) AS inbound_cnt,
                COUNT(DISTINCT (h."CYLINDER_NO", h."HISTORY_SEQ")) FILTER (WHERE h."MOVE_CODE" = ANY(%s)) AS charge_cnt,
                COUNT(DISTINCT (h."CYLINDER_NO", h."HISTORY_SEQ")) FILTER (WHERE h."MOVE_CODE" = ANY(%s)) AS maint_out_cnt,
                COUNT(DISTINCT (h."CYLINDER_NO", h."HISTORY_SEQ")) FILTER (WHERE h."MOVE_CODE" = ANY(%s)) AS maint_in_cnt
            FROM "fcms_cdc"."tr_cylinder_status_histories" h
            LEFT JOIN cy_cylinder_current c
                ON RTRIM(h."CYLINDER_NO") = RTRIM(c.cylinder_no)
            WHERE h."MOVE_DATE" >= %s
              AND h."MOVE_DATE" < %s
              {type_where}
            GROUP BY bucket, c.cylinder_type_key
            ORDER BY bucket DESC, c.cylinder_type_key
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]


    @classmethod
    def get_period_end_occupancy_summary(
        cls,
        *,
        period: str,
        cylinder_type_key: str,
        start_date: date,
        end_date: date,
        snapshot_type: str = "DAILY",
    ) -> List[Dict]:
        """
        HistInventorySnapshot에서 period(week/month)별 '기간 마지막 스냅샷' 기준 점유(총량) 집계.
        - 가용: 보관:미회수, 보관:회수
        - 공정중: 충전중, 충전완료, 분석완료
        - 제품: 제품
        - 출하: 출하 (환경에 따라 출하중이 있으면 포함)
        - 비가용: 이상, 정비대상, 폐기
        """
        if not cylinder_type_key:
            return []

        if period not in ("week", "month"):
            raise ValueError("period must be 'week' or 'month'")

        start_dt = cls._ensure_datetime(start_date)
        end_dt_exclusive = cls._ensure_datetime(end_date) + timedelta(days=1)

        available_statuses = ["보관:미회수", "보관:회수"]
        process_statuses = ["충전중", "충전완료", "분석완료"]
        product_statuses = ["제품"]
        ship_statuses = ["출하", "출하중"]
        unavailable_statuses = ["이상", "정비대상", "폐기"]

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH last_snap AS (
                    SELECT
                        date_trunc(%s, snapshot_datetime) AS bucket,
                        MAX(snapshot_datetime) AS last_dt
                    FROM hist_inventory_snapshot
                    WHERE cylinder_type_key = %s
                      AND snapshot_datetime >= %s
                      AND snapshot_datetime < %s
                      AND snapshot_type = %s
                    GROUP BY 1
                )
                SELECT
                    l.bucket AS bucket,
                    COALESCE(SUM(s.qty) FILTER (WHERE s.status = ANY(%s)), 0) AS available_qty,
                    COALESCE(SUM(s.qty) FILTER (WHERE s.status = ANY(%s)), 0) AS process_qty,
                    COALESCE(SUM(s.qty) FILTER (WHERE s.status = ANY(%s)), 0) AS product_qty,
                    COALESCE(SUM(s.qty) FILTER (WHERE s.status = ANY(%s)), 0) AS ship_qty,
                    COALESCE(SUM(s.qty) FILTER (WHERE s.status = ANY(%s)), 0) AS unavailable_qty,
                    COALESCE(SUM(s.qty), 0) AS total_qty
                FROM last_snap l
                LEFT JOIN hist_inventory_snapshot s
                    ON s.snapshot_datetime = l.last_dt
                   AND s.cylinder_type_key = %s
                   AND s.snapshot_type = %s
                GROUP BY l.bucket
                ORDER BY l.bucket ASC
                """,
                [
                    period,
                    cylinder_type_key,
                    start_dt,
                    end_dt_exclusive,
                    snapshot_type,
                    available_statuses,
                    process_statuses,
                    product_statuses,
                    ship_statuses,
                    unavailable_statuses,
                    cylinder_type_key,
                    snapshot_type,
                ],
            )
            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()

        return [dict(zip(cols, r)) for r in rows]


    @classmethod
    def get_clf3_ship_counts(
        cls,
        ship_codes: List[str],
    ) -> Dict[str, Dict]:
        """
        CLF3 용기별 출하 누적 횟수 (전체 누적)
        """
        if not ship_codes:
            return {}

        params = [ship_codes]
        query = """
            SELECT 
                h."CYLINDER_NO" AS cylinder_no,
                COUNT(*) AS ship_count
            FROM "fcms_cdc"."tr_cylinder_status_histories" h
            LEFT JOIN cy_cylinder_current c
                ON RTRIM(h."CYLINDER_NO") = RTRIM(c.cylinder_no)
            WHERE h."MOVE_CODE" = ANY(%s)
              AND c.dashboard_gas_name ILIKE 'CLF3%%'
            GROUP BY h."CYLINDER_NO"
            ORDER BY ship_count DESC
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        result = {}
        for cylinder_no, ship_count in rows:
            result[cylinder_no] = {
                "ship_count": ship_count,
                "over_limit": ship_count > 5,
            }
        return result

    @classmethod
    def get_type_counts(
        cls,
        move_codes: List[str],
        start_date,
        end_date,
    ) -> List[Dict]:
        """
        이동코드 집합으로 용기종류별 건수 집계
        """
        if not move_codes:
            return []
        params = [
            move_codes,
            cls._ensure_datetime(start_date),
            cls._ensure_datetime(end_date) + timedelta(days=1),
        ]
        query = """
            SELECT 
                c.cylinder_type_key,
                MIN(c.dashboard_gas_name) AS gas_name,
                MIN(c.dashboard_capacity) AS capacity,
                MIN(COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name)) AS valve_spec,
                MIN(c.dashboard_enduser) AS enduser,
                COUNT(DISTINCT (h."CYLINDER_NO", h."HISTORY_SEQ")) AS cnt
            FROM "fcms_cdc"."tr_cylinder_status_histories" h
            LEFT JOIN cy_cylinder_current c
                ON RTRIM(h."CYLINDER_NO") = RTRIM(c.cylinder_no)
            WHERE h."MOVE_CODE" = ANY(%s)
              AND h."MOVE_DATE" >= %s
              AND h."MOVE_DATE" < %s
            GROUP BY c.cylinder_type_key
            ORDER BY MIN(c.dashboard_gas_name), MIN(c.dashboard_capacity) NULLS LAST
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(cols, row)) for row in rows]


