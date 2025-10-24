#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
쿠폰 통합 처리 테스트 및 사용 예제
"""

import os
import sys

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from coupon_integrated import (CouponProcessor, format_coupon_result,
                               process_coupon_simple)


def test_coupon_check():
    """쿠폰 체크 기능 테스트"""
    print("\n🧪 쿠폰 체크 테스트")
    print("-" * 40)
    
    processor = CouponProcessor()
    
    # 테스트용 쿠폰들
    test_coupons = ["ABC123", "INVALID", "EXPIRED"]
    
    for coupon in test_coupons:
        print(f"\n🎫 쿠폰 체크: {coupon}")
        success, response = processor.check_coupon(coupon)
        
        if success:
            print(f"   ✅ API 호출 성공")
            print(f"   유효: {response.is_valid}")
            print(f"   사용됨: {response.is_used}")
            print(f"   메시지: {response.error_message}")
        else:
            print(f"   ❌ API 호출 실패: {response.error_message}")
    
    processor.close()


def test_full_workflow():
    """전체 워크플로우 테스트"""
    print("\n🧪 전체 워크플로우 테스트")
    print("-" * 40)
    
    # 테스트 케이스들
    test_cases = [
        {
            'coupon': 'ABC123',
            'savecode': '7C0W3-AYYYY-V6YYY-YVTYY-YY3GH-I4814-OC1OF-WFS',
            'player_name': '테스터',
            'description': '원본 게임 세이브코드 테스트'
        },
        {
            'coupon': 'XYZ789', 
            'savecode': 'MasinSaveV2_홍길동_37_50000_15_200_100_150_264_266_268_270_272_274',
            'player_name': None,
            'description': '마신 세이브코드 테스트'
        },
        {
            'coupon': 'INVALID',
            'savecode': '7C0W3-AYYYY-V6YYY-YVTYY-YY3GH-I4814-OC1OF-WFS',
            'player_name': '테스터',
            'description': '유효하지 않은 쿠폰 테스트'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 테스트 {i}: {test_case['description']}")
        print(f"   쿠폰: {test_case['coupon']}")
        print(f"   세이브코드: {test_case['savecode'][:20]}...")
        print(f"   플레이어: {test_case.get('player_name', 'None')}")
        
        # 쿠폰 처리 실행
        result = process_coupon_simple(
            test_case['coupon'], 
            test_case['savecode'], 
            test_case.get('player_name')
        )
        
        # 결과 출력
        print(f"\n📋 결과:")
        if result.success:
            print(f"   ✅ 성공!")
            print(f"   골드 증가: {result.gold_gained:,}")
            print(f"   나무 증가: {result.lumber_gained:,}")
            print(f"   수정된 세이브코드: {result.modified_savecode[:30]}...")
        else:
            print(f"   ❌ 실패: {result.error_message}")


def interactive_test():
    """대화형 테스트"""
    print("\n🎮 대화형 쿠폰 처리 테스트")
    print("-" * 40)
    print("쿠폰 코드와 세이브코드를 입력하여 테스트해보세요")
    print("(종료하려면 'quit' 입력)")
    
    while True:
        print("\n" + "="*50)
        
        # 쿠폰 코드 입력
        coupon_code = input("🎫 쿠폰 코드: ").strip()
        if coupon_code.lower() == 'quit':
            break
        
        if not coupon_code:
            print("❌ 쿠폰 코드를 입력해주세요!")
            continue
        
        # 세이브코드 입력
        savecode = input("🔮 세이브코드: ").strip()
        if savecode.lower() == 'quit':
            break
            
        if not savecode:
            print("❌ 세이브코드를 입력해주세요!")
            continue
        
        # 플레이어 이름 입력 (원본 게임 세이브코드인 경우)
        player_name = None
        if not savecode.startswith('MasinSaveV2_'):
            player_name = input("👤 플레이어 이름 (원본 게임 세이브코드용): ").strip()
            if player_name.lower() == 'quit':
                break
            if not player_name:
                print("❌ 원본 게임 세이브코드를 사용하려면 플레이어 이름이 필요합니다!")
                continue
        
        print(f"\n🔄 처리 중...")
        
        # 쿠폰 처리 실행
        result = process_coupon_simple(coupon_code, savecode, player_name)
        
        # 결과 출력
        print(f"\n📋 처리 결과:")
        print(format_coupon_result(result))
        
        if result.success:
            print(f"\n🔍 상세 정보:")
            print(f"   원본: {result.original_savecode[:50]}...")
            print(f"   수정: {result.modified_savecode[:50]}...")


def demo_workflow():
    """워크플로우 데모"""
    print("\n🚀 쿠폰 처리 워크플로우 데모")
    print("=" * 50)
    
    # 샘플 데이터
    sample_coupon = "DEMO123"
    sample_savecode = "7C0W3-AYYYY-V6YYY-YVTYY-YY3GH-I4814-OC1OF-WFS"
    sample_player = "데모플레이어"
    
    print(f"📝 데모 데이터:")
    print(f"   쿠폰: {sample_coupon}")
    print(f"   세이브코드: {sample_savecode}")
    print(f"   플레이어: {sample_player}")
    
    processor = CouponProcessor()
    
    try:
        # 1단계: 쿠폰 체크
        print(f"\n1️⃣ 쿠폰 유효성 체크...")
        check_success, check_response = processor.check_coupon(sample_coupon)
        
        if check_success:
            print(f"   ✅ 쿠폰 체크 API 호출 성공")
            print(f"   유효: {check_response.is_valid}")
            print(f"   사용됨: {check_response.is_used}")
            
            if check_response.is_valid and not check_response.is_used:
                print(f"   ✅ 사용 가능한 쿠폰입니다!")
                
                # 2단계: 쿠폰 사용
                print(f"\n2️⃣ 쿠폰 사용...")
                use_success, use_response = processor.use_coupon(sample_coupon)
                
                if use_success and use_response.is_success:
                    print(f"   ✅ 쿠폰 사용 성공!")
                    print(f"   획득 골드: {use_response.gold:,}")
                    print(f"   획득 나무: {use_response.lumber:,}")
                    
                    # 3단계: 세이브코드 수정
                    print(f"\n3️⃣ 세이브코드 수정...")
                    try:
                        # 전체 워크플로우 실행
                        result = processor.process_coupon_with_savecode(
                            sample_coupon, sample_savecode, sample_player
                        )
                        
                        if result.success:
                            print(f"   ✅ 세이브코드 수정 성공!")
                            print(f"   수정된 세이브코드: {result.modified_savecode[:50]}...")
                        else:
                            print(f"   ❌ 세이브코드 수정 실패: {result.error_message}")
                            
                    except Exception as e:
                        print(f"   ❌ 세이브코드 수정 중 오류: {str(e)}")
                        
                else:
                    print(f"   ❌ 쿠폰 사용 실패: {use_response.error_message}")
                    
            else:
                if not check_response.is_valid:
                    print(f"   ❌ 유효하지 않은 쿠폰입니다")
                if check_response.is_used:
                    print(f"   ❌ 이미 사용된 쿠폰입니다")
                    
        else:
            print(f"   ❌ 쿠폰 체크 API 호출 실패: {check_response.error_message}")
            
    finally:
        processor.close()


def main():
    """메인 실행 함수"""
    print("🎯 쿠폰 통합 처리 시스템 테스트")
    print("=" * 50)
    
    while True:
        print("\n메뉴를 선택하세요:")
        print("1. 쿠폰 체크 테스트")
        print("2. 전체 워크플로우 테스트")
        print("3. 대화형 테스트")
        print("4. 워크플로우 데모")
        print("5. 종료")
        
        choice = input("\n선택 (1-5): ").strip()
        
        if choice == '1':
            test_coupon_check()
        elif choice == '2':
            test_full_workflow()
        elif choice == '3':
            interactive_test()
        elif choice == '4':
            demo_workflow()
        elif choice == '5':
            print("👋 프로그램을 종료합니다.")
            break
        else:
            print("❌ 올바른 번호를 선택해주세요!")


if __name__ == "__main__":
    main()