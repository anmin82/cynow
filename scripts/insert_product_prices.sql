-- 【FPK品の購入値段の算出】_2025 rev 02.pdf 기반 가격 입력
-- 仕入/KG (구매가격/kg) 기준

-- 기존 데이터 삭제 (깨끗하게 재입력)
DELETE FROM product_price_history WHERE note LIKE 'FPK품 구매단가%' OR note LIKE 'TB_자재코드%';

-- ========================================
-- 2025년 1월 단가 (25年1月～)
-- ========================================

-- KF001: COS 40kg USD 180.00/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 180.00, 'USD', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF001'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 180.00, currency = 'USD', note = 'FPK품 구매단가 2025';

-- KF007: COS 25kg KRW 390,850 → 379,100/kg (25年1月以後)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 379100, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF007'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 379100, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF013: COS 25kg KRW 338,530 → 328,350/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 328350, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF013'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 328350, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF014: COS 25kg KRW 338,530 → 328,350/kg (SCS)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 328350, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF014'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 328350, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF015: COS_SP 25kg KRW 342,030 → 331,750/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 331750, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF015'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 331750, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF016: COS 10kg KRW 452,330 → 438,310/kg (SEC파주장)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 438310, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF016'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 438310, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF020: COS 40kg KRW 321,110 → 311,460/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 311460, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF020'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 311460, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF025: COS_40 SP 40kg KRW 323,310 → 313,600/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 313600, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF025'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 313600, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF018: ClF3 40kg KRW 313,380 → 300,930/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 300930, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF018'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 300930, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF024: ClF3 20kg KRW 336,820 → 323,410/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 323410, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF024'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 323410, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF019: ClF3 20kg KRW 456,190 → 438,010/kg (可楽洞U型号)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 438010, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF019'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 438010, currency = 'KRW', note = 'FPK품 구매단가 2025';

-- KF021: ClF3 10kg KRW 451,870 → 429,100/kg (KEY)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 429100, 'KRW', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF021'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 429100, currency = 'KRW', note = 'FPK품 구매단가 2025';

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

-- KF010: CF4 Y 300kg USD 19.29/kg (LGD) - 25年1月以後
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 19.29, 'USD', 'FPK품 구매단가 2025', NOW()
FROM product_code WHERE trade_condition_no = 'KF010'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 19.29, currency = 'USD', note = 'FPK품 구매단가 2025';

-- ========================================
-- 2026년 1월 단가 (26年1月以後～)
-- ========================================

-- KF001: COS 40kg USD 179.76/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 179.76, 'USD', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF001'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 179.76, currency = 'USD', note = 'FPK품 구매단가 2026';

-- KF007: COS 25kg KRW 379,104/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 379104, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF007'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 379104, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF013: COS 25kg KRW 328,349/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 328349, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF013'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 328349, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF014: COS 25kg KRW 328,349/kg (SCS)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 328349, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF014'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 328349, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF015: COS_SP 25kg KRW 331,748/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 331748, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF015'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 331748, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF016: COS 10kg KRW 438,309/kg (SEC파주장)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 438309, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF016'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 438309, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF020: COS 40kg KRW 311,465/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 311465, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF020'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 311465, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF025: COS_40 SP 40kg KRW 313,595/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 313595, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF025'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 313595, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF018: ClF3 40kg KRW 300,930/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 300930, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF018'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 300930, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF024: ClF3 20kg KRW 323,412/kg (SEC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 323412, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF024'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 323412, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF019: ClF3 20kg KRW 438,012/kg (可楽洞U型号)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 438012, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF019'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 438012, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF021: ClF3 10kg KRW 429,103/kg (KEY)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 429103, 'KRW', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF021'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 429103, currency = 'KRW', note = 'FPK품 구매단가 2026';

-- KF005: CF4 Y 300kg JPY 2,197/kg (SDC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 2197, 'JPY', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF005'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2197, currency = 'JPY', note = 'FPK품 구매단가 2026';

-- KF026: CF4 Y/中国産 300kg JPY 2,197/kg (SDC)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 2197, 'JPY', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF026'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2197, currency = 'JPY', note = 'FPK품 구매단가 2026';

-- KF009: CF4 32kg JPY 2,295/kg (KEY)
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2026-01-01', 2295, 'JPY', 'FPK품 구매단가 2026', NOW()
FROM product_code WHERE trade_condition_no = 'KF009'
ON CONFLICT (product_code_id, effective_date) DO UPDATE SET price_per_kg = 2295, currency = 'JPY', note = 'FPK품 구매단가 2026';

-- KF010: CF4 Y 300kg USD 19.29/kg (LGD)
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
    ph.currency as "통화",
    ph.note as "비고"
FROM product_price_history ph
JOIN product_code pc ON ph.product_code_id = pc.selection_pattern_code
ORDER BY pc.trade_condition_no, ph.effective_date;
