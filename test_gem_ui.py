#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
/젬 명령어 테스트 (UI 스타일)
"""

def test_gem_ui_functions():
    """젬 UI 기능 테스트"""
    
    # UI 헬퍼 함수들 테스트
    def _create_progress_bar(current, maximum, length=20):
        """진행바 생성"""
        if maximum == 0:
            return "▱" * length
        
        filled = int((current / maximum) * length)
        bar = "▰" * filled + "▱" * (length - filled)
        return bar
    
    def _create_ability_visual(all_abilities, activated_abilities):
        """능력 활성화 시각적 표시"""
        visual = "```\n"
        for ability in all_abilities:
            if ability in activated_abilities:
                visual += f"🟢 {ability}  "
            else:
                visual += f"⚪ {ability}  "
        visual += "\n```"
        return visual
    
    def _get_core_color(core_type):
        """코어 타입별 색상"""
        colors = {
            "전설": 0xf39c12,  # 주황색
            "유물": 0x9b59b6,  # 보라색
            "고대": 0xe74c3c   # 빨간색
        }
        return colors.get(core_type, 0x95a5a6)
    
    print("=== UI 헬퍼 함수 테스트 ===")
    
    # 진행바 테스트
    print("진행바 테스트:")
    print(f"50%: {_create_progress_bar(10, 20)}")
    print(f"75%: {_create_progress_bar(15, 20)}")
    print(f"100%: {_create_progress_bar(20, 20)}")
    print()
    
    # 능력 시각화 테스트
    print("능력 시각화 테스트:")
    all_abilities = [10, 14, 17, 18, 19, 20]
    activated_abilities = [10, 14, 17]
    print(_create_ability_visual(all_abilities, activated_abilities))
    
    # 색상 테스트
    print("코어 색상 테스트:")
    for core_type in ["전설", "유물", "고대"]:
        color = _get_core_color(core_type)
        print(f"{core_type}: 0x{color:06x}")
    print()
    
    # 실제 최적화 테스트
    print("=== 젬 최적화 테스트 ===")
    from core_optimizer import CoreOptimizer
    
    core_optimizer = CoreOptimizer()
    
    # 단일 코어 테스트
    print("단일 코어 테스트:")
    result = core_optimizer.find_optimal_combination("전설", ["25", "35", "45"])
    if "error" not in result:
        print(f"✅ 전설 코어 - 잼: {result['gems']}, 질서포인트: {result['total_order_points']}")
        print(f"   활성화 능력: {result['activated_abilities']}")
        
        # UI 정보 시뮬레이션
        willpower_bar = _create_progress_bar(result['total_willpower_used'], result['core_willpower'], 15)
        print(f"   의지력 사용: {willpower_bar} ({result['total_willpower_used']}/{result['core_willpower']})")
        
        ability_visual = _create_ability_visual(result['all_abilities'], result['activated_abilities'])
        print(f"   능력 상태: {ability_visual}")
    else:
        print(f"❌ 오류: {result['error']}")
    
    print()
    
    # 멀티 코어 테스트
    print("멀티 코어 테스트:")
    result = core_optimizer.optimize_multiple_cores(["전설", "유물"], ["25", "35", "45", "26"])
    if "error" not in result:
        print(f"✅ 멀티 코어 - 사용된 잼: {result['total_gems_used']}/{result['total_available_gems']}")
        
        # 전체 잼 사용량 진행바
        gem_usage_bar = _create_progress_bar(result['total_gems_used'], result['total_available_gems'], 20)
        print(f"   잼 사용량: {gem_usage_bar}")
        
        for i, core_result in enumerate(result['cores']):
            if core_result['gem_count'] > 0:
                print(f"   {core_result['core_type']} #{i+1}: {core_result['gems']} -> 질서{core_result['total_order_points']}")
                print(f"       활성화: {core_result['activated_abilities']}")
            else:
                print(f"   {core_result['core_type']} #{i+1}: 잼 없음")
    else:
        print(f"❌ 오류: {result['error']}")

if __name__ == "__main__":
    test_gem_ui_functions()