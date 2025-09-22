"""
SaveCode 관리 시스템 모듈
세이브코드 디코딩, 캐릭터 정보 추출, 통계 처리 등을 담당
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from savecode_decoder import decode_savecode2, extract_save_data

logger = logging.getLogger(__name__)


class SaveCodeManager:
    """세이브코드 관리 및 처리 시스템"""
    
    def __init__(self):
        self.character_list = self._load_character_list()
    
    def _load_character_list(self) -> Dict:
        """CharList_by_id.json 파일에서 캐릭터 목록을 로드"""
        try:
            with open('CharList_by_id.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("CharList_by_id.json 파일을 찾을 수 없습니다.")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"CharList_by_id.json 파일 파싱 오류: {e}")
            return {}
        except Exception as e:
            logger.error(f"캐릭터 리스트 로드 중 오류: {e}")
            return {}
    
    def decode_savecode(self, savecode: str) -> Optional[Dict]:
        """세이브코드를 디코딩하여 데이터 반환"""
        try:
            return decode_savecode2(savecode)
        except Exception as e:
            logger.error(f"세이브코드 디코딩 실패: {e}")
            return None
    
    def extract_resources(self, savecode: str) -> Optional[Dict]:
        """세이브코드에서 골드, 목재, 영웅 정보 추출"""
        try:
            return extract_save_data(savecode)
        except Exception as e:
            logger.error(f"리소스 추출 실패: {e}")
            return None
    
    def get_character_name(self, char_id: int) -> str:
        """캐릭터 ID로 캐릭터 이름 조회"""
        try:
            char_id_str = str(char_id)
            if isinstance(self.character_list, dict) and char_id_str in self.character_list:
                char_data = self.character_list[char_id_str]
                
                # JSON 구조가 {"id": "name"} 형태라면
                if isinstance(char_data, str):
                    return char_data
                # JSON 구조가 {"id": {"name": "..."}} 형태라면  
                elif isinstance(char_data, dict) and 'name' in char_data:
                    return char_data['name']
                else:
                    return f"Unknown Character (ID: {char_id})"
            else:
                return f"Unknown Character (ID: {char_id})"
        except Exception as e:
            logger.error(f"get_character_name 오류: {e}")
            return f"Unknown Character (ID: {char_id})"
    
    def format_character_info(self, char_id: int, level: int = None, star: int = None) -> str:
        """캐릭터 정보를 포맷된 문자열로 반환"""
        name = self.get_character_name(char_id)
        
        info_parts = [name]
        if level is not None:
            info_parts.append(f"Lv.{level}")
        if star is not None:
            info_parts.append(f"{star}★")
        
        return " ".join(info_parts)
    
    def process_heroes_data(self, heroes_data: List[Dict]) -> List[Dict]:
        """영웅 데이터를 처리하여 이름과 함께 반환"""
        processed_heroes = []
        
        for hero in heroes_data:
            try:
                char_id = hero.get('charId', 0)
                level = hero.get('level', 1)
                star = hero.get('star', 1)
                
                processed_hero = {
                    'charId': char_id,
                    'name': self.get_character_name(char_id),
                    'level': level,
                    'star': star,
                    'formatted_info': self.format_character_info(char_id, level, star)
                }
                processed_heroes.append(processed_hero)
                
            except Exception as e:
                logger.warning(f"영웅 데이터 처리 실패: {hero}, 오류: {e}")
                continue
        
        return processed_heroes
    
    def analyze_multiple_savecodes(self, savecodes: List[str]) -> Dict:
        """여러 세이브코드를 분석하여 통계 정보 반환"""
        results = {
            'total_count': len(savecodes),
            'successful_decodes': 0,
            'failed_decodes': 0,
            'total_gold': 0,
            'total_lumber': 0,
            'total_heroes': 0,
            'character_stats': {},
            'level_stats': {},
            'star_stats': {},
            'errors': []
        }
        
        for i, savecode in enumerate(savecodes, 1):
            try:
                # 리소스 데이터 추출
                resource_data = self.extract_resources(savecode)
                if resource_data:
                    results['successful_decodes'] += 1
                    results['total_gold'] += resource_data.get('gold', 0)
                    results['total_lumber'] += resource_data.get('lumber', 0)
                    
                    # 영웅 데이터 처리
                    heroes = resource_data.get('heroes', [])
                    processed_heroes = self.process_heroes_data(heroes)
                    results['total_heroes'] += len(processed_heroes)
                    
                    # 캐릭터별 통계
                    for hero in processed_heroes:
                        char_name = hero['name']
                        level = hero['level']
                        star = hero['star']
                        
                        # 캐릭터 카운트
                        if char_name not in results['character_stats']:
                            results['character_stats'][char_name] = 0
                        results['character_stats'][char_name] += 1
                        
                        # 레벨 통계
                        if level not in results['level_stats']:
                            results['level_stats'][level] = 0
                        results['level_stats'][level] += 1
                        
                        # 별 통계
                        if star not in results['star_stats']:
                            results['star_stats'][star] = 0
                        results['star_stats'][star] += 1
                else:
                    results['failed_decodes'] += 1
                    results['errors'].append(f"세이브코드 {i}: 리소스 추출 실패")
                    
            except Exception as e:
                results['failed_decodes'] += 1
                results['errors'].append(f"세이브코드 {i}: {str(e)}")
        
        return results
    
    def format_statistics_embed_data(self, stats: Dict) -> Dict:
        """통계 데이터를 Discord Embed용으로 포맷"""
        embed_data = {
            'title': '📊 세이브코드 통계 분석',
            'color': 0x3498db,
            'fields': []
        }
        
        # 기본 통계
        basic_stats = (
            f"전체 세이브코드: {stats['total_count']}개\n"
            f"성공: {stats['successful_decodes']}개\n"
            f"실패: {stats['failed_decodes']}개\n"
            f"성공률: {(stats['successful_decodes']/stats['total_count']*100):.1f}%"
        )
        embed_data['fields'].append({
            'name': '🔍 처리 결과',
            'value': basic_stats,
            'inline': True
        })
        
        # 리소스 통계
        resource_stats = (
            f"총 골드: {stats['total_gold']:,}\n"
            f"총 목재: {stats['total_lumber']:,}\n"
            f"총 영웅 수: {stats['total_heroes']}명"
        )
        embed_data['fields'].append({
            'name': '💰 리소스 합계',
            'value': resource_stats,
            'inline': True
        })
        
        # 평균 정보
        if stats['successful_decodes'] > 0:
            avg_gold = stats['total_gold'] // stats['successful_decodes']
            avg_lumber = stats['total_lumber'] // stats['successful_decodes']
            avg_heroes = stats['total_heroes'] / stats['successful_decodes']
            
            avg_stats = (
                f"평균 골드: {avg_gold:,}\n"
                f"평균 목재: {avg_lumber:,}\n"
                f"평균 영웅: {avg_heroes:.1f}명"
            )
            embed_data['fields'].append({
                'name': '📈 평균 정보',
                'value': avg_stats,
                'inline': True
            })
        
        # 인기 캐릭터 TOP 5
        if stats['character_stats']:
            top_chars = sorted(stats['character_stats'].items(), 
                             key=lambda x: x[1], reverse=True)[:5]
            top_chars_text = "\n".join([
                f"{i+1}. {char}: {count}명" 
                for i, (char, count) in enumerate(top_chars)
            ])
            embed_data['fields'].append({
                'name': '🌟 인기 캐릭터 TOP 5',
                'value': top_chars_text,
                'inline': False
            })
        
        # 별등급 분포
        if stats['star_stats']:
            star_distribution = []
            for star in sorted(stats['star_stats'].keys(), reverse=True):
                count = stats['star_stats'][star]
                percentage = (count / stats['total_heroes'] * 100) if stats['total_heroes'] > 0 else 0
                star_distribution.append(f"{star}★: {count}명 ({percentage:.1f}%)")
            
            embed_data['fields'].append({
                'name': '⭐ 별등급 분포',
                'value': "\n".join(star_distribution),
                'inline': True
            })
        
        return embed_data