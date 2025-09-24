"""
캐릭터 검색 기능 모듈
캐릭터 이름으로 ID를 찾고, 부분 검색을 지원하는 기능 제공
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CharacterSearcher:
    """캐릭터 검색 클래스"""
    
    def __init__(self, char_list_file: str = "CharList_by_id.json", char_name_file: str = "charName.json"):
        """
        초기화
        
        Args:
            char_list_file: 캐릭터 리스트가 포함된 JSON 파일 경로
            char_name_file: 마신 이름과 캐릭터 이름 매핑이 포함된 JSON 파일 경로
        """
        self.char_list_file = char_list_file
        self.char_name_file = char_name_file
        self.char_data: Dict[str, str] = {}
        self.name_to_id: Dict[str, str] = {}
        self.masin_to_id: Dict[str, str] = {}  # 마신 이름으로 ID 찾기용
        self._load_character_data()
    
    def _load_character_data(self):
        """캐릭터 데이터를 파일에서 로드"""
        # CharList_by_id.json 로드
        try:
            with open(self.char_list_file, 'r', encoding='utf-8') as f:
                self.char_data = json.load(f)
            
            # 이름으로 ID를 찾기 위한 역방향 매핑 생성
            self.name_to_id = {name: char_id for char_id, name in self.char_data.items()}
            
            logger.info(f"캐릭터 데이터 로드 완료: {len(self.char_data)}개")
            
        except FileNotFoundError:
            logger.error(f"캐릭터 파일을 찾을 수 없습니다: {self.char_list_file}")
            self.char_data = {}
            self.name_to_id = {}
        except json.JSONDecodeError as e:
            logger.error(f"캐릭터 파일 파싱 오류: {e}")
            self.char_data = {}
            self.name_to_id = {}
        except Exception as e:
            logger.error(f"캐릭터 데이터 로드 중 오류: {e}")
            self.char_data = {}
            self.name_to_id = {}
        
        # charName.json 로드 (마신 이름 매핑)
        try:
            with open(self.char_name_file, 'r', encoding='utf-8') as f:
                char_name_data = json.load(f)
            
            # 마신 이름으로 캐릭터 찾기 위한 매핑 생성
            for entry in char_name_data:
                masin_name = entry.get("마신", "")
                character_names = entry.get("이름", [])
                
                # 각 캐릭터 이름에 대해 ID 찾기
                for char_name in character_names:
                    if char_name in self.name_to_id:
                        char_id = self.name_to_id[char_name]
                        self.masin_to_id[masin_name] = char_id
                        # 마신 이름도 검색 가능하도록 name_to_id에 추가
                        self.name_to_id[masin_name] = char_id
                        break  # 첫 번째 매칭되는 캐릭터의 ID 사용
            
            logger.info(f"마신 이름 매핑 로드 완료: {len(self.masin_to_id)}개")
            
        except FileNotFoundError:
            logger.warning(f"마신 이름 파일을 찾을 수 없습니다: {self.char_name_file}")
        except json.JSONDecodeError as e:
            logger.error(f"마신 이름 파일 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"마신 이름 데이터 로드 중 오류: {e}")
    
    def search_by_exact_name(self, name: str) -> Optional[Tuple[str, str]]:
        """
        정확한 이름으로 캐릭터 검색
        
        Args:
            name: 검색할 캐릭터 이름
            
        Returns:
            (캐릭터 ID, 캐릭터 이름) 튜플 또는 None
        """
        char_id = self.name_to_id.get(name)
        if char_id:
            return (char_id, name)
        return None
    
    def search_by_partial_name(self, partial_name: str, max_results: int = 10) -> List[Tuple[str, str]]:
        """
        부분 이름으로 캐릭터 검색 (마신 이름과 캐릭터 이름 모두 포함)
        
        Args:
            partial_name: 검색할 부분 이름
            max_results: 최대 결과 개수
            
        Returns:
            [(캐릭터 ID, 검색된 이름)] 리스트
        """
        if not partial_name.strip():
            return []
        
        results = []
        partial_name_lower = partial_name.lower()
        seen_ids = set()  # 중복 방지용
        
        # name_to_id에서 검색 (마신 이름과 캐릭터 이름 모두 포함)
        for name, char_id in self.name_to_id.items():
            if partial_name_lower in name.lower() and char_id not in seen_ids:
                # 실제 캐릭터 이름을 가져오기
                actual_char_name = self.char_data.get(char_id, name)
                results.append((char_id, actual_char_name))
                seen_ids.add(char_id)
                
                if len(results) >= max_results:
                    break
        
        return results
    
    def search_character(self, search_term: str) -> Dict:
        """
        캐릭터 검색 (정확한 검색 우선, 부분 검색 포함)
        
        Args:
            search_term: 검색어
            
        Returns:
            검색 결과 딕셔너리
        """
        if not search_term.strip():
            return {
                'success': False,
                'message': '검색어를 입력해주세요.',
                'results': []
            }
        
        # 1. 정확한 이름으로 먼저 검색
        exact_result = self.search_by_exact_name(search_term)
        if exact_result:
            return {
                'success': True,
                'message': f'정확히 일치하는 캐릭터를 찾았습니다.',
                'search_type': 'exact',
                'results': [exact_result]
            }
        
        # 2. 부분 검색
        partial_results = self.search_by_partial_name(search_term)
        if partial_results:
            return {
                'success': True,
                'message': f'"{search_term}"으로 검색된 캐릭터들입니다.',
                'search_type': 'partial',
                'results': partial_results
            }
        
        # 3. 검색 결과 없음
        return {
            'success': False,
            'message': f'"{search_term}"으로 검색된 캐릭터가 없습니다.',
            'results': []
        }
    
    def get_character_by_id(self, char_id: str) -> Optional[str]:
        """
        ID로 캐릭터 이름 가져오기
        
        Args:
            char_id: 캐릭터 ID
            
        Returns:
            캐릭터 이름 또는 None
        """
        return self.char_data.get(str(char_id))
    
    def get_all_characters(self) -> Dict[str, str]:
        """
        모든 캐릭터 데이터 반환
        
        Returns:
            캐릭터 데이터 딕셔너리
        """
        return self.char_data.copy()
    
    def get_character_count(self) -> int:
        """
        총 캐릭터 수 반환
        
        Returns:
            캐릭터 수
        """
        return len(self.char_data)
    
    def reload_data(self):
        """캐릭터 데이터 다시 로드"""
        self._load_character_data()