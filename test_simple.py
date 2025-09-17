#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 멀티 코어 테스트
"""

from core_optimizer import CoreOptimizer


def simple_test():
    """간단한 테스트"""
    
    core_optimizer = CoreOptimizer()
    
    print("간단한 테스트 시작...")
    
    # 간단한 케이스부터 테스트
    core_types = ["전설", "유물"]
    gems = ["35", "25", "26"]
    
    print(f"코어 타입: {core_types}")
    print(f"잼: {gems}")
    
    try:
        result = core_optimizer.optimize_multiple_cores(core_types, gems)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
        else:
            print(f"✅ 성공! 사용된 잼: {result['total_gems_used']}/{result['total_available_gems']}")
            
            for i, core_result in enumerate(result['cores']):
                print(f"{core_result['core_type']} #{i+1}: {core_result['gems']} -> 질서{core_result['total_order_points']}")
                
    except Exception as e:
        print(f"❌ 예외: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_test()