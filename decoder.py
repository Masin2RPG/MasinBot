"""
세이브코드 디코더 모듈
세이브코드 해석 및 검증 기능 제공
"""

import logging
from typing import List, Optional

from config import Config
from items import ItemDatabase

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
    
    def decode_savecode(self, code: str, use_play_type: bool = True) -> List[int]:
        """세이브코드를 디코드하여 로드 데이터 반환"""
        # 코드 전처리
        clean_code = code.replace("-", "").upper().strip()
        
        # 코드 길이 검증
        if len(clean_code) % 2 != 0:
            raise ValueError(f"코드 길이가 올바르지 않습니다 (홀수): {len(clean_code)}")
        
        if len(clean_code) == 0:
            raise ValueError("코드가 비어있습니다")
        
        # 2글자씩 처리하여 숫자 문자열 생성
        numeric_string = ""
        for i in range(0, len(clean_code), 2):
            pair = clean_code[i:i+2]
            value = self._convert_code_to_int(pair, use_play_type)
            numeric_string += f"{value:03d}"
        
        # 세이브 값 길이에 따라 분할 (원본 게임과 동일하게 16개 배열)
        load_data = [0] * len(self.config.UDG_SAVE_VALUE_LENGTH)  # 16개 배열로 초기화
        position = 0
        save_size = len(self.config.UDG_SAVE_VALUE_LENGTH) - 1  # 인덱스 0은 사용하지 않으므로 -1
        
        for i in range(1, save_size + 1):  # 1부터 15까지
            length = self.config.UDG_SAVE_VALUE_LENGTH[i]
            if position + length > len(numeric_string):
                # 데이터가 부족한 경우 0으로 채움
                load_data[i] = 0
            else:
                chunk = numeric_string[position:position + length]
                load_data[i] = int(chunk) if chunk else 0
            position += length
        
        return load_data
    
    def validate_savecode(self, code: str, player_name: str) -> bool:
        """세이브코드 유효성 검증"""
        try:
            load_data = self.decode_savecode(code)
            
            if len(load_data) < 10:  # 최소 인덱스 9까지 필요
                logger.error("로드 데이터가 충분하지 않습니다")
                return False
            
            # 체크섬 계산 (원본 게임과 동일하게)
            checksum = 0
            save_size = len(self.config.UDG_SAVE_VALUE_LENGTH) - 1  # 인덱스 0은 사용하지 않으므로 -1
            for i in range(1, save_size + 1):  # 1부터 15까지
                if i != 9:  # 9번째 인덱스(체크섬)는 제외
                    checksum += load_data[i] * i
            
            # 게임 버전 보정
            if self.config.GAME_VERSION > 99:
                checksum += self.config.GAME_VERSION % ord('d')
            else:
                checksum += self.config.GAME_VERSION
            
            # 플레이어 이름 기반 가산
            name_value = self._calculate_string_value(player_name)
            checksum += name_value
            
            # 체크섬 정규화 (원본 게임은 [9] 사용)
            checksum %= self._get_nine_power(self.config.UDG_SAVE_VALUE_LENGTH[9])
            
            # 검증 결과 반환
            is_valid = checksum == load_data[9]
            logger.info(f"세이브코드 검증: {'성공' if is_valid else '실패'}")
            return is_valid
            
        except Exception as e:
            logger.error(f"세이브코드 검증 중 오류: {e}")
            return False
    
    def extract_items(self, code: str) -> List[str]:
        """세이브코드에서 아이템 목록 추출"""
        try:
            load_data = self.decode_savecode(code)
            items_list = []
            
            for idx, slot_index in enumerate(self.config.ITEM_SLOTS, 1):
                if slot_index < len(load_data):
                    item_code = load_data[slot_index]
                    item_name = self.item_db.get_item_name(item_code)
                    items_list.append(f"{idx}번째 아이템: {item_name}")
                else:
                    items_list.append(f"{idx}번째 아이템: 데이터 없음")
            
            return items_list
            
        except Exception as e:
            logger.error(f"아이템 추출 중 오류: {e}")
            raise
    
    def get_load_summary(self, code: str) -> dict:
        """세이브코드의 전체 정보 요약"""
        try:
            load_data = self.decode_savecode(code)
            
            summary = {
                "load_data": load_data,
                "total_slots": len(load_data),
                "items": {},
                "checksum_slot": load_data[8] if len(load_data) > 8 else None
            }
            
            # 아이템 정보 추가
            for idx, slot_index in enumerate(self.config.ITEM_SLOTS, 1):
                if slot_index < len(load_data):
                    item_code = load_data[slot_index]
                    item_name = self.item_db.get_item_name(item_code)
                    summary["items"][f"slot_{idx}"] = {
                        "code": item_code,
                        "name": item_name
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"로드 요약 생성 중 오류: {e}")
            raise
