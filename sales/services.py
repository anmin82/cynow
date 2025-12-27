from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import connection

from products.models import ProductCode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShipmentRow:
    supplier_user_code: str
    supplier_user_name: str
    move_report_no: str
    customer_order_no: str
    trade_condition_code: str
    item_name: str
    packing_name: str
    shipping_date: Optional[date]
    shipped_count: int


class SalesService:
    """
    판매(MVP) 집계 서비스

    - 거래명세서/매출집계는 "출하(MOVE_CODE=60)" 기준으로 집계
    - 출하지시서는 이동서번호(=ARRIVAL_SHIPPING_NO / MOVE_REPORT_NO) 기준 조회
    """

    @staticmethod
    def list_shipments(
        start_date: date,
        end_date: date,
        supplier_user_code: str = "",
        trade_condition_code: str = "",
    ) -> List[ShipmentRow]:
        """
        기간 내 출하 목록을 조회합니다.
        - TR_ORDERS(제품코드) + TR_MOVE_REPORTS(출하일) + 출하실적(이력 MOVE_CODE=60) 조합
        """
        query = """
            SELECT
                TRIM(o."SUPPLIER_USER_CODE") AS supplier_user_code,
                TRIM(o."SUPPLIER_USER_NAME") AS supplier_user_name,
                TRIM(o."ARRIVAL_SHIPPING_NO") AS move_report_no,
                TRIM(o."CUSTOMER_ORDER_NO") AS customer_order_no,
                TRIM(o."TRADE_CONDITION_CODE") AS trade_condition_code,
                TRIM(o."ITEM_NAME") AS item_name,
                TRIM(o."PACKING_NAME") AS packing_name,
                m."SHIPPING_DATE" AS shipping_date,
                COALESCE(s.shipped_count, 0) AS shipped_count
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_move_reports m
                ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(m."MOVE_REPORT_NO")
            LEFT JOIN (
                SELECT "MOVE_REPORT_NO", COUNT("CYLINDER_NO") AS shipped_count
                FROM fcms_cdc.tr_cylinder_status_histories
                WHERE "MOVE_CODE" = '60'
                GROUP BY "MOVE_REPORT_NO"
            ) s ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(s."MOVE_REPORT_NO")
            WHERE m."SHIPPING_DATE" IS NOT NULL
              AND DATE(m."SHIPPING_DATE") BETWEEN %s AND %s
              AND (m."PROGRESS_CODE" IS NULL OR m."PROGRESS_CODE" != '51')
        """
        params: List[Any] = [start_date, end_date]

        if supplier_user_code:
            query += ' AND TRIM(o."SUPPLIER_USER_CODE") = %s'
            params.append(supplier_user_code.strip())
        if trade_condition_code:
            query += ' AND TRIM(o."TRADE_CONDITION_CODE") = %s'
            params.append(trade_condition_code.strip())

        query += " ORDER BY m.\"SHIPPING_DATE\" DESC, move_report_no"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        results: List[ShipmentRow] = []
        for r in rows:
            results.append(
                ShipmentRow(
                    supplier_user_code=r[0] or "",
                    supplier_user_name=r[1] or "",
                    move_report_no=r[2] or "",
                    customer_order_no=r[3] or "",
                    trade_condition_code=r[4] or "",
                    item_name=r[5] or "",
                    packing_name=r[6] or "",
                    shipping_date=r[7],
                    shipped_count=int(r[8] or 0),
                )
            )
        return results

    @staticmethod
    def get_product_price_per_kg_at(product: ProductCode, at_date: date) -> Optional[Decimal]:
        """
        특정 날짜 기준 단가(kg당) 조회.
        - ProductPriceHistory.effective_date <= at_date 중 가장 최신
        """
        price = (
            product.price_history.filter(effective_date__lte=at_date)
            .order_by("-effective_date")
            .first()
        )
        return price.price_per_kg if price else None

    @staticmethod
    def build_statement_summary(
        shipments: List[ShipmentRow],
        at_date_for_price: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        거래명세서(요약)용 집계:
        - 제품코드별 출하 수량 합계
        - (옵션) 단가/금액 계산
        """
        by_product: Dict[str, Dict[str, Any]] = {}
        trade_codes = sorted({s.trade_condition_code for s in shipments if s.trade_condition_code})
        pc_map = {
            pc.trade_condition_no: pc
            for pc in ProductCode.objects.filter(trade_condition_no__in=trade_codes)
        }

        for s in shipments:
            code = s.trade_condition_code or "UNKNOWN"
            if code not in by_product:
                pc = pc_map.get(code)
                by_product[code] = {
                    "trade_condition_code": code,
                    "product": pc,
                    "product_name": (pc.display_name or pc.gas_name) if pc else (s.item_name or code),
                    "gas_name": (pc.gas_name if pc else ""),
                    "filling_weight": pc.filling_weight if pc else None,
                    "qty": 0,
                    "unit_price_per_kg": None,
                    "amount": None,
                }
            by_product[code]["qty"] += int(s.shipped_count or 0)

        # 단가/금액 계산 (MVP: 기준일 1개로 계산; 실무는 출하일별 분리 가능)
        if at_date_for_price:
            total_amount = Decimal("0")
            for code, row in by_product.items():
                pc: Optional[ProductCode] = row["product"]
                if not pc:
                    continue
                price = SalesService.get_product_price_per_kg_at(pc, at_date_for_price)
                row["unit_price_per_kg"] = price
                if price is not None and row["filling_weight"] is not None:
                    amount = price * Decimal(row["filling_weight"]) * Decimal(row["qty"])
                    row["amount"] = amount
                    total_amount += amount
            return {"items": list(by_product.values()), "total_amount": total_amount}

        return {"items": list(by_product.values()), "total_amount": None}



