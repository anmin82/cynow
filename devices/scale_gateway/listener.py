"""
Scale Gateway API - TCP 리스너

저울(FG-150KAL)로부터 TCP 연결을 받아 데이터를 수신하고,
파싱하여 최신 안정값(ST)을 메모리에 캐시
"""
import socket
import logging
import time
from typing import Optional

from .parser import ScaleDataParser
from .state import get_state_manager

logger = logging.getLogger(__name__)


class ScaleGatewayListener:
    """
    TCP 저울 데이터 리스너
    
    - 단일 연결 수락 (POC)
    - CRLF 기반 라인 버퍼링
    - 연결 끊김 시 자동 재대기
    - 파싱 예외로 프로세스 종료되지 않도록 방어적 처리
    """
    
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 4001,
        scale_id: str = 'default',
        buffer_size: int = 4096
    ):
        """
        Args:
            host: 리스너 바인딩 주소
            port: 리스너 포트
            scale_id: 저울 식별자
            buffer_size: 수신 버퍼 크기
        """
        self.host = host
        self.port = port
        self.scale_id = scale_id
        self.buffer_size = buffer_size
        
        self.parser = ScaleDataParser()
        self.state_manager = get_state_manager()
        
        self.running = False
        self.server_socket: Optional[socket.socket] = None
    
    def start(self):
        """
        TCP 리스너 시작
        
        무한 루프로 연결을 수락하고 데이터를 수신
        Ctrl+C 또는 외부 신호로 종료
        """
        self.running = True
        
        logger.info(f"[Scale Gateway] 리스너 시작: {self.host}:{self.port}")
        
        try:
            self._run_server()
        except KeyboardInterrupt:
            logger.info("[Scale Gateway] Ctrl+C 감지, 종료 중...")
        except Exception as e:
            logger.exception(f"[Scale Gateway] 리스너 오류: {e}")
        finally:
            self.stop()
    
    def _run_server(self):
        """서버 소켓 생성 및 연결 수락 루프"""
        # 서버 소켓 생성
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)  # 단일 연결 대기
        
        logger.info(f"[Scale Gateway] 포트 {self.port}에서 연결 대기 중...")
        
        while self.running:
            try:
                # 연결 수락 (블로킹)
                client_socket, client_addr = self.server_socket.accept()
                logger.info(f"[Scale Gateway] 연결 수락: {client_addr}")
                
                # 클라이언트 처리
                self._handle_client(client_socket, client_addr)
                
            except Exception as e:
                if self.running:
                    logger.error(f"[Scale Gateway] 연결 수락 오류: {e}")
                    time.sleep(1)  # 오류 시 잠깐 대기 후 재시도
    
    def _handle_client(self, client_socket: socket.socket, client_addr):
        """
        클라이언트 연결 처리
        
        - 라인 단위로 버퍼링
        - 파싱 후 ST 상태만 캐시에 저장
        - 연결 끊기거나 예외 발생 시 종료
        
        Args:
            client_socket: 클라이언트 소켓
            client_addr: 클라이언트 주소
        """
        line_buffer = ""
        
        try:
            while self.running:
                # 데이터 수신 (블로킹)
                data = client_socket.recv(self.buffer_size)
                
                if not data:
                    # 연결 종료
                    logger.info(f"[Scale Gateway] 연결 종료: {client_addr}")
                    break
                
                # 바이트 → 문자열 변환
                try:
                    chunk = data.decode('utf-8')
                except UnicodeDecodeError as e:
                    logger.warning(f"[Scale Gateway] UTF-8 디코딩 실패: {e}")
                    continue
                
                # 버퍼에 추가
                line_buffer += chunk
                
                # CRLF 또는 LF 기준으로 라인 분리
                while '\n' in line_buffer:
                    line, line_buffer = line_buffer.split('\n', 1)
                    line = line.strip()  # \r\n, \n 모두 제거
                    
                    if line:
                        self._process_line(line)
        
        except Exception as e:
            logger.error(f"[Scale Gateway] 클라이언트 처리 오류: {e}", exc_info=True)
        
        finally:
            # 클라이언트 소켓 닫기
            try:
                client_socket.close()
            except Exception:
                pass
            
            logger.info(f"[Scale Gateway] 클라이언트 소켓 닫힘: {client_addr}")
    
    def _process_line(self, line: str):
        """
        한 줄의 데이터를 파싱하고 처리
        
        - ST (안정): 최신값으로 캐시 업데이트
        - US (불안정): 로그만 남김
        - OL (과부하): 로그만 남김
        
        Args:
            line: 수신한 라인 (예: "ST , +000053.26 _kg")
        """
        try:
            parsed = self.parser.parse_line(line)
            
            if not parsed:
                # 파싱 실패 (이미 parser에서 로그 남김)
                return
            
            status = parsed['status']
            weight = parsed['weight']
            raw = parsed['raw']
            
            if status == 'ST':
                # 안정 상태: 최신값 업데이트
                self.state_manager.update_latest(
                    scale_id=self.scale_id,
                    status=status,
                    weight=weight,
                    raw_line=raw
                )
                logger.debug(f"[Scale Gateway] ST 업데이트: {weight} kg")
            
            elif status == 'US':
                # 불안정 상태: 로그만
                logger.debug(f"[Scale Gateway] US (불안정): {weight} kg")
            
            elif status == 'OL':
                # 과부하 상태: 경고 로그
                logger.warning(f"[Scale Gateway] OL (과부하): {weight} kg")
            
            else:
                logger.warning(f"[Scale Gateway] 알 수 없는 상태: {status}")
        
        except Exception as e:
            logger.error(f"[Scale Gateway] 라인 처리 오류: {e}, 라인: {line}", exc_info=True)
    
    def stop(self):
        """리스너 종료"""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        logger.info("[Scale Gateway] 리스너 종료됨")



















