

import logging
import re
from typing import Optional

import discord
from discord.ext import commands

# 로컬 모듈 임포트
from config import Config
from decoder import SaveCodeDecoder
from savecode_decoder import decode_savecode2

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SaveCodeBot:
    """디스코드 세이브코드 봇 클래스"""
    
    def __init__(self):
        self.config = Config()
        self.decoder = SaveCodeDecoder()
        
        # 봇 인텐트 설정
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        
        # 봇 인스턴스 생성
        self.bot = commands.Bot(command_prefix=self.config.COMMAND_PREFIX, intents=intents)
        self._setup_events()
        self._setup_commands()
    
    def _setup_events(self):
        """이벤트 핸들러 설정"""
        @self.bot.event
        async def on_ready():
            logger.info(f'봇 준비 완료: {self.bot.user}')
            print(f'봇 준비 완료: {self.bot.user}')
        
        @self.bot.event
        async def on_command_error(ctx: commands.Context, error: commands.CommandError):
            """명령어 오류 처리"""
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("❌ 필수 인자가 누락되었습니다. 명령어 사용법을 확인해주세요.")
            elif isinstance(error, commands.CommandNotFound):
                await ctx.send("❌ 존재하지 않는 명령어입니다.")
            else:
                logger.error(f"명령어 오류: {error}")
                await ctx.send(f"❌ 오류가 발생했습니다: {error}")
    
    def _setup_commands(self):
        """명령어 설정"""
        
        @self.bot.command(name='검증', help='세이브코드의 유효성을 검증합니다')
        async def validate_command(ctx: commands.Context, code: str, *, name: str):
            """세이브코드 유효성 검증 명령어"""
            if not code or not name:
                await ctx.send("❌ 코드와 이름을 모두 입력해주세요.")
                return
            
            try:
                # 기존 함수와 새 함수 둘 다 사용
                is_valid_legacy = decode_savecode2(code, name)
                is_valid_new = self.decoder.validate_savecode(code, name)
                
                # 결과가 다르면 로그에 기록
                if is_valid_legacy != is_valid_new:
                    logger.warning(f"검증 결과 불일치: Legacy={is_valid_legacy}, New={is_valid_new}")
                
                # 기존 함수 결과 우선 사용 (호환성 유지)
                result = "✅ 유효함" if is_valid_legacy else "❌ 유효하지 않음"
                await ctx.send(f"검증 결과: {result}")
                
            except Exception as e:
                logger.error(f"검증 중 오류: {e}")
                await ctx.send(f"❌ 검증 중 오류 발생: {e}")
        
        @self.bot.command(name='아이템', help='세이브코드에서 아이템 목록을 추출합니다')
        async def items_command(ctx: commands.Context, *, code: str):
            """세이브코드에서 아이템 추출 명령어"""
            if not code:
                await ctx.send("❌ 세이브코드를 입력해주세요.")
                return
            
            try:
                items_list = self.decoder.extract_items(code)
                
                if not items_list:
                    await ctx.send("❌ 아이템 정보를 찾을 수 없습니다.")
                    return
                
                response = "\n".join(items_list)
                await ctx.send(f"**세이브코드 아이템 추출 결과:**\n```\n{response}\n```")
                
            except Exception as e:
                logger.error(f"아이템 추출 중 오류: {e}")
                await ctx.send(f"❌ 아이템 추출 중 오류 발생: {e}")
        
        @self.bot.command(name='로드', help='세이브코드를 검증하고 아이템을 추출합니다')
        async def load_command(ctx: commands.Context, name: str, *, code: str):
            """세이브코드 검증 및 아이템 추출 명령어"""
            if not code or not name:
                await ctx.send("❌ 코드와 이름을 모두 입력해주세요.")
                return
            
            try:
                raw_codes = re.split(r'[;\n,]+|\s{1,}', code.strip()) 
                codes = [c.strip().upper() for c in raw_codes if c.strip()]
                for code in codes:
                    print(f"[DEBUG] 로드된 코드들: {code}")  # 디버그용 출력
                # 검증
                    is_valid = decode_savecode2(code, name)
                    result = "✅ 유효함" if is_valid else "❌ 유효하지 않음"
                    
                    # 아이템 추출
                    items_list = self.decoder.extract_items(code)
                    response = "\n".join(items_list)
                    
                    # 결과 전송
                    await ctx.send(f"**검증 결과:** {result}")
                    if items_list:
                        await ctx.send(f"**세이브코드 아이템 추출 결과:**\n```\n{response}\n```")
                
            except Exception as e:
                logger.error(f"로드 처리 중 오류: {e}")
                await ctx.send(f"❌ 로드 처리 중 오류 발생: {e}")
        
        @self.bot.command(name='도움말', help='사용 가능한 명령어를 보여줍니다')
        async def help_command(ctx: commands.Context):
            """도움말 명령어"""
            embed = discord.Embed(
                title="🤖 세이브코드 봇 도움말",
                description="세이브코드 관련 기능을 제공합니다.",
                color=0x00ff00
            )
            
            embed.add_field(
                name="/검증 <코드> <이름>",
                value="세이브코드의 유효성을 검증합니다.",
                inline=False
            )
            
            embed.add_field(
                name="/아이템 <코드>",
                value="세이브코드에서 아이템 목록을 추출합니다.",
                inline=False
            )
            
            embed.add_field(
                name="/로드 <이름> <코드>",
                value="세이브코드를 검증하고 아이템을 추출합니다.",
                inline=False
            )
            
            embed.add_field(
                name="/도움말",
                value="이 도움말을 표시합니다.",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    def run(self):
        """봇 실행"""
        try:
            logger.info("봇을 시작합니다...")
            self.bot.run(self.config.BOT_TOKEN)
        except Exception as e:
            logger.error(f"봇 실행 중 오류: {e}")
            raise


def main():
    """메인 함수"""
    try:
        bot = SaveCodeBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("봇이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"봇 실행 중 치명적 오류: {e}")
        raise


if __name__ == "__main__":
    main()
