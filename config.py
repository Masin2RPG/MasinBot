"""
개선된 설정 관리 시스템
봇 토큰과 기타 설정값들을 체계적으로 관리
환경변수, 기본값, 검증을 지원
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

# 환경변수 로드 시도
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass  # python-dotenv가 설치되지 않은 경우 무시


@dataclass
class BotSettings:
    """봇 관련 설정"""
    token: str
    command_prefix: str = '/'
    log_level: str = 'INFO'
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


@dataclass
class RaidSettings:
    """레이드 시스템 설정"""
    channel_id: int = 0  # 0이면 자동 검색
    max_participants: int = 30
    timeout_minutes: int = 30


@dataclass
class GameSettings:
    """게임 관련 설정"""
    version: int = 7
    udg_save_value_length: list = None
    item_slots: list = None
    char_map_play_true: str = "1O7EC43VPRN8FXKDTSUQ026HWA5YIM9BJLGZ"
    char_map_play_false: str = "OBX6RAGZKT71N435YDEVPF92LUWQ0IMSCHJ8"
    string_source: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890~`!#$^&*()-_=+|{}[]:;<>,.?@"
    
    def __post_init__(self):
        if self.udg_save_value_length is None:
            self.udg_save_value_length = [6, 3, 6, 3, 6, 3, 6, 3, 3, 3, 2, 3, 4, 2, 4]
        if self.item_slots is None:
            self.item_slots = [1, 3, 5, 7, 9, 11]


@dataclass
class OptimizationSettings:
    """최적화 관련 설정"""
    max_cores: int = 10
    timeout_seconds: int = 300
    default_targets: Dict[str, int] = None
    
    def __post_init__(self):
        if self.default_targets is None:
            self.default_targets = {'str': 4000, 'int': 4000, 'dex': 4000, 'luk': 4000}


class ConfigManager:
    """설정 관리자 클래스"""
    
    def __init__(self):
        self.bot = self._load_bot_settings()
        self.raid = self._load_raid_settings()
        self.game = self._load_game_settings()
        self.optimization = self._load_optimization_settings()
        self._setup_logging()
    
    def _load_bot_settings(self) -> BotSettings:
        """봇 설정 로드"""
        token = os.getenv('DISCORD_BOT_TOKEN', '')
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        
        return BotSettings(
            token=token,
            command_prefix=os.getenv('COMMAND_PREFIX', '/'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    def _load_raid_settings(self) -> RaidSettings:
        """레이드 설정 로드"""
        return RaidSettings(
            channel_id=int(os.getenv('RAID_CHANNEL_ID', '0')),
            max_participants=int(os.getenv('RAID_MAX_PARTICIPANTS', '30')),
            timeout_minutes=int(os.getenv('RAID_TIMEOUT_MINUTES', '30'))
        )
    
    def _load_game_settings(self) -> GameSettings:
        """게임 설정 로드"""
        return GameSettings(
            version=int(os.getenv('GAME_VERSION', '7'))
        )
    
    def _load_optimization_settings(self) -> OptimizationSettings:
        """최적화 설정 로드"""
        return OptimizationSettings(
            max_cores=int(os.getenv('OPTIMIZATION_MAX_CORES', '10')),
            timeout_seconds=int(os.getenv('OPTIMIZATION_TIMEOUT', '300'))
        )
    
    def _setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=getattr(logging, self.bot.log_level.upper()),
            format=self.bot.log_format
        )
    
    def validate(self):
        """설정 유효성 검사"""
        if not self.bot.token:
            raise ValueError("Bot token is required")
        
        if self.game.version < 1:
            raise ValueError("Game version must be >= 1")
        
        if self.optimization.max_cores <= 0:
            raise ValueError("Max cores must be > 0")
        
        if self.raid.max_participants <= 0:
            raise ValueError("Raid max participants must be > 0")
    
    def get_env_info(self) -> Dict[str, Any]:
        """환경 정보 반환 (디버깅용)"""
        return {
            'bot_prefix': self.bot.command_prefix,
            'log_level': self.bot.log_level,
            'game_version': self.game.version,
            'raid_channel_configured': self.raid.channel_id > 0,
            'max_cores': self.optimization.max_cores
        }


# 하위 호환성을 위한 기존 Config 클래스
class Config:
    """기존 Config 클래스 (하위 호환성 유지)"""
    
    def __init__(self):
        self._manager = ConfigManager()
        
        # 기존 속성들을 매핑
        self.BOT_TOKEN = self._manager.bot.token
        self.COMMAND_PREFIX = self._manager.bot.command_prefix
        self.RAID_CHANNEL_ID = self._manager.raid.channel_id
        self.GAME_VERSION = self._manager.game.version
        self.UDG_SAVE_VALUE_LENGTH = self._manager.game.udg_save_value_length
        self.ITEM_SLOTS = self._manager.game.item_slots
        self.CHAR_MAP_PLAY_TRUE = self._manager.game.char_map_play_true
        self.CHAR_MAP_PLAY_FALSE = self._manager.game.char_map_play_false
        self.STRING_SOURCE = self._manager.game.string_source
        self.LOG_LEVEL = self._manager.bot.log_level
        self.LOG_FORMAT = self._manager.bot.log_format
    
    def validate(self):
        """설정 유효성 검사"""
        return self._manager.validate()
    
    @classmethod
    def validate_config(cls):
        """클래스 메서드로 설정 검증"""
        config = cls()
        return config.validate()
    
    def get_manager(self) -> ConfigManager:
        """새로운 ConfigManager 반환"""
        return self._manager
