"""CYNOW 배포 빌드 스크립트"""
import os
import shutil
from pathlib import Path

# 버전 읽기
version = open('VERSION').read().strip()
dist_dir = Path(f'dist/cynow-v{version}')

print(f'Building CYNOW v{version}...')

# 기존 폴더 정리
if dist_dir.exists():
    shutil.rmtree(dist_dir)
dist_dir.mkdir(parents=True)

# 복사할 폴더/파일 목록
include_dirs = [
    'alerts',
    'config',
    'core',
    'cylinders',
    'dashboard',
    'deploy',   # 배포 설정 파일
    'devices',  # Scale Gateway API
    'docs',
    'history',
    'orders',   # 주문/출하 관리
    'plans',
    'reports',
    'sql',
    'static',
    'templates',
]

include_files = [
    'manage.py',
    'requirements.txt',
    'README.md',
    'VERSION',
    'CHANGELOG.md',
    'env.example.txt',
    'SCALE_GATEWAY_IMPLEMENTATION.md',  # Scale Gateway 구현 문서
]

# 제외 패턴
exclude_patterns = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '.git',
    '.env',
    'db.sqlite3',
    '*.md.bak',
]

def should_exclude(path):
    """제외할 파일/폴더인지 확인"""
    name = os.path.basename(path)
    for pattern in exclude_patterns:
        if pattern.startswith('*'):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    return False

def copy_tree_filtered(src, dst):
    """필터링된 폴더 복사"""
    if should_exclude(src):
        return
    
    if os.path.isfile(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    elif os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if not should_exclude(s):
                copy_tree_filtered(s, d)

# 폴더 복사
for dir_name in include_dirs:
    src = Path(dir_name)
    if src.exists():
        print(f'  Copying {dir_name}/...')
        copy_tree_filtered(str(src), str(dist_dir / dir_name))

# 파일 복사
for file_name in include_files:
    src = Path(file_name)
    if src.exists():
        print(f'  Copying {file_name}...')
        shutil.copy2(src, dist_dir / file_name)

# INSTALL.md는 이미 생성됨

# 빌드 정보 파일 생성
from datetime import datetime
build_info = f"""CYNOW v{version}
Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
(dist_dir / 'BUILD_INFO.txt').write_text(build_info)

print()
print(f'Build complete: {dist_dir}')
print()

# 파일 목록 출력
file_count = sum(1 for _ in dist_dir.rglob('*') if _.is_file())
print(f'Total files: {file_count}')

