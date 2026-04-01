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
    
    def __init__(
        self,
        config_file: str = 'graduation_conditions.json',
        raid_items_file: str = 'raid_graduation_items.json'
    ):
        """
        졸업 조건 확인기 초기화
        
        Args:
            config_file: 졸업 조건 JSON 파일 경로
            raid_items_file: 레이드 졸업 아이템 JSON 파일 경로
        """
        self.conditions = self._load_conditions(config_file)
        self.raid_items = self._load_raid_items(raid_items_file)
        
    def _load_conditions(self, filename: str) -> dict:
        """졸업 조건 JSON 파일 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"{filename} 파일 로드 실패: {e}")
            return {}

    def _load_raid_items(self, filename: str) -> Dict[str, Dict[str, Set[int]]]:
        """레이드 졸업 아이템 JSON 파일 로드"""
        default_structure = {
            'apocalypse': {'any_of': set(), 'pairs': []},
            'raphael': {'any_of': set(), 'pairs': []},
            'gabriel': {'any_of': set(), 'pairs': []},
            'uriel': {'any_of': set(), 'pairs': []},
            'terminator': {'any_of': set(), 'pairs': []},
            'mikael': {'any_of': set(), 'pairs': []},
        }

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"{filename} 파일 로드 실패: {e}")
            return default_structure

        normalized: Dict[str, Dict[str, Set[int]]] = {}
        for raid_name, rule in default_structure.items():
            rule_data = data.get(raid_name, {}) if isinstance(data, dict) else {}

            any_of = rule_data.get('any_of', []) if isinstance(rule_data, dict) else []
            pairs = rule_data.get('pairs', []) if isinstance(rule_data, dict) else []

            normalized_any = {int(x) for x in any_of}
            normalized_pairs = [tuple(int(x) for x in pair) for pair in pairs if isinstance(pair, (list, tuple))]

            normalized[raid_name] = {
                'any_of': normalized_any,
                'pairs': normalized_pairs,
            }
            
            # combined_conditions 처리 (미카엘용)
            if 'combined_conditions' in rule_data:
                normalized[raid_name]['combined_conditions'] = rule_data['combined_conditions']

        return normalized
    
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
    
    def _check_raid_by_ids(self, item_ids: Set[int], raid: str) -> bool:
        """레이드별 아이템 규칙을 ID 기반으로 확인"""
        rules = self.raid_items.get(raid, {})
        if not rules:
            return False

        # all_of 규칙 (모든 아이템 필요) - 종결자용
        all_of = rules.get('all_of', [])
        if all_of:
            if all(item_id in item_ids for item_id in all_of):
                return True

        # combined_conditions 규칙 (여러 그룹에서 각각 하나씩) - 미카엘용
        combined_conditions = rules.get('combined_conditions', {})
        if combined_conditions:
            group1 = combined_conditions.get('group1_any', [])
            group2 = combined_conditions.get('group2_any', [])
            
            has_group1 = any(item_id in item_ids for item_id in group1)
            has_group2 = any(item_id in item_ids for item_id in group2)
            
            if has_group1 and has_group2:
                return True

        # 쌍(모두 필요) 규칙
        pairs = rules.get('pairs', [])
        if pairs:
            for pair in pairs:
                if all(pair_item in item_ids for pair_item in pair):
                    return True

        # 단일(하나라도) 규칙
        any_of = rules.get('any_of', set())
        if any_of and item_ids.intersection(any_of):
            return True

        return False

    def get_graduation_status(self, items_list: List[str] = None, item_ids: List[int] = None) -> str:
        """
        졸업 상태를 업그레이드 시스템을 고려해서 반환
        
        Args:
            items_list: 아이템 이름 목록 (기존 문자열 기반 체크용)
            item_ids: 아이템 코드(ID) 목록 (우선 사용)
            
        Returns:
            졸업 상태 ('raphael', 'gabriel', 'uriel', 'apocalypse', 'none')
        """
        # ID 기반 규칙이 우선이며, 실패 시 문자열 매칭으로 폴백
        if item_ids is not None:
            item_id_set = set(item_ids)
            # 우선순위: 미카엘 > 종결자 > 가브리엘 > 라파엘 > 우리엘 > 묵시록
            if self._check_raid_by_ids(item_id_set, 'mikael'):
                return 'mikael'
            if self._check_raid_by_ids(item_id_set, 'terminator'):
                return 'terminator'
            if self._check_raid_by_ids(item_id_set, 'gabriel'):
                return 'gabriel'
            if self._check_raid_by_ids(item_id_set, 'raphael'):
                return 'raphael'
            if self._check_raid_by_ids(item_id_set, 'uriel'):
                return 'uriel'
            if self._check_raid_by_ids(item_id_set, 'apocalypse'):
                return 'apocalypse'
            return 'none'

        if items_list is None:
            return 'none'

        # 문자열 기반 폴백 로직 (기존 방식 유지)
        if self.check_gabriel_graduation(items_list):
            return 'gabriel'
        elif self.check_raphael_graduation(items_list):
            return 'raphael'
        elif self.check_uriel_graduation(items_list):
            return 'uriel'
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
            'mikael': ('🌟', '미카엘 졸업'),
            'terminator': ('💀', '종결자 졸업'),
            'raphael': ('🕊️', '라파엘 졸업'),
            'gabriel': ('⚔️', '가브리엘 졸업'),
            'uriel': ('👼', '우리엘 졸업'),
            'apocalypse': ('😈', '묵시록 레이드 졸업'),
            'none': ('', '졸업 없음')
        }
        
        return status_map.get(status, ('', '알 수 없음'))