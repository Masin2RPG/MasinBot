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
    
    def _calculate_checksum(self, load_data: List[int], player_name: str) -> int:
        """체크섬 계산 (원본 게임과 동일하게)"""
        checksum = 0
        save_size = len(self.config.UDG_SAVE_VALUE_LENGTH) - 1  # 인덱스 0은 사용하지 않으므로 -1
        
        # 1-based 인덱스로 계산, i 가중치 사용 (원본 게임과 동일)
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
    
    def encode_savecode(self, load_data: List[int], player_name: str, use_play_type: bool = True) -> str:
        """로드 데이터를 세이브코드로 인코딩"""
        try:
            # 로드 데이터 복사 (체크섬 계산을 위해)
            encoded_data = load_data.copy()
            
            # 로드 데이터 길이 검증 및 보정
            if len(encoded_data) < len(self.config.UDG_SAVE_VALUE_LENGTH):
                # 부족한 데이터는 0으로 채움
                while len(encoded_data) < len(self.config.UDG_SAVE_VALUE_LENGTH):
                    encoded_data.append(0)
            elif len(encoded_data) > len(self.config.UDG_SAVE_VALUE_LENGTH):
                # 초과한 데이터는 잘라냄
                encoded_data = encoded_data[:len(self.config.UDG_SAVE_VALUE_LENGTH)]
            
            # 체크섬 계산 및 설정
            checksum = self._calculate_checksum(encoded_data, player_name)
            encoded_data[9] = checksum  # 10번째 슬롯(인덱스 9)에 체크섬 저장 (원본 게임과 동일)
            
            # 로드 데이터를 문자열로 변환 (인덱스 1부터 시작, 원본 게임과 동일)
            numeric_string = ""
            save_size = len(self.config.UDG_SAVE_VALUE_LENGTH) - 1  # 인덱스 0은 사용하지 않으므로 -1
            for i in range(1, save_size + 1):  # 1부터 15까지
                value = encoded_data[i]
                length = self.config.UDG_SAVE_VALUE_LENGTH[i]
                formatted_value = f"{value:0{length}d}"
                
                # 길이 초과 시 잘라냄
                if len(formatted_value) > length:
                    formatted_value = formatted_value[-length:]
                
                numeric_string += formatted_value
            
            # 숫자 문자열을 3자리씩 나누어 코드로 변환
            code_parts = []
            for i in range(0, len(numeric_string), 3):
                chunk = numeric_string[i:i+3]
                if len(chunk) < 3:
                    chunk = chunk.ljust(3, '0')  # 부족한 부분은 0으로 채움
                
                value = int(chunk)
                if value >= 36 * 36:
                    # 1296 이상인 경우 모듈로 연산으로 범위 내로 맞춤
                    value = value % (36 * 36)
                
                code_pair = self._convert_int_to_code(value, use_play_type)
                code_parts.append(code_pair)
            
            # 40글자가 되도록 패딩 추가 (게임 호환성을 위해)
            full_code = "".join(code_parts)
            while len(full_code) < 40:
                # 0 값을 추가 (11 = 0)
                full_code += "11"
            
            # 38글자로 자르기 (올바른 게임 형식)
            if len(full_code) > 38:
                full_code = full_code[:38]
            
            # 최종 코드 생성 (5글자씩 하이픈으로 구분, 마지막은 3글자)
            # 패턴: 5-5-5-5-5-5-5-3 = 총 38글자
            formatted_parts = []
            for i in range(0, 35, 5):  # 0, 5, 10, 15, 20, 25, 30
                formatted_parts.append(full_code[i:i+5])
            # 마지막 3글자 추가
            if len(full_code) > 35:
                formatted_parts.append(full_code[35:38])
            
            formatted_code = "-".join(formatted_parts)
            
            return formatted_code
            
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