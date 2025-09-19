

import json
import logging
import re
from typing import Optional

import discord
from discord import ui
from discord.ext import commands

# 로컬 모듈 임포트
from config import Config
from core_optimizer import CoreOptimizer
from decoder import SaveCodeDecoder
from item_searcher import ItemSearcher
from savecode_decoder import decode_savecode2, extract_save_data

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 캐릭터 리스트 로드 함수
def load_character_list():
    """CharList_by_id.json 파일에서 캐릭터 목록을 로드"""
    try:
        with open('CharList_by_id.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("CharList_by_id.json 파일을 찾을 수 없습니다. 기본 영웅 타입을 사용합니다.")
        return {}
    except json.JSONDecodeError:
        logger.error("CharList_by_id.json 파일 형식이 올바르지 않습니다.")
        return {}

# 전역 캐릭터 목록 로드
CHARACTER_LIST = load_character_list()


class CoreSetupModal(ui.Modal, title='🔮 코어 설정'):
    """코어 타입별 개수 설정 모달"""
    
    def __init__(self, core_optimizer):
        super().__init__()
        self.core_optimizer = core_optimizer
    
    legend_count = ui.TextInput(
        label='전설 코어 개수',
        placeholder='0',
        default='0',
        style=discord.TextStyle.short,
        max_length=2,
        required=True
    )
    
    relic_count = ui.TextInput(
        label='유물 코어 개수',
        placeholder='0', 
        default='0',
        style=discord.TextStyle.short,
        max_length=2,
        required=True
    )
    
    ancient_count = ui.TextInput(
        label='고대 코어 개수',
        placeholder='0',
        default='0', 
        style=discord.TextStyle.short,
        max_length=2,
        required=True
    )
    
    gems_input = ui.TextInput(
        label='젬 정보',
        placeholder='예: 25 35 45 26 36 16',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    target_points = ui.TextInput(
        label='목표 질서 포인트 (선택사항)',
        placeholder='예: 15 20 18 (각 코어별 목표값, 비워두면 자동)',
        style=discord.TextStyle.short,
        max_length=100,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 시"""
        try:
            # 코어 개수 파싱
            legend_num = int(self.legend_count.value.strip() or '0')
            relic_num = int(self.relic_count.value.strip() or '0')
            ancient_num = int(self.ancient_count.value.strip() or '0')
            
            # 유효성 검사
            if legend_num < 0 or relic_num < 0 or ancient_num < 0:
                await interaction.response.send_message("❌ 코어 개수는 0 이상이어야 합니다!", ephemeral=True)
                return
            
            if legend_num + relic_num + ancient_num == 0:
                await interaction.response.send_message("❌ 최소 1개의 코어는 필요합니다!", ephemeral=True)
                return
            
            if legend_num + relic_num + ancient_num > 10:
                await interaction.response.send_message("❌ 코어는 최대 10개까지만 가능합니다!", ephemeral=True)
                return
            
            # 젬 파싱
            gems_text = self.gems_input.value.strip()
            if not gems_text:
                await interaction.response.send_message("❌ 젬 정보를 입력해주세요!", ephemeral=True)
                return
            
            gems = gems_text.split()
            valid_gems = []
            for gem in gems:
                if len(gem) == 2 and gem.isdigit():
                    valid_gems.append(gem)
                else:
                    await interaction.response.send_message(f"❌ 잘못된 젬 형식: '{gem}' (예: 25, 36)", ephemeral=True)
                    return
            
            if not valid_gems:
                await interaction.response.send_message("❌ 유효한 젬이 없습니다!", ephemeral=True)
                return
            
            # 목표 질서 포인트 파싱
            target_points_list = None
            target_text = self.target_points.value.strip() if self.target_points.value else ""
            if target_text:
                try:
                    target_points_list = [int(x.strip()) for x in target_text.split() if x.strip().isdigit()]
                    total_cores = legend_num + relic_num + ancient_num
                    
                    if len(target_points_list) != total_cores:
                        await interaction.response.send_message(
                            f"❌ 목표 질서 포인트 개수가 맞지 않습니다! 코어 {total_cores}개에 대해 {len(target_points_list)}개 입력됨", 
                            ephemeral=True
                        )
                        return
                    
                    # 목표값이 유효한 범위인지 확인 (5-30 정도)
                    for target in target_points_list:
                        if target < 5 or target > 50:
                            await interaction.response.send_message(
                                f"❌ 목표 질서 포인트는 5-50 범위여야 합니다: {target}", 
                                ephemeral=True
                            )
                            return
                except ValueError:
                    await interaction.response.send_message("❌ 목표 질서 포인트는 숫자로 입력해주세요!", ephemeral=True)
                    return
            
            # 코어 리스트 생성
            core_types = []
            core_types.extend(['전설'] * legend_num)
            core_types.extend(['유물'] * relic_num)
            core_types.extend(['고대'] * ancient_num)
            
            # 최적화 수행
            if len(core_types) == 1:
                # 단일 코어
                result = self.core_optimizer.find_optimal_combination(core_types[0], valid_gems)
                await self._send_single_core_result(interaction, result, valid_gems)
            else:
                # 멀티 코어
                result = self.core_optimizer.optimize_multiple_cores(core_types, valid_gems, target_points_list)
                await self._send_multi_core_result(interaction, result, core_types, valid_gems, target_points_list)
                
        except ValueError:
            await interaction.response.send_message("❌ 코어 개수는 숫자여야 합니다!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)
    
    async def _send_single_core_result(self, interaction: discord.Interaction, result, gems_data):
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
        
        # 젬 정보
        embed.add_field(
            name="💎 선택된 젬",
            value=f"```yaml\n젬: {', '.join(result['gems'])}\n개수: {result['gem_count']}개\n질서: {result['total_order_points']}\n```",
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
        view = GemOptimizationView(self.core_optimizer)
        embed.set_footer(text="🔄 다시 최적화하려면 아래 버튼을 사용하세요!")
        
        await interaction.response.send_message(embed=embed, view=view)
    
    async def _send_multi_core_result(self, interaction: discord.Interaction, result, core_types, gems_data, target_points=None):
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
        
        # 코어 구성 요약
        core_summary = {}
        for core_type in core_types:
            core_summary[core_type] = core_summary.get(core_type, 0) + 1
        
        core_info = []
        for core_type, count in core_summary.items():
            core_info.append(f"{core_type}: {count}개")
        
        embed.add_field(
            name="🔮 코어 구성",
            value=f"```yaml\n{chr(10).join(core_info)}\n총 {len(core_types)}개\n```",
            inline=True
        )
        
        # 전체 요약
        total_gems_used = result['total_gems_used']
        total_available = result['total_available_gems']
        usage_percentage = (total_gems_used / total_available * 100) if total_available > 0 else 0
        
        embed.add_field(
            name="📊 젬 사용량",
            value=f"```yaml\n사용: {total_gems_used}/{total_available}개\n사용률: {usage_percentage:.1f}%\n```",
            inline=True
        )
        
        # 각 코어별 상태 (간략하게)
        core_results_text = ""
        for i, core_result in enumerate(result['cores']):
            if core_result['gem_count'] > 0:
                gems_str = ', '.join(core_result['gems'])
                activated_count = len(core_result['activated_abilities'])
                
                # 목표 질서 포인트 정보 추가
                target_info = ""
                if target_points and i < len(target_points):
                    target = target_points[i]
                    current = core_result['total_order_points']
                    if current == target:
                        target_info = f" (목표{target} ✅)"
                    elif current < target:
                        target_info = f" (목표{target} ⬇️{target-current})"
                    else:
                        target_info = f" (목표{target} ⬆️{current-target})"
                
                core_results_text += f"{core_result['core_type']} #{i+1}: {gems_str} → 질서{core_result['total_order_points']}{target_info} (능력{activated_count}개) [의지력 {core_result['remaining_willpower']}남음]\n"
            else:
                # 목표 질서 포인트가 있는 경우 빈 코어에도 표시
                target_info = ""
                if target_points and i < len(target_points):
                    target_info = f" (목표{target_points[i]})"
                core_results_text += f"{core_result['core_type']} #{i+1}: 젬 없음{target_info}\n"
        
        if core_results_text:
            embed.add_field(
                name="📋 코어별 결과",
                value=f"```{core_results_text}```",
                inline=False
            )
        
        # 새로운 최적화 버튼 추가
        view = GemOptimizationView(self.core_optimizer)
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


class DynamicCoreSetupView(ui.View):
    """동적 코어 설정을 위한 View"""
    
    def __init__(self, core_optimizer):
        super().__init__(timeout=300)
        self.core_optimizer = core_optimizer
        self.cores_data = []  # [{'type': '전설', 'target': 15}, ...]
        self.gems_input = ""
        self.update_display()
    
    def update_display(self):
        """현재 설정 상태에 맞게 View 업데이트"""
        self.clear_items()
        
        # 코어 추가 버튼
        add_button = ui.Button(
            label="➕ 코어 추가",
            style=discord.ButtonStyle.primary,
            custom_id="add_core"
        )
        add_button.callback = self.add_core_callback
        self.add_item(add_button)
        
        # 젬 설정 버튼
        gems_button = ui.Button(
            label="💎 젬 설정",
            style=discord.ButtonStyle.secondary,
            custom_id="set_gems"
        )
        gems_button.callback = self.set_gems_callback
        self.add_item(gems_button)
        
        # 코어 목록이 있으면 코어별 설정 버튼들 추가
        for i, core in enumerate(self.cores_data):
            if len(self.children) >= 5:  # Discord 제한
                break
                
            core_button = ui.Button(
                label=f"{core['type']} (목표: {core.get('target', '최대')})",
                style=discord.ButtonStyle.secondary,
                custom_id=f"edit_core_{i}"
            )
            core_button.callback = lambda interaction, idx=i: self.edit_core_callback(interaction, idx)
            self.add_item(core_button)
        
        # 최적화 실행 버튼 (코어와 젬이 모두 설정되었을 때만)
        if self.cores_data and self.gems_input:
            optimize_button = ui.Button(
                label="🚀 최적화 실행",
                style=discord.ButtonStyle.success,
                custom_id="optimize"
            )
            optimize_button.callback = self.optimize_callback
            self.add_item(optimize_button)
    
    async def add_core_callback(self, interaction: discord.Interaction):
        """코어 추가 콜백"""
        modal = AddCoreModal(self)
        await interaction.response.send_modal(modal)
    
    async def set_gems_callback(self, interaction: discord.Interaction):
        """젬 설정 콜백"""
        modal = SetGemsModal(self)
        await interaction.response.send_modal(modal)
    
    async def edit_core_callback(self, interaction: discord.Interaction, core_index: int):
        """코어 편집 콜백"""
        if core_index < len(self.cores_data):
            modal = EditCoreModal(self, core_index)
            await interaction.response.send_modal(modal)
    
    async def optimize_callback(self, interaction: discord.Interaction):
        """최적화 실행 콜백"""
        try:
            # 코어 타입 리스트 생성
            core_types = [core['type'] for core in self.cores_data]
            
            # 목표 질서 포인트 리스트 생성
            target_points = []
            for core in self.cores_data:
                target = core.get('target')
                if target and str(target).isdigit():
                    target_points.append(int(target))
                else:
                    target_points.append(None)
            
            # 젬 파싱
            gems = self.gems_input.split() if self.gems_input else []
            
            # 유효성 검사
            if not core_types:
                await interaction.response.send_message("❌ 최소 1개의 코어를 추가해주세요!", ephemeral=True)
                return
            
            if not gems:
                await interaction.response.send_message("❌ 젬을 설정해주세요!", ephemeral=True)
                return
            
            # 최적화 수행
            if len(core_types) == 1:
                result = self.core_optimizer.find_optimal_combination(core_types[0], gems)
                await self._send_single_core_result(interaction, result, gems)
            else:
                # 목표 질서 포인트를 숫자로 변환 (None이나 '최대'인 경우 0으로 처리)
                processed_target_points = []
                for target in target_points:
                    if target is None or target == '최대':
                        processed_target_points.append(0)
                    else:
                        processed_target_points.append(target)
                    
                result = self.core_optimizer.optimize_multiple_cores(core_types, gems, processed_target_points)
                await self._send_multi_core_result(interaction, result, core_types, gems, processed_target_points)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)
    
    async def update_message(self, interaction: discord.Interaction):
        """메시지 업데이트"""
        self.update_display()
        
        embed = discord.Embed(
            title="🔮 동적 코어 설정",
            description="코어별로 개별 설정이 가능합니다!",
            color=0x3498db
        )
        
        # 현재 코어 설정 표시
        if self.cores_data:
            core_list = []
            for i, core in enumerate(self.cores_data):
                target_str = f"목표: {core.get('target', '최대')}"
                priority_str = f"우선순위: {core.get('priority', i+1)}"
                core_list.append(f"{i+1}. {core['type']} ({target_str}, {priority_str})")
            
            embed.add_field(
                name="📋 설정된 코어",
                value="\n".join(core_list),
                inline=False
            )
        else:
            embed.add_field(
                name="📋 설정된 코어",
                value="아직 설정된 코어가 없습니다.",
                inline=False
            )
        
        # 젬 설정 표시
        if self.gems_input:
            embed.add_field(
                name="💎 젬 설정",
                value=f"```{self.gems_input}```",
                inline=False
            )
        else:
            embed.add_field(
                name="💎 젬 설정",
                value="아직 젬이 설정되지 않았습니다.",
                inline=False
            )
        
        # 이미 응답한 interaction인지 확인하고 적절한 방법 선택
        try:
            if interaction.response.is_done():
                # 이미 응답된 경우 edit_original_response 사용
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                # 아직 응답하지 않은 경우 response 사용
                await interaction.response.edit_message(embed=embed, view=self)
        except Exception:
            # 응답이 실패한 경우 followup 사용
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
    
    async def update_original_message(self, interaction: discord.Interaction):
        """원본 메시지 업데이트 (Modal submit 후 사용)"""
        self.update_display()
        
        embed = discord.Embed(
            title="🔮 동적 코어 설정",
            description="코어별로 개별 설정이 가능합니다!",
            color=0x3498db
        )
        
        # 현재 코어 설정 표시
        if self.cores_data:
            core_list = []
            for i, core in enumerate(self.cores_data):
                target_str = f"목표: {core.get('target', '최대')}"
                core_list.append(f"{i+1}. {core['type']} ({target_str})")
            
            embed.add_field(
                name="📋 설정된 코어",
                value="\n".join(core_list),
                inline=False
            )
        else:
            embed.add_field(
                name="📋 설정된 코어",
                value="아직 설정된 코어가 없습니다.",
                inline=False
            )
        
        # 젬 설정 표시
        if self.gems_input:
            embed.add_field(
                name="💎 젬 설정",
                value=f"```{self.gems_input}```",
                inline=False
            )
        else:
            embed.add_field(
                name="💎 젬 설정",
                value="아직 젬이 설정되지 않았습니다.",
                inline=False
            )
        
        # 원본 메시지를 찾아서 업데이트
        # interaction의 message나 부모 메시지를 찾아야 합니다
        try:
            # 원본 메시지 ID를 저장해두었다면 사용
            if hasattr(self, 'original_message'):
                await self.original_message.edit(embed=embed, view=self)
            else:
                # 채널에서 봇의 마지막 메시지를 찾아 업데이트
                async for message in interaction.channel.history(limit=10):
                    if message.author == interaction.client.user and message.embeds:
                        if "동적 코어 설정" in message.embeds[0].title:
                            await message.edit(embed=embed, view=self)
                            break
        except Exception as e:
            print(f"메시지 업데이트 실패: {e}")
    
    async def _send_single_core_result(self, interaction: discord.Interaction, result, gems_data):
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
        
        # 젬 정보
        embed.add_field(
            name="💎 선택된 젬",
            value=f"```yaml\n젬: {', '.join(result['gems'])}\n개수: {result['gem_count']}개\n질서: {result['total_order_points']}\n```",
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
        
        await interaction.response.send_message(embed=embed)
    
    async def _send_multi_core_result(self, interaction: discord.Interaction, result, core_types, gems_data, target_points=None):
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
        
        # 각 코어별 상태 (목표 포함)
        core_results_text = ""
        for i, core_result in enumerate(result['cores']):
            if core_result['gem_count'] > 0:
                gems_str = ', '.join(core_result['gems'])
                activated_count = len(core_result['activated_abilities'])
                
                # 목표 질서 포인트 정보 추가
                target_info = ""
                if target_points and i < len(target_points):
                    target = target_points[i]
                    current = core_result['total_order_points']
                    if current == target:
                        target_info = f" (목표{target} ✅)"
                    elif current < target:
                        target_info = f" (목표{target} ⬇️{target-current})"
                    else:
                        target_info = f" (목표{target} ⬆️{current-target})"
                
                core_results_text += f"{core_result['core_type']} #{i+1}: {gems_str} → 질서{core_result['total_order_points']}{target_info} (능력{activated_count}개) [의지력 {core_result['remaining_willpower']}남음]\n"
            else:
                # 목표 질서 포인트가 있는 경우 빈 코어에도 표시
                target_info = ""
                if target_points and i < len(target_points):
                    target_info = f" (목표{target_points[i]})"
                core_results_text += f"{core_result['core_type']} #{i+1}: 젬 없음{target_info}\n"
        
        if core_results_text:
            embed.add_field(
                name="📋 코어별 결과",
                value=f"```{core_results_text}```",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    def _get_core_color(self, core_type):
        """코어 타입별 색상"""
        colors = {
            "전설": 0xf39c12,  # 주황색
            "유물": 0x9b59b6,  # 보라색
            "고대": 0xe74c3c   # 빨간색
        }
        return colors.get(core_type, 0x95a5a6)


class AddCoreModal(ui.Modal, title='코어 추가'):
    """코어 추가를 위한 모달"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    core_type = ui.TextInput(
        label='코어 종류',
        placeholder='전설, 유물, 고대 중 입력',
        max_length=10,
        required=True
    )
    
    target_points = ui.TextInput(
        label='목표 질서 포인트 (선택사항)',
        placeholder='숫자 입력 (비어있으면 최대)',
        max_length=10,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        core_type = self.core_type.value.strip()
        target = self.target_points.value.strip()
        
        # 코어 타입 검증
        if core_type not in ['전설', '유물', '고대']:
            await interaction.response.send_message("❌ 코어 종류는 '전설', '유물', '고대' 중 하나여야 합니다!", ephemeral=True)
            return
        
        # 목표 질서 포인트 검증
        target_value = None
        if target:
            try:
                target_value = int(target)
                if target_value < 5 or target_value > 50:
                    await interaction.response.send_message("❌ 목표 질서 포인트는 5-50 사이여야 합니다!", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ 목표 질서 포인트는 숫자여야 합니다!", ephemeral=True)
                return
        
        # 성공 메시지
        await interaction.response.send_message(f"✅ {core_type} 코어가 추가되었습니다!", ephemeral=True)
        
        # 코어 추가
        core_data = {'type': core_type}
        if target_value:
            core_data['target'] = target_value
        
        self.parent_view.cores_data.append(core_data)
        
        # 메시지 업데이트 (원본 메시지를 직접 업데이트)
        await self.parent_view.update_original_message(interaction)


class EditCoreModal(ui.Modal, title='코어 편집'):
    """코어 편집을 위한 모달"""
    
    def __init__(self, parent_view, core_index):
        super().__init__()
        self.parent_view = parent_view
        self.core_index = core_index
        
        # 현재 값으로 초기화
        current_core = parent_view.cores_data[core_index]
        self.core_type.default = current_core['type']
        if 'target' in current_core:
            self.target_points.default = str(current_core['target'])
        if 'priority' in current_core:
            self.priority.default = str(current_core['priority'])
    
    core_type = ui.TextInput(
        label='코어 종류',
        placeholder='전설, 유물, 고대 중 입력',
        max_length=10,
        required=True
    )
    
    target_points = ui.TextInput(
        label='목표 질서 포인트 (선택사항)',
        placeholder='숫자 입력 (비어있으면 최대)',
        max_length=10,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        core_type = self.core_type.value.strip()
        target = self.target_points.value.strip()
        
        # 코어 타입 검증
        if core_type not in ['전설', '유물', '고대']:
            await interaction.response.send_message("❌ 코어 종류는 '전설', '유물', '고대' 중 하나여야 합니다!", ephemeral=True)
            return
        
        # 목표 질서 포인트 검증
        target_value = None
        if target:
            try:
                target_value = int(target)
                if target_value < 5 or target_value > 50:
                    await interaction.response.send_message("❌ 목표 질서 포인트는 5-50 사이여야 합니다!", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ 목표 질서 포인트는 숫자여야 합니다!", ephemeral=True)
                return
        
        # 성공 메시지
        await interaction.response.send_message(f"✅ {core_type} 코어가 수정되었습니다!", ephemeral=True)
        
        # 코어 업데이트
        core_data = {'type': core_type}
        if target_value:
            core_data['target'] = target_value
        
        self.parent_view.cores_data[self.core_index] = core_data
        await self.parent_view.update_original_message(interaction)


class SetGemsModal(ui.Modal, title='젬 설정'):
    """젬 설정을 위한 모달"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        if parent_view.gems_input:
            self.gems_input.default = parent_view.gems_input
    
    gems_input = ui.TextInput(
        label='젬 정보',
        placeholder='예: 25 35 45 26 36 16',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        gems_text = self.gems_input.value.strip()
        
        if not gems_text:
            await interaction.response.send_message("❌ 젬 정보를 입력해주세요!", ephemeral=True)
            return
        
        # 젬 유효성 검사
        gems = gems_text.split()
        valid_gems = []
        for gem in gems:
            if len(gem) == 2 and gem.isdigit():
                valid_gems.append(gem)
            else:
                await interaction.response.send_message(f"❌ 잘못된 젬 형식: '{gem}' (예: 25, 36)", ephemeral=True)
                return
        
        if not valid_gems:
            await interaction.response.send_message("❌ 유효한 젬이 없습니다!", ephemeral=True)
            return
        
        # 먼저 성공 메시지로 응답
        await interaction.response.send_message("✅ 젬이 설정되었습니다!", ephemeral=True)
        
        self.parent_view.gems_input = ' '.join(valid_gems)
        await self.parent_view.update_original_message(interaction)


class QuickSetupView(ui.View):
    """빠른 설정을 위한 간단한 View"""
    
    def __init__(self, core_optimizer):
        super().__init__(timeout=300)
        self.core_optimizer = core_optimizer
    
    @ui.button(label="🔮 시작하기", style=discord.ButtonStyle.primary)
    async def start_setup(self, interaction: discord.Interaction, button: ui.Button):
        """바로 코어 설정 모달 띄우기"""
        modal = CoreSetupModal(self.core_optimizer)
        await interaction.response.send_modal(modal)


class GemOptimizationView(ui.View):
    """젬 최적화 메인 UI"""
    
    def __init__(self, core_optimizer):
        super().__init__(timeout=300)  # 5분 타임아웃
        self.core_optimizer = core_optimizer
    
    @ui.button(label="🔮 코어 설정 & 젬 입력", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def setup_cores_button(self, interaction: discord.Interaction, button: ui.Button):
        """코어 설정 및 젬 입력 버튼"""
        modal = CoreSetupModal(self.core_optimizer)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="❓ 도움말", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def help_button(self, interaction: discord.Interaction, button: ui.Button):
        """도움말 버튼"""
        embed = discord.Embed(
            title="💎 젬 최적화 도움말",
            description="새로운 코어 개수 설정 방식",
            color=0x3498db
        )
        
        embed.add_field(
            name="� 젬 형식",
            value="```\n25 = 의지력 2, 질서포인트 5\n36 = 의지력 3, 질서포인트 6\n47 = 의지력 4, 질서포인트 7\n```",
            inline=False
        )
        
        embed.add_field(
            name="� 코어 정보",
            value="```\n전설: 의지력 11, 능력 [10, 14]\n유물: 의지력 15, 능력 [10, 14, 17, 18, 19, 20]\n고대: 의지력 17, 능력 [10, 14, 17, 18, 19, 20]\n```",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ 새로운 설정 방식",
            value="1. **🔮 코어 설정 & 젬 입력** 버튼 클릭\n2. 각 코어 타입별 개수 입력:\n   • 전설 코어: 2개\n   • 유물 코어: 1개\n   • 고대 코어: 0개\n3. 젬 정보 입력: `25 35 45 26`\n4. 자동으로 최적화 결과 표시",
            inline=False
        )
        
        embed.add_field(
            name="� 예시",
            value="**코어 구성:** 고대 2개, 전설 1개\n**젬:** 25 35 45 26 36 16\n→ 총 3개 코어에 최적 분배",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def on_timeout(self):
        """타임아웃 시 버튼 비활성화"""
        for item in self.children:
            item.disabled = True


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
                
                # 통계 변수 초기화
                valid_count = 0
                invalid_count = 0
                characters = set()  # 중복 캐릭터 제거를 위한 set
                character_counts = {}  # 캐릭터별 출현 횟수 추적
                
                for code in codes:
                    print(f"[DEBUG] 로드된 코드들: {code}")  # 디버그용 출력
                # 검증
                    is_valid = decode_savecode2(code, name)
                    result = "✅ 유효함" if is_valid else "❌ 유효하지 않음"
                    
                    # 통계 업데이트
                    if is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1
                    
                    # 세이브 데이터 추출
                    save_data = extract_save_data(code, name)
                    
                    # 영웅 타입 이름 매핑 (JSON 파일 기반)
                    hero_type_index = save_data['hero_type_index']
                    hero_name = CHARACTER_LIST.get(str(hero_type_index), f"알 수 없는 캐릭터 (ID: {hero_type_index})")
                    
                    # 캐릭터 세트에 추가 (중복 제거)
                    characters.add(hero_name)
                    
                    # 캐릭터별 출현 횟수 카운트
                    character_counts[hero_name] = character_counts.get(hero_name, 0) + 1
                    
                    # 아이템 추출
                    items_list = self.decoder.extract_items(code)
                    response = "\n".join(items_list)
                    
                    # 결과 전송 - Embed 사용
                    embed = discord.Embed(
                        title="🎮 세이브코드 분석 결과",
                        color=0x00ff00 if is_valid else 0xff0000
                    )
                    embed.add_field(name="검증 상태", value=result, inline=True)
                    embed.add_field(name="플레이어", value=name, inline=True)
                    embed.add_field(name="영웅", value=hero_name, inline=True)
                    embed.add_field(name="💰 골드", value=f"{save_data['gold']:,}", inline=True)
                    embed.add_field(name="🌲 나무", value=f"{save_data['lumber']:,}", inline=True)
                    embed.add_field(name="📈 레벨", value=save_data['level'], inline=True)
                    
                    await ctx.send(embed=embed)
                    
                    # 아이템 목록을 모던한 Embed로 표시
                    if items_list:
                        items_embed = discord.Embed(
                            title="🎒 세이브코드 아이템 목록",
                            description="추출된 아이템들입니다",
                            color=0x3498db
                        )
                        
                        # 아이템들을 6개씩 나누어서 표시 (인벤토리 슬롯처럼)
                        items_per_row = 3
                        for i in range(0, len(items_list), items_per_row):
                            batch = items_list[i:i+items_per_row]
                            slot_numbers = [f"슬롯 {j+1+i}" for j in range(len(batch))]
                            
                            field_name = f"📦 아이템 슬롯 {i+1}-{min(i+items_per_row, len(items_list))}"
                            field_value = ""
                            
                            for j, item in enumerate(batch):
                                slot_num = i + j + 1
                                # 아이템 이름에 따른 이모지 추가
                                emoji = "⚔️" if "무기" in item or "검" in item or "창" in item else \
                                       "🛡️" if "방패" in item or "갑옷" in item or "투구" in item else \
                                       "💍" if "반지" in item or "목걸이" in item else \
                                       "🧪" if "포션" in item or "물약" in item else \
                                       "💎" if "젬" in item or "보석" in item else \
                                       "📜" if "스크롤" in item or "두루마리" in item else \
                                       "🔮" if "오브" in item or "수정" in item else \
                                       "⚡" if "룬" in item else \
                                       "🎯"
                                
                                field_value += f"{emoji} **{slot_num}.** {item}\n"
                            
                            items_embed.add_field(
                                name=field_name,
                                value=field_value or "빈 슬롯",
                                inline=True
                            )
                        
                        # 총 아이템 개수 표시
                        items_embed.set_footer(text=f"총 {len(items_list)}개의 아이템이 발견되었습니다")
                        
                        await ctx.send(embed=items_embed)
                
                # 여러 세이브코드가 있는 경우 통계 표시
                if len(codes) > 1:
                    stats_embed = discord.Embed(
                        title="📊 세이브코드 처리 통계",
                        description="처리된 모든 세이브코드의 통계입니다",
                        color=0x9b59b6
                    )
                    
                    stats_embed.add_field(
                        name="✅ 유효한 검증", 
                        value=f"{valid_count}건", 
                        inline=True
                    )
                    stats_embed.add_field(
                        name="❌ 유효하지 않은 검증", 
                        value=f"{invalid_count}건", 
                        inline=True
                    )
                    stats_embed.add_field(
                        name="👥 캐릭터 수", 
                        value=f"{len(characters)}건", 
                        inline=True
                    )
                    
                    # 발견된 캐릭터 목록 추가
                    if characters:
                        character_list = ", ".join(sorted(characters))
                        if len(character_list) > 1024:  # Discord 필드 제한
                            character_list = character_list[:1021] + "..."
                        stats_embed.add_field(
                            name="🎭 발견된 캐릭터",
                            value=character_list,
                            inline=False
                        )
                    
                    # 중복된 캐릭터 목록 추가
                    duplicated_characters = {name: count for name, count in character_counts.items() if count > 1}
                    if duplicated_characters:
                        duplicate_list = []
                        for char_name, count in sorted(duplicated_characters.items()):
                            duplicate_list.append(f"{char_name} (×{count})")
                        
                        duplicate_text = ", ".join(duplicate_list)
                        if len(duplicate_text) > 1024:  # Discord 필드 제한
                            duplicate_text = duplicate_text[:1021] + "..."
                        
                        stats_embed.add_field(
                            name="🔄 중복된 캐릭터",
                            value=duplicate_text,
                            inline=False
                        )
                    else:
                        stats_embed.add_field(
                            name="🔄 중복된 캐릭터",
                            value="중복된 캐릭터가 없습니다",
                            inline=False
                        )
                    
                    stats_embed.set_footer(text=f"총 {len(codes)}개의 세이브코드를 처리했습니다")
                    
                    await ctx.send(embed=stats_embed)
                
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
        
        @self.bot.command(name='젬', help='동적 코어 설정으로 젬 최적화를 수행합니다')
        async def gem_command(ctx: commands.Context):
            """동적 코어 설정 젬 최적화 명령어"""
            
            embed = discord.Embed(
                title="� 동적 코어 설정",
                description="코어별로 개별 설정이 가능한 새로운 방식입니다!",
                color=0x3498db
            )
            
            embed.add_field(
                name="⚙️ 새로운 설정 방식",
                value="🔮 **코어 설정 & 젬 입력** 버튼을 눌러서:\n• 각 코어 타입별 개수 입력\n• 젬 정보 입력\n• 한 번에 모든 설정 완료!",
                inline=False
            )
            
            embed.add_field(
                name="� 코어 타입",
                value="```yaml\n전설: 의지력 11, 능력 [10, 14]\n유물: 의지력 15, 능력 [10, 14, 17, 18, 19, 20]\n고대: 의지력 17, 능력 [10, 14, 17, 18, 19, 20]\n```",
                inline=False
            )
            
            embed.add_field(
                name="💡 예시",
                value="**코어 구성:**\n• 전설: 1개\n• 유물: 0개  \n• 고대: 2개\n\n**젬:** 25 35 45 26 36 16\n\n→ 총 3개 코어에 젬을 최적 분배",
                inline=False
            )
            
            view = DynamicCoreSetupView(self.core_optimizer)
            message = await ctx.send(embed=embed, view=view)
            view.original_message = message
        
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
                name="/젬",
                value="🔮 **코어 개수 설정으로 젬 최적화**\n**사용법:** `/젬`\n\n**새로운 특징:**\n• ⚙️ 각 코어 타입별 개수 직접 입력\n• 💎 젬 정보를 한 번에 입력\n• 🎯 고대 2개, 전설 1개 등 자유로운 구성\n• 📊 최적화 결과를 시각적으로 표시\n• � 목표 포인트 기반 최적화로 정확한 타겟팅\n• 📈 각 코어별 목표 질서 포인트 설정 가능",
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
