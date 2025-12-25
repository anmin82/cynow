-- TB_자재코드에서 추출한 단가 정보 (kg당 단가로 변환)
-- 병당 단가 ÷ 충전량 = kg당 단가

-- KF001: USD 7200 / 40kg = 180 USD/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 180, 'USD', 'TB_자재코드 (7200/40kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF001'
ON CONFLICT DO NOTHING;

-- KF002: JPY 67200 / 32kg = 2100 JPY/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2100, 'JPY', 'TB_자재코드 (67200/32kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF002'
ON CONFLICT DO NOTHING;

-- KF003: JPY 1400000 / 35kg = 40000 JPY/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 40000, 'JPY', 'TB_자재코드 (1400000/35kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF003'
ON CONFLICT DO NOTHING;

-- KF004: KRW 11937500 / 25kg = 477500 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 477500, 'KRW', 'TB_자재코드 (11937500/25kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF004'
ON CONFLICT DO NOTHING;

-- KF005: JPY 630000 / 300kg = 2100 JPY/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2100, 'JPY', 'TB_자재코드 (630000/300kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF005'
ON CONFLICT DO NOTHING;

-- KF006: JPY 568400 / 245kg = 2320 JPY/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2320, 'JPY', 'TB_자재코드 (568400/245kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF006'
ON CONFLICT DO NOTHING;

-- KF007: KRW 12443500 / 25kg = 497740 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 497740, 'KRW', 'TB_자재코드 (12443500/25kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF007'
ON CONFLICT DO NOTHING;

-- KF009: JPY 70272 / 32kg = 2196 JPY/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2196, 'JPY', 'TB_자재코드 (70272/32kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF009'
ON CONFLICT DO NOTHING;

-- KF010: JPY 696000 / 300kg = 2320 JPY/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2320, 'JPY', 'TB_자재코드 (696000/300kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF010'
ON CONFLICT DO NOTHING;

-- KF011: KRW 11937500 / 25kg = 477500 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 477500, 'KRW', 'TB_자재코드 (11937500/25kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF011'
ON CONFLICT DO NOTHING;

-- KF012: KRW 11987500 / 25kg = 479500 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 479500, 'KRW', 'TB_자재코드 (11987500/25kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF012'
ON CONFLICT DO NOTHING;

-- KF013: KRW 10292250 / 25kg = 411690 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 411690, 'KRW', 'TB_자재코드 (10292250/25kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF013'
ON CONFLICT DO NOTHING;

-- KF014: KRW 10292250 / 25kg = 411690 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 411690, 'KRW', 'TB_자재코드 (10292250/25kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF014'
ON CONFLICT DO NOTHING;

-- KF015: KRW 10553500 / 25kg = 422140 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 422140, 'KRW', 'TB_자재코드 (10553500/25kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF015'
ON CONFLICT DO NOTHING;

-- KF016: KRW 5515700 / 10kg = 551570 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 551570, 'KRW', 'TB_자재코드 (5515700/10kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF016'
ON CONFLICT DO NOTHING;

-- KF017: JPY 630000 / 300kg = 2100 JPY/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 2100, 'JPY', 'TB_자재코드 (630000/300kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF017'
ON CONFLICT DO NOTHING;

-- KF018: KRW 13655600 / 40kg = 341390 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 341390, 'KRW', 'TB_자재코드 (13655600/40kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF018'
ON CONFLICT DO NOTHING;

-- KF019: KRW 9102200 / 20kg = 455110 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 455110, 'KRW', 'TB_자재코드 (9102200/20kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF019'
ON CONFLICT DO NOTHING;

-- KF022: KRW 17857600 / 40kg = 446440 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 446440, 'KRW', 'TB_자재코드 (17857600/40kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF022'
ON CONFLICT DO NOTHING;

-- KF023: USD 53700 / 300kg = 179 USD/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 179, 'USD', 'TB_자재코드 (53700/300kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF023'
ON CONFLICT DO NOTHING;

-- KF024: KRW 6810200 / 20kg = 340510 KRW/kg
INSERT INTO product_price_history (product_code_id, effective_date, price_per_kg, currency, note, created_at)
SELECT selection_pattern_code, '2025-01-01', 340510, 'KRW', 'TB_자재코드 (6810200/20kg)', NOW()
FROM product_code WHERE trade_condition_no = 'KF024'
ON CONFLICT DO NOTHING;

-- 결과 확인
SELECT pc.trade_condition_no, ph.price_per_kg, ph.currency, ph.note
FROM product_price_history ph
JOIN product_code pc ON ph.product_code_id = pc.selection_pattern_code
ORDER BY pc.trade_condition_no;
