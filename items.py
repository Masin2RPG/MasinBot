"""
아이템 데이터베이스 모듈
JSON 파일에서 아이템 ID와 이름 매핑을 로드
"""

import json
import os
from typing import Dict


class ItemDatabase:
    """아이템 데이터베이스 클래스"""
    
    def __init__(self, json_file_path: str = "items_list.json"):
        self.json_file_path = json_file_path
        self._items: Dict[int, str] = {}
        self._load_items_from_json()
    
    def _load_items_from_json(self):
        """JSON 파일에서 아이템 데이터 로드"""
        try:
            if os.path.exists(self.json_file_path):
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    items_json = json.load(f)
                    # 문자열 키를 정수로 변환
                    self._items = {int(k): v for k, v in items_json.items()}
                print(f"아이템 {len(self._items)}개를 {self.json_file_path}에서 로드했습니다.")
            else:
                print(f"경고: {self.json_file_path} 파일을 찾을 수 없습니다. 기본 아이템만 사용합니다.")
                self._load_default_items()
        except Exception as e:
            print(f"오류: JSON 파일 로드 실패 - {e}")
            print("기본 아이템 데이터를 사용합니다.")
            self._load_default_items()
    
    def _load_default_items(self):
        """기본 아이템 데이터 (JSON 파일 로드 실패시 백업용)"""
        self._items = {
            0: "없음",
            1: "예언의 손길",
            2: "사무엘의 영혼",
            3: "사무엘의 의식 예복",
            4: "사무엘의 고귀한 지팡이",
            5: "패닉소울"
            # 기본 몇 개만 포함 (전체는 JSON 파일에서 로드)
        }

    def get_item_name(self, item_id: int) -> str:
        """아이템 ID로 아이템 이름 조회"""
        return self._items.get(item_id, f"알 수 없는 아이템({item_id})")
    
    def get_item_code_by_name(self, item_name: str) -> int:
        """아이템 이름으로 아이템 코드(ID) 조회"""
        for item_id, name in self._items.items():
            if name == item_name:
                return item_id
        return None
    
    def get_all_items(self) -> Dict[int, str]:
        """모든 아이템 딕셔너리 반환"""
        return self._items.copy()
    
    def save_items_to_json(self) -> bool:
        """현재 아이템 데이터를 JSON 파일에 저장"""
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                # 정수 키를 문자열로 변환하여 JSON 저장
                items_json = {str(k): v for k, v in self._items.items()}
                json.dump(items_json, f, ensure_ascii=False, indent=2)
            print(f"아이템 {len(self._items)}개가 {self.json_file_path}에 저장되었습니다.")
            return True
        except Exception as e:
            print(f"오류: JSON 파일 저장 실패 - {e}")
            return False
    
    def add_item(self, item_id: int, item_name: str, save_to_file: bool = True):
        """새 아이템 추가"""
        self._items[item_id] = item_name
        if save_to_file:
            self.save_items_to_json()
        print(f"아이템 추가됨: {item_id} - {item_name}")
    
    def get_item_count(self) -> int:
        """총 아이템 개수 반환"""
        return len(self._items)
