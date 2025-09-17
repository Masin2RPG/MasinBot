"""
코어 최적화 모듈
코어에 잼을 조합하여 최적의 질서포인트를 얻는 기능을 제공
"""

import logging
from itertools import combinations
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CoreType:
    """코어 타입 정의"""
    LEGEND = "전설"
    RELIC = "유물" 
    ANCIENT = "고대"


class CoreData:
    """코어 데이터 클래스"""
    
    def __init__(self, core_type: str, willpower: int, ability_points: List[int]):
        self.core_type = core_type
        self.willpower = willpower  # 의지력
        self.ability_points = sorted(ability_points)  # 질서포인트 임계값들 (정렬)
        
    def get_activated_abilities(self, total_order_points: int) -> List[int]:
        """총 질서포인트로 활성화되는 능력들 반환"""
        return [point for point in self.ability_points if point <= total_order_points]


class Gem:
    """잼 클래스"""
    
    def __init__(self, willpower_cost: int, order_points: int):
        self.willpower_cost = willpower_cost  # 의지력 소모
        self.order_points = order_points     # 질서포인트 제공
        
    def __str__(self):
        return f"{self.willpower_cost}{self.order_points}"
    
    def __repr__(self):
        return f"Gem({self.willpower_cost}, {self.order_points})"


class CoreOptimizer:
    """코어 최적화 클래스"""
    
    # 코어별 기본 데이터 (의지력, 능력 포인트들)
    CORE_CONFIGS = {
        CoreType.LEGEND: {
            "willpower": 11,
            "ability_points": [10, 14]
        },
        CoreType.RELIC: {
            "willpower": 15,
            "ability_points": [10, 14, 17, 18, 19, 20]
        },
        CoreType.ANCIENT: {
            "willpower": 17,
            "ability_points": [10, 14, 17, 18, 19, 20]
        }
    }
    
    def __init__(self):
        pass
    
    def parse_gems(self, gem_strings: List[str]) -> List[Gem]:
        """잼 문자열들을 Gem 객체로 파싱"""
        gems = []
        for gem_str in gem_strings:
            try:
                # "25" -> willpower=2, order_points=5
                if len(gem_str) >= 2:
                    willpower = int(gem_str[:-1])  # 마지막 자리 제외
                    order_points = int(gem_str[-1])  # 마지막 자리
                    gems.append(Gem(willpower, order_points))
                else:
                    logger.warning(f"잘못된 잼 형식: {gem_str}")
            except ValueError:
                logger.warning(f"잼 파싱 실패: {gem_str}")
        
        return gems
    
    def get_core_data(self, core_type: str) -> Optional[CoreData]:
        """코어 타입으로 CoreData 객체 생성"""
        if core_type not in self.CORE_CONFIGS:
            return None
            
        config = self.CORE_CONFIGS[core_type]
        return CoreData(core_type, config["willpower"], config["ability_points"])
    
    def can_equip_gems(self, core: CoreData, gems: List[Gem]) -> bool:
        """코어에 잼들을 장착할 수 있는지 확인"""
        total_willpower_cost = sum(gem.willpower_cost for gem in gems)
        return total_willpower_cost <= core.willpower
    
    def calculate_total_order_points(self, gems: List[Gem]) -> int:
        """잼들의 총 질서포인트 계산"""
        return sum(gem.order_points for gem in gems)
    
    def find_optimal_combination(self, core_type: str, gem_strings: List[str]) -> Dict:
        """최적의 잼 조합 찾기"""
        core = self.get_core_data(core_type)
        if not core:
            return {"error": f"알 수 없는 코어 타입: {core_type}"}
        
        gems = self.parse_gems(gem_strings)
        if not gems:
            return {"error": "유효한 잼이 없습니다"}
        
        best_combination = None
        best_score = -1
        best_activated_abilities = []
        
        # 모든 가능한 잼 조합 시도 (최대 4개까지)
        max_gems = min(4, len(gems))
        
        for num_gems in range(1, max_gems + 1):
            for gem_combination in combinations(gems, num_gems):
                if self.can_equip_gems(core, gem_combination):
                    total_order_points = self.calculate_total_order_points(gem_combination)
                    activated_abilities = core.get_activated_abilities(total_order_points)
                    
                    # 점수 계산: 활성화된 능력의 개수와 총 질서포인트
                    score = len(activated_abilities) * 1000 + total_order_points
                    
                    if score > best_score:
                        best_score = score
                        best_combination = gem_combination
                        best_activated_abilities = activated_abilities
        
        if best_combination is None:
            return {"error": "장착 가능한 잼 조합이 없습니다"}
        
        # 결과 구성
        total_willpower_used = sum(gem.willpower_cost for gem in best_combination)
        remaining_willpower = core.willpower - total_willpower_used
        total_order_points = self.calculate_total_order_points(best_combination)
        
        return {
            "core_type": core_type,
            "core_willpower": core.willpower,
            "gems": [str(gem) for gem in best_combination],
            "total_willpower_used": total_willpower_used,
            "remaining_willpower": remaining_willpower,
            "total_order_points": total_order_points,
            "activated_abilities": best_activated_abilities,
            "all_abilities": core.ability_points,
            "gem_count": len(best_combination)
        }
    
    def get_all_combinations_analysis(self, core_type: str, gem_strings: List[str]) -> List[Dict]:
        """모든 가능한 조합 분석 (디버깅용)"""
        core = self.get_core_data(core_type)
        if not core:
            return []
        
        gems = self.parse_gems(gem_strings)
        if not gems:
            return []
        
        results = []
        max_gems = min(4, len(gems))
        
        for num_gems in range(1, max_gems + 1):
            for gem_combination in combinations(gems, num_gems):
                total_willpower_used = sum(gem.willpower_cost for gem in gem_combination)
                can_equip = total_willpower_used <= core.willpower
                
                if can_equip:
                    total_order_points = self.calculate_total_order_points(gem_combination)
                    activated_abilities = core.get_activated_abilities(total_order_points)
                    
                    results.append({
                        "gems": [str(gem) for gem in gem_combination],
                        "willpower_used": total_willpower_used,
                        "remaining_willpower": core.willpower - total_willpower_used,
                        "order_points": total_order_points,
                        "activated_abilities": activated_abilities,
                        "score": len(activated_abilities) * 1000 + total_order_points
                    })
        
        # 점수순으로 정렬
        results.sort(key=lambda x: x["score"], reverse=True)
        return results