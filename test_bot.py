"""
간단한 테스트 스크립트
리팩토링된 코드의 기본 기능을 테스트합니다.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from decoder import SaveCodeDecoder
from items import ItemDatabase


def test_config():
    """설정 테스트"""
    print("=== 설정 테스트 ===")
    try:
        config = Config()
        config.validate()
        print("✅ 설정 로드 성공")
        print(f"봇 토큰 길이: {len(config.BOT_TOKEN)}")
        print(f"명령어 prefix: {config.COMMAND_PREFIX}")
        print(f"게임 버전: {config.GAME_VERSION}")
    except Exception as e:
        print(f"❌ 설정 테스트 실패: {e}")

def test_item_database():
    """아이템 데이터베이스 테스트"""
    print("\n=== 아이템 데이터베이스 테스트 ===")
    try:
        item_db = ItemDatabase()
        
        # 기본 아이템 조회
        item_0 = item_db.get_item_name(0)
        item_1 = item_db.get_item_name(1)
        print(f"아이템 0: {item_0}")
        print(f"아이템 1: {item_1}")
        
        # 존재하지 않는 아이템
        item_999 = item_db.get_item_name(999)
        print(f"아이템 999: {item_999}")
        
        # 아이템 검색
        search_results = item_db.search_items("사무엘")
        print(f"'사무엘' 검색 결과: {len(search_results)}개")
        
        print("✅ 아이템 데이터베이스 테스트 성공")
    except Exception as e:
        print(f"❌ 아이템 데이터베이스 테스트 실패: {e}")

def test_decoder():
    """디코더 테스트"""
    print("\n=== 디코더 테스트 ===")
    try:
        decoder = SaveCodeDecoder()
        
        # 테스트용 세이브코드 (실제 유효하지 않을 수 있음)
        test_code = "1O7EC43VPRN8FXKD"
        test_name = "테스트플레이어"
        
        # 디코드 테스트
        try:
            load_data = decoder.decode_savecode(test_code)
            print(f"디코드 결과: {load_data[:5]}... (처음 5개)")
        except Exception as e:
            print(f"디코드 테스트: {e}")
        
        # 검증 테스트
        try:
            is_valid = decoder.validate_savecode(test_code, test_name)
            print(f"검증 결과: {is_valid}")
        except Exception as e:
            print(f"검증 테스트: {e}")
        
        # 아이템 추출 테스트
        try:
            items = decoder.extract_items(test_code)
            print(f"아이템 추출: {len(items)}개 슬롯")
            for item in items[:3]:  # 처음 3개만 출력
                print(f"  - {item}")
        except Exception as e:
            print(f"아이템 추출 테스트: {e}")
        
        print("✅ 디코더 테스트 완료")
    except Exception as e:
        print(f"❌ 디코더 테스트 실패: {e}")

def test_string_encoding():
    """문자열 인코딩 테스트"""
    print("\n=== 문자열 인코딩 테스트 ===")
    try:
        decoder = SaveCodeDecoder()
        
        # ASCII 문자열
        ascii_name = "TestPlayer"
        ascii_value = decoder._calculate_string_value(ascii_name)
        print(f"ASCII '{ascii_name}': {ascii_value}")
        
        # 한글 문자열
        korean_name = "테스트플레이어"
        korean_value = decoder._calculate_string_value(korean_name)
        print(f"Korean '{korean_name}': {korean_value}")
        
        print("✅ 문자열 인코딩 테스트 성공")
    except Exception as e:
        print(f"❌ 문자열 인코딩 테스트 실패: {e}")

def main():
    """메인 테스트 함수"""
    print("🧪 세이브코드 봇 테스트 시작\n")
    
    test_config()
    test_item_database()
    test_decoder()
    test_string_encoding()
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    main()
