"""
최적화 시스템 관리 모듈
코어 최적화 UI 및 기능들을 캡슐화
"""

import logging
from typing import Dict, List, Optional, Tuple

import discord
from discord import ui

from core_optimizer import CoreOptimizer

logger = logging.getLogger(__name__)


class CoreSetupModal(ui.Modal, title='🔮 코어 설정'):
    """코어 타입별 개수 설정 모달"""
    
    def __init__(self, optimization_manager):
        super().__init__()
        self.optimization_manager = optimization_manager
    
    legend_count = ui.TextInput(
        label='전설 코어 개수',
        placeholder='0',
        default='0',
        style=discord.TextStyle.short,
        max_length=2,
        required=True
    )
    
    epic_count = ui.TextInput(
        label='영웅 코어 개수',
        placeholder='0',
        default='0',
        style=discord.TextStyle.short,
        max_length=2,
        required=True
    )
    
    rare_count = ui.TextInput(
        label='레어 코어 개수',
        placeholder='0',
        default='0',
        style=discord.TextStyle.short,
        max_length=3,
        required=True
    )
    
    common_count = ui.TextInput(
        label='일반 코어 개수',
        placeholder='0',
        default='0',
        style=discord.TextStyle.short,
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 입력값 검증 및 변환
            legend = int(self.legend_count.value or '0')
            epic = int(self.epic_count.value or '0')
            rare = int(self.rare_count.value or '0')
            common = int(self.common_count.value or '0')
            
            # 음수 체크
            if any(count < 0 for count in [legend, epic, rare, common]):
                await interaction.response.send_message("❌ 코어 개수는 0 이상이어야 합니다.", ephemeral=True)
                return
            
            # 총 코어 개수 체크
            total_cores = legend + epic + rare + common
            if total_cores == 0:
                await interaction.response.send_message("❌ 최소 1개 이상의 코어가 필요합니다.", ephemeral=True)
                return
            
            # 코어 설정 업데이트
            self.optimization_manager.set_core_counts(legend, epic, rare, common)
            
            embed = discord.Embed(
                title="✅ 코어 설정 완료",
                description=f"코어 설정이 업데이트되었습니다.",
                color=0x00ff00
            )
            embed.add_field(
                name="설정된 코어",
                value=f"🟠 전설: {legend}개\n🟣 영웅: {epic}개\n🔵 레어: {rare}개\n⚪ 일반: {common}개\n\n**총 {total_cores}개**",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ 올바른 숫자를 입력해주세요.", ephemeral=True)
        except Exception as e:
            logger.error(f"코어 설정 중 오류: {e}")
            await interaction.response.send_message(f"❌ 코어 설정 중 오류 발생: {e}", ephemeral=True)


class TargetSetupModal(ui.Modal, title='🎯 타겟 설정'):
    """코어 최적화 타겟 설정 모달"""
    
    def __init__(self, optimization_manager):
        super().__init__()
        self.optimization_manager = optimization_manager
    
    str_target = ui.TextInput(
        label='힘 목표값',
        placeholder='예: 4000',
        style=discord.TextStyle.short,
        max_length=6,
        required=False
    )
    
    int_target = ui.TextInput(
        label='지능 목표값',
        placeholder='예: 4000',
        style=discord.TextStyle.short,
        max_length=6,
        required=False
    )
    
    dex_target = ui.TextInput(
        label='민첩 목표값',
        placeholder='예: 4000',
        style=discord.TextStyle.short,
        max_length=6,
        required=False
    )
    
    luk_target = ui.TextInput(
        label='행운 목표값',
        placeholder='예: 4000',
        style=discord.TextStyle.short,
        max_length=6,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 입력값 처리
            targets = {}
            
            if self.str_target.value:
                targets['str'] = int(self.str_target.value)
            if self.int_target.value:
                targets['int'] = int(self.int_target.value)
            if self.dex_target.value:
                targets['dex'] = int(self.dex_target.value)
            if self.luk_target.value:
                targets['luk'] = int(self.luk_target.value)
            
            # 유효성 검증
            if not targets:
                await interaction.response.send_message("❌ 최소 하나의 목표값을 설정해주세요.", ephemeral=True)
                return
            
            # 음수나 너무 큰 값 체크
            for stat, value in targets.items():
                if value < 0:
                    await interaction.response.send_message(f"❌ {stat.upper()} 목표값은 0 이상이어야 합니다.", ephemeral=True)
                    return
                if value > 99999:
                    await interaction.response.send_message(f"❌ {stat.upper()} 목표값이 너무 큽니다. (최대 99999)", ephemeral=True)
                    return
            
            # 타겟 설정 업데이트
            self.optimization_manager.set_targets(targets)
            
            # 결과 표시
            embed = discord.Embed(
                title="🎯 타겟 설정 완료",
                description="최적화 목표가 설정되었습니다.",
                color=0x3498db
            )
            
            target_text = ""
            stat_names = {'str': '💪 힘', 'int': '🧠 지능', 'dex': '🏃 민첩', 'luk': '🍀 행운'}
            for stat, value in targets.items():
                target_text += f"{stat_names[stat]}: {value:,}\n"
            
            embed.add_field(
                name="설정된 목표",
                value=target_text,
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ 올바른 숫자를 입력해주세요.", ephemeral=True)
        except Exception as e:
            logger.error(f"타겟 설정 중 오류: {e}")
            await interaction.response.send_message(f"❌ 타겟 설정 중 오류 발생: {e}", ephemeral=True)


class OptimizationView(ui.View):
    """코어 최적화 메인 UI"""
    
    def __init__(self, optimization_manager):
        super().__init__(timeout=300)
        self.optimization_manager = optimization_manager
    
    @ui.button(label="코어 설정", style=discord.ButtonStyle.primary, emoji="🔮")
    async def setup_cores(self, interaction: discord.Interaction, button: ui.Button):
        """코어 개수 설정"""
        modal = CoreSetupModal(self.optimization_manager)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="타겟 설정", style=discord.ButtonStyle.secondary, emoji="🎯")
    async def setup_targets(self, interaction: discord.Interaction, button: ui.Button):
        """최적화 타겟 설정"""
        modal = TargetSetupModal(self.optimization_manager)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="최적화 실행", style=discord.ButtonStyle.success, emoji="⚡")
    async def run_optimization(self, interaction: discord.Interaction, button: ui.Button):
        """최적화 실행"""
        try:
            # defer로 응답 시간 연장
            await interaction.response.defer(ephemeral=True)
            
            # 설정 확인
            if not self.optimization_manager.is_ready():
                await interaction.followup.send("❌ 코어와 타겟을 먼저 설정해주세요.", ephemeral=True)
                return
            
            # 최적화 실행
            result = await self.optimization_manager.run_optimization()
            
            if result is None:
                await interaction.followup.send("❌ 최적화 실행 중 오류가 발생했습니다.", ephemeral=True)
                return
            
            # 결과 표시
            embed = self.optimization_manager.format_optimization_result(result)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"최적화 실행 중 오류: {e}")
            await interaction.followup.send(f"❌ 최적화 실행 중 오류 발생: {e}", ephemeral=True)
    
    @ui.button(label="현재 설정", style=discord.ButtonStyle.secondary, emoji="📋")
    async def show_current_settings(self, interaction: discord.Interaction, button: ui.Button):
        """현재 설정 표시"""
        embed = self.optimization_manager.get_current_settings_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)


