#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
새로운 코어 설정 UI 테스트
"""

def test_new_core_setup():
    """새로운 코어 설정 방식 테스트"""
    
    print("=== 새로운 코어 설정 UI 테스트 ===")
    
    # 코어 개수 파싱 테스트
    def parse_core_setup(legend_count_str, relic_count_str, ancient_count_str):
        """코어 개수 파싱"""
        try:
            legend_num = int(legend_count_str.strip() or '0')
            relic_num = int(relic_count_str.strip() or '0')
            ancient_num = int(ancient_count_str.strip() or '0')
            
            if legend_num < 0 or relic_num < 0 or ancient_num < 0:
                return None, "코어 개수는 0 이상이어야 합니다"
            
            if legend_num + relic_num + ancient_num == 0:
                return None, "최소 1개의 코어는 필요합니다"
            
            if legend_num + relic_num + ancient_num > 10:
                return None, "코어는 최대 10개까지만 가능합니다"
            
            # 코어 리스트 생성
            core_types = []
            core_types.extend(['전설'] * legend_num)
            core_types.extend(['유물'] * relic_num) 
            core_types.extend(['고대'] * ancient_num)
            
            return core_types, None
            
        except ValueError:
            return None, "코어 개수는 숫자여야 합니다"
    
    # 테스트 케이스들
    test_cases = [
        ("1", "0", "2"),  # 전설 1개, 고대 2개
        ("0", "2", "1"),  # 유물 2개, 고대 1개
        ("1", "1", "1"),  # 각각 1개씩
        ("3", "0", "0"),  # 전설만 3개
        ("0", "0", "0"),  # 오류 케이스 - 모두 0
        ("-1", "1", "0"), # 오류 케이스 - 음수
        ("5", "5", "5"),  # 오류 케이스 - 너무 많음
        ("abc", "1", "0") # 오류 케이스 - 문자
    ]
    
    print("코어 설정 파싱 테스트:")
    for legend, relic, ancient in test_cases:
        core_types, error = parse_core_setup(legend, relic, ancient)
        if error:
            print(f"  전설:{legend}, 유물:{relic}, 고대:{ancient} -> ❌ {error}")
        else:
            # 코어 요약 생성
            core_summary = {}
            for core_type in core_types:
                core_summary[core_type] = core_summary.get(core_type, 0) + 1
            summary_text = ", ".join([f"{k}:{v}개" for k, v in core_summary.items()])
            print(f"  전설:{legend}, 유물:{relic}, 고대:{ancient} -> ✅ {summary_text} (총 {len(core_types)}개)")
    
    print()
    
    # 실제 최적화 테스트
    print("=== 새로운 설정으로 최적화 테스트 ===")
    
    from core_optimizer import CoreOptimizer
    
    core_optimizer = CoreOptimizer()
    
    # 테스트 케이스: 고대 2개, 전설 1개
    core_types = ['고대', '고대', '전설']
    gems = ["25", "35", "45", "26", "36", "16"]
    
    print(f"테스트 설정:")
    print(f"  코어 구성: {core_types}")
    
    # 코어 요약
    core_summary = {}
    for core_type in core_types:
        core_summary[core_type] = core_summary.get(core_type, 0) + 1
    
    print(f"  코어 요약: {', '.join([f'{k}: {v}개' for k, v in core_summary.items()])}")
    print(f"  젬: {gems}")
    print()
    
    # 멀티 코어 최적화
    result = core_optimizer.optimize_multiple_cores(core_types, gems)
    
    if "error" not in result:
        print(f"✅ 최적화 결과:")
        print(f"  사용된 젬: {result['total_gems_used']}/{result['total_available_gems']}")
        
        for i, core_result in enumerate(result['cores']):
            if core_result['gem_count'] > 0:
                gems_str = ', '.join(core_result['gems'])
                activated_count = len(core_result['activated_abilities'])
                print(f"  {core_result['core_type']} #{i+1}: {gems_str} → 질서{core_result['total_order_points']} (능력{activated_count}개)")
            else:
                print(f"  {core_result['core_type']} #{i+1}: 젬 없음")
        
        print()
        print("UI 표시 시뮬레이션:")
        
        # 코어 구성 정보 (UI에 표시될 내용)
        core_info = []
        for core_type, count in core_summary.items():
            core_info.append(f"{core_type}: {count}개")
        
        print(f"  🔮 코어 구성:")
        for info in core_info:
            print(f"    {info}")
        print(f"    총 {len(core_types)}개")
        
        # 젬 사용량
        total_gems_used = result['total_gems_used']
        total_available = result['total_available_gems']
        usage_percentage = (total_gems_used / total_available * 100) if total_available > 0 else 0
        print(f"  📊 젬 사용량:")
        print(f"    사용: {total_gems_used}/{total_available}개")
        print(f"    사용률: {usage_percentage:.1f}%")
        
    else:
        print(f"❌ 오류: {result['error']}")

if __name__ == "__main__":
    test_new_core_setup()