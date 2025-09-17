#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from core_optimizer import CoreOptimizer


def test_simple_multi_core():
    """간단한 멀티 코어 테스트"""
    print("=== 간단한 멀티 코어 테스트 ===")
    
    try:
        optimizer = CoreOptimizer()
        
        print("테스트 1: 전설 + 유물, 잼 4개")
        result = optimizer.optimize_multiple_cores(["전설", "유물"], ["25", "35", "45", "22"])
        
        if "error" in result:
            print(f"오류: {result['error']}")
        else:
            print(f"성공! 사용된 잼: {result['total_gems_used']}/{result['total_available_gems']}")
            for i, core in enumerate(result['cores']):
                print(f"  {core['core_type']} #{i+1}: {core['gems']} -> 질서{core['total_order_points']}")
        
        print(f"\n✅ 간단한 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_multi_core()