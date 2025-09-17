

import json
import logging
import re
from typing import Optional

import discord
from discord import SelectOption, ui
from discord.ext import commands

# 로컬 모듈 임포트
from config import Config
from core_optimizer import CoreOptimizer
from decoder import SaveCodeDecoder
from item_searcher import ItemSearcher
from savecode_decoder import decode_savecode2

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoreTypeSelector(ui.Select):
    """코어 타입 선택 드롭다운"""
    
    def __init__(self, gems_data, core_optimizer):
        self.gems_data = gems_data
        self.core_optimizer = core_optimizer
        
        options = [
            SelectOption(
                label="전설 코어",
                description="의지력 11, 능력 포인트: 10, 14",
                emoji="🟠",
                value="전설"
            ),
            SelectOption(
                label="유물 코어", 
                description="의지력 15, 능력 포인트: 10, 14, 17, 18, 19, 20",
                emoji="🟣",
                value="유물"
            ),
            SelectOption(
                label="고대 코어",
                description="의지력 17, 능력 포인트: 10, 14, 17, 18, 19, 20", 
                emoji="🔴",
                value="고대"
            )
        ]
        
        super().__init__(
            placeholder="코어 타입을 선택하세요...",
            min_values=1,
            max_values=3,  # 멀티 코어 지원
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """코어 타입 선택 콜백"""
        selected_cores = self.values
        
        # 선택된 코어들로 최적화 수행
        if len(selected_cores) == 1:
            # 단일 코어
            result = self.core_optimizer.find_optimal_combination(selected_cores[0], self.gems_data)
            await self._send_single_core_result(interaction, result)
        else:
            # 멀티 코어
            result = self.core_optimizer.optimize_multiple_cores(selected_cores, self.gems_data)
            await self._send_multi_core_result(interaction, result, selected_cores)
    
    async def _send_single_core_result(self, interaction: discord.Interaction, result):
        """단일 코어 결과 전송"""
        if "error" in result:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚡ 젬 최적화 결과",
            description=f"**{result['core_type']} 코어** 최적화 완료!",
            color=self._get_core_color(result['core_type'])
        )
        
        # 코어 정보
        embed.add_field(
            name="🔮 코어 상태",
            value=f"```yaml\n타입: {result['core_type']}\n의지력: {result['core_willpower']}\n사용: {result['total_willpower_used']}/{result['core_willpower']}\n```",
            inline=True
        )
        
        # 잼 정보
        embed.add_field(
            name="💎 선택된 잼",
            value=f"```yaml\n잼: {', '.join(result['gems'])}\n개수: {result['gem_count']}개\n질서: {result['total_order_points']}\n```",
            inline=True
        )
        
        # 능력 상태
        activated = ', '.join(map(str, result['activated_abilities'])) if result['activated_abilities'] else '없음'
        efficiency = len(result['activated_abilities']) / len(result['all_abilities']) * 100
        
        embed.add_field(
            name="⚡ 능력 상태",
            value=f"```yaml\n활성화: {activated}\n효율성: {efficiency:.1f}%\n```",
            inline=False
        )
        
        # 진행바 추가
        willpower_bar = self._create_progress_bar(result['total_willpower_used'], result['core_willpower'])
        embed.add_field(
            name="📊 의지력 사용량",
            value=f"```{willpower_bar}```",
            inline=False
        )
        
        # 새로운 최적화 버튼 추가
        view = GemOptimizationView(self.gems_data, self.core_optimizer)
        embed.set_footer(text="🔄 다시 최적화하려면 아래 버튼을 사용하세요!")
        
        await interaction.response.send_message(embed=embed, view=view)
    
    async def _send_multi_core_result(self, interaction: discord.Interaction, result, core_types):
        """멀티 코어 결과 전송"""
        if "error" in result:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        
        # 메인 대시보드
        embed = discord.Embed(
            title="🎮 멀티 젬 최적화 결과",
            description=f"**{len(core_types)}개 코어** 동시 최적화 완료!",
            color=0x9b59b6
        )
        
        # 전체 요약
        total_gems_used = result['total_gems_used']
        total_available = result['total_available_gems']
        usage_percentage = (total_gems_used / total_available * 100) if total_available > 0 else 0
        
        embed.add_field(
            name="📊 전체 요약",
            value=f"```yaml\n코어: {len(core_types)}개\n사용 잼: {total_gems_used}/{total_available}개\n사용률: {usage_percentage:.1f}%\n```",
            inline=False
        )
        
        # 각 코어별 상태
        for i, core_result in enumerate(result['cores']):
            if core_result['gem_count'] > 0:
                gems_str = ', '.join(core_result['gems'])
                activated_str = ', '.join(map(str, core_result['activated_abilities'])) if core_result['activated_abilities'] else '없음'
                
                embed.add_field(
                    name=f"🔮 {core_result['core_type']} #{i+1}",
                    value=f"```yaml\n잼: {gems_str}\n질서: {core_result['total_order_points']}\n활성화: {activated_str}\n```",
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"🔮 {core_result['core_type']} #{i+1}",
                    value="```yaml\n상태: 잼 없음\n질서: 0\n활성화: 없음\n```",
                    inline=True
                )
        
        # 새로운 최적화 버튼 추가
        view = GemOptimizationView(self.gems_data, self.core_optimizer)
        embed.set_footer(text="🔄 다시 최적화하려면 아래 버튼을 사용하세요!")
        
        await interaction.response.send_message(embed=embed, view=view)
    
    def _get_core_color(self, core_type):
        """코어 타입별 색상"""
        colors = {
            "전설": 0xf39c12,  # 주황색
            "유물": 0x9b59b6,  # 보라색
            "고대": 0xe74c3c   # 빨간색
        }
        return colors.get(core_type, 0x95a5a6)
    
    def _create_progress_bar(self, current, maximum, length=15):
        """진행바 생성"""
        if maximum == 0:
            return "▱" * length
        
        filled = int((current / maximum) * length)
        bar = "▰" * filled + "▱" * (length - filled)
        return bar


