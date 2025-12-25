-- 【FPK品の購入値段の算出】_2025 rev 02.pdf 기반 가격 입력
-- 仕入/KG = FPK가 KDKK에 판매하는 kg당 단가

-- 기존 데이터 삭제 (깨끗하게 재입력)
DELETE FROM product_price_history WHERE note LIKE 'FPK품 구매단가%' OR note LIKE 'TB_자재코드%';

-- ========================================
-- 2025년 1월 단가 (25年～ 仕入/KG)
-- ========================================

-- KF001: COS 40kg USD 180.00/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 180.00, 'USD', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF001'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 180.00, currency = 'USD', note = 'FPK품 구매단가 2025';

-- KF007: COS 25kg KRW 390,850/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 390850, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF007'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 390850, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF013: COS 25kg KRW 338,530/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 338530, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF013'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 338530, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF014: COS 25kg KRW 338,530/kg (SCS)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 338530, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF014'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 338530, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF015: COS_SP 25kg KRW 342,030/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 342030, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF015'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 342030, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF016: COS 10kg KRW 452,330/kg (SEC파주장)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 452330, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF016'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 452330, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF020: COS 40kg KRW 321,110/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 321110, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF020'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 321110, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF025: COS_40 SP 40kg KRW 323,310/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 323310, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF025'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 323310, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF018: ClF3 40kg KRW 313,380/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 313380, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF018'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 313380, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF024: ClF3 20kg KRW 336,820/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 336820, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF024'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 336820, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF019: ClF3 20kg KRW 456,190/kg (기타)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 456190, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF019'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 456190, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF021: ClF3 10kg KRW 451,870/kg (KEY)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 451870, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF021'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 451870, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF005: CF4 Y 300kg JPY 2,200/kg (SDC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2200, 'JPY', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF005'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2200, currency = 'JPY', note = 'FPK품 구매단가 2025';

-- KF026: CF4 Y/中国産 300kg JPY 2,200/kg (SDC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2200, 'JPY', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF026'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2200, currency = 'JPY', note = 'FPK품 구매단가 2025';

-- KF009: CF4 32kg JPY 2,300/kg (KEY)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2300, 'JPY', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF009'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2300, currency = 'JPY', note = 'FPK품 구매단가 2025';

-- KF010: CF4 Y 300kg USD 21.95/kg (LGD)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 21.95, 'USD', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF010'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 21.95, currency = 'USD', note = 'FPK품 구매단가 2025';

-- ========================================
-- 2026년 1월 단가 (26年1月以後～ 仕入/KG)
-- ========================================

-- KF001: COS 40kg USD 180.00/kg (동일)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 180.00, 'USD', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF001'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 180.00, currency = 'USD', note = 'FPK품 구매단가 2026';

-- KF007: COS 25kg KRW 379,100/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 379100, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF007'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 379100, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF013: COS 25kg KRW 328,350/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 328350, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF013'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 328350, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF014: COS 25kg KRW 328,350/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 328350, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF014'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 328350, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF015: COS_SP 25kg KRW 331,750/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 331750, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF015'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 331750, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF016: COS 10kg KRW 438,310/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 438310, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF016'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 438310, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF020: COS 40kg KRW 311,460/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 311460, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF020'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 311460, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF025: COS_40 SP 40kg KRW 313,600/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 313600, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF025'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 313600, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF018: ClF3 40kg KRW 300,930/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 300930, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF018'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 300930, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF024: ClF3 20kg KRW 323,410/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 323410, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF024'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 323410, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF019: ClF3 20kg KRW 438,010/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 438010, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF019'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 438010, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF021: ClF3 10kg KRW 429,100/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 429100, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF021'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 429100, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF005: CF4 Y 300kg JPY 2,200/kg (동일)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 2200, 'JPY', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF005'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2200, currency = 'JPY', note = 'FPK품 구매단가 2026';

-- KF026: CF4 Y/中国産 300kg JPY 2,200/kg (동일)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 2200, 'JPY', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF026'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2200, currency = 'JPY', note = 'FPK품 구매단가 2026';

-- KF009: CF4 32kg JPY 2,300/kg (동일)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 2300, 'JPY', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF009'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2300, currency = 'JPY', note = 'FPK품 구매단가 2026';

-- KF010: CF4 Y 300kg USD 19.29/kg (↓ 인하)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 19.29, 'USD', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF010'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 19.29, currency = 'USD', note = 'FPK품 구매단가 2026';

-- ========================================
-- 결과 확인
-- ========================================
SELECT 
    pc.trade_condition_no as "제품코드",
    pc.gas_name as "가스",
    pc.filling_weight as "충전량",
    ph.effective_date as "적용일",
    ph.price_per_kg as "kg단가",
    ph.currency as "통화"
FROM product_price_history ph
JOIN product_code pc ON ph.product_code_id = pc.selection_pattern_code
ORDER BY pc.trade_condition_no, ph.effective_date;
