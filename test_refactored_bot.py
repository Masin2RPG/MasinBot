#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bot import SaveCodeBot

def test_refactored_bot():
    try:
        print("=== 리팩토링된 봇 테스트 ===")
        bot = SaveCodeBot()
        
        # 아이템 검색기가 제대로 초기화되었는지 확인
        stats = bot.item_searcher.get_stats()
        print(f"봇 초기화 성공!")
        print(f"아이템 검색기 통계: {stats}")
        
        # 몇 가지 검색 테스트
        test_items = ['화신', '아담']
        
        for item_name in test_items:
            results = bot.item_searcher.find_matching_items(item_name)
            print(f"\n'{item_name}' 검색: {len(results)}개 결과")
        
        print("\n✅ 리팩토링된 봇 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_refactored_bot()
