#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bot import SaveCodeBot

def test_hwashin_search():
    try:
        print("화신 검색 테스트...")
        bot = SaveCodeBot()
        
        results = bot._find_matching_items('화신')
        print(f"\n'화신' 검색 결과: {len(results)}개 아이템")
        
        for i, (key, item_info, value) in enumerate(results, 1):
            clean_name = bot._clean_item_name(item_info)
            print(f"{i}. {clean_name} - 값: {value}")
            
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hwashin_search()
