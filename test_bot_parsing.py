#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
봇 명령어 파싱 테스트
"""

def test_command_parsing():
    """봇 명령어 파싱 로직 테스트"""
    
    # 사용자 입력: /코어 고대 전설 유물 35 35 36 35 25 26 16 35 35 36 35 25 26 16 35 35 36 35 25 26 16
    args = ["고대", "전설", "유물", "35", "35", "36", "35", "25", "26", "16", "35", "35", "36", "35", "25", "26", "16", "35", "35", "36", "35", "25", "26", "16"]
    
    print(f"전체 인수: {args}")
    print(f"인수 개수: {len(args)}")
    
    # 봇의 파싱 로직 재현
    valid_cores = ["전설", "유물", "고대"]
    
    core_types = []
    gems = []
    
    # 앞에서부터 유효한 코어 타입인지 확인
    for i, arg in enumerate(args):
        if arg in valid_cores:
            core_types.append(arg)
        else:
            # 첫 번째 비-코어 타입부터는 모두 잼으로 간주
            gems = list(args[i:])
            break
    
    print(f"파싱된 코어 타입: {core_types}")
    print(f"파싱된 잼: {gems}")
    print(f"잼 개수: {len(gems)}")
    
    # 실제 최적화 테스트
    from core_optimizer import CoreOptimizer
    
    core_optimizer = CoreOptimizer()
    
    try:
        if len(core_types) == 1:
            print("단일 코어 모드")
            result = core_optimizer.find_optimal_combination(core_types[0], gems)
        else:
            print("멀티 코어 모드")
            result = core_optimizer.optimize_multiple_cores(core_types, gems)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
        else:
            print(f"✅ 성공!")
            if "cores" in result:
                # 멀티 코어 결과
                print(f"사용된 잼: {result['total_gems_used']}/{result['total_available_gems']}")
                for i, core_result in enumerate(result['cores']):
                    if core_result['gem_count'] > 0:
                        print(f"{core_result['core_type']} #{i+1}: {core_result['gems']} -> 질서{core_result['total_order_points']}")
                    else:
                        print(f"{core_result['core_type']} #{i+1}: 잼 없음")
            else:
                # 단일 코어 결과
                print(f"코어: {result['core_type']}")
                print(f"잼: {result['gems']}")
                print(f"질서포인트: {result['total_order_points']}")
                
    except Exception as e:
        print(f"❌ 예외: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_command_parsing()