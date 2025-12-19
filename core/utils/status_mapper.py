"""상태 코드 → 표준 상태 매핑 유틸리티"""

# FCMS 상태 코드 → 표준 상태 매핑
CONDITION_CODE_TO_STATUS = {
    '100': '보관:미회수',  # 保管：未回収
    '102': '보관:회수',  # 保管：回収済
    '210': '충전중',  # 充填中
    '220': '충전완료',  # 充填完了
    '420': '분석완료',  # 検査終了
    '500': '제품',  # 倉入
    '600': '출하',  # 出荷
    '190': '이상',  # 異常
    '950': '정비대상',  # 使用不可：未回収 (정비 후 공용기로 사용 가능)
    '952': '정비대상',  # 使用不可：回収済 (정비 후 공용기로 사용 가능)
    '990': '폐기',  # 실제 폐기된 용기 (삭제하지 않고 폐기 상태로 기록)
}

# 표준 상태 목록
STANDARD_STATUSES = ['보관:미회수', '보관:회수', '충전중', '충전완료', '분석완료', '제품', '출하', '이상', '정비대상', '폐기']


def map_condition_code_to_status(condition_code):
    """
    FCMS 상태 코드를 표준 상태로 변환
    
    Args:
        condition_code: FCMS CONDITION_CODE (str)
    
    Returns:
        str: 표준 상태 (보관:미회수, 보관:회수, 충전중, 충전완료, 분석완료, 제품, 출하, 이상, 정비대상, 폐기)
    """
    if condition_code is None:
        return None
    
    code_str = str(condition_code).strip()
    return CONDITION_CODE_TO_STATUS.get(code_str, None)


def is_valid_status(status):
    """표준 상태인지 확인"""
    return status in STANDARD_STATUSES

