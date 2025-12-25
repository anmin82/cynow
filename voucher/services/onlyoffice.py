"""
ONLYOFFICE Document Server 연동 서비스

ONLYOFFICE를 사용하여 DOCX 템플릿을 웹에서 직접 편집할 수 있도록 합니다.

사용법:
    from voucher.services.onlyoffice import OnlyOfficeService
    
    service = OnlyOfficeService()
    config = service.get_editor_config(
        filename='offer_template.docx',
        user_id='admin',
        user_name='관리자'
    )
"""
import os
import json
import time
import hashlib
import hmac
import base64
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

from django.conf import settings


class OnlyOfficeService:
    """
    ONLYOFFICE Document Server 연동 서비스
    
    환경변수:
    - ONLYOFFICE_URL: Document Server URL (예: http://10.78.30.98:8080)
    - ONLYOFFICE_JWT_SECRET: JWT 시크릿 키
    - ONLYOFFICE_CALLBACK_URL: 저장 콜백 URL (Django 서버)
    """
    
    def __init__(self):
        # 환경변수에서 설정 로드
        self.server_url = os.getenv('ONLYOFFICE_URL', 'http://localhost:8080')
        self.jwt_secret = os.getenv('ONLYOFFICE_JWT_SECRET', 'cynow-onlyoffice-secret-2025')
        
        # Django 서버 URL (ONLYOFFICE가 파일을 가져갈 URL)
        self.django_base_url = os.getenv('DJANGO_BASE_URL', 'http://10.78.30.98')
        
        # 템플릿 디렉토리
        self.template_dir = Path(settings.BASE_DIR) / 'docx_templates'
    
    def get_editor_config(
        self,
        filename: str,
        user_id: str,
        user_name: str,
        mode: str = 'edit',
        lang: str = 'ko'
    ) -> Dict[str, Any]:
        """
        ONLYOFFICE 에디터 설정 JSON 생성
        
        Args:
            filename: 템플릿 파일명 (예: offer_template.docx)
            user_id: 사용자 ID
            user_name: 사용자 이름
            mode: 편집 모드 ('edit' 또는 'view')
            lang: 에디터 언어 ('ko', 'en', 'ja' 등)
            
        Returns:
            ONLYOFFICE 에디터 설정 딕셔너리
        """
        # 파일 정보
        file_path = self.template_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {filename}")
        
        file_ext = file_path.suffix.lower().lstrip('.')
        file_key = self._generate_file_key(file_path)
        
        # 문서 URL (Django에서 서빙)
        document_url = f"{self.django_base_url}/cynow/voucher/template/file/{filename}"
        
        # 콜백 URL (저장 시 ONLYOFFICE가 호출)
        # 파일명을 URL에 포함시켜 저장 시 어떤 파일인지 식별
        encoded_filename = urllib.parse.quote(filename)
        callback_url = f"{self.django_base_url}/cynow/voucher/template/callback/{encoded_filename}"
        
        # 에디터 설정
        config = {
            "document": {
                "fileType": file_ext,
                "key": file_key,
                "title": filename,
                "url": document_url,
                "permissions": {
                    "chat": False,
                    "comment": True,
                    "download": True,
                    "edit": mode == 'edit',
                    "print": True,
                    "review": False,
                }
            },
            "documentType": "word",
            "editorConfig": {
                "callbackUrl": callback_url,
                "lang": lang,
                "mode": mode,
                "user": {
                    "id": user_id,
                    "name": user_name,
                },
                "customization": {
                    "autosave": True,
                    "comments": True,
                    "compactHeader": True,
                    "compactToolbar": False,
                    "feedback": False,
                    "forcesave": True,
                    "help": False,
                    "hideRightMenu": False,
                    "hideRulers": False,
                    "logo": {
                        "image": f"{self.django_base_url}/cynow/static/img/logo.png",
                        "visible": False,
                    },
                    "macros": False,
                    "plugins": False,
                    "toolbarNoTabs": False,
                    "uiTheme": "theme-light",
                    "zoom": 100,
                },
            },
            "height": "100%",
            "width": "100%",
            "type": "desktop",
        }
        
        # JWT 토큰 생성 및 추가
        if self.jwt_secret:
            config["token"] = self._create_jwt_token(config)
        
        return config
    
    def _generate_file_key(self, file_path: Path) -> str:
        """
        파일 고유 키 생성
        
        파일 경로 + 수정 시간을 기반으로 고유 키 생성.
        파일이 수정되면 키가 바뀌어서 ONLYOFFICE가 새로 로드함.
        """
        stat = file_path.stat()
        key_source = f"{file_path.name}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(key_source.encode()).hexdigest()[:20]
    
    def _create_jwt_token(self, payload: Dict[str, Any]) -> str:
        """
        JWT 토큰 생성
        
        ONLYOFFICE는 JWT를 사용하여 요청을 검증합니다.
        """
        # JWT 헤더
        header = {
            "alg": "HS256",
            "typ": "JWT"
        }
        
        # Base64 인코딩
        def base64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
        
        header_b64 = base64url_encode(json.dumps(header).encode())
        payload_b64 = base64url_encode(json.dumps(payload).encode())
        
        # 서명
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.jwt_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64url_encode(signature)
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        JWT 토큰 검증
        
        콜백 요청의 토큰을 검증합니다.
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # 서명 검증
            message = f"{header_b64}.{payload_b64}"
            expected_signature = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            
            # Base64 패딩 복원
            def base64url_decode(data: str) -> bytes:
                padding = 4 - len(data) % 4
                if padding != 4:
                    data += '=' * padding
                return base64.urlsafe_b64decode(data)
            
            actual_signature = base64url_decode(signature_b64)
            
            if not hmac.compare_digest(expected_signature, actual_signature):
                return None
            
            # 페이로드 디코딩
            payload = json.loads(base64url_decode(payload_b64))
            return payload
            
        except Exception:
            return None
    
    def get_api_js_url(self) -> str:
        """ONLYOFFICE API JavaScript URL"""
        return f"{self.server_url}/web-apps/apps/api/documents/api.js"
    
    def save_file_from_url(self, filename: str, download_url: str) -> bool:
        """
        ONLYOFFICE에서 제공하는 URL로부터 파일 다운로드 및 저장
        
        콜백에서 status가 2 또는 6일 때 호출됩니다.
        """
        import urllib.request
        
        try:
            file_path = self.template_dir / filename
            
            # 파일 다운로드
            urllib.request.urlretrieve(download_url, file_path)
            
            return True
        except Exception as e:
            print(f"파일 저장 오류: {e}")
            return False


# 싱글톤 인스턴스
_service_instance = None

def get_onlyoffice_service() -> OnlyOfficeService:
    """OnlyOffice 서비스 인스턴스 반환"""
    global _service_instance
    if _service_instance is None:
        _service_instance = OnlyOfficeService()
    return _service_instance

