#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from item_searcher import ItemSearcher

def test_item_searcher():
    try:
        print("=== ItemSearcher 테스트 ===")
        searcher = ItemSearcher()
        
        # 통계 정보
        stats = searcher.get_stats()
        print(f"통계: {stats}")
        
        # 검색 테스트
        test_items = ['화신', '스텟', '포악']
        
        for item_name in test_items:
            print(f"\n'{item_name}' 검색:")
            results = searcher.find_matching_items(item_name)
            print(f"  - {len(results)}개 발견")
            
            for i, (key, item_info, value) in enumerate(results[:3], 1):
                clean_name = searcher._clean_item_name(item_info)
                print(f"  {i}. {clean_name} - 값: {value}")
        
        print("\n✅ ItemSearcher 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_item_searcher()
