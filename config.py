"""
설정 파일
봇 토큰과 기타 설정값들을 관리
환경변수와 기본값을 지원
"""

import os
from typing import Any, Dict

# 환경변수 로드 시도
try:
    import os

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass  # python-dotenv가 설치되지 않은 경우 무시

class Config:
    """설정 클래스"""
    
    # 봇 설정
    BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')
    # print("[DEBUG] DISCORD_BOT_TOKEN:", repr(BOT_TOKEN))  # 보안상 주석 처리
    COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '/')
    
    # 게임 설정
    GAME_VERSION = int(os.getenv('GAME_VERSION', '7'))
    UDG_SAVE_VALUE_LENGTH = [6, 3, 6, 3, 6, 3, 6, 3, 3, 3, 2, 3, 4, 2, 4]
    ITEM_SLOTS = [1, 3, 5, 7, 9, 11]
    
    # 문자 맵핑
    CHAR_MAP_PLAY_TRUE = "1O7EC43VPRN8FXKDTSUQ026HWA5YIM9BJLGZ"
    CHAR_MAP_PLAY_FALSE = "OBX6RAGZKT71N435YDEVPF92LUWQ0IMSCHJ8"
    STRING_SOURCE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890~`!#$^&*()-_=+|{}[]:;<>,.?@"
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def validate(cls):
        """설정 유효성 검사"""
        if not cls.BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        
        if cls.GAME_VERSION < 1:
            raise ValueError("GAME_VERSION은 1 이상이어야 합니다.")
        
        return True
