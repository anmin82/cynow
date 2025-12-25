-- TB_자재코드에서 추출한 단가 정보
-- 제품코드별 단가 입력 (ProductPriceHistory)

-- KF001: USD 7200
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 7200, 'USD', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF001'
ON CONFLICT DO NOTHING;

-- KF002: JPY 67200
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 67200, 'JPY', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF002'
ON CONFLICT DO NOTHING;

-- KF003: JPY 1400000
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 1400000, 'JPY', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF003'
ON CONFLICT DO NOTHING;

-- KF004: KRW 11937500
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 11937500, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF004'
ON CONFLICT DO NOTHING;

-- KF005: JPY 630000
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 630000, 'JPY', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF005'
ON CONFLICT DO NOTHING;

-- KF006: JPY 568400
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 568400, 'JPY', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF006'
ON CONFLICT DO NOTHING;

-- KF007: KRW 12443500
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 12443500, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF007'
ON CONFLICT DO NOTHING;

-- KF009: JPY 70272
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 70272, 'JPY', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF009'
ON CONFLICT DO NOTHING;

-- KF010: JPY 696000
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 696000, 'JPY', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF010'
ON CONFLICT DO NOTHING;

-- KF011: KRW 11937500
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 11937500, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF011'
ON CONFLICT DO NOTHING;

-- KF012: KRW 11987500
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 11987500, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF012'
ON CONFLICT DO NOTHING;

-- KF013: KRW 10292250
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 10292250, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF013'
ON CONFLICT DO NOTHING;

-- KF014: KRW 10292250
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 10292250, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF014'
ON CONFLICT DO NOTHING;

-- KF015: KRW 10553500
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 10553500, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF015'
ON CONFLICT DO NOTHING;

-- KF016: KRW 5515700
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 5515700, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF016'
ON CONFLICT DO NOTHING;

-- KF017: JPY 630000
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 630000, 'JPY', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF017'
ON CONFLICT DO NOTHING;

-- KF018: KRW 13655600
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 13655600, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF018'
ON CONFLICT DO NOTHING;

-- KF019: KRW 9102200
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 9102200, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF019'
ON CONFLICT DO NOTHING;

-- KF022: KRW 17857600
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 17857600, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF022'
ON CONFLICT DO NOTHING;

-- KF023: USD 53700
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 53700, 'USD', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF023'
ON CONFLICT DO NOTHING;

-- KF024: KRW 6810200
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT id, '2025-01-01', 6810200, 'KRW', 'TB_자재코드 초기 등록', NOW()
FROM product_code WHERE trade_condition_no = 'KF024'
ON CONFLICT DO NOTHING;

-- 결과 확인
SELECT pc.trade_condition_no, ph.price_per_kg, ph.currency, ph.effective_date
FROM product_price_history ph
JOIN product_code pc ON ph.product_code_id = pc.id
ORDER BY pc.trade_condition_no;

