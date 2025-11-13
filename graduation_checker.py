"""
졸업 조건 관리 모듈
JSON 기반으로 졸업 조건을 관리하고 확인하는 기능을 제공
"""

import json
import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class GraduationChecker:
    """졸업 조건 확인 클래스"""
    
    def __init__(self, config_file: str = 'graduation_conditions.json'):
        """
        졸업 조건 확인기 초기화
        
        Args:
            config_file: 졸업 조건 JSON 파일 경로
        """
        self.conditions = self._load_conditions(config_file)
        
    def _load_conditions(self, filename: str) -> dict:
        """졸업 조건 JSON 파일 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"{filename} 파일 로드 실패: {e}")
            return {}
    
    def check_uriel_graduation(self, items_list: List[str]) -> bool:
        """
        우리엘 졸업 조건 확인
        
        Args:
            items_list: 아이템 목록
            
        Returns:
            우리엘 졸업 여부
        """
        if 'uriel' not in self.conditions['graduation_conditions']:
            return False
            
        uriel_config = self.conditions['graduation_conditions']['uriel']
        uriel_items = set()
        
        # 아이템 매칭
        for item in items_list:
            for item_id, item_name in uriel_config['items'].items():
                if item_name in item:
                    uriel_items.add(int(item_id))
        
        # 쌍 조건 확인
        for pair in uriel_config['pairs']:
            if all(item_id in uriel_items for item_id in pair):
                return True
                
        return False
    
    def check_raphael_graduation(self, items_list: List[str]) -> bool:
        """
        라파엘 졸업 조건 확인 (업그레이드된 영혼 포함)
        
        Args:
            items_list: 아이템 목록
            
        Returns:
            라파엘 졸업 여부
        """
        if 'raphael' not in self.conditions['graduation_conditions']:
            return False
            
        raphael_config = self.conditions['graduation_conditions']['raphael']
        
        # 영혼 업그레이드 매핑: 라파엘 → 가브리엘 → 우리엘
        soul_upgrades = {
            '1': ['라파엘의 강인한 영혼', '가브리엘의 강인한 영혼', '우리엘의 강인한 영혼'],
            '2': ['라파엘의 강력한 영혼', '가브리엘의 강력한 영혼', '우리엘의 강력한 영혼'], 
            '3': ['라파엘의 전능한 영혼', '가브리엘의 전능한 영혼', '우리엘의 전능한 영혼']
        }
        
        # 각 레벨별로 확인
        for level, level_config in raphael_config['levels'].items():
            companions = level_config['companions']
            soul_variants = soul_upgrades.get(level, [])
            
            # 해당 레벨의 영혼(원본 또는 업그레이드된 버전) 중 하나라도 있는지 확인
            has_soul = any(
                any(soul_variant in item for item in items_list) 
                for soul_variant in soul_variants
            )
            
            if has_soul:
                # 동반 아이템 중 하나라도 있는지 확인
                has_companion = any(
                    any(companion in item for item in items_list)
                    for companion in companions
                )
                
                if has_companion:
                    return True
                    
        return False
    
    def check_gabriel_graduation(self, items_list: List[str]) -> bool:
        """
        가브리엘 졸업 조건 확인 (업그레이드된 영혼 포함)
        
        Args:
            items_list: 아이템 목록
            
        Returns:
            가브리엘 졸업 여부
        """
        if 'gabriel' not in self.conditions['graduation_conditions']:
            return False
            
        gabriel_config = self.conditions['graduation_conditions']['gabriel']
        
        # 영혼 업그레이드 매핑: 가브리엘 → 우리엘
        soul_upgrades = {
            '1': ['가브리엘의 강인한 영혼', '우리엘의 강인한 영혼'],
            '2': ['가브리엘의 강력한 영혼', '우리엘의 강력한 영혼'],
            '3': ['가브리엘의 전능한 영혼', '우리엘의 전능한 영혼']
        }
        
        # 각 레벨별로 확인
        for level, level_config in gabriel_config['levels'].items():
            companions = level_config['companions']
            soul_variants = soul_upgrades.get(level, [])
            
            # 해당 레벨의 영혼(원본 또는 업그레이드된 버전) 중 하나라도 있는지 확인
            has_soul = any(
                any(soul_variant in item for item in items_list)
                for soul_variant in soul_variants
            )
            
            if has_soul:
                # 동반 아이템 중 하나라도 있는지 확인
                has_companion = any(
                    any(companion in item for item in items_list)
                    for companion in companions
                )
                
                if has_companion:
                    return True
                    
        return False
    
    def check_apocalypse_graduation(self, items_list: List[str]) -> bool:
        """
        묵시록 졸업 조건 확인
        
        Args:
            items_list: 아이템 목록
            
        Returns:
            묵시록 졸업 여부
        """
        if 'apocalypse' not in self.conditions['graduation_conditions']:
            return False
            
        apocalypse_config = self.conditions['graduation_conditions']['apocalypse']
        keyword = apocalypse_config['keyword']
        
        return any(keyword in item for item in items_list)
    
    def get_graduation_status(self, items_list: List[str]) -> str:
        """
        졸업 상태를 업그레이드 시스템을 고려해서 반환
        
        Args:
            items_list: 아이템 목록
            
        Returns:
            졸업 상태 ('raphael', 'gabriel', 'uriel', 'apocalypse', 'none')
        """
        # 업그레이드 시스템: 더 높은 등급 졸업을 우선 확인
        # 우선순위: 가브리엘 > 라파엘 > 우리엘 > 묵시록
        
        # 가브리엘 졸업 확인 (우리엘 영혼이 있어도 가브리엘 조건이면 가브리엘)
        if self.check_gabriel_graduation(items_list):
            return 'gabriel'
            
        # 라파엘 졸업 확인 (가브리엘, 우리엘 영혼이 있어도 라파엘 조건이면 라파엘)
        elif self.check_raphael_graduation(items_list):
            return 'raphael'
            
        # 우리엘 졸업 확인
        elif self.check_uriel_graduation(items_list):
            return 'uriel'
            
        # 묵시록 졸업 확인 (죄: 아이템만 있는 경우)
        elif self.check_apocalypse_graduation(items_list):
            return 'apocalypse'
        else:
            return 'none'
    
    def get_graduation_emoji_and_name(self, status: str) -> tuple:
        """
        졸업 상태에 따른 이모지와 이름 반환
        
        Args:
            status: 졸업 상태
            
        Returns:
            (이모지, 이름) 튜플
        """
        status_map = {
            'raphael': ('🕊️', '라파엘 졸업'),
            'gabriel': ('⚔️', '가브리엘 졸업'),
            'uriel': ('👼', '우리엘 졸업'),
            'apocalypse': ('😈', '묵시록 레이드 졸업'),
            'none': ('', '졸업 없음')
        }
        
        return status_map.get(status, ('', '알 수 없음'))