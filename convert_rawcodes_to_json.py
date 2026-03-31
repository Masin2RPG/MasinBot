"""
item_rawcodes_full.txt를 JSON 파일로 변환하는 스크립트
"""

import json
import re


def parse_rawcodes_txt(filename):
    """
    item_rawcodes_full.txt를 파싱하여 정수형 rawcode와 아이템 이름을 추출
    
    Args:
        filename: 파싱할 txt 파일 경로
        
    Returns:
        {rawcode: item_name} 형태의 딕셔너리
    """
    items = {}
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # 빈 줄이거나 "총 xxx개" 형태의 헤더는 건너뛰기
            if not line or line.startswith('총'):
                continue
            
            # 공백으로 분리 (첫 번째는 rawcode, 나머지는 아이템 이름)
            parts = line.split(None, 1)  # 최대 1번만 분리
            
            if len(parts) == 2:
                rawcode_str = parts[0].strip()
                item_name = parts[1].strip()
                
                # rawcode가 숫자인지 확인
                if rawcode_str.isdigit():
                    items[rawcode_str] = item_name
                else:
                    print(f"⚠️  잘못된 형식 건너뛰기: {line}")
            else:
                print(f"⚠️  잘못된 형식 건너뛰기: {line}")
    
    return items


def create_json_file(items_dict, output_file):
    """
    {아이템이름: rawcode_정수값} 형식의 JSON 파일 생성
    
    Args:
        items_dict: {rawcode: item_name} 딕셔너리
        output_file: 출력 JSON 파일 경로
    """
    # {아이템이름: rawcode_정수값} 형식으로 변환
    items_json = {name: int(rawcode) for rawcode, name in items_dict.items()}
    
    # JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(items_json, f, ensure_ascii=False, indent=2)
    
    return len(items_dict)


def main():
    """메인 실행 함수"""
    print("🔄 item_rawcodes_full.txt를 JSON으로 변환 중...")
    
    # 파일 경로
    input_file = 'item_rawcodes_full.txt'
    output_file = 'items_full.json'
    
    # 파싱
    items = parse_rawcodes_txt(input_file)
    
    if not items:
        print("❌ 파싱된 아이템이 없습니다.")
        return
    
    # JSON 파일 생성
    count = create_json_file(items, output_file)
    
    print(f"✅ 변환 완료!")
    print(f"   - 총 {count}개의 아이템 변환")
    print(f"   - {output_file} 생성")
    
    # 샘플 출력
    print("\n📋 샘플 데이터 (아이템이름: rawcode):")
    for i, (rawcode, name) in enumerate(list(items.items())[:3], 1):
        print(f"   {i}. {name}: {rawcode}")


if __name__ == "__main__":
    main()
