"""
세이브코드 디코더 모듈
세이브코드 해석 및 검증 기능 제공
"""

import logging
from typing import List, Optional

from config import Config
from items import ItemDatabase
from savecode_decoder import parse_savecode

logger = logging.getLogger(__name__)


class SaveCodeDecoder:
    """세이브코드 디코더 클래스"""
    
    def __init__(self):
        self.config = Config()
        self.item_db = ItemDatabase()
    
    def _get_nine_power(self, m: int) -> int:
        """9의 m제곱을 계산"""
        n = 0
        j = 1
        for _ in range(m):
            n += j * 9
            j *= 10
        return n
    
    def _calculate_string_value(self, text: str) -> int:
        """문자열 값 계산 (ASCII/UTF-8 자동 처리)"""
        try:
            # ASCII 인코딩 시도
            text.encode('ascii')
            return self._calculate_ascii_value(text)
        except UnicodeEncodeError:
            # UTF-8 처리
            return self._calculate_utf8_value(text)
    
    def _calculate_ascii_value(self, text: str) -> int:
        """ASCII 문자열 값 계산"""
        text = text.upper()
        total = 0
        
        for i, char in enumerate(text):
            try:
                index = self.config.STRING_SOURCE.index(char) + 1
                total += index * (i + 1)
            except ValueError:
                logger.warning(f"유효하지 않은 문자: '{char}'")
                
        return total
    
    def _calculate_utf8_value(self, text: str) -> int:
        """UTF-8 문자열 값 계산"""
        temp_bytes = text.upper().encode('utf-8')
        total = 0
        
        for i, byte in enumerate(temp_bytes):
            char = chr(byte)
            try:
                index = self.config.STRING_SOURCE.index(char) + 1
            except ValueError:
                index = -1  # 원본 게임과 동일하게 -1 사용
            total += index * (i + 1)
                
        return total
    
    def _convert_code_to_int(self, code_pair: str, use_play_type: bool = True) -> int:
        """2글자 코드를 정수로 변환"""
        char_map = (self.config.CHAR_MAP_PLAY_TRUE if use_play_type 
                   else self.config.CHAR_MAP_PLAY_FALSE)
        
        if len(code_pair) != 2:
            raise ValueError(f"코드 쌍의 길이가 올바르지 않습니다: {code_pair}")
        
        result = 0
        for i, char in enumerate(code_pair):
            try:
                index = char_map.index(char)
            except ValueError:
                raise ValueError(f"유효하지 않은 문자: '{char}'")
            
            if i == 0:
                result = index * 36
            else:
                result += index
                
        return result
    
    def _parse(self, code: str, player_name: str = "", use_play_type: bool = True, validate_checksum: bool = False) -> dict:
        """공통 파서 래퍼"""
        return parse_savecode(
            code=code,
            player_name=player_name,
            play_type=use_play_type,
            save_value_length=self.config.UDG_SAVE_VALUE_LENGTH,
            summon_chunk_n=getattr(self.config, "SUMMON_CHUNK_N", None),
            validate_checksum=validate_checksum,
        )

    def decode_savecode(self, code: str, player_name: str = "", use_play_type: bool = True) -> List[int]:
        """세이브코드를 디코드하여 로드 데이터 반환"""
        parsed = self._parse(code, player_name=player_name, use_play_type=use_play_type, validate_checksum=False)
        return parsed.get("raw_data", [])
    
    def validate_savecode(self, code: str, player_name: str, use_play_type: bool = True) -> bool:
        """세이브코드 유효성 검증"""
        try:
            parsed = self._parse(code, player_name=player_name, use_play_type=use_play_type, validate_checksum=True)
            return bool(parsed.get("checksum_valid", False))
        except Exception as e:
            logger.error(f"세이브코드 검증 중 오류: {e}")
            return False
    
    def extract_items(self, code: str, use_play_type: bool = True) -> List[str]:
        """세이브코드에서 아이템 목록 추출"""
        try:
            parsed = self._parse(code, use_play_type=use_play_type)
            items_list = []

            for idx, item_code in enumerate(parsed.get("items", []), 1):
                item_name = self.item_db.get_item_name(item_code)
                items_list.append(f"{idx}번째 아이템: {item_name}")

            return items_list
        except Exception as e:
            logger.error(f"아이템 추출 중 오류: {e}")
            raise
    
    def get_load_summary(self, code: str) -> dict:
        """세이브코드의 전체 정보 요약"""
        try:
            parsed = self._parse(code)

            summary = {
                "load_data": parsed.get("raw_data", []),
                "total_slots": len(parsed.get("raw_data", [])),
                "items": {},
                "checksum_slot": parsed.get("checksum_value"),
                "save_version": parsed.get("save_version"),
                "hero_type_index": parsed.get("hero_type_index"),
                "checksum_valid": parsed.get("checksum_valid", False),
            }

            for idx, item_code in enumerate(parsed.get("items", []), 1):
                item_name = self.item_db.get_item_name(item_code)
                summary["items"][f"slot_{idx}"] = {
                    "code": item_code,
                    "name": item_name,
                }

            return summary
        except Exception as e:
            logger.error(f"로드 요약 생성 중 오류: {e}")
            raise
