import json

# utf-war3map-items.json 파일 읽기
with open('utf-war3map-items.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 결과를 저장할 딕셔너리
result = {}

# custom 섹션에서 데이터 추출
if 'custom' in data:
    for item_key, item_data in data['custom'].items():
        # 각 아이템의 속성들을 처리
        name = None
        
        for prop in item_data:
            if isinstance(prop, dict):
                prop_id = prop.get('id', '')
                prop_value = prop.get('value', '')
                
                # unam (이름)만 추출
                if prop_id == 'unam' and prop_value:
                    name = prop_value
                    break
        
        # 이름이 있으면 결과에 추가
        if name:
            result[item_key] = [name]

# items.json 형식으로 저장
with open('items_extracted.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)

print(f"추출 완료! {len(result)}개의 아이템이 items_extracted.json에 저장되었습니다.")
