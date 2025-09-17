

import json
import logging
import re
from typing import Optional

import discord
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
        
        @self.bot.command(name='젬', help='UI 형태로 코어 최적화를 수행합니다')
        async def gem_command(ctx: commands.Context, *args):
            """UI 형태의 코어 최적화 명령어"""
            if not args:
                await ctx.send("❌ 코어 타입과 잼 정보를 입력해주세요.\n**사용법:**\n• 단일: `/젬 전설 25 35 45`\n• 멀티: `/젬 전설 유물 유물 33 55 44`")
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
                    
                    # UI 스타일 단일 코어 결과
                    await self._send_ui_single_core_result(ctx, result)
                    
                else:
                    # 멀티 코어 최적화
                    result = self.core_optimizer.optimize_multiple_cores(core_types, gems)
                    
                    if "error" in result:
                        await ctx.send(f"❌ {result['error']}")
                        return
                    
                    # UI 스타일 멀티 코어 결과
                    await self._send_ui_multi_core_result(ctx, result, core_types)
                
            except Exception as e:
                logger.error(f"젬 최적화 중 오류: {e}")
                await ctx.send(f"❌ 젬 최적화 중 오류 발생: {e}")
        
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
                name="/젬 <타입> <잼1> <잼2> ...",
                value="UI 스타일로 코어 최적화를 수행합니다.\n**사용법:** `/젬 전설 25 35 45` 또는 `/젬 전설 유물 25 35 45`\n\n**특징:**\n• 시각적 진행바와 상태 표시\n• 각 코어별 상세 정보 카드\n• 능력 활성화 상태 시각화",
                inline=False
            )
            
            embed.add_field(
                name="/도움말",
                value="이 도움말을 표시합니다.",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    async def _send_ui_single_core_result(self, ctx, result):
        """UI 스타일 단일 코어 결과 전송"""
        # 메인 정보 카드
        main_embed = discord.Embed(
            title="🎮 젬 최적화 UI",
            description=f"**{result['core_type']} 코어** 최적화 결과",
            color=0x2ecc71
        )
        
        # 코어 정보 섹션
        core_info = f"""
```yaml
타입: {result['core_type']}
의지력: {result['core_willpower']}
사용된 의지력: {result['total_willpower_used']}
남은 의지력: {result['remaining_willpower']}
```"""
        main_embed.add_field(name="🔮 코어 정보", value=core_info, inline=True)
        
        # 잼 정보 섹션
        gem_info = f"""
```yaml
선택된 잼: {', '.join(result['gems'])}
잼 개수: {result['gem_count']}개
질서포인트: {result['total_order_points']}
```"""
        main_embed.add_field(name="💎 잼 정보", value=gem_info, inline=True)
        
        # 능력 정보 섹션
        activated = ', '.join(map(str, result['activated_abilities'])) if result['activated_abilities'] else '없음'
        all_abilities = ', '.join(map(str, result['all_abilities']))
        efficiency = len(result['activated_abilities']) / len(result['all_abilities']) * 100
        
        ability_info = f"""
```yaml
활성화된 능력: {activated}
모든 능력: {all_abilities}
효율성: {efficiency:.1f}%
```"""
        main_embed.add_field(name="⚡ 능력 상태", value=ability_info, inline=False)
        
        # 진행바 스타일 의지력 사용량
        willpower_bar = self._create_progress_bar(result['total_willpower_used'], result['core_willpower'], 20)
        main_embed.add_field(
            name="📊 의지력 사용량", 
            value=f"```{willpower_bar}```\n`{result['total_willpower_used']}/{result['core_willpower']}`", 
            inline=False
        )
        
        # 능력 활성화 시각화
        ability_visual = self._create_ability_visual(result['all_abilities'], result['activated_abilities'])
        main_embed.add_field(name="🎯 능력 활성화 상태", value=ability_visual, inline=False)
        
        main_embed.set_footer(text="💡 /젬 명령어로 UI 스타일 최적화를 사용하세요!")
        await ctx.send(embed=main_embed)
    
    async def _send_ui_multi_core_result(self, ctx, result, core_types):
        """UI 스타일 멀티 코어 결과 전송"""
        # 메인 대시보드
        main_embed = discord.Embed(
            title="🎮 멀티 젬 최적화 UI",
            description=f"**{len(core_types)}개 코어** 동시 최적화 결과",
            color=0x9b59b6
        )
        
        # 전체 요약 섹션
        total_gems_used = result['total_gems_used']
        total_available = result['total_available_gems']
        usage_percentage = (total_gems_used / total_available * 100) if total_available > 0 else 0
        
        summary_info = f"""
```yaml
코어 개수: {len(core_types)}개
사용된 잼: {total_gems_used}/{total_available}개
잼 사용률: {usage_percentage:.1f}%
```"""
        main_embed.add_field(name="📊 전체 요약", value=summary_info, inline=False)
        
        # 잼 사용량 진행바
        gem_usage_bar = self._create_progress_bar(total_gems_used, total_available, 25)
        main_embed.add_field(
            name="💎 잼 사용량", 
            value=f"```{gem_usage_bar}```", 
            inline=False
        )
        
        await ctx.send(embed=main_embed)
        
        # 각 코어별 상세 정보 카드들
        for i, core_result in enumerate(result['cores']):
            if core_result['gem_count'] > 0:
                # 잼이 할당된 코어
                core_embed = discord.Embed(
                    title=f"🔮 {core_result['core_type']} 코어 #{i+1}",
                    color=self._get_core_color(core_result['core_type'])
                )
                
                # 코어 상태
                core_status = f"""
```yaml
잼: {', '.join(core_result['gems'])}
잼 개수: {core_result['gem_count']}/4개
의지력 사용: {core_result['total_willpower_used']}
질서포인트: {core_result['total_order_points']}
```"""
                core_embed.add_field(name="📋 상태", value=core_status, inline=False)
                
                # 활성화된 능력
                if core_result['activated_abilities']:
                    activated_str = ', '.join(map(str, core_result['activated_abilities']))
                    core_embed.add_field(name="⚡ 활성화된 능력", value=f"`{activated_str}`", inline=True)
                
                # 능력 효율성
                total_abilities = len(core_result['all_abilities'])
                activated_count = len(core_result['activated_abilities'])
                efficiency = (activated_count / total_abilities * 100) if total_abilities > 0 else 0
                
                efficiency_bar = self._create_progress_bar(activated_count, total_abilities, 15)
                core_embed.add_field(
                    name="📈 효율성", 
                    value=f"```{efficiency_bar}```\n`{efficiency:.1f}% ({activated_count}/{total_abilities})`", 
                    inline=True
                )
                
                await ctx.send(embed=core_embed)
            else:
                # 잼이 할당되지 않은 코어
                empty_embed = discord.Embed(
                    title=f"🔮 {core_result['core_type']} 코어 #{i+1}",
                    description="```yaml\n상태: 잼 없음\n질서포인트: 0\n활성화된 능력: 없음\n```",
                    color=0x95a5a6
                )
                await ctx.send(embed=empty_embed)
    
    def _create_progress_bar(self, current, maximum, length=20):
        """진행바 생성"""
        if maximum == 0:
            return "▱" * length
        
        filled = int((current / maximum) * length)
        bar = "▰" * filled + "▱" * (length - filled)
        return bar
    
    def _create_ability_visual(self, all_abilities, activated_abilities):
        """능력 활성화 시각적 표시"""
        visual = "```\n"
        for ability in all_abilities:
            if ability in activated_abilities:
                visual += f"🟢 {ability}  "
            else:
                visual += f"⚪ {ability}  "
        visual += "\n```"
        return visual
    
    def _get_core_color(self, core_type):
        """코어 타입별 색상"""
        colors = {
            "전설": 0xf39c12,  # 주황색
            "유물": 0x9b59b6,  # 보라색
            "고대": 0xe74c3c   # 빨간색
        }
        return colors.get(core_type, 0x95a5a6)
    
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
