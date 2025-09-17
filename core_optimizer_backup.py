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
    
    def optimize_multiple_cores(self, core_types: List[str], gem_strings: List[str], target_points: List[int] = None, priorities: List[int] = None) -> Dict:
        """
        여러 코어에 잼을 최적으로 분배하는 함수
        
        Args:
            core_types: 코어 타입들의 리스트 (예: ["전설", "유물", "유물"])
            gem_strings: 잼 문자열들의 리스트
            target_points: 각 코어별 목표 질서 포인트 (선택사항)
            priorities: 각 코어별 우선순위 (1이 가장 높음, 선택사항)
            
        Returns:
            최적화 결과 딕셔너리
        """
        # 입력 검증
        if not core_types:
            return {"error": "코어 타입이 지정되지 않았습니다"}
        
        if not gem_strings:
            return {"error": "잼이 지정되지 않았습니다"}
        
        # 코어 데이터 생성
        cores = []
        for i, core_type in enumerate(core_types):
            core_data = self.get_core_data(core_type)
            if not core_data:
                return {"error": f"알 수 없는 코어 타입: {core_type}"}
            
            # 우선순위 추가 (기본값은 인덱스 + 1)
            priority = priorities[i] if priorities and i < len(priorities) else i + 1
            cores.append({
                "index": i, 
                "type": core_type, 
                "data": core_data,
                "priority": priority
            })
        
        # 잼 파싱
        gems = self.parse_gems(gem_strings)
        if not gems:
            return {"error": "유효한 잼이 없습니다"}
        
        # 가능한 모든 잼 분배 조합 시도
        best_allocation = None
        best_total_score = -1
        
        # 각 코어에 최대 4개씩 분배하는 모든 조합 시도
        best_result = self._find_best_allocation(cores, gems, target_points)
        
        if not best_result:
            return {"error": "유효한 잼 분배를 찾을 수 없습니다"}
        
        return best_result
    
    def _find_best_allocation(self, cores: List[Dict], gems: List[Gem], target_points: List[int] = None) -> Optional[Dict]:
        """
        최적의 잼 분배를 찾는 내부 함수
        """
        from itertools import combinations_with_replacement
        
        num_cores = len(cores)
        num_gems = len(gems)
        
        best_allocation = None
        best_total_score = -1
        
        # 효율적인 그리디 알고리즘 사용
        best_allocation = self._greedy_allocation(cores, gems, target_points)
        
        return best_allocation
    
    def _allocate_for_target(self, core_state: Dict, available_gems: List[Gem], target: int) -> List[Gem]:
        """
        목표 질서 포인트에 도달하기 위한 최적의 젬 조합 찾기
        """
        best_combination = None
        best_distance = float('inf')
        remaining_gems = list(available_gems)
        
        # 가능한 모든 젬 조합을 시도하여 목표에 가장 가까운 조합 찾기
        from itertools import combinations
        
        for combo_size in range(1, min(5, len(available_gems) + 1)):  # 최대 4개까지
            for gem_combo in combinations(available_gems, combo_size):
                total_willpower = sum(gem.willpower_cost for gem in gem_combo)
                total_order_points = sum(gem.order_points for gem in gem_combo)
                
                # 의지력 초과 체크
                if total_willpower > core_state["remaining_willpower"]:
                    continue
                
                # 목표와의 거리 계산
                distance = abs(total_order_points - target)
                
                # 목표에 정확히 도달하거나 더 가까운 조합 선택
                if distance < best_distance or (distance == 0 and best_distance > 0):
                    best_distance = distance
                    best_combination = gem_combo
                    
                    # 정확히 목표에 도달했으면 즉시 선택
                    if distance == 0:
                        break
            
            if best_distance == 0:  # 정확히 목표에 도달했으면 더 이상 찾지 않음
                break
        
        # 최적 조합을 코어에 할당
        if best_combination:
            for gem in best_combination:
                core_state["assigned_gems"].append(gem)
                core_state["remaining_willpower"] -= gem.willpower_cost
                core_state["total_order_points"] += gem.order_points
                remaining_gems.remove(gem)
        
        return remaining_gems
    
    def _build_result(self, core_states: List[Dict]) -> Dict:
        """
        최종 결과 구성
        """
        core_results = []
        total_score = 0
        total_gems_used = 0
        
        for i, core_state in enumerate(core_states):
            core_data = core_state["core_info"]["data"]
            assigned_gems = core_state["assigned_gems"]
            
            if assigned_gems:
                total_willpower_used = sum(gem.willpower_cost for gem in assigned_gems)
                total_order_points = sum(gem.order_points for gem in assigned_gems)
                activated_abilities = core_data.get_activated_abilities(total_order_points)
                score = len(activated_abilities) * 1000 + total_order_points
                total_gems_used += len(assigned_gems)
            else:
                total_willpower_used = 0
                total_order_points = 0
                activated_abilities = []
                score = 0
            
            total_score += score
            
            core_results.append({
                "core_type": core_state["core_info"]["type"],
                "core_index": core_state["original_index"],  # 원본 인덱스 사용
                "gems": [str(gem) for gem in assigned_gems],
                "gem_count": len(assigned_gems),
                "total_willpower_used": total_willpower_used,
                "remaining_willpower": core_data.willpower - total_willpower_used,
                "total_order_points": total_order_points,
                "activated_abilities": activated_abilities,
                "all_abilities": core_data.ability_points,
                "score": score
            })
        
        # 원본 순서로 정렬
        core_results.sort(key=lambda x: x["core_index"])
        
        return {
            "cores": core_results,
            "total_score": total_score,
            "total_gems_used": total_gems_used,
            "total_available_gems": len(gems)
        }
    
    def _generate_allocations(self, num_gems: int, num_cores: int, max_gems_per_core: int = 4):
                new_order_points = core_state["total_order_points"] + gem.order_points
                new_abilities = len(core_state["core_info"]["data"].get_activated_abilities(new_order_points))
                
                # 점수 향상 계산 (새로 활성화되는 능력 수 + 질서포인트)
                score_improvement = (new_abilities - current_abilities) * 1000 + gem.order_points
                
                # 목표 질서 포인트가 설정된 경우 목표 달성 우선순위 적용
                if target_points and original_index < len(target_points):
                    target = target_points[original_index]
                    if target > 0:  # 목표가 설정된 경우에만
                        current_distance = abs(core_state["total_order_points"] - target)
                        new_distance = abs(new_order_points - target)
                        
                        # 목표에 정확히 도달하면 최고 우선순위
                        if new_order_points == target:
                            score_improvement += 10000
                        # 목표에 가까워지면 큰 보너스
                        elif new_distance < current_distance:
                            score_improvement += 5000 - new_distance * 100
                        # 목표에서 멀어지면 큰 페널티
                        elif new_distance > current_distance:
                            score_improvement -= 3000
                        
                        # 목표를 초과하는 경우 큰 페널티
                        if new_order_points > target:
                            excess = new_order_points - target
                            score_improvement -= excess * 500
                else:
                    # 목표가 없는 코어는 우선순위만 적용
                    priority = core_state["core_info"]["priority"]
                    priority_bonus = (11 - priority) * 50  # 목표 있는 코어보다 낮은 보너스
                    score_improvement += priority_bonus
                
                if score_improvement > best_score_improvement:
                    best_score_improvement = score_improvement
                    best_core = i
            
            # 가장 좋은 코어에 잼 할당
            if best_core is not None:
                core_states[best_core]["assigned_gems"].append(gem)
                core_states[best_core]["remaining_willpower"] -= gem.willpower_cost
                core_states[best_core]["total_order_points"] += gem.order_points
        
        # 결과 구성
        core_results = []
        total_score = 0
        total_gems_used = 0
        
        for i, core_state in enumerate(core_states):
            core_data = core_state["core_info"]["data"]
            assigned_gems = core_state["assigned_gems"]
            
            if assigned_gems:
                total_willpower_used = sum(gem.willpower_cost for gem in assigned_gems)
                total_order_points = sum(gem.order_points for gem in assigned_gems)
                activated_abilities = core_data.get_activated_abilities(total_order_points)
                score = len(activated_abilities) * 1000 + total_order_points
                total_gems_used += len(assigned_gems)
            else:
                total_willpower_used = 0
                total_order_points = 0
                activated_abilities = []
                score = 0
            
            total_score += score
            
            core_results.append({
                "core_type": core_state["core_info"]["type"],
                "core_index": i,
                "gems": [str(gem) for gem in assigned_gems],
                "gem_count": len(assigned_gems),
                "total_willpower_used": total_willpower_used,
                "remaining_willpower": core_data.willpower - total_willpower_used,
                "total_order_points": total_order_points,
                "activated_abilities": activated_abilities,
                "all_abilities": core_data.ability_points,
                "score": score
            })
        
        return {
            "cores": core_results,
            "total_score": total_score,
            "total_gems_used": total_gems_used,
            "total_available_gems": len(gems)
        }
    
    def _generate_allocations(self, num_gems: int, num_cores: int, max_gems_per_core: int = 4):
        """
        각 잼을 코어에 할당하는 모든 가능한 조합 생성
        각 코어당 최대 4개까지만 할당
        """
        from itertools import product

        # 각 잼이 들어갈 수 있는 코어 옵션 (0~num_cores-1, 또는 -1은 사용하지 않음)
        core_options = list(range(num_cores)) + [-1]  # -1은 해당 잼을 사용하지 않음
        
        # 모든 가능한 할당 조합
        for allocation in product(core_options, repeat=num_gems):
            # 각 코어당 4개 제한 검사
            core_counts = [0] * num_cores
            for core_idx in allocation:
                if core_idx >= 0:
                    core_counts[core_idx] += 1
            
            # 4개 제한 체크
            if all(count <= max_gems_per_core for count in core_counts):
                yield allocation
    
    def _evaluate_allocation(self, cores: List[Dict], gems: List[Gem], allocation: tuple) -> Optional[Dict]:
        """
        특정 잼 할당에 대한 결과 평가
        """
        core_results = []
        total_score = 0
        total_gems_used = 0
        
        # 각 코어별로 할당된 잼들 정리
        for core_info in cores:
            core_idx = core_info["index"]
            core_data = core_info["data"]
            
            # 이 코어에 할당된 잼들 찾기
            assigned_gems = []
            for gem_idx, assigned_core in enumerate(allocation):
                if assigned_core == core_idx:
                    assigned_gems.append(gems[gem_idx])
            
            # 이 코어에 잼이 할당되지 않았으면 스킵
            if not assigned_gems:
                core_results.append({
                    "core_type": core_info["type"],
                    "core_index": core_idx,
                    "gems": [],
                    "gem_count": 0,
                    "total_willpower_used": 0,
                    "remaining_willpower": core_data.willpower,
                    "total_order_points": 0,
                    "activated_abilities": [],
                    "all_abilities": core_data.ability_points,
                    "score": 0
                })
                continue
            
            # 의지력 체크
            total_willpower_used = sum(gem.willpower_cost for gem in assigned_gems)
            if total_willpower_used > core_data.willpower:
                return None  # 의지력 초과시 무효한 할당
            
            # 질서포인트 및 능력 계산
            total_order_points = sum(gem.order_points for gem in assigned_gems)
            activated_abilities = core_data.get_activated_abilities(total_order_points)
            
            # 점수 계산 (활성화된 능력 개수 우선, 그 다음 질서포인트)
            score = len(activated_abilities) * 1000 + total_order_points
            total_score += score
            total_gems_used += len(assigned_gems)
            
            core_results.append({
                "core_type": core_info["type"],
                "core_index": core_idx,
                "gems": [str(gem) for gem in assigned_gems],
                "gem_count": len(assigned_gems),
                "total_willpower_used": total_willpower_used,
                "remaining_willpower": core_data.willpower - total_willpower_used,
                "total_order_points": total_order_points,
                "activated_abilities": activated_abilities,
                "all_abilities": core_data.ability_points,
                "score": score
            })
        
        return {
            "cores": core_results,
            "total_score": total_score,
            "total_gems_used": total_gems_used,
            "total_available_gems": len(gems)
        }