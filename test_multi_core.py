#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from core_optimizer import CoreOptimizer


def test_multi_core_optimization():
    """멀티 코어 최적화 테스트"""
    print("=== 멀티 코어 최적화 테스트 ===")
    
    try:
        optimizer = CoreOptimizer()
        
        # 사용자 예시: /코어 전설 유물 유물 33 55 44 33 55 33 44 55 66 77 88
        print("사용자 예시 테스트:")
        print("코어: 전설, 유물, 유물")
        print("잼: 33, 55, 44, 33, 55, 33, 44, 55, 66, 77, 88")
        
        core_types = ["전설", "유물", "유물"]
        gems = ["33", "55", "44", "33", "55", "33", "44", "55", "66", "77", "88"]
        
        result = optimizer.optimize_multiple_cores(core_types, gems)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
            return
        
        print(f"\n결과:")
        print(f"총 사용된 잼: {result['total_gems_used']}/{result['total_available_gems']}")
        print(f"총 점수: {result['total_score']}")
        
        for i, core_result in enumerate(result['cores']):
            print(f"\n{core_result['core_type']} #{i+1}:")
            if core_result['gem_count'] > 0:
                print(f"  잼: {core_result['gems']}")
                print(f"  의지력: {core_result['total_willpower_used']}/{core_result['total_willpower_used'] + core_result['remaining_willpower']}")
                print(f"  질서포인트: {core_result['total_order_points']}")
                print(f"  활성화 능력: {core_result['activated_abilities']}")
                print(f"  점수: {core_result['score']}")
            else:
                print(f"  잼: 없음")
        
        # 간단한 테스트들
        print(f"\n=== 간단한 테스트들 ===")
        
        simple_tests = [
            (["전설"], ["25", "35"]),
            (["전설", "유물"], ["25", "35", "45", "22"]),
            (["고대", "고대"], ["15", "25", "35", "45", "55"])
        ]
        
        for cores, test_gems in simple_tests:
            print(f"\n코어: {cores}, 잼: {test_gems}")
            result = optimizer.optimize_multiple_cores(cores, test_gems)
            
            if "error" not in result:
                used_gems = sum(core['gem_count'] for core in result['cores'])
                print(f"  사용된 잼: {used_gems}/{len(test_gems)}")
                for i, core in enumerate(result['cores']):
                    if core['gem_count'] > 0:
                        print(f"  {core['core_type']} #{i+1}: {core['gems']} -> 질서{core['total_order_points']}")
            else:
                print(f"  오류: {result['error']}")
        
        print(f"\n✅ 멀티 코어 최적화 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_core_optimization()