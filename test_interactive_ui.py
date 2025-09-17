#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
인터랙티브 젬 UI 테스트
"""

def test_interactive_gem_ui():
    """인터랙티브 젬 UI 컴포넌트 테스트"""
    
    print("=== 인터랙티브 젬 UI 테스트 ===")
    
    # 젬 파싱 테스트
    def parse_gems(gems_text):
        """젬 텍스트 파싱"""
        gems = gems_text.split()
        valid_gems = []
        for gem in gems:
            if len(gem) == 2 and gem.isdigit():
                valid_gems.append(gem)
            else:
                return None, f"잘못된 잼 형식: '{gem}'"
        return valid_gems, None
    
    # 파싱 테스트 케이스들
    test_cases = [
        "25 35 45",
        "25 35 45 26 36 16",
        "25 35 abc",  # 오류 케이스
        "25 35 456",  # 오류 케이스 (3자리)
        ""
    ]
    
    print("젬 파싱 테스트:")
    for case in test_cases:
        valid_gems, error = parse_gems(case)
        if error:
            print(f"  '{case}' -> ❌ {error}")
        else:
            print(f"  '{case}' -> ✅ {valid_gems}")
    
    print()
    
    # UI 색상 테스트
    def get_core_color(core_type):
        """코어 타입별 색상"""
        colors = {
            "전설": 0xf39c12,  # 주황색
            "유물": 0x9b59b6,  # 보라색
            "고대": 0xe74c3c   # 빨간색
        }
        return colors.get(core_type, 0x95a5a6)
    
    print("코어 색상 테스트:")
    for core_type in ["전설", "유물", "고대"]:
        color = get_core_color(core_type)
        print(f"  {core_type}: 0x{color:06x}")
    
    print()
    
    # 진행바 테스트
    def create_progress_bar(current, maximum, length=15):
        """진행바 생성"""
        if maximum == 0:
            return "▱" * length
        
        filled = int((current / maximum) * length)
        bar = "▰" * filled + "▱" * (length - filled)
        return bar
    
    print("진행바 테스트:")
    test_values = [
        (5, 11),   # 전설 코어
        (10, 15),  # 유물 코어
        (17, 17),  # 고대 코어 (풀)
        (0, 11)    # 빈 상태
    ]
    
    for current, maximum in test_values:
        bar = create_progress_bar(current, maximum)
        percentage = (current / maximum * 100) if maximum > 0 else 0
        print(f"  {current}/{maximum}: {bar} ({percentage:.1f}%)")
    
    print()
    
    # 실제 최적화 결과 시뮬레이션
    print("=== 최적화 결과 시뮬레이션 ===")
    
    from core_optimizer import CoreOptimizer
    
    core_optimizer = CoreOptimizer()
    
    # 단일 코어 테스트
    gems = ["25", "35", "45"]
    result = core_optimizer.find_optimal_combination("전설", gems)
    
    if "error" not in result:
        print(f"단일 코어 결과:")
        print(f"  코어: {result['core_type']}")
        print(f"  잼: {result['gems']}")
        print(f"  의지력: {result['total_willpower_used']}/{result['core_willpower']}")
        print(f"  질서포인트: {result['total_order_points']}")
        print(f"  활성화된 능력: {result['activated_abilities']}")
        
        # UI 요소들 적용
        willpower_bar = create_progress_bar(result['total_willpower_used'], result['core_willpower'])
        print(f"  진행바: {willpower_bar}")
        
        efficiency = len(result['activated_abilities']) / len(result['all_abilities']) * 100
        print(f"  효율성: {efficiency:.1f}%")
    
    print()
    
    # 멀티 코어 테스트
    gems = ["25", "35", "45", "26"]
    result = core_optimizer.optimize_multiple_cores(["전설", "유물"], gems)
    
    if "error" not in result:
        print(f"멀티 코어 결과:")
        print(f"  사용된 잼: {result['total_gems_used']}/{result['total_available_gems']}")
        
        gem_usage_bar = create_progress_bar(result['total_gems_used'], result['total_available_gems'])
        usage_percentage = (result['total_gems_used'] / result['total_available_gems'] * 100) if result['total_available_gems'] > 0 else 0
        print(f"  잼 사용률: {gem_usage_bar} ({usage_percentage:.1f}%)")
        
        for i, core_result in enumerate(result['cores']):
            if core_result['gem_count'] > 0:
                print(f"  {core_result['core_type']} #{i+1}: {core_result['gems']} -> 질서{core_result['total_order_points']}")
            else:
                print(f"  {core_result['core_type']} #{i+1}: 잼 없음")

if __name__ == "__main__":
    test_interactive_gem_ui()