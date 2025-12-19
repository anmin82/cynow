"""CF4 YC 용기의 cylinder_type_key 디버깅"""
from django.core.management.base import BaseCommand
from django.db import connection
import hashlib


class Command(BaseCommand):
    help = 'CF4 YC 용기의 cylinder_type_key 디버깅'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 세 개의 SDC 카드 샘플 확인
            self.stdout.write("=== SDC 카드 1 (89개) 샘플 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    c.cylinder_type_key,
                    -- cylinder_type_key 생성에 사용되는 값들
                    COALESCE(c.dashboard_gas_name, '') as key_gas,
                    COALESCE(CAST(c.dashboard_capacity AS TEXT), '') as key_capacity,
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name, '') as key_valve,
                    COALESCE(c.dashboard_cylinder_spec_name, '') as key_cylinder,
                    COALESCE(c.dashboard_enduser, '') as key_enduser
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser = 'SDC'
                GROUP BY 
                    c.cylinder_type_key,
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                HAVING COUNT(*) = 89
                LIMIT 1
            """)
            
            row1 = cursor.fetchone()
            if row1:
                key_string1 = f"{row1[8]}|{row1[9]}|{row1[10]}|{row1[11]}|{row1[12]}"
                calculated_key1 = hashlib.md5(key_string1.encode('utf-8')).hexdigest()
                self.stdout.write(f"  용기번호: {row1[0]}\n")
                self.stdout.write(f"    Key String: '{key_string1}'\n")
                self.stdout.write(f"    Calculated Key: {calculated_key1}\n")
                self.stdout.write(f"    Actual Key: {row1[7]}\n")
                self.stdout.write(f"    Match: {'YES' if calculated_key1 == row1[7] else 'NO'}\n")
                self.stdout.write(f"    각 값: gas='{row1[8]}', capacity='{row1[9]}', valve='{row1[10]}', cylinder='{row1[11]}', enduser='{row1[12]}'\n")
            
            self.stdout.write("\n=== SDC 카드 2 (64개) 샘플 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    c.cylinder_type_key,
                    COALESCE(c.dashboard_gas_name, '') as key_gas,
                    COALESCE(CAST(c.dashboard_capacity AS TEXT), '') as key_capacity,
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name, '') as key_valve,
                    COALESCE(c.dashboard_cylinder_spec_name, '') as key_cylinder,
                    COALESCE(c.dashboard_enduser, '') as key_enduser
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser = 'SDC'
                GROUP BY 
                    c.cylinder_type_key,
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                HAVING COUNT(*) = 64
                LIMIT 1
            """)
            
            row2 = cursor.fetchone()
            if row2:
                key_string2 = f"{row2[8]}|{row2[9]}|{row2[10]}|{row2[11]}|{row2[12]}"
                calculated_key2 = hashlib.md5(key_string2.encode('utf-8')).hexdigest()
                self.stdout.write(f"  용기번호: {row2[0]}\n")
                self.stdout.write(f"    Key String: '{key_string2}'\n")
                self.stdout.write(f"    Calculated Key: {calculated_key2}\n")
                self.stdout.write(f"    Actual Key: {row2[7]}\n")
                self.stdout.write(f"    Match: {'YES' if calculated_key2 == row2[7] else 'NO'}\n")
                self.stdout.write(f"    각 값: gas='{row2[8]}', capacity='{row2[9]}', valve='{row2[10]}', cylinder='{row2[11]}', enduser='{row2[12]}'\n")
            
            self.stdout.write("\n=== SDC 카드 3 (54개) 샘플 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    c.cylinder_type_key,
                    COALESCE(c.dashboard_gas_name, '') as key_gas,
                    COALESCE(CAST(c.dashboard_capacity AS TEXT), '') as key_capacity,
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name, '') as key_valve,
                    COALESCE(c.dashboard_cylinder_spec_name, '') as key_cylinder,
                    COALESCE(c.dashboard_enduser, '') as key_enduser
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser = 'SDC'
                GROUP BY 
                    c.cylinder_type_key,
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                HAVING COUNT(*) = 54
                LIMIT 1
            """)
            
            row3 = cursor.fetchone()
            if row3:
                key_string3 = f"{row3[8]}|{row3[9]}|{row3[10]}|{row3[11]}|{row3[12]}"
                calculated_key3 = hashlib.md5(key_string3.encode('utf-8')).hexdigest()
                self.stdout.write(f"  용기번호: {row3[0]}\n")
                self.stdout.write(f"    Key String: '{key_string3}'\n")
                self.stdout.write(f"    Calculated Key: {calculated_key3}\n")
                self.stdout.write(f"    Actual Key: {row3[7]}\n")
                self.stdout.write(f"    Match: {'YES' if calculated_key3 == row3[7] else 'NO'}\n")
                self.stdout.write(f"    각 값: gas='{row3[8]}', capacity='{row3[9]}', valve='{row3[10]}', cylinder='{row3[11]}', enduser='{row3[12]}'\n")
            
            # 세 카드의 차이점 비교
            if row1 and row2 and row3:
                self.stdout.write("\n=== 세 카드의 차이점 비교 ===\n")
                self.stdout.write(f"  Key String 1: '{key_string1}'\n")
                self.stdout.write(f"  Key String 2: '{key_string2}'\n")
                self.stdout.write(f"  Key String 3: '{key_string3}'\n")
                self.stdout.write(f"\n  Key String 1 == Key String 2: {key_string1 == key_string2}\n")
                self.stdout.write(f"  Key String 1 == Key String 3: {key_string1 == key_string3}\n")
                self.stdout.write(f"  Key String 2 == Key String 3: {key_string2 == key_string3}\n")

