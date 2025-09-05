#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bot import SaveCodeBot
import sys

def test_bot():
    try:
        print("봇 초기화 중...")
        bot = SaveCodeBot()
        
        print(f"JSON 파일 로드 성공:")
        print(f"  - items.json: {len(bot.items_data)}개 아이템")
        print(f"  - items_Rowcode.json: {len(bot.items_rowcode_data)}개 값")
        
        # 검색 테스트
        test_items = ['스텟', '포악', '화신', '아담']
        
        for item_name in test_items:
            print(f"\n'{item_name}' 검색 테스트:")
            results = bot._find_matching_items(item_name)
            print(f"  - 검색 결과: {len(results)}개")
            
            if results:
                key, item_info, value = results[0]
                clean_name = bot._clean_item_name(item_info)
                print(f"  - 첫 번째: {clean_name} (값: {value})")
        
        print("\n✅ 모든 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bot()
