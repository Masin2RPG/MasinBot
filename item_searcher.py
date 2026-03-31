"""
아이템 검색 모듈
아이템 이름으로 값을 검색하는 기능을 제공
"""

import json
import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class ItemSearcher:
    """아이템 검색 클래스"""
    
    def __init__(self, items_file: str = 'items_full.json'):
        """
        아이템 검색기 초기화
        
        Args:
            items_file: 아이템 정보 JSON 파일 경로 ({아이템이름: rawcode} 형식)
        """
        self.items_data = self._load_json(items_file)
        
    def _load_json(self, filename: str) -> dict:
        """JSON 파일 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"{filename} 파일 로드 실패: {e}")
            return {}
    
    def _clean_item_name(self, text: str) -> str:
        """
        아이템 이름에서 색상 코드 등을 제거
        
        Args:
            text: 정리할 텍스트
            
        Returns:
            정리된 텍스트
        """
        # 색상 코드 제거 (|CFF....|R, |r 등)
        cleaned = re.sub(r'\|[Cc][Ff][Ff][0-9A-Fa-f]{6}', '', text)
        cleaned = re.sub(r'\|[Rr]', '', cleaned)
        cleaned = re.sub(r'\|[a-zA-Z0-9]+', '', cleaned)
        # 특수문자 정리
        cleaned = re.sub(r'[\r\n\t]', ' ', cleaned)
        return cleaned.strip()
    
    def find_item_value(self, item_name: str) -> Optional[str]:
        """
        아이템 이름으로 첫 번째 매칭되는 값을 반환
        
        Args:
            item_name: 검색할 아이템 이름
            
        Returns:
            매칭된 첫 번째 아이템의 값 (없으면 None)
        """
        matching_items = self.find_matching_items(item_name)
        if matching_items:
            return matching_items[0][2]  # 첫 번째 아이템의 값 반환
        return None
    
    def find_matching_items(self, item_name: str) -> List[Tuple[str, str, str]]:
        """
        아이템 이름으로 매칭되는 모든 아이템 찾기
        
        Args:
            item_name: 검색할 아이템 이름
            
        Returns:
            (아이템명, 아이템명, rawcode) 튜플의 리스트
        """
        matching_items = []
        search_name = item_name.lower().strip()
        
        for item_name_in_db, rawcode in self.items_data.items():
            clean_name = self._clean_item_name(item_name_in_db).lower()
            if search_name in clean_name or clean_name in search_name:
                matching_items.append((item_name_in_db, item_name_in_db, str(rawcode)))
        
        return matching_items
    
    def search_items_by_keyword(self, keyword: str, max_results: int = 10) -> List[Tuple[str, str, str]]:
        """
        키워드로 아이템 검색 (더 넓은 범위 검색)
        
        Args:
            keyword: 검색 키워드
            max_results: 최대 결과 개수
            
        Returns:
            (아이템명, 아이템명, rawcode) 튜플의 리스트
        """
        matching_items = []
        search_keyword = keyword.lower().strip()
        
        for item_name, rawcode in self.items_data.items():
            if len(matching_items) >= max_results:
                break
                
            clean_name = self._clean_item_name(item_name).lower()
            if search_keyword in clean_name:
                matching_items.append((item_name, item_name, str(rawcode)))
        
        return matching_items
    
    def get_stats(self) -> dict:
        """
        로드된 데이터 통계 반환
        
        Returns:
            통계 정보 딕셔너리
        """
        return {
            'total_items': len(self.items_data),
            'total_rowcodes': len(self.items_data),
            'matched_items': len(self.items_data)
        }
