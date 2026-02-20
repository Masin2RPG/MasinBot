"""
세이브코드에서 나무(목제) 수량만 변경하는 테스트 스크립트
기존 세이브코드를 받아서 나무 값만 바꾸고 새로운 세이브코드를 생성
"""

import os
import sys

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decoder import SaveCodeDecoder
from encoder import SaveCodeEncoder
from savecode_decoder import parse_savecode


class LumberModifier:
    """세이브코드의 나무 수량을 변경하는 클래스"""
    
    def __init__(self):
        self.decoder = SaveCodeDecoder()
        self.encoder = SaveCodeEncoder()
    
    def parse_masin_savecode(self, savecode: str) -> dict:
        """
        MasinSaveV2 형식의 세이브코드를 파싱
        
        Format: MasinSaveV2_플레이어이름_캐릭터ID_나무_레벨_힘_민첩_지능_아이템1_아이템2_아이템3_아이템4_아이템5_아이템6
        """
        if not savecode.startswith('MasinSaveV2_'):
            raise ValueError("MasinSaveV2 형식이 아닙니다")
        
        # 프리픽스 제거하고 파싱
        parts = savecode[len('MasinSaveV2_'):].split('_')
        
        if len(parts) < 8:
            raise ValueError(f"세이브코드 형식이 올바르지 않습니다. 예상: 최소 8개 부분, 실제: {len(parts)}개")
        
        try:
            data = {
                'player_name': parts[0],
                'character_id': int(parts[1]),
                'lumber': int(parts[2]),
                'level': int(parts[3]) if len(parts) > 3 else 1,
                'strength': int(parts[4]) if len(parts) > 4 else 0,
                'agility': int(parts[5]) if len(parts) > 5 else 0,
                'intelligence': int(parts[6]) if len(parts) > 6 else 0,
                'items': []
            }
            
            # 아이템 파싱 (7번째 인덱스부터 최대 6개)
            for i in range(7, min(len(parts), 13)):  # 7~12번 인덱스 (6개 아이템)
                item_id = int(parts[i])
                if item_id > 0:
                    data['items'].append(item_id)
                else:
                    data['items'].append(0)
            
            # 6개까지 채우기
            while len(data['items']) < 6:
                data['items'].append(0)
            
            return data
            
        except ValueError as e:
            raise ValueError(f"세이브코드 파싱 중 오류: {e}")
    
    def create_masin_savecode(self, data: dict) -> str:
        """
        데이터를 MasinSaveV2 형식의 세이브코드로 생성
        """
        parts = [
            'MasinSaveV2',
            data.get('player_name', ''),
            str(data.get('character_id', 0)),
            str(data.get('lumber', 0)),
            str(data.get('level', 1)),
            str(data.get('strength', 0)),
            str(data.get('agility', 0)),
            str(data.get('intelligence', 0))
        ]
        
        # 아이템 추가 (6개)
        items = data.get('items', [])
        for i in range(6):
            if i < len(items):
                parts.append(str(items[i]))
            else:
                parts.append('0')
        
        return '_'.join(parts)
    
    def parse_original_savecode(self, savecode: str) -> dict:
        """
        원본 게임 세이브코드를 파싱하여 구조화된 데이터로 변환
        """
        parsed = parse_savecode(
            savecode,
            summon_chunk_n=getattr(self.decoder.config, "SUMMON_CHUNK_N", 0)
        )

        decoded_data = parsed.get('raw_data', [])
        data = {
            'raw_data': decoded_data,
            'gold': parsed.get('gold', 0),
            'lumber': parsed.get('lumber', 0),
            'character_id': parsed.get('hero_type_index', 0),
            'level': parsed.get('level', 0),
            'exp': parsed.get('exp_compact', 0),
            'strength': decoded_data[3] if len(decoded_data) > 3 else 0,
            'agility': decoded_data[5] if len(decoded_data) > 5 else 0,
            'intelligence': decoded_data[7] if len(decoded_data) > 7 else 0,
            'items': []
        }

        item_slots = self.decoder.config.ITEM_SLOTS
        for slot in item_slots:
            if slot < len(decoded_data):
                item_id = decoded_data[slot]
                data['items'].append(item_id)

        return data
    
    def create_original_savecode(self, data: dict, player_name: str) -> str:
        """
        구조화된 데이터를 원본 게임 세이브코드로 변환
        
        Args:
            data: 구조화된 세이브코드 데이터
            player_name: 플레이어 이름 (체크섬 계산에 필요)
        """
        # 원본 raw_data 복사
        load_data = data['raw_data'].copy()
        
        # 스케일 팩터
        scale_factor = 100
        
        # 골드 수량 업데이트 (100으로 나누어 저장)
        if 'gold' in data:
            load_data[1] = data['gold'] // scale_factor
        
        # 나무 수량 업데이트 (100으로 나누어 저장)
        if 'lumber' in data:
            load_data[15] = data['lumber'] // scale_factor
        
        # 인코더로 새로운 세이브코드 생성
        new_savecode = self.encoder.encode_savecode(load_data, player_name)
        
        return new_savecode

    def modify_lumber(self, savecode: str, lumber_amount: int, player_name: str = None) -> str:
        """
        주어진 세이브코드에서 나무 수량을 수정하여 새로운 세이브코드 반환
        MasinSaveV2_ 형식과 원본 게임 형식 모두 지원
        
        Args:
            savecode: 원본 세이브코드 (MasinSaveV2_ 형식 또는 원본 게임 형식)
            lumber_amount: 설정할 나무 수량
            player_name: 플레이어 이름 (원본 게임 세이브코드의 경우 필수)
            
        Returns:
            str: 수정된 세이브코드
        """
        # 세이브코드 형식 감지
        if savecode.startswith('MasinSaveV2_'):
            # 마신 세이브코드 형식 처리
            data = self.parse_masin_savecode(savecode)
            data['lumber'] = lumber_amount
            return self.create_masin_savecode(data)
        else:
            # 원본 게임 세이브코드 형식 처리
            if player_name is None:
                raise ValueError("원본 게임 세이브코드를 수정하려면 player_name이 필요합니다.")
            
            data = self.parse_original_savecode(savecode)
            data['lumber'] = lumber_amount
            return self.create_original_savecode(data, player_name)
    
    def modify_gold(self, savecode: str, gold_amount: int, player_name: str = None) -> str:
        """
        주어진 세이브코드에서 골드 수량을 수정하여 새로운 세이브코드 반환
        현재는 원본 게임 형식만 지원
        
        Args:
            savecode: 원본 세이브코드
            gold_amount: 설정할 골드 수량
            player_name: 플레이어 이름 (체크섬 계산에 필요)
            
        Returns:
            str: 수정된 세이브코드
        """
        if savecode.startswith('MasinSaveV2_'):
            raise ValueError("마신 세이브코드는 현재 골드 수정을 지원하지 않습니다.")
        
        if player_name is None:
            raise ValueError("원본 게임 세이브코드를 수정하려면 player_name이 필요합니다.")
        
        data = self.parse_original_savecode(savecode)
        data['gold'] = gold_amount
        return self.create_original_savecode(data, player_name)
    
    def modify_resources(self, savecode: str, gold_amount: int = None, lumber_amount: int = None, player_name: str = None) -> str:
        """
        주어진 세이브코드에서 골드와 나무를 동시에 수정
        
        Args:
            savecode: 원본 세이브코드
            gold_amount: 설정할 골드 수량 (None이면 변경하지 않음)
            lumber_amount: 설정할 나무 수량 (None이면 변경하지 않음)
            player_name: 플레이어 이름 (원본 게임 세이브코드의 경우 필수)
            
        Returns:
            str: 수정된 세이브코드
        """
        if savecode.startswith('MasinSaveV2_'):
            # 마신 세이브코드는 나무만 지원
            if gold_amount is not None:
                raise ValueError("마신 세이브코드는 현재 골드 수정을 지원하지 않습니다.")
            if lumber_amount is not None:
                data = self.parse_masin_savecode(savecode)
                data['lumber'] = lumber_amount
                return self.create_masin_savecode(data)
            return savecode
        else:
            # 원본 게임 세이브코드
            if player_name is None:
                raise ValueError("원본 게임 세이브코드를 수정하려면 player_name이 필요합니다.")
            
            data = self.parse_original_savecode(savecode)
            
            if gold_amount is not None:
                data['gold'] = gold_amount
            if lumber_amount is not None:
                data['lumber'] = lumber_amount
            
            return self.create_original_savecode(data, player_name)
    
    def test_with_samples(self):
        """샘플 데이터로 테스트"""
        print("=" * 60)
        print("🧪 세이브코드 나무 수량 변경 테스트")
        print("=" * 60)
        
        # 테스트용 샘플 세이브코드 (실제 세이브코드를 넣어서 테스트하세요)
        test_cases = [
            {
                'savecode': 'MasinSaveV2_홍길동_37_50000_15_200_100_150_264_266_268_270_272_274',
                'new_lumber': 100000,
                'description': '기본 테스트'
            },
            {
                'savecode': 'MasinSaveV2_테스터_1_10000_1_0_0_0_0_0_0_0_0_0',
                'new_lumber': 999999,
                'description': '아이템 없는 캐릭터'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 테스트 {i}: {test_case['description']}")
            print("-" * 40)
            
            success, result, original_data = self.modify_lumber(
                test_case['savecode'], 
                test_case['new_lumber']
            )
            
            if success:
                print(f"✅ 테스트 {i} 성공!")
                print(f"📋 결과:")
                print(f"   원본: {test_case['savecode']}")
                print(f"   변경: {result}")
                
                # 검증: 새로운 세이브코드를 다시 파싱해서 확인
                print(f"\n🔍 검증: 새로운 세이브코드 파싱...")
                try:
                    verification = self.parse_masin_savecode(result)
                    print(f"✅ 검증 성공!")
                    print(f"   플레이어: {verification.get('player_name')}")
                    print(f"   나무: {verification.get('lumber', 0):,}")
                    print(f"   캐릭터 ID: {verification.get('character_id')}")
                except Exception as e:
                    print(f"❌ 검증 실패: {str(e)}")
            else:
                print(f"❌ 테스트 {i} 실패: {result}")
    
    def interactive_test(self):
        """대화형 테스트"""
        print("\n" + "=" * 60)
        print("🎮 대화형 나무 수량 변경 테스트")
        print("=" * 60)
        
        while True:
            print("\n📝 세이브코드와 새로운 나무 수량을 입력하세요")
            print("(종료하려면 'quit' 입력)")
            
            # 세이브코드 입력
            savecode = input("\n🔮 세이브코드: ").strip()
            if savecode.lower() == 'quit':
                break
            
            if not savecode:
                print("❌ 세이브코드를 입력해주세요!")
                continue
            
            # 새로운 나무 수량 입력
            try:
                new_lumber_input = input("🌳 새로운 나무 수량: ").strip()
                if new_lumber_input.lower() == 'quit':
                    break
                
                new_lumber = int(new_lumber_input)
                if new_lumber < 0:
                    print("❌ 나무 수량은 0 이상이어야 합니다!")
                    continue
                    
            except ValueError:
                print("❌ 올바른 숫자를 입력해주세요!")
                continue
            
            # 나무 수량 변경 실행
            print(f"\n🔄 처리 중...")
            success, result, original_data = self.modify_lumber(savecode, new_lumber)
            
            if success:
                print(f"\n🎉 성공!")
                print(f"📋 새로운 세이브코드:")
                print(f"   {result}")
                
                # 원본과 비교
                print(f"\n📊 변경 사항:")
                print(f"   플레이어: {original_data.get('player_name', 'Unknown')}")
                print(f"   나무: {original_data.get('lumber', 0):,} → {new_lumber:,}")
                print(f"   차이: {new_lumber - original_data.get('lumber', 0):+,}")
            else:
                print(f"\n❌ 실패: {result}")


def main():
    """메인 실행 함수"""
    modifier = LumberModifier()
    
    print("🚀 세이브코드 나무 수량 변경 도구")
    print("=" * 50)
    
    while True:
        print("\n메뉴를 선택하세요:")
        print("1. 샘플 데이터 테스트")
        print("2. 대화형 테스트")
        print("3. 종료")
        
        choice = input("\n선택 (1-3): ").strip()
        
        if choice == '1':
            modifier.test_with_samples()
        elif choice == '2':
            modifier.interactive_test()
        elif choice == '3':
            print("👋 프로그램을 종료합니다.")
            break
        else:
            print("❌ 올바른 번호를 선택해주세요!")


if __name__ == "__main__":
    main()