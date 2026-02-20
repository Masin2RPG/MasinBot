"""
세이브코드 인코더 모듈
로드 데이터를 세이브코드로 생성하는 기능 제공
"""

import logging
from typing import List, Optional

from config import Config
from items import ItemDatabase

logger = logging.getLogger(__name__)


class SaveCodeEncoder:
    """세이브코드 인코더 클래스"""
    
    def __init__(self):
        self.config = Config()
        self.item_db = ItemDatabase()
        self.summon_chunk_n = getattr(self.config, "SUMMON_CHUNK_N", 0)
    
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
    
    def _calculate_checksum(self, load_data: List[int], player_name: str, length_map: List[int], save_data_n: int,
                            save_version: int) -> int:
        """체크섬 계산 (버전 10 규칙)"""
        checksum = 0

        for i in range(1, save_data_n + 1):
            if i != 9:
                checksum += load_data[i] * i

        checksum += save_version
        checksum += self._calculate_string_value(player_name)
        checksum %= self._get_nine_power(length_map[9])

        return checksum
    
    def _convert_int_to_code(self, value: int, use_play_type: bool = True) -> str:
        """정수를 2글자 코드로 변환"""
        char_map = (self.config.CHAR_MAP_PLAY_TRUE if use_play_type 
                   else self.config.CHAR_MAP_PLAY_FALSE)
        
        if value < 0 or value >= 36 * 36:
            raise ValueError(f"값이 범위를 벗어났습니다: {value} (0-1295 범위)")
        
        first_char_index = value // 36
        second_char_index = value % 36
        
        return char_map[first_char_index] + char_map[second_char_index]
    
    def encode_savecode(self, load_data: List[int], player_name: str, use_play_type: bool = True,
                        save_version: int = 10, summon_chunk_n: int = None) -> str:
        """로드 데이터를 세이브코드로 인코딩 (버전 10)

        summon_chunk_n가 None이면 인스턴스 기본값(self.summon_chunk_n)을 사용합니다.
        소환 정보를 포함하지 않으려면 0을 넘기면 됩니다.
        """
        try:
            encoded_data = load_data.copy()
            chunk_n = self.summon_chunk_n if summon_chunk_n is None else summon_chunk_n
            save_size = len(self.config.UDG_SAVE_VALUE_LENGTH) - 1

            # 영웅 타입을 low/high(/extra)로 분해하여 길이 제한을 우회
            hero_id = encoded_data[14] if len(encoded_data) > 14 else 0
            hero_low = hero_id % 100
            hero_high = (hero_id // 100) % 1000
            hero_extra = (hero_id // 100000) % 1000  # 존재하면 17번 슬롯 사용

            # 길이 계획: 기본 16(1~16) + 소환 청크 + hero_extra 여부
            save_data_n = save_size + 1 + chunk_n + (1 if hero_extra > 0 else 0)

            # 버전 9 포맷(추가 슬롯) 대응: hero_extra가 있을 때 summon_chunk가 없으면 v9 규칙으로 체크섬 계산
            effective_save_version = save_version
            if hero_extra > 0 and chunk_n == 0:
                effective_save_version = 9

            length_map = self.config.UDG_SAVE_VALUE_LENGTH[:]
            need_len = save_data_n + 1
            if len(length_map) < need_len:
                length_map += [0] * (need_len - len(length_map))
            length_map[16] = 3
            for i in range(1, chunk_n + 1):
                length_map[16 + i] = 3
            if hero_extra > 0:
                length_map[17] = 3

            while len(encoded_data) < need_len:
                encoded_data.append(0)
            if len(encoded_data) > need_len:
                encoded_data = encoded_data[:need_len]

            # 영웅 타입 필드 분배
            encoded_data[14] = hero_low
            if len(encoded_data) > 16:
                encoded_data[16] = hero_high
            if hero_extra > 0 and len(encoded_data) > 17:
                encoded_data[17] = hero_extra

            checksum = self._calculate_checksum(encoded_data, player_name, length_map, save_data_n, effective_save_version)
            encoded_data[9] = checksum

            numeric_string = ""
            for i in range(1, save_data_n + 1):
                value = encoded_data[i]
                length = length_map[i] if i < len(length_map) else 3
                formatted_value = f"{value:0{length}d}"
                if len(formatted_value) > length:
                    formatted_value = formatted_value[-length:]
                numeric_string += formatted_value

            code_parts = []
            for i in range(0, len(numeric_string), 3):
                chunk = numeric_string[i:i + 3]
                if len(chunk) < 3:
                    chunk = chunk.ljust(3, '0')
                value = int(chunk)
                value = value % (36 * 36)
                code_parts.append(self._convert_int_to_code(value, use_play_type))

            return "".join(code_parts)

        except Exception as e:
            logger.error(f"세이브코드 인코딩 중 오류: {e}")
            raise
    
    def create_savecode_with_items(self, player_name: str, items: dict = None, 
                                 other_values: dict = None, use_play_type: bool = True) -> str:
        """아이템과 기타 값들로 세이브코드 생성"""
        try:
            # 기본 로드 데이터 생성 (모든 값을 0으로 초기화)
            load_data = [0] * len(self.config.UDG_SAVE_VALUE_LENGTH)
            
            # 아이템 설정
            if items:
                for slot_num, item_name_or_code in items.items():
                    if isinstance(slot_num, str) and slot_num.startswith('slot_'):
                        slot_index = int(slot_num.split('_')[1]) - 1
                    else:
                        slot_index = int(slot_num) - 1
                    
                    if 0 <= slot_index < len(self.config.ITEM_SLOTS):
                        data_index = self.config.ITEM_SLOTS[slot_index]
                        
                        if isinstance(item_name_or_code, str):
                            # 아이템 이름으로 코드 찾기
                            item_code = self.item_db.get_item_code_by_name(item_name_or_code)
                            if item_code is not None:
                                load_data[data_index] = item_code
                        else:
                            # 직접 코드 설정
                            load_data[data_index] = int(item_name_or_code)
            
            # 기타 값들 설정
            if other_values:
                for index, value in other_values.items():
                    if 0 <= index < len(load_data) and index != 8:  # 체크섬 슬롯 제외
                        load_data[index] = int(value)
            
            # 세이브코드 생성
            return self.encode_savecode(load_data, player_name, use_play_type)
            
        except Exception as e:
            logger.error(f"아이템 기반 세이브코드 생성 중 오류: {e}")
            raise
    
    def copy_and_modify_savecode(self, original_code: str, player_name: str, 
                               modifications: dict = None, use_play_type: bool = True) -> str:
        """기존 세이브코드를 복사해서 일부 값만 수정"""
        try:
            # 기존 코드에서 디코더로 데이터 추출
            from decoder import SaveCodeDecoder
            decoder = SaveCodeDecoder()
            
            load_data = decoder.decode_savecode(original_code, use_play_type)
            
            # 수정사항 적용
            if modifications:
                for index, value in modifications.items():
                    if 0 <= index < len(load_data) and index != 8:  # 체크섬 슬롯 제외
                        load_data[index] = int(value)
            
            # 새로운 세이브코드 생성
            return self.encode_savecode(load_data, player_name, use_play_type)
            
        except Exception as e:
            logger.error(f"세이브코드 복사 및 수정 중 오류: {e}")
            raise


def create_custom_savecode(player_name: str, items: dict = None, other_values: dict = None) -> str:
    """사용자 정의 세이브코드 생성 편의 함수"""
    encoder = SaveCodeEncoder()
    return encoder.create_savecode_with_items(player_name, items, other_values)


def modify_existing_savecode(original_code: str, player_name: str, modifications: dict) -> str:
    """기존 세이브코드 수정 편의 함수"""
    encoder = SaveCodeEncoder()
    return encoder.copy_and_modify_savecode(original_code, player_name, modifications)