class OptimizationManager:
    """최적화 시스템 관리자"""
    
    def __init__(self):
        self.core_optimizer = CoreOptimizer()
        self.core_counts = {'legend': 0, 'epic': 0, 'rare': 0, 'common': 0}
        self.targets = {}
        
    def set_core_counts(self, legend: int, epic: int, rare: int, common: int):
        """코어 개수 설정"""
        self.core_counts = {
            'legend': legend,
            'epic': epic,
            'rare': rare,
            'common': common
        }
    
    def set_targets(self, targets: Dict[str, int]):
        """목표값 설정"""
        self.targets = targets.copy()
    
    def is_ready(self) -> bool:
        """최적화 실행 준비 상태 확인"""
        total_cores = sum(self.core_counts.values())
        return total_cores > 0 and len(self.targets) > 0
    
    async def run_optimization(self) -> Optional[Dict]:
        """최적화 실행"""
        try:
            return self.core_optimizer.allocate_cores_with_targets(
                self.core_counts['legend'],
                self.core_counts['epic'],
                self.core_counts['rare'],
                self.core_counts['common'],
                self.targets
            )
        except Exception as e:
            logger.error(f"최적화 실행 실패: {e}")
            return None
    
    def get_current_settings_embed(self) -> discord.Embed:
        """현재 설정을 Embed로 반환"""
        embed = discord.Embed(
            title="📋 현재 최적화 설정",
            color=0x95a5a6
        )
        
        # 코어 설정
        total_cores = sum(self.core_counts.values())
        if total_cores > 0:
            core_text = (
                f"🟠 전설: {self.core_counts['legend']}개\n"
                f"🟣 영웅: {self.core_counts['epic']}개\n"
                f"🔵 레어: {self.core_counts['rare']}개\n"
                f"⚪ 일반: {self.core_counts['common']}개\n\n"
                f"**총 {total_cores}개**"
            )
        else:
            core_text = "설정되지 않음"
        
        embed.add_field(
            name="🔮 코어 설정",
            value=core_text,
            inline=True
        )
        
        # 타겟 설정
        if self.targets:
            stat_names = {'str': '💪 힘', 'int': '🧠 지능', 'dex': '🏃 민첩', 'luk': '🍀 행운'}
            target_text = ""
            for stat, value in self.targets.items():
                target_text += f"{stat_names[stat]}: {value:,}\n"
        else:
            target_text = "설정되지 않음"
        
        embed.add_field(
            name="🎯 목표 설정",
            value=target_text,
            inline=True
        )
        
        # 준비 상태
        ready_status = "✅ 준비됨" if self.is_ready() else "❌ 설정 필요"
        embed.add_field(
            name="⚡ 실행 준비",
            value=ready_status,
            inline=False
        )
        
        return embed
    
    def format_optimization_result(self, result: Dict) -> discord.Embed:
        """최적화 결과를 Embed로 포맷"""
        embed = discord.Embed(
            title="⚡ 코어 최적화 결과",
            color=0x00ff00
        )
        
        # 할당된 코어 정보
        allocation = result.get('allocation', {})
        core_info = ""
        core_types = ['legend', 'epic', 'rare', 'common']
        core_emojis = {'legend': '🟠', 'epic': '🟣', 'rare': '🔵', 'common': '⚪'}
        core_names = {'legend': '전설', 'epic': '영웅', 'rare': '레어', 'common': '일반'}
        
        for core_type in core_types:
            if core_type in allocation and allocation[core_type]:
                core_info += f"{core_emojis[core_type]} {core_names[core_type]} 코어:\n"
                for stat, count in allocation[core_type].items():
                    if count > 0:
                        stat_names = {'str': '힘', 'int': '지능', 'dex': '민첩', 'luk': '행운'}
                        core_info += f"  • {stat_names.get(stat, stat)}: {count}개\n"
                core_info += "\n"
        
        if core_info:
            embed.add_field(
                name="🔮 할당된 코어",
                value=core_info,
                inline=False
            )
        
        # 최종 스탯
        final_stats = result.get('final_stats', {})
        if final_stats:
            stat_names = {'str': '💪 힘', 'int': '🧠 지능', 'dex': '🏃 민첩', 'luk': '🍀 행운'}
            stats_info = ""
            for stat, value in final_stats.items():
                target_value = self.targets.get(stat, 0)
                status = "✅" if value >= target_value else "❌"
                stats_info += f"{stat_names.get(stat, stat)}: {value:,} {status}\n"
            
            embed.add_field(
                name="📊 최종 스탯",
                value=stats_info,
                inline=True
            )
        
        # 목표 달성 정보
        targets_met = result.get('targets_met', 0)
        total_targets = len(self.targets)
        achievement_rate = (targets_met / total_targets * 100) if total_targets > 0 else 0
        
        embed.add_field(
            name="🎯 목표 달성",
            value=f"{targets_met}/{total_targets} ({achievement_rate:.1f}%)",
            inline=True
        )
        
        return embed