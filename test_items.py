import json
import re

def clean_item_name(text):
    """아이템 이름에서 색상 코드 등을 제거"""
    # 색상 코드 제거 (|CFF....|R, |r 등)
    cleaned = re.sub(r'\|[Cc][Ff][Ff][0-9A-Fa-f]{6}', '', text)
    cleaned = re.sub(r'\|[Rr]', '', cleaned)
    cleaned = re.sub(r'\|[a-zA-Z0-9]+', '', cleaned)
    # 특수문자 정리
    cleaned = re.sub(r'[\r\n\t]', ' ', cleaned)
    return cleaned.strip()

# JSON 파일 로드
with open('items.json', 'r', encoding='utf-8') as f:
    items = json.load(f)
with open('items_Rowcode.json', 'r', encoding='utf-8') as f:
    rowcodes = json.load(f)

# 처음 5개 아이템 확인
print("=== 아이템 데이터 구조 확인 ===")
count = 0
for key, values in items.items():
    if count >= 5:
        break
    if isinstance(values, list) and len(values) > 0:
        print(f'Key: {repr(key)}')
        print(f'Raw Item: {values[0]}')
        print(f'Clean Item: {clean_item_name(values[0])}')
        print(f'Value: {rowcodes.get(key, "Not found")}')
        print('---')
        count += 1

print("\n=== 검색 테스트 ===")
# 간단한 검색 테스트
test_names = ['스텟', '포악', '화신', '아담']
for test_name in test_names:
    print(f"\n'{test_name}' 검색 결과:")
    found = False
    for key, values in items.items():
        if isinstance(values, list) and len(values) > 0:
            for value in values:
                if isinstance(value, str):
                    clean_value = clean_item_name(value).lower()
                    if test_name.lower() in clean_value:
                        print(f"  - {clean_item_name(value)} (값: {rowcodes.get(key, 'N/A')})")
                        found = True
                        break
        if found:
            break
    if not found:
        print(f"  - 찾을 수 없음")
