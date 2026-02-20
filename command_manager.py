"""
봇 명령어 시스템 관리 모듈
Discord 봇의 명령어들을 기능별로 그룹화하여 관리
"""

import logging
from typing import Dict, List

import discord
from discord.ext import commands

from raid_system import RaidWaitingSystem
from savecode_manager import SaveCodeManager

logger = logging.getLogger(__name__)


class SaveCodeCommands:
    """세이브코드 관련 명령어 그룹"""
    
    def __init__(self, bot: commands.Bot, savecode_manager: SaveCodeManager, decoder):
        self.bot = bot
        self.savecode_manager = savecode_manager
        self.decoder = decoder
        self._register_commands()
    
    def _register_commands(self):
        """세이브코드 관련 명령어 등록"""
        
        @self.bot.command(name='검증', help='세이브코드의 유효성을 검증합니다')
        async def validate_command(ctx: commands.Context, code: str, *, name: str):
            """세이브코드 유효성 검증 명령어"""
            if not code or not name:
                await ctx.send("❌ 코드와 이름을 모두 입력해주세요.")
                return
            
            try:
                # SaveCodeManager를 통한 검증
                decoded_data = self.savecode_manager.decode_savecode(code, name)
                is_valid = bool(decoded_data)
                
                result = "✅ 유효함" if is_valid else "❌ 유효하지 않음"
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
                
                # 아이템 정보를 Discord Embed로 표시
                embed = discord.Embed(
                    title="📦 아이템 목록",
                    description=f"총 {len(items_list)}개의 아이템",
                    color=0x3498db
                )
                
                # 아이템을 10개씩 나누어 필드로 표시
                for i in range(0, len(items_list), 10):
                    items_chunk = items_list[i:i+10]
                    items_text = "\n".join([f"• {item}" for item in items_chunk])
                    
                    embed.add_field(
                        name=f"아이템 {i+1}-{min(i+10, len(items_list))}",
                        value=items_text,
                        inline=True
                    )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"아이템 추출 중 오류: {e}")
                await ctx.send(f"❌ 아이템 추출 중 오류 발생: {e}")
        
        @self.bot.command(name='영웅', help='세이브코드에서 영웅 정보를 추출합니다')
        async def heroes_command(ctx: commands.Context, *, code: str):
            """세이브코드에서 영웅 정보 추출 명령어"""
            if not code:
                await ctx.send("❌ 세이브코드를 입력해주세요.")
                return
            
            try:
                resource_data = self.savecode_manager.extract_resources(code)
                if not resource_data:
                    await ctx.send("❌ 영웅 정보를 찾을 수 없습니다.")
                    return
                
                heroes = resource_data.get('heroes', [])
                if not heroes:
                    await ctx.send("❌ 영웅 데이터가 없습니다.")
                    return
                
                processed_heroes = self.savecode_manager.process_heroes_data(heroes)
                
                embed = discord.Embed(
                    title="🦸 영웅 정보",
                    description=f"총 {len(processed_heroes)}명의 영웅",
                    color=0xe74c3c
                )
                
                # 영웅을 5명씩 나누어 필드로 표시
                for i in range(0, len(processed_heroes), 5):
                    heroes_chunk = processed_heroes[i:i+5]
                    heroes_text = "\n".join([hero['formatted_info'] for hero in heroes_chunk])
                    
                    embed.add_field(
                        name=f"영웅 {i+1}-{min(i+5, len(processed_heroes))}",
                        value=heroes_text,
                        inline=True
                    )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"영웅 정보 추출 중 오류: {e}")
                await ctx.send(f"❌ 영웅 정보 추출 중 오류 발생: {e}")



class RaidCommands:
    """레이드 관련 명령어 그룹"""
    
    def __init__(self, bot: commands.Bot, raid_system: RaidWaitingSystem, config):
        self.bot = bot
        self.raid_system = raid_system
        self.config = config
        self._register_commands()
    
    def _register_commands(self):
        """레이드 관련 명령어 등록"""
        pass  # 레이드는 이미 Persistent View로 구현되어 있음


class UtilityCommands:
    """유틸리티 명령어 그룹"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._register_commands()
    
    def _register_commands(self):
        """유틸리티 명령어 등록"""
        
        @self.bot.command(name='도움말', help='사용 가능한 명령어를 보여줍니다')
        async def help_command(ctx: commands.Context):
            """도움말 명령어"""
            embed = discord.Embed(
                title="🤖 세이브코드 봇 도움말",
                description="세이브코드 관련 기능을 제공합니다.",
                color=0x00ff00
            )
            
            # 세이브코드 관련 명령어
            embed.add_field(
                name="📄 세이브코드 명령어",
                value=(
                    "`/검증 <코드> <이름>` - 세이브코드 유효성 검증\n"
                    "`/아이템 <코드>` - 아이템 목록 추출\n"
                    "`/영웅 <코드>` - 영웅 정보 추출\n"
                    "`/통계 <여러코드>` - 여러 세이브코드 통계 분석"
                ),
                inline=False
            )
            
            # 최적화 관련 명령어

            
            # 레이드 관련 기능
            embed.add_field(
                name="🏛️ 레이드 기능",
                value=(
                    "레이드 관련 기능은 레이드 버튼을 통해 사용할 수 있습니다.\n"
                    "관리자가 `/레이드메시지` 명령어로 버튼을 설치할 수 있습니다."
                ),
                inline=False
            )
            
            # 기타 명령어
            embed.add_field(
                name="🔧 기타 명령어",
                value=(
                    "`/도움말` - 이 도움말 표시\n"
                    "`/아이템찾기 <이름>` - 아이템 검색"
                ),
                inline=False
            )
            
            embed.set_footer(text="명령어는 '/명령어 도움말'로 개별 도움말을 볼 수 있습니다.")
            await ctx.send(embed=embed)


class CommandManager:
    """명령어 시스템 전체 관리자"""
    
    def __init__(self, bot: commands.Bot, savecode_manager: SaveCodeManager, 
                 raid_system: RaidWaitingSystem, 
                 decoder, config):
        self.bot = bot
        
        # 각 명령어 그룹 초기화
        self.savecode_commands = SaveCodeCommands(bot, savecode_manager, decoder)
        self.raid_commands = RaidCommands(bot, raid_system, config)
        self.utility_commands = UtilityCommands(bot)
    
    def get_command_groups(self) -> Dict[str, object]:
        """명령어 그룹 목록 반환"""
        return {
            'savecode': self.savecode_commands,
            'raid': self.raid_commands,
            'utility': self.utility_commands
        }