class GemOptimizationView(ui.View):
    """젬 최적화 메인 UI"""
    
    def __init__(self, gems_data, core_optimizer):
        super().__init__(timeout=300)  # 5분 타임아웃
        self.gems_data = gems_data
        self.core_optimizer = core_optimizer
        
        # 코어 선택 드롭다운 추가
        self.add_item(CoreTypeSelector(gems_data, core_optimizer))
    
    @ui.button(label="🔄 새로운 잼으로 다시", style=discord.ButtonStyle.primary, emoji="🆕")
    async def new_gems_button(self, interaction: discord.Interaction, button: ui.Button):
        """새로운 잼 입력 버튼"""
        modal = GemInputModal(self.core_optimizer)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="❓ 도움말", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def help_button(self, interaction: discord.Interaction, button: ui.Button):
        """도움말 버튼"""
        embed = discord.Embed(
            title="💎 젬 최적화 도움말",
            description="인터랙티브 젬 최적화 사용법",
            color=0x3498db
        )
        
        embed.add_field(
            name="📝 잼 형식",
            value="```\n25 = 의지력 2, 질서포인트 5\n36 = 의지력 3, 질서포인트 6\n47 = 의지력 4, 질서포인트 7\n```",
            inline=False
        )
        
        embed.add_field(
            name="🔮 코어 정보",
            value="```\n전설: 의지력 11, 능력 [10, 14]\n유물: 의지력 15, 능력 [10, 14, 17, 18, 19, 20]\n고대: 의지력 17, 능력 [10, 14, 17, 18, 19, 20]\n```",
            inline=False
        )
        
        embed.add_field(
            name="🎯 사용법",
            value="1. 위 드롭다운에서 코어 선택\n2. 🆕 버튼으로 새 잼 입력\n3. 자동으로 최적화 결과 표시",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def on_timeout(self):
        """타임아웃 시 버튼 비활성화"""
        for item in self.children:
            item.disabled = True


class GemInputModal(ui.Modal, title='💎 젬 정보 입력'):
    """젬 입력 모달"""
    
    def __init__(self, core_optimizer):
        super().__init__()
        self.core_optimizer = core_optimizer
    
    gems_input = ui.TextInput(
        label='잼 정보',
        placeholder='예: 25 35 45 26 36 16',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 시"""
        gems_text = self.gems_input.value.strip()
        
        if not gems_text:
            await interaction.response.send_message("❌ 잼 정보를 입력해주세요!", ephemeral=True)
            return
        
        # 잼 파싱
        gems = gems_text.split()
        
        # 잼 유효성 검사
        valid_gems = []
        for gem in gems:
            if len(gem) == 2 and gem.isdigit():
                valid_gems.append(gem)
            else:
                await interaction.response.send_message(f"❌ 잘못된 잼 형식: '{gem}' (예: 25, 36)", ephemeral=True)
                return
        
        if not valid_gems:
            await interaction.response.send_message("❌ 유효한 잼이 없습니다!", ephemeral=True)
            return
        
        # 새로운 최적화 UI 표시
        embed = discord.Embed(
            title="💎 젬 최적화 설정",
            description=f"**입력된 잼:** `{' '.join(valid_gems)}`\n**잼 개수:** {len(valid_gems)}개",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="📋 다음 단계",
            value="아래 드롭다운에서 코어 타입을 선택하여 최적화를 시작하세요!",
            inline=False
        )
        
        view = GemOptimizationView(valid_gems, self.core_optimizer)
        await interaction.response.send_message(embed=embed, view=view)


class SaveCodeBot:
    """디스코드 세이브코드 봇 클래스"""
    
    def __init__(self):
        self.config = Config()
        self.decoder = SaveCodeDecoder()
        self.item_searcher = ItemSearcher()  # 아이템 검색기 초기화
        self.core_optimizer = CoreOptimizer()  # 코어 최적화기 초기화
        
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
        
        @self.bot.command(name='값', help='아이템 이름으로 해당 아이템의 정수 값을 찾습니다')
        async def value_command(ctx: commands.Context, *, item_name: str):
            """아이템 이름으로 값을 찾는 명령어"""
            if not item_name:
                await ctx.send("❌ 아이템 이름을 입력해주세요.")
                return
            
            try:
                # 매칭되는 아이템들 찾기
                matching_items = self.item_searcher.find_matching_items(item_name)
                
                if not matching_items:
                    await ctx.send(f"❌ '{item_name}'과(와) 일치하는 아이템을 찾을 수 없습니다.")
                    return
                
                if len(matching_items) == 1:
                    # 하나만 찾았을 때
                    key, item_info, value = matching_items[0]
                    embed = discord.Embed(
                        title="🔍 아이템 값 조회 결과",
                        color=0x00ff00
                    )
                    embed.add_field(name="아이템명", value=item_info, inline=False)
                    embed.add_field(name="정수값", value=f"```{value}```", inline=False)
                    await ctx.send(embed=embed)
                else:
                    # 여러 개 찾았을 때
                    response = f"**'{item_name}'로 검색된 아이템들:**\n"
                    for i, (key, item_info, value) in enumerate(matching_items[:5], 1):  # 최대 5개만 표시
                        clean_name = self.item_searcher._clean_item_name(item_info)[:50]  # 50자로 제한
                        response += f"{i}. `{clean_name}` - 값: `{value}`\n"
                    
                    if len(matching_items) > 5:
                        response += f"\n... 그 외 {len(matching_items) - 5}개 더 있습니다."
                    
                    await ctx.send(response)
                
            except Exception as e:
                logger.error(f"아이템 값 검색 중 오류: {e}")
                await ctx.send(f"❌ 아이템 값 검색 중 오류 발생: {e}")
        
        @self.bot.command(name='통계', help='아이템 데이터베이스 통계를 표시합니다')
        async def stats_command(ctx: commands.Context):
            """아이템 데이터베이스 통계 명령어"""
            try:
                stats = self.item_searcher.get_stats()
                
                embed = discord.Embed(
                    title="📊 아이템 데이터베이스 통계",
                    color=0x3498db
                )
                
                embed.add_field(
                    name="총 아이템 수", 
                    value=f"```{stats['total_items']:,}개```", 
                    inline=True
                )
                embed.add_field(
                    name="총 값 개수", 
                    value=f"```{stats['total_rowcodes']:,}개```", 
                    inline=True
                )
                embed.add_field(
                    name="매칭된 아이템", 
                    value=f"```{stats['matched_items']:,}개```", 
                    inline=True
                )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"통계 조회 중 오류: {e}")
                await ctx.send(f"❌ 통계 조회 중 오류 발생: {e}")
        
        @self.bot.command(name='코어', help='코어에 잼을 조합하여 최적의 조합을 찾습니다')
        async def core_command(ctx: commands.Context, *args):
            """코어 최적화 명령어 (단일 코어 또는 멀티 코어 지원)"""
            if not args:
                await ctx.send("❌ 코어 타입과 잼 정보를 입력해주세요.\n**사용법:**\n• 단일: `/코어 전설 25 35 45`\n• 멀티: `/코어 전설 유물 유물 33 55 44`")
                return
            
            try:
                # 유효한 코어 타입들
                valid_cores = ["전설", "유물", "고대"]
                
                # 앞부분에서 코어 타입들과 뒷부분의 잼들을 분리
                core_types = []
                gems = []
                
                # 앞에서부터 유효한 코어 타입인지 확인
                for i, arg in enumerate(args):
                    if arg in valid_cores:
                        core_types.append(arg)
                    else:
                        # 첫 번째 비-코어 타입부터는 모두 잼으로 간주
                        gems = list(args[i:])
                        break
                
                if not core_types:
                    await ctx.send(f"❌ 올바른 코어 타입을 입력해주세요: {', '.join(valid_cores)}")
                    return
                
                if not gems:
                    await ctx.send("❌ 잼 정보를 입력해주세요. (예: 25 35 45)")
                    return
                
                # 단일 코어 vs 멀티 코어 처리
                if len(core_types) == 1:
                    # 단일 코어 최적화
                    result = self.core_optimizer.find_optimal_combination(core_types[0], gems)
                    
                    if "error" in result:
                        await ctx.send(f"❌ {result['error']}")
                        return
                    
                    # 단일 코어 결과 임베드
                    embed = discord.Embed(
                        title="⚡ 코어 최적화 결과",
                        color=0xff6b35
                    )
                    
                    embed.add_field(
                        name="🔮 코어 정보",
                        value=f"**타입:** {result['core_type']}\n**의지력:** {result['core_willpower']}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="💎 선택된 잼",
                        value=f"```{', '.join(result['gems'])}```\n**개수:** {result['gem_count']}개",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="📊 사용량",
                        value=f"**사용된 의지력:** {result['total_willpower_used']}\n**남은 의지력:** {result['remaining_willpower']}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="✨ 질서포인트",
                        value=f"```총 {result['total_order_points']}포인트```",
                        inline=False
                    )
                    
                    # 활성화된 능력들
                    if result['activated_abilities']:
                        activated_str = ", ".join(map(str, result['activated_abilities']))
                        embed.add_field(
                            name="🎯 활성화된 능력",
                            value=f"```{activated_str}```",
                            inline=True
                        )
                    
                    # 모든 능력들
                    all_abilities_str = ", ".join(map(str, result['all_abilities']))
                    embed.add_field(
                        name="📋 모든 능력",
                        value=f"```{all_abilities_str}```",
                        inline=True
                    )
                    
                    # 효율성 표시
                    efficiency = len(result['activated_abilities']) / len(result['all_abilities']) * 100
                    embed.add_field(
                        name="📈 효율성",
                        value=f"```{efficiency:.1f}% ({len(result['activated_abilities'])}/{len(result['all_abilities'])})```",
                        inline=True
                    )
                    
                    embed.set_footer(text="💡 팁: 다른 잼 조합도 시도해보세요!")
                    await ctx.send(embed=embed)
                    
                else:
                    # 멀티 코어 최적화
                    result = self.core_optimizer.optimize_multiple_cores(core_types, gems)
                    
                    if "error" in result:
                        await ctx.send(f"❌ {result['error']}")
                        return
                    
                    # 멀티 코어 결과 임베드
                    embed = discord.Embed(
                        title="⚡ 멀티 코어 최적화 결과",
                        color=0x9b59b6
                    )
                    
                    # 전체 요약
                    total_gems_used = result['total_gems_used']
                    total_available = result['total_available_gems']
                    embed.add_field(
                        name="📊 전체 요약",
                        value=f"**코어 개수:** {len(core_types)}개\n**사용된 잼:** {total_gems_used}/{total_available}개",
                        inline=False
                    )
                    
                    # 각 코어별 결과
                    for i, core_result in enumerate(result['cores']):
                        if core_result['gem_count'] > 0:
                            gems_str = ", ".join(core_result['gems'])
                            activated_str = ", ".join(map(str, core_result['activated_abilities'])) if core_result['activated_abilities'] else "없음"
                            
                            embed.add_field(
                                name=f"🔮 {core_result['core_type']} #{i+1}",
                                value=f"**잼:** `{gems_str}`\n**질서포인트:** {core_result['total_order_points']}\n**활성화:** {activated_str}",
                                inline=True
                            )
                        else:
                            embed.add_field(
                                name=f"🔮 {core_result['core_type']} #{i+1}",
                                value="**잼:** 없음\n**질서포인트:** 0\n**활성화:** 없음",
                                inline=True
                            )
                    
                    embed.set_footer(text="💡 팁: 멀티 코어로 더 많은 능력을 활성화하세요!")
                    await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"코어 최적화 중 오류: {e}")
                await ctx.send(f"❌ 코어 최적화 중 오류 발생: {e}")
        
        @self.bot.command(name='젬', help='인터랙티브 UI로 코어 최적화를 수행합니다')
        async def gem_command(ctx: commands.Context, *args):
            """인터랙티브 젬 최적화 명령어"""
            
            if args:
                # 인수가 있으면 바로 파싱해서 UI 제공
                gems = list(args)
                
                # 잼 유효성 검사
                valid_gems = []
                for gem in gems:
                    if len(gem) == 2 and gem.isdigit():
                        valid_gems.append(gem)
                    else:
                        await ctx.send(f"❌ 잘못된 잼 형식: '{gem}' (올바른 예: 25, 36)")
                        return
                
                if not valid_gems:
                    await ctx.send("❌ 유효한 잼이 없습니다!")
                    return
                
                # 잼이 입력된 경우 바로 최적화 UI 제공
                embed = discord.Embed(
                    title="💎 젬 최적화 UI",
                    description=f"**입력된 잼:** `{' '.join(valid_gems)}`\n**잼 개수:** {len(valid_gems)}개",
                    color=0x2ecc71
                )
                
                embed.add_field(
                    name="🎮 코어 선택",
                    value="아래 드롭다운에서 코어 타입을 선택하여 최적화를 시작하세요!\n\n**코어 정보:**\n🟠 전설: 의지력 11\n🟣 유물: 의지력 15\n🔴 고대: 의지력 17",
                    inline=False
                )
                
                view = GemOptimizationView(valid_gems, self.core_optimizer)
                await ctx.send(embed=embed, view=view)
                
            else:
                # 인수가 없으면 잼 입력부터 시작
                embed = discord.Embed(
                    title="💎 젬 최적화 시작",
                    description="인터랙티브 UI로 젬 최적화를 시작합니다!",
                    color=0x3498db
                )
                
                embed.add_field(
                    name="📝 사용법",
                    value="1. **🆕 새 젬 입력** 버튼을 클릭\n2. 젬 정보를 입력 (예: 25 35 45)\n3. 코어 타입 선택\n4. 자동 최적화 결과 확인",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 팁",
                    value="• 명령어에 바로 젬을 입력할 수도 있습니다: `/젬 25 35 45`\n• 여러 코어를 동시에 선택하면 멀티 코어 최적화됩니다",
                    inline=False
                )
                
                view = GemOptimizationView([], self.core_optimizer)
                await ctx.send(embed=embed, view=view)
        
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
                name="/값 <아이템이름>",
                value="아이템 이름으로 해당 아이템의 정수 값을 찾습니다.",
                inline=False
            )
            
            embed.add_field(
                name="/통계",
                value="아이템 데이터베이스의 통계 정보를 표시합니다.",
                inline=False
            )
            
            embed.add_field(
                name="/코어 <타입> <잼1> <잼2> ...",
                value="코어에 잼을 조합하여 최적의 조합을 찾습니다.\n**단일:** `/코어 전설 25 35 45`\n**멀티:** `/코어 전설 유물 유물 33 55 44`\n\n**잼 형식 설명:**\n`25` = 의지력 2, 질서포인트 5\n(앞자리: 의지력 소모, 뒷자리: 질서포인트 제공)",
                inline=False
            )
            
            embed.add_field(
                name="/젬 [잼1] [잼2] ...",
                value="🎮 **인터랙티브 UI로 코어 최적화**\n**사용법:** `/젬` 또는 `/젬 25 35 45`\n\n**특징:**\n• 🎯 클릭 가능한 코어 선택 드롭다운\n• 🆕 모달로 젬 입력\n• 🔄 실시간 최적화 결과\n• 📊 시각적 진행바와 상태 표시",
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
