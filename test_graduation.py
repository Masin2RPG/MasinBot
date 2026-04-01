"""
세이브코드 졸업 체크 테스트
"""

from decoder import SaveCodeDecoder
from savecode_decoder import extract_save_data
from graduation_checker import GraduationChecker

def test_savecode_graduation(name, code):
    """세이브코드의 졸업 상태 확인"""
    print(f"\n{'='*60}")
    print(f"테스트 세이브코드: {code}")
    print(f"{'='*60}")
    
    decoder = SaveCodeDecoder()
    checker = GraduationChecker()
    
    # 하이픈 제거
    clean_code = code.replace("-", "")
    
    # 아이템 추출
    items_list = decoder.extract_items(clean_code)
    print("\n아이템 목록:")
    for item in items_list:
        print(f"  {item}")
    
    # 세이브 데이터 추출
    save_data = extract_save_data(clean_code, name, summon_chunk_n=0)
    item_ids = save_data.get('items', [])
    print(f"\n아이템 ID: {item_ids}")
    
    # 각 졸업 조건 체크
    print("\n개별 졸업 조건 체크:")
    for raid in ['mikael', 'terminator', 'gabriel', 'raphael', 'uriel', 'apocalypse']:
        result = checker._check_raid_by_ids(set(item_ids), raid)
        print(f"  {raid}: {'✅' if result else '❌'}")
    
    # 최종 졸업 상태
    graduation_status = checker.get_graduation_status(
        items_list=items_list,
        item_ids=item_ids
    )
    emoji, status_name = checker.get_graduation_emoji_and_name(graduation_status)
    print(f"\n최종 졸업 상태: {emoji} {status_name}")
    
    return graduation_status


if __name__ == "__main__":
    name = "SinLime#31230"
    code1 = "11114-8YYYY-VTYYY-YV6YY-YYVLE-M3G11-1711U-J1111"
    code2 = "11114-8YYYY-VTYYY-YV6YY-YYVLE-O3G11-1711U-F1111"
    
    status1 = test_savecode_graduation(name, code1)
    status2 = test_savecode_graduation(name, code2)
    
    print(f"\n{'='*60}")
    print("테스트 결과 요약")
    print(f"{'='*60}")
    print(f"코드 1 졸업 상태: {status1}")
    print(f"코드 2 졸업 상태: {status2}")
