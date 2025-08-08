"""
리팩토링된 디스코드 봇
- 클래스 기반 구조로 재구성
- 중복 코드 제거
- 상수 분리
- 에러 처리 개선
- 타입 힌트 추가
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union

import discord
from discord.ext import commands

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlayType(Enum):
    """플레이 타입 열거형"""
    PLAY_TYPE_TRUE = True
    PLAY_TYPE_FALSE = False


@dataclass
class GameConstants:
    """게임 관련 상수들"""
    GAME_VERSION = 7
    UDG_SAVE_VALUE_LENGTH = [6, 3, 6, 3, 6, 3, 6, 3, 3, 3, 2, 3, 4, 2, 4]
    ITEM_SLOTS = [1, 3, 5, 7, 9, 11]  # 아이템이 저장되는 슬롯 인덱스
    
    # 문자 맵핑
    CHAR_MAP_PLAY_TRUE = "1O7EC43VPRN8FXKDTSUQ026HWA5YIM9BJLGZ"
    CHAR_MAP_PLAY_FALSE = "OBX6RAGZKT71N435YDEVPF92LUWQ0IMSCHJ8"
    STRING_SOURCE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890~`!#$^&*()-_=+|{}[]:;<>,.?@"


class ItemDatabase:
    """아이템 데이터베이스 클래스"""
    
    def __init__(self):
        self.items: Dict[int, str] = {
            0: "없음",
            1: "예언의 손길",
            2: "사무엘의 영혼",
            3: "사무엘의 의식 예복",
            4: "사무엘의 고귀한 지팡이",
            5: "패닉소울",
            6: "야휘림의 영혼",
            7: "풍마반지",
            8: "풍신권법",
            9: "색마의 풀어헤쳐진 청천의",
            10: "마천율의 영혼",
            11: "광천검법",
            12: "광마의 칠흑도포",
            13: "청혈주",
            14: "을령의 영혼",
            15: "을령의 정돈된 백옥신의",
            16: "혈마의 반지",
            17: "수라멸마장",
            18: "체프의 영혼",
            19: "체프의 빛나는 장갑",
            20: "체프의 구겨진 천옷",
            21: "체프의 작은구체",
            22: "에누크의 영혼",
            23: "에누크의 끈장갑",
            24: "에누크의 용문양 훈도시",
            25: "에누크의 강철부메랑",
            26: "모나크의 영혼",
            27: "모나크의 위협적인 갑주",
            28: "모나크의 마그넷블레이드",
            29: "모나크의 가죽장갑",
            30: "위트겡의 영혼",
            31: "위트겡의 찢겨진 손",
            32: "위트겡의 허물어버린 손톱",
            33: "위트겡의 낡아버린 가죽",
            34: "용암지옥거미의 영혼",
            35: "용암지옥거미의 화염",
            36: "용암지옥거미의 뾰족한 다리",
            37: "용암지옥거미의 탄탄한 껍질",
            38: "포악한자의 미약한 무력",
            39: "포악한자의 미약한 영혼",
            40: "포악한자의 미약한 요력",
            41: "포악한자의 미약한 사력",
            42: "카마엘의 영혼",
            43: "파괴의 갑옷",
            44: "파괴의 장갑",
            45: "파괴의검",
            46: "데스펄엑스",
            47: "죽음의 손길",
            48: "아즈라엘의 영혼",
            49: "아즈라엘의 사슬갑옷",
            50: "카인의 견고한 팔목대",
            51: "카인의 배신의 대검",
            52: "카인의 브론즈 플레이트",
            53: "카인의 영혼",
            54: "Go To Hell !!!!!!!",
            55: "루드비아나의 약혼반지",
            56: "파워즈의 쇠도끼",
            57: "악마삼총사의 지령서 Go",
            58: "악마삼총사의 지령서 Hell",
            59: "악마삼총사의 지령서 To",
            60: "슈나이더를 쓰러트린자",
            61: "루시퍼의 계약서",
            62: "루시퍼의 권속",
            63: "루시퍼의 인정",
            64: "루시퍼의 축복",
            65: "하늘이 되고 싶었던 자 [강력]",
            66: "하늘이 되고 싶었던 자 [강인]",
            67: "하늘이 되고 싶었던 자 [전능]",
            68: "로망 Of 아즈라엘 [강력]",
            69: "로망 Of 아즈라엘 [강인]",
            70: "로망 Of 아즈라엘 [전능]",
            71: "그레모리의 오래된 목걸이",
            72: "전쟁",
            73: "투신의 기운",
            74: "위대한 공작의 타오르는 둔기",
            75: "구시온의 영혼",
            76: "구시온의 값비싼 갑주",
            77: "분노의 갑주",
            78: "사타니스",
            79: "베리알의 영혼",
            80: "그레모리의 소중한 목걸이",
            81: "위리놈의 라이벌",
            82: "전쟁의 슬픔",
            83: "§펜타그램§ - [그레모리]",
            84: "§펜타그램§ - [에리고스]",
            85: "§펜타그램§ - [오세]",
            86: "태뢰진갑",
            87: "암살용 가죽 장갑",
            88: "파이몬의 영혼",
            89: "진:태뢰진갑",
            90: "진:암살용 가죽 장갑",
            91: "진:파이몬의 영혼",
            92: "교만의 태뢰진갑",
            93: "교만의 암살용 가죽 장갑",
            94: "슬픈 영혼의 파이몬",
            95: "탐욕의 마력",
            96: "어비스 of 시타엘 [강력]",
            97: "어비스 of 시타엘 [강인]",
            98: "어비스 of 시타엘 [전능]",
            99: "질투의 마력",
            100: "아벨의 고통 [강력]",
            101: "아벨의 고통 [강인]",
            102: "아벨의 고통 [전능]",
            103: "음욕의 마력",
            104: "디스트럭티브",
            105: "몰로크의 영혼",
            106: "질긴 철가죽",
            107: "블레이즈 블레이드",
            108: "사타나키아의 영혼",
            109: "어긋나버린 형제의 레지스트",
            110: "리리스의 검은 날개 옷",
            111: "리리스의 마신구",
            112: "리리스의 영혼",
            113: "강력의 마신석",
            114: "강인의 마신석",
            115: "전능의 마신석",
            116: "나태의 마력",
            117: "디스트럭티브",
            118: "프라이드소울",
            119: "다크매터",
            120: "가디스 폴른",
            121: "데스티니 사이드",
            122: "마궁 샤르베",
            123: "브레이크 블레이드",
            124: "블라드 네클레스",
            125: "아슈켈론",
            126: "제람불뤼트",
            127: "제블나인",
            128: "합쳐진 아담과 리리스의 마신구",
            129: "티르빙",
            130: "베리알의 권속기",
            131: "사탄의 힘을 내는 자",
            132: "죽음을 부정하는 자",
            133: "제블나인 서열 7위",
            134: "잔혹한 인연",
            135: "악령공주의 영혼",
            136: "파괴신 [강력]",
            137: "파괴신 [강인]",
            138: "파괴신 [전능]",
            139: "블레이즈 블레이드[모조품]",
            140: "불완전한 플뤼톤의 영혼",
            141: "이프리트의 영혼",
            142: "흑암의 영혼갑주",
            143: "불완전한 흑염의 영혼갑주",
            144: "데빌테스트",
            145: "그람다이트",
            146: "디스트럭티브",
            147: "완전한 플뤼톤의 영혼",
            148: "완전한 플뤼톤의 영혼갑주",
            149: "단탈리온의 영혼",
            150: "더블잭나이프",
            151: "안드레알푸스의 가죽팬티",
            152: "안드레알푸스의 강철채찍",
            153: "안드레알푸스의 영혼",
            154: "자간의 영혼",
            155: "자간의 푸른 영혼의 갑주",
            156: "자간의 푸른구체",
            157: "후엠아이",
            158: "화신 [강력]",
            159: "화신 [강인]",
            160: "화신 [전능]",
            161: "대마신 [강력]",
            162: "대마신 [강인]",
            163: "대마신 [전능]",
            164: "태초의 무력",
            165: "델모크의 영혼",
            166: "불이 모여드는 자",
            167: "악령이 모여드는 자",
            168: "지옥의 어머니",
            169: "위리놈의 대적자",
            170: "최초의 살인자",
            172: "레바테인",
            173: "옥마혈도",
            174: "예궁 피나카",
            175: "지옥묵시록",
            176: "아몬의 아귀혈복",
            177: "아몬의 지옥신의",
            178: "아몬의 패천투갑",
            179: "아몬의 강력한 영혼",
            180: "아몬의 강인한 영혼",
            181: "아몬의 전능한 영혼",
            182: "태초의 마신 [강력]",
            183: "태초의 마신 [강인]",
            184: "태초의 마신 [전능]",
            185: "사탄의 근원",
            186: "강자멸시",
            187: "선악과",
            188: "죽음의 낙인",
            189: "신기루",
            190: "뱀페러가 건네준 심장덩어리",
            191: "교만의 마력",
            192: "분노의 마력",
            193: "폭식의 마력",
            194: "종말의 뿔피리",
            195: "마황의 마신석",
            196: "크리스마스의 재림 [1단계]",
            197: "크리스마스의 재림 [2단계]",
            198: "크리스마스의 재림 [3단계]",
            199: "크리스마스의 재림 [4단계]",
            200: "크리스마스의 재림 [5단계]",
            201: "크리스마스의 재림 [6단계]",
            202: "완전한 크리스마스의 재림 [강력]",
            203: "완전한 크리스마스의 재림 [강인]",
            204: "완전한 크리스마스의 재림 [전능]",
            205: "검붉게 정화된 지옥문",
            206: "영겁을 머금은 지옥문",
            207: "하얗게 침식된 지옥문",
            208: "묵시록의 강력한 영혼",
            209: "묵시록의 강인한 영혼",
            210: "묵시록의 전능한 영혼",
            211: "죄:가디스폴른",
            212: "죄:그람다이트",
            213: "죄:데스티니 사이드",
            214: "죄:낙인",
            215: "죄:레바테인",
            216: "죄:마황의 마신석",
            217: "죄:브레이크 블레이드",
            218: "죄:블라드 네클레스",
            219: "죄:샤르베",
            220: "죄:신기루",
            221: "죄:아슈켈론",
            222: "죄:에덴의 결정구",
            223: "죄:옥마혈도",
            224: "죄:제람불뤼트",
            225: "죄:제블나인",
            226: "죄:종말의 뿔피리",
            227: "죄:진조의 심장",
            228: "죄:티르빙",
            229: "죄:피나카",
            230: "죄:지옥묵시록",
            231: "죄:인과율의 수레바퀴",
            232: "오망성의 샛별",
            233: "죄:오망성의 눈물",
            234: "데빌엔드",
            235: "죄:데빌엔드",
            236: "라파엘의 강인한 영혼",
            237: "라파엘의 강력한 영혼",
            238: "라파엘의 전능한 영혼",
            239: "희망과 절망의 대천사 [강인]",
            240: "희망과 절망의 대천사 [강력]",
            241: "희망과 절망의 대천사 [전능]",
            242: "죄:붉은 밤",
            243: "죄:디아블로의 심장",
            244: "죄:아르스 게티아",
            245: "가브리엘의 강인한 영혼",
            246: "가브리엘의 강력한 영혼",
            247: "가브리엘의 전능한 영혼",
            248: "어두운 자들의 유혹",
            249: "풀려나버린 죄의 원죄",
            250: "최초의 금지된 성서",
            251: "죄의 원죄",
            252: "몰려드는 어두운 자들의 유혹",
            253: "금지된 성서",
            254: "영원의 밤",
            255: "죄:영원의 밤",
            256: "몰려드는 어두운 자들의 유혹",
            257: "절망 황녀의 피눈물",
            258: "죄:절망",
            259: "아포칼립스",
            260: "죄:아포칼립스",
            261: "혼돈",
            262: "죄:혼돈",
            263: "무거운 죄의 십자가",
            264: "거대한 죄의 십자가",
            265: "육신을 짓이기는 월계관",
            266: "영혼을 짓이기는 월계관",
            267: "재앙을 부르는 피의 잔",
            268: "멸망을 부르는 피의 잔",
            269: "우리엘의 강인한 영혼",
            270: "심판하는자의 강인한 영혼",
            271: "우리엘의 강력한 영혼",
            272: "심판하는자의 강력한 영혼",
            273: "우리엘의 전능한 영혼",
            274: "심판하는자의 전능한 영혼",
            275: "파괴검 - 누야",
            276: "죄:누야",
            277: "천마신검",
            278: "죄:천마신검",
            279: "이클립스",
            280: "죄:이클립스",
            281: "아카식 레코드"
        }
    
    def get_item_name(self, item_id: int) -> str:
        """아이템 ID로 아이템 이름 조회"""
        return self.items.get(item_id, f"알 수 없는 아이템({item_id})")


class SaveCodeDecoder:
    """세이브코드 디코더 클래스"""
    
    def __init__(self):
        self.constants = GameConstants()
        self.item_db = ItemDatabase()
    
    def get_nine_n(self, m: int) -> int:
        """9의 n제곱을 계산하는 함수"""
        n = 0
        j = 1
        for _ in range(m):
            n += j * 9
            j *= 10
        return n
    
    def get_string_value(self, text: str) -> int:
        """문자열의 값을 계산 (ASCII/UTF-8 자동 처리)"""
        try:
            text.encode('ascii')
            return self._get_string_value_ascii(text)
        except UnicodeEncodeError:
            return self._get_string_value_utf8(text)
    
    def _get_string_value_ascii(self, text: str) -> int:
        """ASCII 문자열 값 계산"""
        text = text.upper()
        temp_value = 0
        for i, char in enumerate(text):
            try:
                index = self.constants.STRING_SOURCE.index(char) + 1
                temp_value += index * (i + 1)
            except ValueError:
                logger.warning(f"Invalid character '{char}' in ASCII string")
        return temp_value
    
    def _get_string_value_utf8(self, text: str) -> int:
        """UTF-8 문자열 값 계산"""
        temp_bytes = text.upper().encode('utf-8')
        temp_value = 0
        for i, byte in enumerate(temp_bytes):
            char = chr(byte)
            try:
                index = self.constants.STRING_SOURCE.index(char) + 1
                temp_value += index * (i + 1)
            except ValueError:
                logger.warning(f"Invalid character '{char}' in UTF-8 string")
        return temp_value
    
    def code_str_to_int(self, value: str, play_type: bool = True) -> int:
        """코드 문자열을 정수로 변환"""
        char_map = (self.constants.CHAR_MAP_PLAY_TRUE if play_type 
                   else self.constants.CHAR_MAP_PLAY_FALSE)
        
        result = 0
        strlen = len(value)
        
        for i, char in enumerate(value):
            try:
                index = char_map.index(char)
            except ValueError:
                raise ValueError(f"Invalid character '{char}' in code")
            
            if i != strlen - 1:
                result = index * 36
            else:
                result += index
        
        return result
    
    def decode_savecode(self, code: str, play_type: bool = True) -> List[int]:
        """세이브코드를 디코드하여 로드 데이터 반환"""
        # 코드 전처리
        code = code.replace("-", "").upper()
        
        # 코드 길이 검증
        if len(code) % 2 != 0:
            raise ValueError("코드 길이가 올바르지 않습니다 (홀수 길이)")
        
        # 2글자씩 처리하여 숫자 문자열 생성
        temp_string = ""
        for i in range(0, len(code), 2):
            pair = code[i:i+2]
            if len(pair) < 2:
                raise ValueError("코드 길이가 올바르지 않습니다")
            
            value = self.code_str_to_int(pair, play_type)
            temp_string += f"{value:03d}"
        
        # 세이브 값 길이에 따라 분할
        load_data = []
        position = 0
        
        for length in self.constants.UDG_SAVE_VALUE_LENGTH:
            chunk = temp_string[position:position + length]
            position += length
            
            if chunk == "":
                load_data.append(0)
            else:
                load_data.append(int(chunk))
        
        return load_data
    
    def validate_savecode(self, code: str, player_name: str) -> bool:
        """세이브코드의 유효성 검증"""
        try:
            load_data = self.decode_savecode(code)
            
            # 체크넘 계산
            checknum = 0
            save_size = len(self.constants.UDG_SAVE_VALUE_LENGTH)
            
            for i in range(save_size):
                if i != 8:  # 9번째 인덱스(체크넘)는 제외
                    checknum += load_data[i] * (i + 1)
            
            # 게임 버전 보정
            if self.constants.GAME_VERSION > 99:
                checknum += self.constants.GAME_VERSION % ord('d')
            else:
                checknum += self.constants.GAME_VERSION
            
            # 플레이어 이름 기반 가산
            string_value = self.get_string_value(player_name)
            checknum += string_value
            checknum %= self.get_nine_n(self.constants.UDG_SAVE_VALUE_LENGTH[8])
            
            # 검증 결과 반환
            return checknum == load_data[8]
            
        except Exception as e:
            logger.error(f"세이브코드 검증 중 오류: {e}")
            return False
    
    def extract_items(self, code: str) -> List[str]:
        """세이브코드에서 아이템 목록 추출"""
        load_data = self.decode_savecode(code)
        items_list = []
        
        for idx, slot_index in enumerate(self.constants.ITEM_SLOTS, 1):
            if slot_index < len(load_data):
                item_code = load_data[slot_index]
                item_name = self.item_db.get_item_name(item_code)
                items_list.append(f"{idx}번째 아이템: {item_name}")
            else:
                items_list.append(f"{idx}번째 아이템: 데이터 없음")
        
        return items_list


class DiscordBot:
    """디스코드 봇 클래스"""
    
    def __init__(self, token: str, prefix: str = "/"):
        self.token = token
        self.decoder = SaveCodeDecoder()
        
        # 봇 인텐트 설정
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        
        # 봇 인스턴스 생성
        self.bot = commands.Bot(command_prefix=prefix, intents=intents)
        self._setup_events()
        self._setup_commands()
    
    def _setup_events(self):
        """이벤트 핸들러 설정"""
        @self.bot.event
        async def on_ready():
            logger.info(f'봇 준비 완료: {self.bot.user}')
            print(f'봇 준비 완료: {self.bot.user}')
    
    def _setup_commands(self):
        """명령어 설정"""
        
        @self.bot.command(name='검증')
        async def validate_command(ctx: commands.Context, code: str, *, name: str):
            """세이브코드 유효성 검증 명령어"""
            try:
                is_valid = self.decoder.validate_savecode(code, name)
                result = "✅ 유효함" if is_valid else "❌ 유효하지 않음"
                await ctx.send(f"검증 결과: {result}")
                
            except Exception as e:
                logger.error(f"검증 중 오류: {e}")
                await ctx.send(f"검증 중 오류 발생: {e}")
        
        @self.bot.command(name='아이템')
        async def items_command(ctx: commands.Context, *, code: str):
            """세이브코드에서 아이템 추출 명령어"""
            try:
                items_list = self.decoder.extract_items(code)
                response = "\n".join(items_list)
                await ctx.send(f"세이브코드 아이템 추출 결과:\n{response}")
                
            except Exception as e:
                logger.error(f"아이템 추출 중 오류: {e}")
                await ctx.send(f"아이템 추출 중 오류 발생: {e}")
        
        @self.bot.command(name='로드')
        async def load_command(ctx: commands.Context, code: str, *, name: str):
            """세이브코드 검증 및 아이템 추출 명령어"""
            try:
                # 검증
                is_valid = self.decoder.validate_savecode(code, name)
                result = "✅ 유효함" if is_valid else "❌ 유효하지 않음"
                
                # 아이템 추출
                items_list = self.decoder.extract_items(code)
                response = "\n".join(items_list)
                
                # 결과 전송
                await ctx.send(f"검증 결과: {result}")
                await ctx.send(f"세이브코드 아이템 추출 결과:\n{response}")
                
            except Exception as e:
                logger.error(f"로드 처리 중 오류: {e}")
                await ctx.send(f"로드 처리 중 오류 발생: {e}")
    
    def run(self):
        """봇 실행"""
        self.bot.run(self.token)


# 봇 실행
if __name__ == "__main__":
    # 봇 토큰 (보안상 환경변수나 설정파일에서 가져오는 것을 권장)
    from config import BOT_TOKEN

    # 봇 인스턴스 생성 및 실행
    discord_bot = DiscordBot(BOT_TOKEN)
    discord_bot.run()
