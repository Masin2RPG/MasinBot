# MasinSavecode
MasinBot

MasinBot은 Masin2RPG 게임을 위한 아이템 검색 및 디코딩 기능을 제공하는 Python 기반 봇입니다.

## 주요 파일 및 기능

- `bot.py`: 봇의 메인 실행 파일입니다.
- `refactored_bot.py`: 리팩토링된 봇 코드입니다.
- `item_searcher.py`: 아이템 검색 기능을 담당합니다.
- `items.py`: 아이템 데이터 관리 및 처리 기능을 제공합니다.
- `decoder.py`, `savecode_decoder.py`: 게임 저장 코드 및 아이템 코드 디코딩 기능을 제공합니다.
- `config.py`: 봇의 설정 정보를 관리합니다.
- `items.json`, `items_Rowcode.json`: 아이템 데이터가 저장된 JSON 파일입니다.

## 테스트

- `test_*.py` 파일들을 통해 각 기능별 유닛 테스트가 제공됩니다.

## 설치 및 실행 방법

1. Python 3.8 이상이 필요합니다.
2. 필요한 패키지를 설치합니다:
	```cmd
	pip install -r requirements.txt
	```
3. 봇을 실행합니다:
	```cmd
	python bot.py
	```

## 기여

이 리포지토리는 Masin2RPG 커뮤니티를 위해 개발되었습니다. 버그 제보 및 기능 개선 요청은 이슈로 등록해 주세요.
