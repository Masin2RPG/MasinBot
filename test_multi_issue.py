#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
멀티 코어 테스트 스크립트
"""

from core_optimizer import CoreOptimizer


def test_multi_core_issue():
    """사용자가 제공한 명령어로 테스트"""
    
    core_optimizer = CoreOptimizer()
    
    # 사용자 입력: /코어 고대 전설 유물 35 35 36 35 25 26 16 35 35 36 35 25 26 16 35 35 36 35 25 26 16
    core_types = ["고대", "전설", "유물"]
    gems = ["35", "35", "36", "35", "25", "26", "16", "35", "35", "36", "35", "25", "26", "16", "35", "35", "36", "35", "25", "26", "16"]
    
    print(f"테스트 입력:")
    print(f"코어 타입: {core_types}")
    print(f"잼 개수: {len(gems)}개")
    print(f"잼 목록: {gems}")
    print()
    
    try:
        result = core_optimizer.optimize_multiple_cores(core_types, gems)
        
        if "error" in result:
            print(f"❌ 오류 발생: {result['error']}")
        else:
            print(f"✅ 성공!")
            print(f"사용된 잼: {result['total_gems_used']}/{result['total_available_gems']}")
            
            for i, core_result in enumerate(result['cores']):
                print(f"\n{core_result['core_type']} #{i+1}:")
                print(f"  잼: {core_result['gems']}")
                print(f"  질서포인트: {core_result['total_order_points']}")
                print(f"  활성화된 능력: {core_result['activated_abilities']}")
                
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_core_issue()