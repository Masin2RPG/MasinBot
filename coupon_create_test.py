#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
쿠폰 생성 기능 테스트
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from coupon_integrated import create_coupon_simple, format_coupon_create_result


def test_coupon_creation():
    """쿠폰 생성 기능 테스트"""
    print("🧪 쿠폰 생성 기능 테스트")
    print("=" * 50)
    
    # 테스트 케이스들
    test_cases = [
        {"lumber": 100000, "gold": 500000, "description": "일반적인 쿠폰"},
        {"lumber": 0, "gold": 1000000, "description": "골드만 있는 쿠폰"},
        {"lumber": 500000, "gold": 0, "description": "나무만 있는 쿠폰"},
        {"lumber": 1, "gold": 1, "description": "최소값 쿠폰"}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 테스트 {i}: {test_case['description']}")
        print(f"   나무: {test_case['lumber']:,}")
        print(f"   골드: {test_case['gold']:,}")
        print("-" * 30)
        
        try:
            success, response = create_coupon_simple(test_case['lumber'], test_case['gold'])
            
            if success:
                print(f"✅ API 호출 성공")
                print(f"   응답 성공: {response.is_success}")
                print(f"   쿠폰 코드: {response.coupon_code}")
                print(f"   메시지: {response.error_message}")
                
                if response.is_success and response.coupon_code:
                    print(f"\n📋 사용자 친화적 메시지:")
                    formatted_message = format_coupon_create_result(success, response)
                    print(formatted_message)
                
            else:
                print(f"❌ API 호출 실패")
                print(f"   오류: {response.error_message}")
                
        except Exception as e:
            print(f"❌ 테스트 중 오류: {str(e)}")


def interactive_coupon_creation():
    """대화형 쿠폰 생성 테스트"""
    print("\n🎮 대화형 쿠폰 생성 테스트")
    print("=" * 50)
    print("나무와 골드 수량을 입력하여 쿠폰을 생성해보세요")
    print("(종료하려면 'quit' 입력)")
    
    while True:
        print("\n" + "="*40)
        
        # 나무 수량 입력
        lumber_input = input("🌲 나무 수량: ").strip()
        if lumber_input.lower() == 'quit':
            break
        
        if not lumber_input:
            print("❌ 나무 수량을 입력해주세요!")
            continue
        
        try:
            lumber = int(lumber_input)
        except ValueError:
            print("❌ 올바른 숫자를 입력해주세요!")
            continue
        
        # 골드 수량 입력
        gold_input = input("💰 골드 수량: ").strip()
        if gold_input.lower() == 'quit':
            break
            
        if not gold_input:
            print("❌ 골드 수량을 입력해주세요!")
            continue
        
        try:
            gold = int(gold_input)
        except ValueError:
            print("❌ 올바른 숫자를 입력해주세요!")
            continue
        
        if lumber < 0 or gold < 0:
            print("❌ 나무와 골드는 0 이상이어야 합니다!")
            continue
        
        print(f"\n🔄 쿠폰 생성 중...")
        print(f"   나무: {lumber:,}")
        print(f"   골드: {gold:,}")
        
        try:
            success, response = create_coupon_simple(lumber, gold)
            
            print(f"\n📋 생성 결과:")
            formatted_result = format_coupon_create_result(success, response)
            print(formatted_result)
            
        except Exception as e:
            print(f"\n❌ 쿠폰 생성 중 오류: {str(e)}")


if __name__ == "__main__":
    print("🎯 쿠폰 생성 기능 테스트 시작")
    print("=" * 60)
    
    while True:
        print("\n메뉴를 선택하세요:")
        print("1. 자동 테스트 케이스 실행")
        print("2. 대화형 쿠폰 생성 테스트")
        print("3. 종료")
        
        choice = input("\n선택 (1-3): ").strip()
        
        if choice == '1':
            test_coupon_creation()
        elif choice == '2':
            interactive_coupon_creation()
        elif choice == '3':
            print("👋 프로그램을 종료합니다.")
            break
        else:
            print("❌ 올바른 번호를 선택해주세요!")