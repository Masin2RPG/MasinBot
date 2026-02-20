

import json
import logging
import re
from typing import Optional

import discord
from discord import ui
from discord.ext import commands

# 로컬 모듈 임포트
from config import Config
from coupon_integrated import (create_coupon_simple,
                               format_coupon_create_result,
                               format_coupon_result, process_coupon_simple)
from decoder import SaveCodeDecoder
from encoder import SaveCodeEncoder, create_custom_savecode
from graduation_checker import GraduationChecker
from item_searcher import ItemSearcher
from items import ItemDatabase
from raid_system import RaidWaitingSystem
from savecode_decoder import decode_savecode2, extract_save_data
from savecode_manager import SaveCodeManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)







# 레이드 시스템 UI 클래스들

class RaidSelectView(ui.View):
    """레이드 선택 셀렉트 박스 뷰"""
    
    def __init__(self, raid_system, user_id):
        super().__init__(timeout=300)
        self.raid_system = raid_system
        self.user_id = user_id
        
        # 레이드 목록을 셀렉트 옵션으로 변환
        options = []
        for raid_name in raid_system.get_all_raids():
            options.append(discord.SelectOption(
                label=raid_name,
                value=raid_name,
                description=f"{raid_name} 파티 모집"
            ))
        
        # 셀렉트 메뉴 추가
        if options:
            self.raid_select = ui.Select(
                placeholder="모집할 레이드를 선택하세요...",
                options=options[:25],  # Discord 제한으로 최대 25개
                min_values=1,
                max_values=1
            )
            self.raid_select.callback = self.raid_select_callback
            self.add_item(self.raid_select)
    
    async def raid_select_callback(self, interaction: discord.Interaction):
        """레이드 선택 시 실행되는 콜백"""
        selected_raid = self.raid_select.values[0]
        
        # 먼저 모달 열기
        modal = PartyRecruitmentModal(self.raid_system, self.user_id, selected_raid)
        await interaction.response.send_modal(modal)
        
        # 백그라운드에서 원본 메시지 업데이트
        async def update_original_message():
            import asyncio
            await asyncio.sleep(1)  # 모달이 열린 후 잠깐 대기
            try:
                updated_embed = discord.Embed(
                    title="✅ 레이드 선택 완료",
                    description=f"**{selected_raid}** 레이드를 선택했습니다.",
                    color=0x00ff00
                )
                await interaction.edit_original_response(embed=updated_embed, view=None)
            except:
                pass  # 오류 무시
        
        # 백그라운드 태스크로 실행
        import asyncio
        asyncio.create_task(update_original_message())

class PartyRecruitmentModal(ui.Modal, title='📢 파티 모집하기'):
    """파티 모집 생성 모달 (레이드는 이미 선택됨)"""
    
    def __init__(self, raid_system, user_id, selected_raid):
        super().__init__()
        self.raid_system = raid_system
        self.user_id = user_id
        self.selected_raid = selected_raid
    
    room_title = ui.TextInput(
        label='방제',
        placeholder='예: 빠른 클리어, 초보 환영, 숙련자만 등',
        style=discord.TextStyle.short,
        max_length=50,
        required=True
    )
    
    max_members = ui.TextInput(
        label='모집 인원',
        placeholder='예: 4 (본인 포함)',
        default='4',
        style=discord.TextStyle.short,
        max_length=2,
        required=True
    )
    
    scheduled_time = ui.TextInput(
        label='예정 시간 (선택사항)',
        placeholder='예: 오늘 저녁 8시, 30분 후 등',
        style=discord.TextStyle.short,
        max_length=50,
        required=False
    )
    
    description = ui.TextInput(
        label='모집 설명 (선택사항)',
        placeholder='예: 초보 환영, 숙련자만, 빠른 클리어 등',
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 입력값 검증
            raid_name = self.selected_raid  # 미리 선택된 레이드 사용
            max_members_count = int(self.max_members.value.strip())
            room_title = self.room_title.value.strip()
            
            # 방제 검증
            if not room_title:
                await interaction.response.send_message(
                    "❌ 방제를 입력해주세요.",
                    ephemeral=True
                )
                return
            
            # 인원수 검증
            if max_members_count < 2 or max_members_count > 8:
                await interaction.response.send_message(
                    "❌ 모집 인원은 2명~8명 사이여야 합니다.",
                    ephemeral=True
                )
                return
            
            # 기존 파티 확인 (한 명당 하나의 파티만 리더 가능)
            existing_parties = self.raid_system.get_user_led_parties(self.user_id)
            if existing_parties:
                await interaction.response.send_message(
                    "❌ 이미 리더로 모집 중인 파티가 있습니다. 기존 파티를 먼저 종료해주세요.",
                    ephemeral=True
                )
                return
            
            # 파티 생성
            party_id = self.raid_system.create_party_recruitment(
                leader_id=self.user_id,
                raid_name=raid_name,
                max_members=max_members_count,
                description=self.description.value.strip(),
                scheduled_time=self.scheduled_time.value.strip(),
                room_title=self.room_title.value.strip()
            )
            
            party = self.raid_system.get_party_recruitment(party_id)
            
            # 해당 레이드 대기자들에게 알림 DM 발송
            await self.send_party_notification(interaction, party, raid_name)
            
            embed = discord.Embed(
                title="✅ 파티 모집이 생성되었습니다!",
                description=f"파티 ID: `{party_id}`",
                color=0x00ff00
            )
            
            embed.add_field(
                name="📋 모집 정보",
                value=self.raid_system.format_party_info(party, interaction.guild),
                inline=False
            )
            
            embed.add_field(
                name="💡 안내",
                value="• 다른 사용자들이 '파티 찾기'에서 참가할 수 있습니다\n• 해당 레이드 대기자들에게 알림을 발송했습니다",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # 백그라운드에서 15초 후 메시지 자동 삭제
            async def delete_after_delay():
                import asyncio
                await asyncio.sleep(15)
                try:
                    await interaction.delete_original_response()
                except:
                    pass  # 이미 삭제된 경우 무시
            
            # 백그라운드 태스크로 실행
            import asyncio
            asyncio.create_task(delete_after_delay())
            
        except ValueError:
            await interaction.response.send_message("❌ 모집 인원은 숫자로 입력해주세요.", ephemeral=True)
        except Exception as e:
            logger.error(f"파티 모집 생성 중 오류: {e}")
            await interaction.response.send_message(f"❌ 파티 모집 생성 중 오류 발생: {e}", ephemeral=True)
    
    async def send_party_notification(self, interaction, party, raid_name):
        """해당 레이드 대기자들에게 파티 모집 알림 DM 발송"""
        try:
            # 해당 레이드 대기자 목록 가져오기
            waiting_users = self.raid_system.get_raid_participants(raid_name)
            
            # 파티 리더는 제외
            waiting_users = [user_id for user_id in waiting_users if user_id != self.user_id]
            
            if not waiting_users:
                return  # 대기자가 없으면 알림 안 보냄
            
            sent_count = 0
            failed_count = 0
            
            for user_id in waiting_users:
                try:
                    user = interaction.guild.get_member(user_id)
                    if user:
                        # 알림 DM 생성
                        notification_embed = discord.Embed(
                            title="🔔 파티 모집 알림",
                            description=f"대기 중이신 **{raid_name}** 레이드의 파티 모집이 등록되었습니다!",
                            color=0x3498db
                        )
                        
                        notification_embed.add_field(
                            name="📋 모집 정보",
                            value=f"**레이드**: {raid_name}\n**리더**: {interaction.guild.get_member(party.leader_id).display_name if interaction.guild.get_member(party.leader_id) else 'Unknown'}\n**모집 인원**: {party.max_members}명\n**현재 인원**: {len(party.current_members)}명",
                            inline=False
                        )
                        
                        if party.description:
                            notification_embed.add_field(
                                name="📝 모집 설명",
                                value=party.description,
                                inline=False
                            )
                        
                        if party.scheduled_time:
                            notification_embed.add_field(
                                name="⏰ 예정 시간",
                                value=party.scheduled_time,
                                inline=False
                            )
                        
                        notification_embed.add_field(
                            name="💡 참가 방법",
                            value="서버의 **👥 파티 찾기** 버튼을 클릭하여 참가할 수 있습니다!",
                            inline=False
                        )
                        
                        notification_embed.set_footer(text=f"서버: {interaction.guild.name}")
                        
                        await user.send(embed=notification_embed)
                        sent_count += 1
                        
                except discord.Forbidden:
                    # DM을 받을 수 없는 사용자
                    failed_count += 1
                except Exception as e:
                    logger.error(f"파티 모집 알림 DM 발송 중 오류 (user_id: {user_id}): {e}")
                    failed_count += 1
            
            logger.info(f"파티 모집 알림 발송 완료 - 성공: {sent_count}명, 실패: {failed_count}명")
            
        except Exception as e:
            logger.error(f"파티 모집 알림 발송 중 전체 오류: {e}")


class CouponProcessModal(ui.Modal, title='🎫 쿠폰 사용하기'):
    """쿠폰 처리를 위한 모달"""
    
    def __init__(self, bot_instance):
        super().__init__()
        self.bot_instance = bot_instance
    
    coupon_code = ui.TextInput(
        label='쿠폰 코드',
        placeholder='쿠폰 코드를 입력해주세요',
        style=discord.TextStyle.short,
        max_length=50,
        required=True
    )
    
    player_name = ui.TextInput(
        label='플레이어 이름',
        placeholder='게임 내 플레이어 이름을 입력해주세요',
        style=discord.TextStyle.short,
        max_length=30,
        required=True
    )
    
    savecode = ui.TextInput(
        label='세이브코드',
        placeholder='현재 세이브코드를 입력해주세요 (MasinSaveV2_ 또는 원본 형식)',
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 시 쿠폰 처리"""
        try:
            # 즉시 응답하여 타임아웃 방지
            await interaction.response.defer(ephemeral=True)
            
            # 입력값 검증
            coupon_code = self.coupon_code.value.strip()
            player_name = self.player_name.value.strip()
            savecode = self.savecode.value.strip()
            
            if not coupon_code or not player_name or not savecode:
                await interaction.followup.send(
                    "❌ 모든 필드를 올바르게 입력해주세요.",
                    ephemeral=True
                )
                return
            
            # 처리 시작 메시지
            processing_embed = discord.Embed(
                title="🔄 쿠폰 처리 중...",
                description="쿠폰을 확인하고 세이브코드를 처리하고 있습니다. 잠시만 기다려주세요.",
                color=0xffff00
            )
            await interaction.followup.send(embed=processing_embed, ephemeral=True)
            
            # 쿠폰 처리 실행
            result = process_coupon_simple(coupon_code, savecode, player_name)
            
            # 결과 처리
            if result.success:
                # 성공 시 DM으로 결과 전송
                success_embed = discord.Embed(
                    title="🎉 쿠폰 사용 성공!",
                    color=0x00ff00
                )
                
                success_embed.add_field(
                    name="🎫 쿠폰 코드",
                    value=f"`{result.coupon_code}`",
                    inline=True
                )
                
                success_embed.add_field(
                    name="👤 플레이어",
                    value=f"`{player_name}`",
                    inline=True
                )
                
                success_embed.add_field(
                    name="💰 획득 리워드",
                    value=f"골드: +{result.gold_gained:,}\n나무: +{result.lumber_gained:,}",
                    inline=False
                )
                
                success_embed.add_field(
                    name="🔮 수정된 세이브코드",
                    value=f"```{result.modified_savecode}```",
                    inline=False
                )
                
                success_embed.add_field(
                    name="💡 사용 방법",
                    value="게임에서 '불러오기'를 선택하고 위의 세이브코드를 입력하세요.",
                    inline=False
                )
                
                success_embed.set_footer(text=f"처리 완료 시간: {discord.utils.format_dt(discord.utils.utcnow(), style='F')}")
                
                try:
                    await interaction.user.send(embed=success_embed)
                    
                    # 서버에서는 DM 전송 완료 메시지
                    await interaction.edit_original_response(
                        embed=discord.Embed(
                            title="✅ 처리 완료",
                            description="쿠폰이 성공적으로 처리되었습니다!\n결과를 개인 DM으로 발송했습니다.",
                            color=0x00ff00
                        )
                    )
                    
                except discord.Forbidden:
                    # DM을 보낼 수 없는 경우 서버에서 직접 표시
                    await interaction.edit_original_response(embed=success_embed)
                    
            else:
                # 실패 시 오류 메시지
                error_embed = discord.Embed(
                    title="❌ 쿠폰 사용 실패",
                    description=result.error_message,
                    color=0xff0000
                )
                
                error_embed.add_field(
                    name="🎫 쿠폰 코드",
                    value=f"`{result.coupon_code}`",
                    inline=True
                )
                
                error_embed.add_field(
                    name="👤 플레이어",
                    value=f"`{player_name}`",
                    inline=True
                )
                
                # DM으로 오류 메시지 전송 시도
                try:
                    await interaction.user.send(embed=error_embed)
                    
                    await interaction.edit_original_response(
                        embed=discord.Embed(
                            title="❌ 처리 실패",
                            description="쿠폰 처리에 실패했습니다.\n오류 내용을 개인 DM으로 발송했습니다.",
                            color=0xff0000
                        )
                    )
                    
                except discord.Forbidden:
                    # DM을 보낼 수 없는 경우 서버에서 직접 표시
                    await interaction.edit_original_response(embed=error_embed)
                    
        except Exception as e:
            logger.error(f"쿠폰 처리 중 오류: {str(e)}")
            
            error_embed = discord.Embed(
                title="❌ 시스템 오류",
                description="쿠폰 처리 중 예상치 못한 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xff0000
            )
            
            try:
                await interaction.edit_original_response(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)


class CouponCreateModal(ui.Modal, title='🎫 쿠폰 생성하기'):
    """쿠폰 생성을 위한 모달"""
    
    def __init__(self):
        super().__init__()
    
    lumber = ui.TextInput(
        label='나무 수량',
        placeholder='나무 수량을 입력하세요 (예: 100000)',
        style=discord.TextStyle.short,
        max_length=10,
        required=True
    )
    
    gold = ui.TextInput(
        label='골드 수량',
        placeholder='골드 수량을 입력하세요 (예: 500000)',
        style=discord.TextStyle.short,
        max_length=10,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 시 쿠폰 생성"""
        try:
            # 즉시 응답하여 타임아웃 방지
            await interaction.response.defer(ephemeral=True)
            
            # 입력값 검증
            lumber_value = self.lumber.value.strip()
            gold_value = self.gold.value.strip()
            
            if not lumber_value or not gold_value:
                await interaction.followup.send(
                    "❌ 나무와 골드 수량을 모두 입력해주세요.",
                    ephemeral=True
                )
                return
            
            try:
                lumber_int = int(lumber_value)
                gold_int = int(gold_value)
            except ValueError:
                await interaction.followup.send(
                    "❌ 나무와 골드는 숫자로 입력해주세요.",
                    ephemeral=True
                )
                return
            
            if lumber_int < 0 or gold_int < 0:
                await interaction.followup.send(
                    "❌ 나무와 골드는 0 이상의 값이어야 합니다.",
                    ephemeral=True
                )
                return
            
            if lumber_int > 99999999 or gold_int > 99999999:
                await interaction.followup.send(
                    "❌ 나무와 골드는 99,999,999 이하의 값이어야 합니다.",
                    ephemeral=True
                )
                return
            
            # 처리 시작 메시지
            processing_embed = discord.Embed(
                title="🔄 쿠폰 생성 중...",
                description="쿠폰을 생성하고 있습니다. 잠시만 기다려주세요.",
                color=0xffff00
            )
            await interaction.followup.send(embed=processing_embed, ephemeral=True)
            
            # 쿠폰 생성 실행
            success, response = create_coupon_simple(lumber_int, gold_int)
            
            # 결과 처리
            if success and response.is_success:
                # 성공 시 DM으로 결과 전송
                success_embed = discord.Embed(
                    title="🎉 쿠폰 생성 성공!",
                    color=0x00ff00
                )
                
                success_embed.add_field(
                    name="🎫 생성된 쿠폰 코드",
                    value=f"```{response.coupon_code}```",
                    inline=False
                )
                
                success_embed.add_field(
                    name="💰 쿠폰 내용",
                    value=f"골드: {response.gold:,}\n나무: {response.lumber:,}",
                    inline=True
                )
                
                success_embed.add_field(
                    name="💡 사용 방법",
                    value="/쿠폰 명령어로 이 코드를 사용할 수 있습니다!",
                    inline=True
                )
                
                success_embed.set_footer(text=f"생성 시간: {discord.utils.format_dt(discord.utils.utcnow(), style='F')}")
                
                try:
                    await interaction.user.send(embed=success_embed)
                    
                    # 서버에서는 DM 전송 완료 메시지
                    await interaction.edit_original_response(
                        embed=discord.Embed(
                            title="✅ 쿠폰 생성 완료",
                            description=f"쿠폰이 성공적으로 생성되었습니다!\n쿠폰 코드를 개인 DM으로 발송했습니다.",
                            color=0x00ff00
                        )
                    )
                    
                except discord.Forbidden:
                    # DM을 보낼 수 없는 경우 서버에서 직접 표시
                    await interaction.edit_original_response(embed=success_embed)
                    
            else:
                # 실패 시 오류 메시지
                error_embed = discord.Embed(
                    title="❌ 쿠폰 생성 실패",
                    description=response.error_message,
                    color=0xff0000
                )
                
                error_embed.add_field(
                    name="💰 요청한 내용",
                    value=f"골드: {gold_int:,}\n나무: {lumber_int:,}",
                    inline=True
                )
                
                await interaction.edit_original_response(embed=error_embed)
                    
        except Exception as e:
            logger.error(f"쿠폰 생성 중 오류: {str(e)}")
            
            error_embed = discord.Embed(
                title="❌ 시스템 오류",
                description="쿠폰 생성 중 예상치 못한 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xff0000
            )
            
            try:
                await interaction.edit_original_response(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)


class PartyListView(ui.View):
    """파티 찾기 UI"""
    
    def __init__(self, raid_system, current_parties, user_id):
        super().__init__(timeout=300)
        self.raid_system = raid_system
        self.current_parties = current_parties
        self.user_id = user_id
        
        # 파티별 참가 버튼 생성 (최대 25개 버튼 제한)
        for i, party in enumerate(current_parties[:20]):  # 최대 20개 파티만 표시
            button = ui.Button(
                label=f"{party.raid_name} ({len(party.current_members)}/{party.max_members})",
                style=discord.ButtonStyle.primary,
                custom_id=f"join_party_{party.party_id}",
                row=i // 4  # 4개씩 한 줄에 배치
            )
            button.callback = self.create_join_callback(party.party_id)
            self.add_item(button)
        
        # 새로고침 버튼
        refresh_button = ui.Button(
            label="🔄 새로고침",
            style=discord.ButtonStyle.secondary,
            row=4
        )
        refresh_button.callback = self.refresh_party_list
        self.add_item(refresh_button)
    
    def create_join_callback(self, party_id: str):
        """파티 참가 콜백 생성"""
        async def join_callback(interaction: discord.Interaction):
            try:
                party = self.raid_system.get_party_recruitment(party_id)
                if not party or not party.is_active:
                    await interaction.response.send_message("❌ 해당 파티 모집이 종료되었습니다.", ephemeral=True)
                    return
                
                if party.is_full():
                    await interaction.response.send_message("❌ 파티가 이미 가득 찼습니다.", ephemeral=True)
                    return
                
                if self.user_id in party.current_members:
                    await interaction.response.send_message("❌ 이미 해당 파티에 참가 중입니다.", ephemeral=True)
                    return
                
                # 파티 참가
                success = self.raid_system.join_party(party_id, self.user_id)
                if success:
                    # 파티 참가 성공 시 해당 레이드 대기 목록에서 제거
                    was_waiting = self.user_id in self.raid_system.get_raid_participants(party.raid_name)
                    if was_waiting:
                        self.raid_system.toggle_raid_participation(party.raid_name, self.user_id)
                    
                    embed = discord.Embed(
                        title="✅ 파티 참가 완료!",
                        description=f"**{party.raid_name}** 파티에 참가했습니다.",
                        color=0x00ff00
                    )
                    
                    if was_waiting:
                        embed.add_field(
                            name="📤 대기 목록 제거",
                            value=f"**{party.raid_name}** 레이드 대기 목록에서 자동으로 제거되었습니다.",
                            inline=False
                        )
                    
                    embed.add_field(
                        name="📋 파티 정보",
                        value=self.raid_system.format_party_info(party, interaction.guild),
                        inline=False
                    )
                    
                    # 파티가 가득 찬 경우
                    if party.is_full():
                        embed.add_field(
                            name="🎉 파티 구성 완료!",
                            value="모든 자리가 채워졌습니다!\n리더가 **내 파티 관리**에서 레이드를 시작할 수 있습니다.",
                            inline=False
                        )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    # 백그라운드에서 10초 후 메시지 자동 삭제
                    async def delete_after_delay():
                        import asyncio
                        await asyncio.sleep(10)
                        try:
                            await interaction.delete_original_response()
                        except:
                            pass  # 이미 삭제된 경우 무시
                    
                    # 백그라운드 태스크로 실행
                    import asyncio
                    asyncio.create_task(delete_after_delay())
                else:
                    await interaction.response.send_message("❌ 파티 참가에 실패했습니다.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"파티 참가 중 오류: {e}")
                await interaction.response.send_message(f"❌ 파티 참가 중 오류 발생: {e}", ephemeral=True)
        
        return join_callback
    
    async def refresh_party_list(self, interaction: discord.Interaction):
        """파티 목록 새로고침"""
        try:
            # 새로운 파티 목록 가져오기
            new_parties = self.raid_system.get_active_parties()
            
            if not new_parties:
                embed = discord.Embed(
                    title="👥 파티 찾기",
                    description="현재 모집 중인 파티가 없습니다.",
                    color=0x95a5a6
                )
                embed.add_field(
                    name="💡 파티 모집하는 방법",
                    value="• **📢 파티 모집하기** 버튼 클릭\n• 레이드와 인원수 설정\n• 다른 사용자들이 참가 신청",
                    inline=False
                )
                await interaction.response.edit_message(embed=embed, view=None)
                return
            
            # 새로운 파티 목록으로 업데이트
            self.parties = new_parties
            self.current_page = 0
            
            # UI 갱신
            embed = discord.Embed(
                title="👥 파티 찾기",
                description=f"현재 {len(new_parties)}개의 파티가 모집 중입니다.",
                color=0x3498db
            )
            
            for i, party in enumerate(new_parties[:10]):
                embed.add_field(
                    name=f"🎯 {party.raid_name}",
                    value=self.raid_system.format_party_info(party, interaction.guild),
                    inline=True
                )
            
            if len(new_parties) > 10:
                embed.set_footer(text=f"+ {len(new_parties) - 10}개의 추가 파티가 있습니다.")
            
            # 새로운 뷰로 업데이트
            new_view = PartyListView(self.raid_system, new_parties, self.user_id)
            await interaction.response.edit_message(embed=embed, view=new_view)
            
        except Exception as e:
            logger.error(f"파티 목록 새로고침 중 오류: {e}")
            await interaction.response.send_message(f"❌ 파티 목록 새로고침 중 오류 발생: {e}", ephemeral=True)


class PartyManagementView(ui.View):
    """사용자의 파티 관리를 위한 뷰"""
    
    def __init__(self, raid_system, user_id, led_parties, joined_parties):
        super().__init__(timeout=300)
        self.raid_system = raid_system
        self.user_id = user_id
        self.led_parties = led_parties
        self.joined_parties = joined_parties
        
        # 리더인 파티가 있으면 관련 버튼들 추가
        if led_parties:
            for party in led_parties:
                # 파티에 2명 이상 있으면 레이드 시작 버튼 추가 (인원이 다 차지 않아도 가능)
                if len(party.current_members) >= 2:
                    start_button = ui.Button(
                        label=f"🚀 {party.raid_name} 레이드 시작",
                        style=discord.ButtonStyle.success,
                        custom_id=f"start_raid_{party.party_id}"
                    )
                    start_button.callback = self.create_start_raid_callback(party.party_id)
                    self.add_item(start_button)
                
                # 모집 종료 버튼 (항상 표시)
                close_button = ui.Button(
                    label=f"🚪 {party.raid_name} 모집 종료",
                    style=discord.ButtonStyle.danger,
                    custom_id=f"close_party_{party.party_id}"
                )
                close_button.callback = self.create_close_party_callback(party.party_id)
                self.add_item(close_button)
        
        # 참가 중인 파티가 있으면 탈퇴 버튼 추가 (리더가 아닌 경우만)
        if joined_parties:
            for party in joined_parties:
                if party.leader_id != user_id:  # 리더가 아닌 경우만
                    leave_button = ui.Button(
                        label=f"🚶 {party.raid_name} 파티 탈퇴",
                        style=discord.ButtonStyle.secondary,
                        custom_id=f"leave_party_{party.party_id}"
                    )
                    leave_button.callback = self.create_leave_party_callback(party.party_id)
                    self.add_item(leave_button)
    
    def create_close_party_callback(self, party_id: str):
        """파티 모집 종료 콜백 생성"""
        async def close_callback(interaction: discord.Interaction):
            try:
                party = self.raid_system.get_party_recruitment(party_id)
                if not party or not party.is_active:
                    await interaction.response.send_message("❌ 해당 파티 모집이 이미 종료되었습니다.", ephemeral=True)
                    return
                
                if party.leader_id != self.user_id:
                    await interaction.response.send_message("❌ 파티 리더만 모집을 종료할 수 있습니다.", ephemeral=True)
                    return
                
                # 파티 모집 종료
                success = self.raid_system.close_party_recruitment(party_id)
                if success:
                    embed = discord.Embed(
                        title="🚪 파티 모집 종료",
                        description=f"**{party.raid_name}** 파티 모집이 종료되었습니다.",
                        color=0xff9900
                    )
                    
                    embed.add_field(
                        name="📋 최종 파티 구성",
                        value=self.raid_system.format_party_info(party, interaction.guild),
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ 파티 모집 종료에 실패했습니다.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"파티 모집 종료 중 오류: {e}")
                # interaction이 이미 응답되었는지 확인
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ 파티 모집 종료 중 오류 발생: {e}", ephemeral=True)
                else:
                    # 이미 응답된 경우 followup 사용
                    await interaction.followup.send(f"❌ 파티 모집 종료 중 오류 발생: {e}", ephemeral=True)
        
        return close_callback
    
    def create_start_raid_callback(self, party_id: str):
        """레이드 시작 콜백 생성"""
        async def start_raid_callback(interaction: discord.Interaction):
            try:
                party = self.raid_system.get_party_recruitment(party_id)
                if not party or not party.is_active:
                    await interaction.response.send_message("❌ 해당 파티 모집이 이미 종료되었습니다.", ephemeral=True)
                    return
                
                if party.leader_id != self.user_id:
                    await interaction.response.send_message("❌ 파티 리더만 레이드를 시작할 수 있습니다.", ephemeral=True)
                    return
                
                if len(party.current_members) < 2:
                    await interaction.response.send_message("❌ 파티에 최소 2명 이상이 있어야 레이드를 시작할 수 있습니다.", ephemeral=True)
                    return
                
                # 파티 모집 종료 (레이드 시작)
                success = self.raid_system.close_party_recruitment(party_id)
                if success:
                    # 리더에게 성공 메시지
                    leader_embed = discord.Embed(
                        title="✅ 레이드 시작 완료",
                        description=f"**{party.raid_name}** 레이드가 시작되었습니다!\n모든 파티원에게 개인 메시지를 발송했습니다.",
                        color=0x00ff00
                    )
                    
                    # 각 파티원에게 개인 DM 발송
                    sent_count = 0
                    failed_count = 0
                    
                    for user_id in party.current_members:
                        try:
                            user = interaction.guild.get_member(user_id)
                            if user:
                                dm_embed = discord.Embed(
                                    title="🚀 레이드 시작 알림",
                                    description=f"참가하신 **{party.raid_name}** 레이드가 시작되었습니다!",
                                    color=0x00ff00
                                )
                                
                                dm_embed.add_field(
                                    name="🎯 레이드 정보",
                                    value=f"**레이드**: {party.raid_name}\n**방제**: {party.room_title}\n**파티원**: {len(party.current_members)}명\n**리더**: {interaction.guild.get_member(party.leader_id).display_name if interaction.guild.get_member(party.leader_id) else 'Unknown'}",
                                    inline=False
                                )
                                
                                # 파티원 목록 (DM용)
                                member_names = []
                                for member_id in party.current_members:
                                    member = interaction.guild.get_member(member_id)
                                    if member:
                                        if member_id == party.leader_id:
                                            member_names.append(f"👑 {member.display_name}")
                                        else:
                                            member_names.append(f"• {member.display_name}")
                                
                                dm_embed.add_field(
                                    name="👥 파티원",
                                    value="\n".join(member_names),
                                    inline=False
                                )
                                
                                dm_embed.add_field(
                                    name="💡 안내",
                                    value="레이드를 즐겨주세요! 파티원들과 함께 멋진 레이드를 완주하시길 바랍니다.",
                                    inline=False
                                )
                                
                                dm_embed.set_footer(text=f"서버: {interaction.guild.name}")
                                
                                await user.send(embed=dm_embed)
                                sent_count += 1
                            else:
                                failed_count += 1
                        except discord.Forbidden:
                            # DM을 받을 수 없는 사용자
                            failed_count += 1
                        except Exception as e:
                            logger.error(f"DM 발송 중 오류 (user_id: {user_id}): {e}")
                            failed_count += 1
                    
                    # 발송 결과 추가
                    leader_embed.add_field(
                        name="📨 발송 결과",
                        value=f"✅ 성공: {sent_count}명\n❌ 실패: {failed_count}명",
                        inline=False
                    )
                    
                    if failed_count > 0:
                        leader_embed.add_field(
                            name="⚠️ 알림",
                            value="일부 파티원에게 DM을 보낼 수 없었습니다. (DM 차단 또는 설정 문제)",
                            inline=False
                        )
                    
                    await interaction.response.send_message(embed=leader_embed, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ 레이드 시작에 실패했습니다.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"레이드 시작 중 오류: {e}")
                # interaction이 이미 응답되었는지 확인
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ 레이드 시작 중 오류 발생: {e}", ephemeral=True)
                else:
                    # 이미 응답된 경우 followup 사용
                    await interaction.followup.send(f"❌ 레이드 시작 중 오류 발생: {e}", ephemeral=True)
        
        return start_raid_callback
    
    def create_leave_party_callback(self, party_id: str):
        """파티 탈퇴 콜백 생성"""
        async def leave_callback(interaction: discord.Interaction):
            try:
                party = self.raid_system.get_party_recruitment(party_id)
                if not party or not party.is_active:
                    await interaction.response.send_message("❌ 해당 파티 모집이 이미 종료되었습니다.", ephemeral=True)
                    return
                
                if self.user_id not in party.current_members:
                    await interaction.response.send_message("❌ 해당 파티에 참가하고 있지 않습니다.", ephemeral=True)
                    return
                
                if party.leader_id == self.user_id:
                    await interaction.response.send_message("❌ 파티 리더는 탈퇴할 수 없습니다. 파티 모집을 종료해주세요.", ephemeral=True)
                    return
                
                # 파티 탈퇴
                success = self.raid_system.leave_party(party_id, self.user_id)
                if success:
                    embed = discord.Embed(
                        title="🚶 파티 탈퇴 완료",
                        description=f"**{party.raid_name}** 파티에서 탈퇴했습니다.",
                        color=0xff9900
                    )
                    
                    # 다시 레이드 대기 목록에 추가할지 선택할 수 있는 뷰 생성
                    rejoin_view = RejoinWaitingView(self.raid_system, self.user_id, party.raid_name)
                    
                    embed.add_field(
                        name="📋 현재 파티 구성",
                        value=self.raid_system.format_party_info(party, interaction.guild),
                        inline=False
                    )
                    
                    embed.add_field(
                        name="💡 레이드 대기 재등록",
                        value="아래 버튼을 클릭하여 다시 레이드 대기 목록에 등록할 수 있습니다.",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed, view=rejoin_view, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ 파티 탈퇴에 실패했습니다.", ephemeral=True)
                
            except Exception as e:
                logger.error(f"파티 탈퇴 중 오류: {e}")
                # interaction이 이미 응답되었는지 확인
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ 파티 탈퇴 중 오류 발생: {e}", ephemeral=True)
                else:
                    # 이미 응답된 경우 followup 사용
                    await interaction.followup.send(f"❌ 파티 탈퇴 중 오류 발생: {e}", ephemeral=True)
        
        return leave_callback


class RejoinWaitingView(ui.View):
    """파티 탈퇴 후 레이드 대기 재등록 뷰"""
    
    def __init__(self, raid_system, user_id, raid_name):
        super().__init__(timeout=300)
        self.raid_system = raid_system
        self.user_id = user_id
        self.raid_name = raid_name
    
    @ui.button(label="🔄 레이드 대기 재등록", style=discord.ButtonStyle.primary, emoji="🔄")
    async def rejoin_waiting_button(self, interaction: discord.Interaction, button: ui.Button):
        """레이드 대기 재등록 버튼"""
        try:
            # 이미 대기 중인지 확인
            if self.user_id in self.raid_system.get_raid_participants(self.raid_name):
                await interaction.response.send_message("❌ 이미 해당 레이드 대기 목록에 등록되어 있습니다.", ephemeral=True)
                return
            
            # 레이드 대기 목록에 추가
            self.raid_system.toggle_raid_participation(self.raid_name, self.user_id)
            
            embed = discord.Embed(
                title="✅ 레이드 대기 재등록 완료",
                description=f"**{self.raid_name}** 레이드 대기 목록에 다시 등록되었습니다.",
                color=0x00ff00
            )
            
            embed.add_field(
                name="💡 안내",
                value="새로운 파티 모집이 있을 때 알림을 받게 됩니다.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # 원본 메시지의 View 비활성화
            try:
                original_embed = discord.Embed(
                    title="✅ 재등록 완료",
                    description="레이드 대기 목록에 재등록되었습니다.",
                    color=0x00ff00
                )
                await interaction.edit_original_response(embed=original_embed, view=None)
            except:
                pass
            
        except Exception as e:
            logger.error(f"레이드 대기 재등록 중 오류: {e}")
            await interaction.response.send_message(f"❌ 레이드 대기 재등록 중 오류 발생: {e}", ephemeral=True)
    
    @ui.button(label="❌ 취소", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        """취소 버튼"""
        embed = discord.Embed(
            title="❌ 취소됨",
            description="레이드 대기 재등록을 취소했습니다.",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # 원본 메시지의 View 비활성화
        try:
            original_embed = discord.Embed(
                title="❌ 취소됨",
                description="레이드 대기 재등록을 취소했습니다.",
                color=0x95a5a6
            )
            await interaction.edit_original_response(embed=original_embed, view=None)
        except:
            pass


class RaidSelectionView(ui.View):
    """레이드 선택 토글 UI"""
    
    def __init__(self, raid_system: RaidWaitingSystem, user_id: int):
        super().__init__(timeout=300)
        self.raid_system = raid_system
        self.user_id = user_id
        self.selected_raids = set()  # 선택된 레이드들
        
        # 현재 사용자가 대기 중인 레이드들 확인
        for raid_name in self.raid_system.get_all_raids():
            if user_id in self.raid_system.get_raid_participants(raid_name):
                self.selected_raids.add(raid_name)
        
        # 레이드별 토글 버튼 생성
        raid_names = self.raid_system.get_all_raids()
        for i, raid_name in enumerate(raid_names):
            is_selected = raid_name in self.selected_raids
            button = ui.Button(
                label=raid_name,
                style=discord.ButtonStyle.success if is_selected else discord.ButtonStyle.secondary,
                emoji="✅" if is_selected else "⬜",
                row=i // 4  # 4개씩 한 줄에 배치
            )
            button.callback = self.create_toggle_callback(raid_name)
            self.add_item(button)
        
        # 제출/취소 버튼 추가
        submit_button = ui.Button(
            label="제출",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            row=2
        )
        submit_button.callback = self.submit_selection
        self.add_item(submit_button)
        
        cancel_button = ui.Button(
            label="취소",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            row=2
        )
        cancel_button.callback = self.cancel_selection
        self.add_item(cancel_button)
    
    def create_toggle_callback(self, raid_name: str):
        """레이드별 토글 콜백 생성"""
        async def toggle_callback(interaction: discord.Interaction):
            if raid_name in self.selected_raids:
                self.selected_raids.remove(raid_name)
            else:
                self.selected_raids.add(raid_name)
            
            # 버튼 상태 업데이트
            for item in self.children:
                if isinstance(item, ui.Button) and item.label == raid_name:
                    is_selected = raid_name in self.selected_raids
                    item.style = discord.ButtonStyle.success if is_selected else discord.ButtonStyle.secondary
                    item.emoji = "✅" if is_selected else "⬜"
                    break
            
            await interaction.response.edit_message(view=self)
        
        return toggle_callback
    
    async def submit_selection(self, interaction: discord.Interaction):
        """선택 내용 제출"""
        # 기존 대기 목록에서 사용자 제거
        for raid_name in self.raid_system.get_all_raids():
            self.raid_system.remove_from_raid(raid_name, self.user_id)
        
        # 새로 선택된 레이드에 사용자 추가
        for raid_name in self.selected_raids:
            self.raid_system.add_to_raid(raid_name, self.user_id)
        
        # 결과 메시지 생성
        if self.selected_raids:
            selected_list = "\n".join([f"• {raid}" for raid in sorted(self.selected_raids)])
            embed = discord.Embed(
                title="✅ 레이드 대기 등록 완료",
                description=f"다음 레이드 대기 목록에 등록되었습니다:\n\n{selected_list}",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="📤 레이드 대기 해제",
                description="모든 레이드 대기가 해제되었습니다.",
                color=0xff9900
            )
        
        # 버튼 비활성화
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def cancel_selection(self, interaction: discord.Interaction):
        """선택 취소"""
        embed = discord.Embed(
            title="❌ 레이드 대기 등록 취소",
            description="레이드 대기 등록이 취소되었습니다.",
            color=0xff0000
        )
        
        # 버튼 비활성화
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)


class RaidControlView(ui.View):
    """레이드 제어 버튼을 제공하는 Persistent View"""
    
    def __init__(self, raid_system: RaidWaitingSystem):
        super().__init__(timeout=None)  # persistent view는 timeout 없음
        self.raid_system = raid_system
    
    @ui.button(label="레이드 대기 등록", style=discord.ButtonStyle.primary, emoji="🎯", custom_id="raid_wait_button")
    async def raid_wait_button(self, interaction: discord.Interaction, button: ui.Button):
        """레이드 대기 등록 버튼"""
        try:
            user_id = interaction.user.id
            
            # 현재 대기 중인 레이드 확인
            current_raids = []
            for raid_name in self.raid_system.get_all_raids():
                if user_id in self.raid_system.get_raid_participants(raid_name):
                    current_raids.append(raid_name)
            
            embed = discord.Embed(
                title="🎯 레이드 대기 등록",
                description="참여하고 싶은 레이드를 선택해주세요.\n토글 버튼으로 ON/OFF 할 수 있습니다.",
                color=0x3498db
            )
            
            if current_raids:
                current_list = "\n".join([f"• {raid}" for raid in current_raids])
                embed.add_field(
                    name="현재 대기 중인 레이드",
                    value=current_list,
                    inline=False
                )
            
            view = RaidSelectionView(self.raid_system, user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"레이드 대기 등록 중 오류: {e}")
            await interaction.response.send_message(f"❌ 레이드 대기 등록 중 오류 발생: {e}", ephemeral=True)
    
    @ui.button(label="헬퍼 대기 등록", style=discord.ButtonStyle.secondary, emoji="🤝", custom_id="helper_wait_button")
    async def helper_wait_button(self, interaction: discord.Interaction, button: ui.Button):
        """헬퍼 대기 등록 버튼"""
        try:
            user_id = interaction.user.id
            
            # 헬퍼 대기 상태 토글
            is_helper = self.raid_system.toggle_helper_participation(user_id)
            
            if is_helper:
                embed = discord.Embed(
                    title="✅ 헬퍼 대기 등록 완료",
                    description="헬퍼 대기 목록에 등록되었습니다!\n다른 플레이어들이 도움을 요청할 수 있습니다.",
                    color=0x00ff00
                )
                embed.add_field(
                    name="🤝 역할",
                    value="• 레이드 도움 제공\n• 가이드 및 조언\n• 파티 지원",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="📤 헬퍼 대기 해제",
                    description="헬퍼 대기 목록에서 제거되었습니다.",
                    color=0xff9900
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"헬퍼 대기 등록 중 오류: {e}")
            await interaction.response.send_message(f"❌ 헬퍼 대기 등록 중 오류 발생: {e}", ephemeral=True)
    
    @ui.button(label="파티 모집하기", style=discord.ButtonStyle.success, emoji="📢", custom_id="party_recruit_button")
    async def party_recruit_button(self, interaction: discord.Interaction, button: ui.Button):
        """파티 모집하기 버튼"""
        try:
            # 레이드 선택 뷰 생성
            raid_select_view = RaidSelectView(self.raid_system, interaction.user.id)
            
            # 사용 가능한 레이드가 있는지 확인
            if not hasattr(raid_select_view, 'raid_select'):
                await interaction.response.send_message(
                    "❌ 현재 사용 가능한 레이드가 없습니다.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="📢 파티 모집하기",
                description="모집할 레이드를 선택해주세요.",
                color=0x00ff00
            )
            
            await interaction.response.send_message(
                embed=embed,
                view=raid_select_view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"파티 모집 뷰 생성 중 오류: {e}")
            await interaction.response.send_message(f"❌ 파티 모집 뷰 생성 중 오류 발생: {e}", ephemeral=True)
    
    @ui.button(label="파티 찾기", style=discord.ButtonStyle.success, emoji="👥", custom_id="party_find_button")
    async def party_find_button(self, interaction: discord.Interaction, button: ui.Button):
        """파티 찾기 버튼"""
        try:
            # 현재 모집 중인 파티 목록 가져오기
            active_parties = self.raid_system.get_active_parties()
            
            if not active_parties:
                embed = discord.Embed(
                    title="👥 파티 찾기",
                    description="현재 모집 중인 파티가 없습니다.\n\n파티를 직접 모집해보세요!",
                    color=0x95a5a6
                )
                embed.add_field(
                    name="💡 파티 모집하는 방법",
                    value="• **📢 파티 모집하기** 버튼 클릭\n• 레이드와 인원수 설정\n• 다른 사용자들이 참가 신청",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # 파티 목록 표시
            embed = discord.Embed(
                title="👥 파티 찾기",
                description=f"현재 {len(active_parties)}개의 파티가 모집 중입니다.",
                color=0x3498db
            )
            
            for i, party in enumerate(active_parties[:10]):  # 최대 10개 파티 정보 표시
                embed.add_field(
                    name=f"🎯 {party.raid_name}",
                    value=self.raid_system.format_party_info(party, interaction.guild),
                    inline=True
                )
            
            if len(active_parties) > 10:
                embed.set_footer(text=f"+ {len(active_parties) - 10}개의 추가 파티가 있습니다.")
            
            # 파티 참가 UI 표시
            view = PartyListView(self.raid_system, active_parties, interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"파티 찾기 중 오류: {e}")
            await interaction.response.send_message(f"❌ 파티 찾기 중 오류 발생: {e}", ephemeral=True)
    
    @ui.button(label="대기방 현황", style=discord.ButtonStyle.secondary, emoji="🏛️", custom_id="raid_room_button")
    async def raid_room_button(self, interaction: discord.Interaction, button: ui.Button):
        """대기방 현황 버튼"""
        try:
            embed = discord.Embed(
                title="🏛️ 레이드 대기방 현황",
                description="각 레이드별 대기자 목록입니다",
                color=0x9b59b6
            )
            
            # 각 레이드별 대기자 정보 추가
            has_participants = False
            for raid_name in self.raid_system.get_all_raids():
                participants = self.raid_system.get_raid_participants(raid_name)
                if participants:
                    has_participants = True
                    participant_mentions = []
                    for user_id in participants:
                        try:
                            user = interaction.guild.get_member(user_id)
                            if user:
                                participant_mentions.append(user.display_name)
                            else:
                                participant_mentions.append(f"Unknown User ({user_id})")
                        except:
                            participant_mentions.append(f"Unknown User ({user_id})")
                    
                    embed.add_field(
                        name=f"🎯 {raid_name}",
                        value=f"**대기자 {len(participants)}명**\n" + "\n".join([f"• {name}" for name in participant_mentions[:5]]) + 
                              (f"\n... 외 {len(participants)-5}명" if len(participants) > 5 else ""),
                        inline=True
                    )
            
            # 헬퍼 대기자 정보 추가
            helpers = self.raid_system.get_helper_participants()
            if helpers:
                has_participants = True
                helper_mentions = []
                for user_id in helpers:
                    try:
                        user = interaction.guild.get_member(user_id)
                        if user:
                            helper_mentions.append(user.display_name)
                        else:
                            helper_mentions.append(f"Unknown User ({user_id})")
                    except:
                        helper_mentions.append(f"Unknown User ({user_id})")
                
                embed.add_field(
                    name="🤝 헬퍼 대기",
                    value=f"**헬퍼 {len(helpers)}명**\n" + "\n".join([f"• {name}" for name in helper_mentions[:5]]) + 
                          (f"\n... 외 {len(helpers)-5}명" if len(helpers) > 5 else ""),
                    inline=True
                )
            
            if not has_participants:
                embed.add_field(
                    name="📭 현재 상황",
                    value="아직 대기 중인 사용자가 없습니다.\n\n레이드 대기 등록을 해보세요!",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"대기방 현황 조회 중 오류: {e}")
            await interaction.response.send_message(f"❌ 대기방 현황 조회 중 오류 발생: {e}", ephemeral=True)

    @ui.button(label="내 파티 관리", style=discord.ButtonStyle.danger, emoji="⚙️", custom_id="party_manage_button", row=1)
    async def party_manage_button(self, interaction: discord.Interaction, button: ui.Button):
        """내 파티 관리 버튼"""
        try:
            user_id = interaction.user.id
            
            # 사용자가 리더인 파티와 참가 중인 파티 확인
            led_parties = self.raid_system.get_user_led_parties(user_id)
            joined_parties = self.raid_system.get_user_joined_parties(user_id)
            
            if not led_parties and not joined_parties:
                embed = discord.Embed(
                    title="⚙️ 내 파티 관리",
                    description="현재 리더이거나 참가 중인 파티가 없습니다.",
                    color=0x95a5a6
                )
                embed.add_field(
                    name="💡 파티 참가 방법",
                    value="• **📢 파티 모집하기**로 새 파티 만들기\n• **👥 파티 찾기**에서 기존 파티 참가",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # 파티 관리 뷰 표시
            view = PartyManagementView(self.raid_system, user_id, led_parties, joined_parties)
            
            embed = discord.Embed(
                title="⚙️ 내 파티 관리",
                description="• 파티에 2명 이상 있는 경우: **🚀 레이드 시작** 버튼으로 레이드 개시\n• 리더인 파티: **🚪 모집 종료** 가능\n• 참가 중인 파티: **🚶 파티 탈퇴** 가능",
                color=0xe74c3c
            )
            
            if led_parties:
                led_info = []
                for party in led_parties:
                    status = " (🚀 시작 가능)" if party.is_full() else ""
                    led_info.append(f"• **{party.raid_name}** ({len(party.current_members)}/{party.max_members}명){status}")
                embed.add_field(
                    name="👑 리더인 파티",
                    value="\n".join(led_info),
                    inline=False
                )
            
            if joined_parties:
                joined_info = []
                for party in joined_parties:
                    if user_id != party.leader_id:  # 리더가 아닌 경우만
                        joined_info.append(f"• **{party.raid_name}** ({len(party.current_members)}/{party.max_members}명)")
                if joined_info:
                    embed.add_field(
                        name="👥 참가 중인 파티",
                        value="\n".join(joined_info),
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"파티 관리 중 오류: {e}")
            await interaction.response.send_message(f"❌ 파티 관리 중 오류 발생: {e}", ephemeral=True)
            
            active_raids = 0
            
            for raid_name in self.raid_system.get_all_raids():
                waiting_users = self.raid_system.get_raid_participants(raid_name)
                
                if waiting_users:
                    active_raids += 1
                    
                    # 사용자 이름 목록 생성
                    user_list = []
                    for user_id in waiting_users:
                        try:
                            # 1. 길드 멤버로 먼저 시도 (더 정확한 정보)
                            member = interaction.guild.get_member(user_id) if interaction.guild else None
                            if member:
                                user_list.append(member.display_name)
                                continue
                            
                            # 2. 봇 캐시에서 사용자 정보 가져오기
                            user = interaction.client.get_user(user_id)
                            if user:
                                user_list.append(user.display_name)
                                continue
                            
                            # 3. API를 통해 사용자 정보 가져오기 (비동기)
                            try:
                                user = await interaction.client.fetch_user(user_id)
                                if user:
                                    user_list.append(user.display_name)
                                    continue
                            except:
                                pass
                            
                            # 4. 모든 방법이 실패한 경우
                            user_list.append(f"User#{user_id}")
                            
                        except Exception as e:
                            logger.warning(f"사용자 정보 가져오기 실패 (ID: {user_id}): {e}")
                            user_list.append(f"User#{user_id}")
                    
                    user_text = "\n".join([f"• {name}" for name in user_list[:10]])  # 최대 10명만 표시
                    if len(user_list) > 10:
                        user_text += f"\n... 외 {len(user_list) - 10}명"
                    
                    embed.add_field(
                        name=f"{raid_name} ({len(waiting_users)}명)",
                        value=user_text or "대기자 없음",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name=f"{raid_name} (0명)",
                        value="대기자 없음",
                        inline=True
                    )
            
            # 헬퍼 대기자 목록 추가
            helper_participants = self.raid_system.get_helper_participants()
            if helper_participants:
                helper_list = []
                for user_id in helper_participants:
                    try:
                        # 1. 길드 멤버로 먼저 시도
                        member = interaction.guild.get_member(user_id) if interaction.guild else None
                        if member:
                            helper_list.append(member.display_name)
                            continue
                        
                        # 2. 봇 캐시에서 사용자 정보 가져오기
                        user = interaction.client.get_user(user_id)
                        if user:
                            helper_list.append(user.display_name)
                            continue
                        
                        # 3. API를 통해 사용자 정보 가져오기
                        try:
                            user = await interaction.client.fetch_user(user_id)
                            if user:
                                helper_list.append(user.display_name)
                                continue
                        except:
                            pass
                        
                        # 4. 모든 방법이 실패한 경우
                        helper_list.append(f"User#{user_id}")
                        
                    except Exception as e:
                        logger.warning(f"헬퍼 사용자 정보 가져오기 실패 (ID: {user_id}): {e}")
                        helper_list.append(f"User#{user_id}")
                
                helper_text = "\n".join([f"• {name}" for name in helper_list[:10]])  # 최대 10명만 표시
                if len(helper_list) > 10:
                    helper_text += f"\n... 외 {len(helper_list) - 10}명"
                
                embed.add_field(
                    name=f"🤝 헬퍼 ({len(helper_participants)}명)",
                    value=helper_text,
                    inline=True
                )
            else:
                embed.add_field(
                    name="🤝 헬퍼 (0명)",
                    value="대기자 없음",
                    inline=True
                )
            
            embed.set_footer(text=f"활성 레이드: {active_raids}개 | 헬퍼: {len(helper_participants)}명 | 서버: {interaction.guild.name if interaction.guild else 'DM'}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"레이드 대기방 조회 중 오류: {e}")
            await interaction.response.send_message(f"❌ 레이드 대기방 조회 중 오류 발생: {e}", ephemeral=True)


# 사용하지 않는 세이브코드 생성 관련 클래스들 (주석 처리)
# class SaveCodeCreationModal(ui.Modal, title='🎒 아이템 기반 세이브코드 생성'):
#     """아이템 기반 세이브코드 생성 모달"""
#     
#     def __init__(self, encoder, player_name):
#         super().__init__()
#         self.encoder = encoder
#         self.player_name = player_name
#     
#     item1 = ui.TextInput(
#         label='1번째 아이템',
#         placeholder='예: 예언의 손길',
#         style=discord.TextStyle.short,
#         max_length=50,
#         required=False
#     )
#     
#     item2 = ui.TextInput(
#         label='2번째 아이템',
#         placeholder='예: 사무엘의 영혼',
#         style=discord.TextStyle.short,
#         max_length=50,
#         required=False
#     )
#     
#     item3 = ui.TextInput(
#         label='3번째 아이템',
#         placeholder='예: 패닉소울',
#         style=discord.TextStyle.short,
#         max_length=50,
#         required=False
#     )
#     
#     item4 = ui.TextInput(
#         label='4번째 아이템',
#         placeholder='예: 풍마반지',
#         style=discord.TextStyle.short,
#         max_length=50,
#         required=False
#     )
#     
#     item5 = ui.TextInput(
#         label='5번째 아이템',
#         placeholder='예: 청혈주',
#         style=discord.TextStyle.short,
#         max_length=50,
#         required=False
#     )
#     
#     async def on_submit(self, interaction: discord.Interaction):
#         try:
#             items = {}
#             item_inputs = [self.item1, self.item2, self.item3, self.item4, self.item5]
#             
#             for i, item_input in enumerate(item_inputs, 1):
#                 if item_input.value.strip():
#                     items[i] = item_input.value.strip()
#             
#             if not items:
#                 await interaction.response.send_message("❌ 최소 1개의 아이템은 입력해야 합니다.", ephemeral=True)
#                 return
#             
#             # 세이브코드 생성
#             try:
#                 savecode = create_custom_savecode(self.player_name, items)
#                 
#                 embed = discord.Embed(
#                     title="✅ 세이브코드 생성 완료",
#                     description=f"**플레이어**: {self.player_name}",
#                     color=0x00ff00
#                 )
#                 
#                 embed.add_field(
#                     name="🔮 생성된 세이브코드",
#                     value=f"```{savecode}```",
#                     inline=False
#                 )
#                 
#                 item_list = []
#                 for slot, item_name in items.items():
#                     item_list.append(f"{slot}번째: {item_name}")
#                 
#                 embed.add_field(
#                     name="🎒 설정된 아이템",
#                     value="\n".join(item_list),
#                     inline=False
#                 )
#                 
#                 embed.set_footer(text="생성된 세이브코드는 자동으로 검증되었습니다.")
#                 
#                 await interaction.response.send_message(embed=embed, ephemeral=True)
#                 
#             except Exception as e:
#                 await interaction.response.send_message(f"❌ 세이브코드 생성 중 오류: {e}", ephemeral=True)
#                 
#         except Exception as e:
#             logger.error(f"아이템 기반 세이브코드 생성 중 오류: {e}")
#             await interaction.response.send_message(f"❌ 처리 중 오류 발생: {e}", ephemeral=True)


# class CustomSaveCodeModal(ui.Modal, title='📊 커스텀 세이브코드 생성'):
#     """커스텀 세이브코드 생성 모달"""
#     
#     def __init__(self, encoder, player_name):
#         super().__init__()
#         self.encoder = encoder
#         self.player_name = player_name
#     
#     values_input = ui.TextInput(
#         label='데이터 값들 (인덱스:값 형식)',
#         placeholder='예: 0:123456 1:999 2:456789',
#         style=discord.TextStyle.paragraph,
#         max_length=1000,
#         required=True
#     )
#     
#     async def on_submit(self, interaction: discord.Interaction):
#         try:
#             # 입력 파싱
#             values_text = self.values_input.value.strip()
#             other_values = {}
#             
#             for pair in values_text.split():
#                 try:
#                     index_str, value_str = pair.split(':')
#                     index = int(index_str)
#                     value = int(value_str)
#                     other_values[index] = value
#                 except ValueError:
#                     await interaction.response.send_message(f"❌ 잘못된 형식: {pair}. '인덱스:값' 형식으로 입력해주세요.", ephemeral=True)
#                     return
#             
#             if not other_values:
#                 await interaction.response.send_message("❌ 최소 1개의 값은 입력해야 합니다.", ephemeral=True)
#                 return
#             
#             # 세이브코드 생성
#             try:
#                 savecode = create_custom_savecode(self.player_name, None, other_values)
#                 
#                 embed = discord.Embed(
#                     title="✅ 커스텀 세이브코드 생성 완료",
#                     description=f"**플레이어**: {self.player_name}",
#                     color=0x00ff00
#                 )
#                 
#                 embed.add_field(
#                     name="🔮 생성된 세이브코드",
#                     value=f"```{savecode}```",
#                     inline=False
#                 )
#                 
#                 values_list = []
#                 for index, value in other_values.items():
#                     values_list.append(f"슬롯 {index}: {value}")
#                 
#                 embed.add_field(
#                     name="📊 설정된 값들",
#                     value="\n".join(values_list),
#                     inline=False
#                 )
#                 
#                 embed.set_footer(text="생성된 세이브코드는 자동으로 검증되었습니다.")
#                 
#                 await interaction.response.send_message(embed=embed, ephemeral=True)
#                 
#             except Exception as e:
#                 await interaction.response.send_message(f"❌ 세이브코드 생성 중 오류: {e}", ephemeral=True)
#                 
#         except Exception as e:
#             logger.error(f"커스텀 세이브코드 생성 중 오류: {e}")
#             await interaction.response.send_message(f"❌ 처리 중 오류 발생: {e}", ephemeral=True)


# class SaveCodeCreationView(ui.View):
#     """세이브코드 생성 View"""
#     
#     def __init__(self, encoder):
#         super().__init__(timeout=300)
#         self.encoder = encoder
#         self.player_name = None
#     
#     @ui.button(label="🎒 아이템 기반 생성", style=discord.ButtonStyle.primary, emoji="🎒")
#     async def item_based_creation(self, interaction: discord.Interaction, button: ui.Button):
#         """아이템 기반 세이브코드 생성"""
#         # 상호작용에서 플레이어 이름 추출
#         embed_desc = interaction.message.embeds[0].description
#         player_name = embed_desc.split("**플레이어**: ")[1].split("\n")[0]
#         
#         modal = SaveCodeCreationModal(self.encoder, player_name)
#         await interaction.response.send_modal(modal)
#     
#     @ui.button(label="📊 커스텀 생성", style=discord.ButtonStyle.secondary, emoji="📊")
#     async def custom_creation(self, interaction: discord.Interaction, button: ui.Button):
#         """커스텀 세이브코드 생성"""
#         # 상호작용에서 플레이어 이름 추출
#         embed_desc = interaction.message.embeds[0].description
#         player_name = embed_desc.split("**플레이어**: ")[1].split("\n")[0]
#         
#         modal = CustomSaveCodeModal(self.encoder, player_name)
#         await interaction.response.send_modal(modal)


class SaveCodeBot:
    """아이템 기반 세이브코드 생성 모달"""
    
    def __init__(self, encoder, player_name):
        super().__init__()
        self.encoder = encoder
        self.player_name = player_name
    
    item1 = ui.TextInput(
        label='1번째 아이템',
        placeholder='예: 예언의 손길',
        style=discord.TextStyle.short,
        max_length=50,
        required=False
    )
    
    item2 = ui.TextInput(
        label='2번째 아이템',
        placeholder='예: 사무엘의 영혼',
        style=discord.TextStyle.short,
        max_length=50,
        required=False
    )
    
    item3 = ui.TextInput(
        label='3번째 아이템',
        placeholder='예: 패닉소울',
        style=discord.TextStyle.short,
        max_length=50,
        required=False
    )
    
    item4 = ui.TextInput(
        label='4번째 아이템',
        placeholder='예: 풍마반지',
        style=discord.TextStyle.short,
        max_length=50,
        required=False
    )
    
    item5 = ui.TextInput(
        label='5번째 아이템',
        placeholder='예: 청혈주',
        style=discord.TextStyle.short,
        max_length=50,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            items = {}
            item_inputs = [self.item1, self.item2, self.item3, self.item4, self.item5]
            
            for i, item_input in enumerate(item_inputs, 1):
                if item_input.value.strip():
                    items[i] = item_input.value.strip()
            
            if not items:
                await interaction.response.send_message("❌ 최소 1개의 아이템은 입력해야 합니다.", ephemeral=True)
                return
            
            # 세이브코드 생성
            try:
                savecode = create_custom_savecode(self.player_name, items)
                
                embed = discord.Embed(
                    title="✅ 세이브코드 생성 완료",
                    description=f"**플레이어**: {self.player_name}",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="🔮 생성된 세이브코드",
                    value=f"```{savecode}```",
                    inline=False
                )
                
                item_list = []
                for slot, item_name in items.items():
                    item_list.append(f"{slot}번째: {item_name}")
                
                embed.add_field(
                    name="🎒 설정된 아이템",
                    value="\n".join(item_list),
                    inline=False
                )
                
                embed.set_footer(text="생성된 세이브코드는 자동으로 검증되었습니다.")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ 세이브코드 생성 중 오류: {e}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"아이템 기반 세이브코드 생성 중 오류: {e}")
            await interaction.response.send_message(f"❌ 처리 중 오류 발생: {e}", ephemeral=True)


class CustomSaveCodeModal(ui.Modal, title='📊 커스텀 세이브코드 생성'):
    """커스텀 세이브코드 생성 모달"""
    
    def __init__(self, encoder, player_name):
        super().__init__()
        self.encoder = encoder
        self.player_name = player_name
    
    values_input = ui.TextInput(
        label='데이터 값들 (인덱스:값 형식)',
        placeholder='예: 0:123456 1:999 2:456789',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 입력 파싱
            values_text = self.values_input.value.strip()
            other_values = {}
            
            for pair in values_text.split():
                try:
                    index_str, value_str = pair.split(':')
                    index = int(index_str)
                    value = int(value_str)
                    other_values[index] = value
                except ValueError:
                    await interaction.response.send_message(f"❌ 잘못된 형식: {pair}. '인덱스:값' 형식으로 입력해주세요.", ephemeral=True)
                    return
            
            if not other_values:
                await interaction.response.send_message("❌ 최소 1개의 값은 입력해야 합니다.", ephemeral=True)
                return
            
            # 세이브코드 생성
            try:
                savecode = create_custom_savecode(self.player_name, None, other_values)
                
                embed = discord.Embed(
                    title="✅ 커스텀 세이브코드 생성 완료",
                    description=f"**플레이어**: {self.player_name}",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="🔮 생성된 세이브코드",
                    value=f"```{savecode}```",
                    inline=False
                )
                
                values_list = []
                for index, value in other_values.items():
                    values_list.append(f"슬롯 {index}: {value}")
                
                embed.add_field(
                    name="📊 설정된 값들",
                    value="\n".join(values_list),
                    inline=False
                )
                
                embed.set_footer(text="생성된 세이브코드는 자동으로 검증되었습니다.")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ 세이브코드 생성 중 오류: {e}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"커스텀 세이브코드 생성 중 오류: {e}")
            await interaction.response.send_message(f"❌ 처리 중 오류 발생: {e}", ephemeral=True)


# class SaveCodeCreationView(ui.View):
#     """세이브코드 생성 View"""
#     
#     def __init__(self, encoder):
#         super().__init__(timeout=300)
#         self.encoder = encoder
#         self.player_name = None
#     
#     @ui.button(label="🎒 아이템 기반 생성", style=discord.ButtonStyle.primary, emoji="🎒")
#     async def item_based_creation(self, interaction: discord.Interaction, button: ui.Button):
#         """아이템 기반 세이브코드 생성"""
#         # 상호작용에서 플레이어 이름 추출
#         embed_desc = interaction.message.embeds[0].description
#         player_name = embed_desc.split("**플레이어**: ")[1].split("\n")[0]
#         
#         modal = SaveCodeCreationModal(self.encoder, player_name)
#         await interaction.response.send_modal(modal)
#     
#     @ui.button(label="📊 커스텀 생성", style=discord.ButtonStyle.secondary, emoji="📊")
#     async def custom_creation(self, interaction: discord.Interaction, button: ui.Button):
#         """커스텀 세이브코드 생성"""
#         # 상호작용에서 플레이어 이름 추출
#         embed_desc = interaction.message.embeds[0].description
#         player_name = embed_desc.split("**플레이어**: ")[1].split("\n")[0]
#         
#         modal = CustomSaveCodeModal(self.encoder, player_name)
#         await interaction.response.send_modal(modal)


class SaveCodeBot:
    """디스코드 세이브코드 봇 클래스"""
    
    def __init__(self):
        self.config = Config()
        self.decoder = SaveCodeDecoder()
        self.encoder = SaveCodeEncoder()  # 세이브코드 인코더 초기화
        self.item_searcher = ItemSearcher()  # 아이템 검색기 초기화
        self.item_db = ItemDatabase()  # 아이템 데이터베이스 초기화
        self.graduation_checker = GraduationChecker()  # 졸업 조건 확인기 초기화

        self.raid_system = RaidWaitingSystem()  # 레이드 대기 시스템 초기화
        # summon_chunk_n None이면 자동 감지
        self.savecode_manager = SaveCodeManager(summon_chunk_n=getattr(self.config, "SUMMON_CHUNK_N", None))

        
        # 봇 인텐트 설정
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True  # 길드 정보 접근
        intents.members = True  # 멤버 정보 접근 (특권 인텐트)
        
        # 봇 인스턴스 생성
        self.bot = commands.Bot(command_prefix=self.config.COMMAND_PREFIX, intents=intents)
        
        # Persistent View는 on_ready에서 생성
        self.raid_control_view = None
        
        self._setup_events()
        self._setup_commands()
    
    def _check_savecode_permission(self, ctx: commands.Context) -> bool:
        """세이브코드 생성 권한 검사"""
        # 관리자 전용 모드가 활성화된 경우
        if self.config.SAVECODE_ADMIN_ONLY:
            # 서버 관리자 권한 확인
            if ctx.author.guild_permissions.administrator:
                return True
        
        # 허용된 사용자 ID 확인
        if ctx.author.id in self.config.SAVECODE_ALLOWED_USERS:
            return True
        
        # 허용된 역할 확인
        if ctx.guild and hasattr(ctx.author, 'roles'):
            user_role_names = [role.name for role in ctx.author.roles]
            for allowed_role in self.config.SAVECODE_ALLOWED_ROLES:
                if allowed_role in user_role_names:
                    return True
        
        return False
    
    def _check_modal_permission(self, interaction: discord.Interaction) -> bool:
        """모달에서 세이브코드 생성 권한 검사"""
        # 관리자 전용 모드가 활성화된 경우
        if self.config.SAVECODE_ADMIN_ONLY:
            # 서버 관리자 권한 확인
            if interaction.user.guild_permissions.administrator:
                return True
        
        # 허용된 사용자 ID 확인
        if interaction.user.id in self.config.SAVECODE_ALLOWED_USERS:
            return True
        
        # 허용된 역할 확인
        if interaction.guild and hasattr(interaction.user, 'roles'):
            user_role_names = [role.name for role in interaction.user.roles]
            for allowed_role in self.config.SAVECODE_ALLOWED_ROLES:
                if allowed_role in user_role_names:
                    return True
        
        return False
    
    def _validate_savecode_inputs(self, lumber, character_id, level, strength, agility, intelligence, items):
        """세이브코드 입력값 검증"""
        if lumber < 0:
            return "나무는 0 이상의 값이어야 합니다."
        
        if character_id < 0:
            return "캐릭터 ID는 0 이상의 값이어야 합니다."
        
        if level < 1 or level > 2000:
            return "캐릭터 레벨은 1~2000 사이의 값이어야 합니다."
        
        if strength < 0 or strength > 999999:
            return "힘 스탯은 0~999999 사이의 값이어야 합니다."
        
        if agility < 0 or agility > 999999:
            return "민첩 스탯은 0~999999 사이의 값이어야 합니다."
        
        if intelligence < 0 or intelligence > 999999:
            return "지능 스탯은 0~999999 사이의 값이어야 합니다."
        
        # 아이템 ID 검증
        for i, item_id in enumerate(items):
            if item_id < 0 or item_id > 281:
                return f"아이템{i+1} ID는 0~281 사이의 값이어야 합니다. (입력값: {item_id})"
        
        return None
    
    async def _create_savecode_internal(self, player_name, character_id, lumber, level, strength, agility, intelligence, item1, item2, item3, item4, item5, item6):
        """내부 세이브코드 생성 메서드"""
        try:
            # 캐릭터 이름 조회
            import json
            try:
                with open('CharList_by_id.json', 'r', encoding='utf-8') as f:
                    char_list = json.load(f)
                character_name = char_list.get(str(character_id), f"Unknown Character({character_id})")
            except:
                character_name = f"Character ID {character_id}"
            
            # 기본 로드 데이터 생성 (원본 게임과 동일한 16개 배열)
            load_data = [0] * len(self.config.UDG_SAVE_VALUE_LENGTH)
            
            # 게임 데이터 구조에 맞게 설정 (원본 게임과 동일)
            # 인덱스 0은 사용하지 않고, 1~15 사용
            scale_factor = 100
            
            load_data[1] = 0                           # 골드 (기본값 0) - load[1]
            load_data[15] = lumber // scale_factor     # 나무 (100으로 나누어 저장) - load[15]
            load_data[14] = character_id               # 캐릭터 타입 ID - load[14]
            load_data[13] = level                      # 레벨 - load[13]
            load_data[11] = 0                          # 경험치 (기본값 0) - load[11]
            
            # 스탯 설정 (추정되는 인덱스, 실제 게임 구조에 맞게 조정 필요)
            load_data[3] = strength                    # 힘 스탯 - load[3]
            load_data[5] = agility                     # 민첩 스탯 - load[5] 
            load_data[7] = intelligence                # 지능 스탯 - load[7]
            
            # 아이템 슬롯들에 아이템 ID 설정: load_data[2], [4], [6], [8], [10], [12] (원본 게임과 동일)
            items = [item1, item2, item3, item4, item5, item6]
            item_slots = [2, 4, 6, 8, 10, 12]  # 아이템 슬롯 인덱스
            
            for i, item_id in enumerate(items):
                if i < len(item_slots) and item_id > 0:  # 0보다 큰 아이템 ID만 설정
                    load_data[item_slots[i]] = item_id
            
            # 세이브코드 생성
            savecode = self.encoder.encode_savecode(load_data, player_name, summon_chunk_n=0)
            # 하이픈 포맷(5글자 단위)으로 표시용 변환
            display_code = "-".join([savecode[i:i+5] for i in range(0, len(savecode), 5)])
            
            # 검증 (하이픈 유무 무관)
            is_valid = self.decoder.validate_savecode(savecode, player_name)
            
            embed = discord.Embed(
                title="✅ 세이브코드 생성 완료" if is_valid else "⚠️ 세이브코드 생성됨 (검증 실패)",
                description=f"**플레이어**: {player_name}\n**캐릭터**: {character_name} (ID: {character_id})",
                color=0x00ff00 if is_valid else 0xffaa00
            )
            
            embed.add_field(
                name="🔮 생성된 세이브코드",
                value=f"```{display_code}```",
                inline=False
            )
            
            # 입력된 아이템들의 이름 가져오기
            item_names = []
            for item_id in items:
                if item_id > 0:
                    item_name = self.item_db.get_item_name(item_id)
                    item_names.append(f"{item_id}: {item_name}")
            
            embed.add_field(
                name="📊 설정된 값들",
                value=f"🌳 나무: {lumber:,}\n💰 골드: 0 (기본값)\n👤 캐릭터: {character_name}\n📈 레벨: {level}",
                inline=False
            )
            
            embed.add_field(
                name="💪 스탯 정보",
                value=f"💪 힘: {strength}\n🏃 민첩: {agility}\n🧠 지능: {intelligence}",
                inline=True
            )
            
            # 아이템이 있는 경우 아이템 정보 추가
            if item_names:
                embed.add_field(
                    name="🎒 설정된 아이템들",
                    value="\n".join(item_names) if item_names else "아이템 없음",
                    inline=False
                )
            
            embed.add_field(
                name="✅ 검증 결과",
                value="세이브코드가 유효합니다." if is_valid else "⚠️ 검증에 실패했지만 코드는 생성되었습니다.",
                inline=False
            )
            
            embed.set_footer(text=f"캐릭터 ID: {character_id} | UI를 통해 생성됨")
            
            return embed
            
        except Exception as e:
            logger.error(f"세이브코드 생성 중 오류: {e}")
            embed = discord.Embed(
                title="❌ 세이브코드 생성 실패",
                description=f"세이브코드 생성 중 오류가 발생했습니다: {e}",
                color=0xff0000
            )
            return embed
    
    def _setup_events(self):
        """이벤트 핸들러 설정"""
        @self.bot.event
        async def on_ready():
            logger.info(f'봇 준비 완료: {self.bot.user}')
            print(f'봇 준비 완료: {self.bot.user}')
            
            # Persistent View 생성 및 등록 (봇이 준비된 후)
            try:
                self.raid_control_view = RaidControlView(self.raid_system)
                self.bot.add_view(self.raid_control_view)
                logger.info("Persistent View 생성 및 등록 완료")
                print("Persistent View 생성 및 등록 완료")
            except Exception as e:
                logger.error(f"Persistent View 생성/등록 실패: {e}")
                print(f"Persistent View 생성/등록 실패: {e}")
            
            print("레이드 버튼 메시지를 보내려면 관리자가 '/레이드메시지' 명령어를 사용하세요.")
        
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
                is_valid_legacy = decode_savecode2(code, name, summon_chunk_n=self.config.SUMMON_CHUNK_N)
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
                apocalypse_characters = set()  # 묵시록 레이드 졸업 캐릭터 (죄: 아이템 보유)
                uriel_characters = set()  # 우리엘 졸업 캐릭터
                raphael_characters = set()  # 라파엘 졸업 캐릭터
                gabriel_characters = set()  # 가브리엘 졸업 캐릭터
                
                for code in codes:
                    print(f"[DEBUG] 로드된 코드들: {code}")  # 디버그용 출력
                    try:
                        # 검증
                        is_valid = decode_savecode2(code, name, summon_chunk_n=self.config.SUMMON_CHUNK_N)
                        result = "✅ 유효함" if is_valid else "❌ 유효하지 않음"
                        
                        # 통계 업데이트
                        if is_valid:
                            valid_count += 1
                        else:
                            invalid_count += 1
                        
                        # 세이브 데이터 추출
                        save_data = extract_save_data(code, name, summon_chunk_n=self.config.SUMMON_CHUNK_N)
                        
                        # 디버깅을 위한 타입 확인
                        print(f"[DEBUG] save_data type: {type(save_data)}")
                        print(f"[DEBUG] save_data content: {save_data}")
                        
                        # 영웅 타입 이름 매핑 (SaveCodeManager 사용)
                        if isinstance(save_data, dict) and 'hero_type_index' in save_data:
                            hero_type_index = save_data['hero_type_index']
                            hero_name = self.savecode_manager.get_character_name(hero_type_index)
                        else:
                            print(f"[ERROR] save_data is not a valid dict: {save_data}")
                            hero_name = "Unknown Character"
                            # 기본값 설정
                            save_data = {
                                'gold': 0,
                                'lumber': 0,
                                'hero_type_index': 0,
                                'level': 1
                            }
                        
                        # 캐릭터 세트에 추가 (중복 제거)
                        characters.add(hero_name)
                        
                        # 캐릭터별 출현 횟수 카운트
                        character_counts[hero_name] = character_counts.get(hero_name, 0) + 1
                        
                        # 아이템 추출
                        items_list = self.decoder.extract_items(code)
                        item_ids = save_data.get('items', []) if isinstance(save_data, dict) else []
                        response = "\n".join(items_list)
                        
                        # 졸업 상태 확인 (레이드 아이템 JSON 기반)
                        graduation_status = self.graduation_checker.get_graduation_status(
                            items_list=items_list,
                            item_ids=item_ids
                        )
                        
                        # 졸업 상태에 따라 캐릭터를 해당 카테고리에 추가
                        if graduation_status == 'raphael':
                            raphael_characters.add(hero_name)
                        elif graduation_status == 'gabriel':
                            gabriel_characters.add(hero_name)
                        elif graduation_status == 'uriel':
                            uriel_characters.add(hero_name)
                        elif graduation_status == 'apocalypse':
                            apocalypse_characters.add(hero_name)
                        
                        # 결과 전송 - Embed 사용
                        embed = discord.Embed(
                            title="🎮 세이브코드 분석 결과",
                            color=0x00ff00 if is_valid else 0xff0000
                        )
                        embed.add_field(name="검증 상태", value=result, inline=True)
                        embed.add_field(name="플레이어", value=name, inline=True)
                        embed.add_field(name="영웅", value=hero_name, inline=True)
                        embed.add_field(name="💰 골드", value=f"{save_data.get('gold', 0):,}", inline=True)
                        embed.add_field(name="🌲 나무", value=f"{save_data.get('lumber', 0):,}", inline=True)
                        embed.add_field(name="📈 레벨", value=save_data.get('level', 1), inline=True)
                        
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
                        
                    except Exception as e:
                        print(f"[ERROR] 개별 코드 처리 중 오류: {e}")
                        logger.error(f"개별 코드 '{code}' 처리 중 오류: {e}")
                        
                        # 오류 발생한 코드에 대한 에러 메시지 전송
                        error_embed = discord.Embed(
                            title="❌ 코드 처리 오류",
                            description=f"코드 '{code[:20]}...' 처리 중 오류가 발생했습니다.",
                            color=0xff0000
                        )
                        error_embed.add_field(name="오류 내용", value=str(e), inline=False)
                        await ctx.send(embed=error_embed)
                        continue
                
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
                    stats_embed.add_field(
                        name="😈 묵시록 레이드 졸업", 
                        value=f"{len(apocalypse_characters)}건", 
                        inline=True
                    )
                    stats_embed.add_field(
                        name="👼 우리엘 졸업", 
                        value=f"{len(uriel_characters)}건", 
                        inline=True
                    )
                    stats_embed.add_field(
                        name="🕊️ 라파엘 졸업", 
                        value=f"{len(raphael_characters)}건", 
                        inline=True
                    )
                    stats_embed.add_field(
                        name="⚔️ 가브리엘 졸업", 
                        value=f"{len(gabriel_characters)}건", 
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
                    
                    # 묵시록 레이드 졸업 캐릭터 목록 추가
                    if apocalypse_characters:
                        apocalypse_list = ", ".join(sorted(apocalypse_characters))
                        if len(apocalypse_list) > 1024:  # Discord 필드 제한
                            apocalypse_list = apocalypse_list[:1021] + "..."
                        
                        stats_embed.add_field(
                            name="😈 묵시록 레이드 졸업 캐릭터",
                            value=apocalypse_list,
                            inline=False
                        )
                    else:
                        stats_embed.add_field(
                            name="😈 묵시록 레이드 졸업 캐릭터",
                            value="묵시록 레이드 아이템(죄:)을 보유한 캐릭터가 없습니다",
                            inline=False
                        )
                    
                    # 우리엘 졸업 캐릭터 목록 추가
                    if uriel_characters:
                        uriel_list = ", ".join(sorted(uriel_characters))
                        if len(uriel_list) > 1024:  # Discord 필드 제한
                            uriel_list = uriel_list[:1021] + "..."
                        
                        stats_embed.add_field(
                            name="👼 우리엘 졸업 캐릭터",
                            value=uriel_list,
                            inline=False
                        )
                    else:
                        stats_embed.add_field(
                            name="👼 우리엘 졸업 캐릭터",
                            value="우리엘 졸업 아이템 쌍을 보유한 캐릭터가 없습니다",
                            inline=False
                        )
                    
                    # 라파엘 졸업 캐릭터 목록 추가
                    if raphael_characters:
                        raphael_list = ", ".join(sorted(raphael_characters))
                        if len(raphael_list) > 1024:  # Discord 필드 제한
                            raphael_list = raphael_list[:1021] + "..."
                        
                        stats_embed.add_field(
                            name="🕊️ 라파엘 졸업 캐릭터",
                            value=raphael_list,
                            inline=False
                        )
                    else:
                        stats_embed.add_field(
                            name="🕊️ 라파엘 졸업 캐릭터",
                            value="라파엘 졸업 아이템 쌍을 보유한 캐릭터가 없습니다",
                            inline=False
                        )
                    
                    # 가브리엘 졸업 캐릭터 목록 추가
                    if gabriel_characters:
                        gabriel_list = ", ".join(sorted(gabriel_characters))
                        if len(gabriel_list) > 1024:  # Discord 필드 제한
                            gabriel_list = gabriel_list[:1021] + "..."
                        
                        stats_embed.add_field(
                            name="⚔️ 가브리엘 졸업 캐릭터",
                            value=gabriel_list,
                            inline=False
                        )
                    else:
                        stats_embed.add_field(
                            name="⚔️ 가브리엘 졸업 캐릭터",
                            value="가브리엘 졸업 아이템 쌍을 보유한 캐릭터가 없습니다",
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
                name="/세이브생성 <플레이어이름> <캐릭터ID> <나무> [레벨] [힘] [민첩] [지능] [아이템1~6]",
                value="🔮 **세이브코드 생성** 🔐\n플레이어 정보로 세이브코드를 생성합니다.\n\n**사용 예시:**\n`/세이브생성 홍길동 37 50000`\n`/세이브생성 홍길동 37 50000 10 100 50 75`\n`/세이브생성 홍길동 37 50000 15 200 100 150 264 266 268`\n• 플레이어 이름: 홍길동\n• 캐릭터 ID: 37 (종말의 네피림)\n• 나무: 50,000\n• 레벨: 1~2000 (기본값: 1)\n• 힘/민첩/지능: 0~999999 (기본값: 0)\n• 아이템1~6: 아이템 ID (선택사항, 0~281)\n\n💡 캐릭터 ID를 모르면 `/캐릭터` 명령어로 검색하세요!\n💡 아이템 ID를 모르면 `/값` 명령어로 검색하세요!\n\n⚠️ **권한 필요**: 관리자 또는 허용된 사용자만 사용 가능",
                inline=False
            )
            
            embed.add_field(
                name="/캐릭터 <캐릭터이름>",
                value="🔍 **캐릭터 검색**\n캐릭터 이름으로 ID를 검색합니다. 부분 검색도 지원합니다.\n\n**사용 예시:**\n`/캐릭터 환골` → '환골탈퇴' 찾기\n`/캐릭터 네피림` → '종말의 네피림' 찾기\n`/캐릭터 데몬` → '데몬' 찾기\n\n• 정확한 이름이나 일부만 입력해도 검색 가능\n• 검색 결과에서 ID를 확인하여 `/세이브생성`에 사용",
                inline=False
            )
            
            embed.add_field(
                name="/세이브",
                value="🔮 **UI 세이브코드 생성** ⭐**추천**\n사용자 친화적인 UI를 통해 세이브코드를 생성합니다.\n\n**특징:**\n• 📋 직관적인 폼 인터페이스\n• ✨ 실시간 입력값 검증\n• 🎯 플레이어 이름, 캐릭터, 나무, 레벨, 스탯, 아이템 설정\n• 🚀 버튼 클릭만으로 간편 생성\n\n💡 `/세이브생성` 명령어보다 더 편리합니다!",
                inline=False
            )
            
            embed.add_field(
                name="/도움말",
                value="이 도움말을 표시합니다.",
                inline=False
            )
            
            embed.add_field(
                name="🎯 레이드 시스템",
                value="**완전한 레이드 관리 생태계**\n• 🎯 **레이드 대기**: 토글로 대기 등록, 파티 모집 시 자동 DM 알림\n• 📢 **파티 모집**: 방제 필수, 2~8명 모집, 실시간 참가/탈퇴\n• 🚀 **레이드 시작**: 2명 이상이면 시작 가능, 개인 DM 알림\n• 🏛️ **실시간 현황**: 대기자 및 파티 목록 조회\n• 🔧 **자동 관리**: 메시지 정리, 상태 동기화\n\n*관리자가 '/레이드메시지' 명령어로 버튼을 활성화해야 합니다.*",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ 관리자 명령어",
                value="/레이드채널 [채널ID] - 레이드 버튼을 보낼 채널 설정\n/레이드메시지 - 현재 채널에 레이드 버튼 메시지 보내기 ⭐**필수**\n/세이브권한 - 세이브코드 생성 권한 관리 🔐",
                inline=False
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='레이드채널', help='레이드 버튼 메시지를 보낼 채널을 설정합니다 (관리자 전용)')
        @commands.has_permissions(administrator=True)
        async def set_raid_channel(ctx: commands.Context, channel_id: int = None):
            """레이드 채널 설정 명령어 (관리자 전용)"""
            try:
                if channel_id is None:
                    # 현재 채널 정보 표시
                    if self.config.RAID_CHANNEL_ID > 0:
                        current_channel = self.bot.get_channel(self.config.RAID_CHANNEL_ID)
                        if current_channel:
                            embed = discord.Embed(
                                title="🎯 레이드 채널 설정 현황",
                                description=f"현재 설정된 레이드 채널: {current_channel.mention} (ID: {self.config.RAID_CHANNEL_ID})",
                                color=0x00ff00
                            )
                        else:
                            embed = discord.Embed(
                                title="⚠️ 레이드 채널 설정 오류",
                                description=f"설정된 채널 ID ({self.config.RAID_CHANNEL_ID})를 찾을 수 없습니다.",
                                color=0xff9900
                            )
                    else:
                        embed = discord.Embed(
                            title="🎯 레이드 채널 설정 현황",
                            description="레이드 채널이 설정되지 않았습니다. 자동 검색 모드로 동작 중입니다.",
                            color=0x0099ff
                        )
                    
                    embed.add_field(
                        name="사용법",
                        value="`/레이드채널 <채널ID>` - 특정 채널을 설정\n`/레이드채널 0` - 자동 검색 모드로 변경",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    return
                
                # 채널 ID 업데이트
                if channel_id == 0:
                    # 자동 검색 모드로 설정
                    self.config.RAID_CHANNEL_ID = 0
                    embed = discord.Embed(
                        title="✅ 레이드 채널 설정 완료",
                        description="레이드 채널이 자동 검색 모드로 설정되었습니다.",
                        color=0x00ff00
                    )
                else:
                    # 특정 채널로 설정
                    target_channel = self.bot.get_channel(channel_id)
                    if not target_channel:
                        embed = discord.Embed(
                            title="❌ 레이드 채널 설정 실패",
                            description=f"채널 ID {channel_id}를 찾을 수 없습니다.",
                            color=0xff0000
                        )
                        await ctx.send(embed=embed)
                        return
                    
                    if not target_channel.permissions_for(ctx.guild.me).send_messages:
                        embed = discord.Embed(
                            title="❌ 레이드 채널 설정 실패",
                            description=f"{target_channel.mention} 채널에 메시지를 보낼 권한이 없습니다.",
                            color=0xff0000
                        )
                        await ctx.send(embed=embed)
                        return
                    
                    self.config.RAID_CHANNEL_ID = channel_id
                    embed = discord.Embed(
                        title="✅ 레이드 채널 설정 완료",
                        description=f"레이드 채널이 {target_channel.mention}으로 설정되었습니다.",
                        color=0x00ff00
                    )
                
                await ctx.send(embed=embed)
                
            except commands.MissingPermissions:
                embed = discord.Embed(
                    title="❌ 권한 부족",
                    description="이 명령어는 관리자만 사용할 수 있습니다.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
            except Exception as e:
                logger.error(f"레이드 채널 설정 중 오류: {e}")
                await ctx.send(f"❌ 레이드 채널 설정 중 오류 발생: {e}")
        
        @self.bot.command(name='레이드메시지', help='레이드 버튼 메시지를 현재 채널에 수동으로 보냅니다 (관리자 전용)')
        @commands.has_permissions(administrator=True)
        async def send_raid_message(ctx: commands.Context):
            """레이드 버튼 메시지를 수동으로 보내는 명령어 (관리자 전용)"""
            try:
                # View가 아직 생성되지 않았으면 생성
                if self.raid_control_view is None:
                    self.raid_control_view = RaidControlView(self.raid_system)
                    self.bot.add_view(self.raid_control_view)
                
                embed = discord.Embed(
                    title="🎯 레이드 시스템",
                    description="완전한 레이드 관리 시스템! 대기 등록부터 파티 모집, 레이드 시작까지 모든 기능을 제공합니다.",
                    color=0x3498db
                )
                embed.add_field(
                    name="🎯 레이드 대기 등록",
                    value="• 원하는 레이드에 대기 등록/해제\n• 대기 중일 때 해당 레이드 파티 모집 시 개인 DM 알림\n• 파티 참가 시 대기 목록에서 자동 제거",
                    inline=False
                )
                embed.add_field(
                    name="🏛️ 대기방 현황",
                    value="• 각 레이드별 현재 대기자 목록 실시간 확인\n• 헬퍼/딜러별 대기 인원 구분 표시\n• 대기자 수 및 상세 정보 제공",
                    inline=False
                )
                embed.add_field(
                    name="📢 파티 모집 시스템",
                    value="• **방제 필수 입력**으로 파티 컨셉 명확화\n• 2~8명 인원 모집 가능\n• 예정 시간 및 상세 설명 추가 가능\n• 파티 참가/탈퇴 원클릭 지원",
                    inline=False
                )
                embed.add_field(
                    name="🚀 레이드 시작 & 관리",
                    value="• **2명 이상이면 언제든 레이드 시작 가능**\n• 레이드 시작 시 모든 파티원에게 **개인 DM 알림**\n• DM에 방제, 파티원 정보 포함\n• 파티 모집 종료 및 관리 기능",
                    inline=False
                )
                embed.add_field(
                    name="🔧 자동 관리 기능",
                    value="• 완료된 메시지 자동 삭제로 채널 정리\n• 파티 참가 시 대기 목록 자동 업데이트\n• 실시간 파티 상태 동기화",
                    inline=False
                )
                embed.add_field(
                    name="💡 사용법",
                    value="🎯 **레이드 대기**: 버튼으로 대기 등록/해제\n📢 **파티 모집**: 버튼으로 모집 생성/참가\n🏛️ **현황 확인**: 대기자 및 파티 목록 조회",
                    inline=False
                )
                embed.set_footer(text="모든 기능은 버튼 클릭만으로 간편하게 이용 가능합니다!")
                
                await ctx.send(embed=embed, view=self.raid_control_view)
                logger.info(f"레이드 메시지를 {ctx.guild.name}의 #{ctx.channel.name}에 수동으로 전송했습니다.")
                
            except commands.MissingPermissions:
                embed = discord.Embed(
                    title="❌ 권한 부족",
                    description="이 명령어는 관리자만 사용할 수 있습니다.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
            except Exception as e:
                logger.error(f"레이드 메시지 전송 중 오류: {e}")
                await ctx.send(f"❌ 레이드 메시지 전송 중 오류 발생: {e}")
        
        @self.bot.command(name='세이브권한', help='세이브코드 생성 권한을 관리합니다 (관리자 전용)')
        @commands.has_permissions(administrator=True)
        async def manage_savecode_permission(ctx: commands.Context, action: str = None, *, target: str = None):
            """세이브코드 생성 권한 관리 명령어 (관리자 전용)"""
            try:
                if action is None:
                    # 현재 권한 설정 표시
                    embed = discord.Embed(
                        title="🔐 세이브코드 생성 권한 설정",
                        description="현재 세이브코드 생성 권한 설정입니다.",
                        color=0x3498db
                    )
                    
                    # 관리자 전용 모드
                    admin_status = "✅ 활성화" if self.config.SAVECODE_ADMIN_ONLY else "❌ 비활성화"
                    embed.add_field(
                        name="👑 관리자 전용 모드",
                        value=admin_status,
                        inline=False
                    )
                    
                    # 허용된 역할들
                    if self.config.SAVECODE_ALLOWED_ROLES:
                        roles_text = "\n".join([f"• {role}" for role in self.config.SAVECODE_ALLOWED_ROLES])
                        embed.add_field(
                            name="🎭 허용된 역할",
                            value=roles_text,
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🎭 허용된 역할",
                            value="없음",
                            inline=False
                        )
                    
                    # 허용된 사용자들
                    if self.config.SAVECODE_ALLOWED_USERS:
                        users_text = "\n".join([f"• <@{user_id}>" for user_id in self.config.SAVECODE_ALLOWED_USERS])
                        embed.add_field(
                            name="👤 허용된 사용자",
                            value=users_text,
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="👤 허용된 사용자",
                            value="없음",
                            inline=False
                        )
                    
                    embed.add_field(
                        name="💡 사용법",
                        value="`/세이브권한 상태` - 현재 설정 확인\n`/세이브권한 도움말` - 상세 사용법 확인",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    return
                
                if action.lower() == "도움말":
                    embed = discord.Embed(
                        title="📖 세이브코드 권한 관리 도움말",
                        description="세이브코드 생성 권한을 관리하는 방법입니다.",
                        color=0x00ff00
                    )
                    
                    embed.add_field(
                        name="⚠️ 주의사항",
                        value="현재 권한 설정은 런타임에만 적용됩니다.\n서버 재시작 시 기본 설정으로 돌아갑니다.\n영구적인 설정은 환경변수나 .env 파일을 수정하세요.",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="🔧 환경변수 설정",
                        value="`.env` 파일에 다음과 같이 설정하세요:\n```env\nSAVECODE_ADMIN_ONLY=false\nSAVECODE_ALLOWED_ROLES=모더레이터,세이브관리자\nSAVECODE_ALLOWED_USERS=123456789,987654321\n```",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    return
                
                if action.lower() == "상태":
                    # 상태 확인은 기본 동작과 동일
                    await manage_savecode_permission(ctx)
                    return
                
                await ctx.send("❌ 올바르지 않은 명령어입니다. `/세이브권한 도움말`을 참고하세요.")
                
            except commands.MissingPermissions:
                embed = discord.Embed(
                    title="❌ 권한 부족",
                    description="이 명령어는 관리자만 사용할 수 있습니다.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
            except Exception as e:
                logger.error(f"세이브코드 권한 관리 중 오류: {e}")
                await ctx.send(f"❌ 세이브코드 권한 관리 중 오류 발생: {e}")
        
        @self.bot.command(name='세이브생성', help='플레이어 정보로 세이브코드를 생성합니다. 사용법: /세이브생성 [플레이어이름] [캐릭터ID] [나무] [레벨] [힘] [민첩] [지능] [아이템1] [아이템2] [아이템3] [아이템4] [아이템5] [아이템6]')
        async def create_savecode_command(ctx: commands.Context, player_name: str, character_id: int, lumber: int, level: int = 1, strength: int = 0, agility: int = 0, intelligence: int = 0, item1: int = 0, item2: int = 0, item3: int = 0, item4: int = 0, item5: int = 0, item6: int = 0):
            """세이브코드 생성 명령어"""
            try:
                # 권한 검사
                if not self._check_savecode_permission(ctx):
                    embed = discord.Embed(
                        title="❌ 권한 없음",
                        description="세이브코드 생성 권한이 없습니다.",
                        color=0xff0000
                    )
                    
                    permission_info = []
                    if self.config.SAVECODE_ADMIN_ONLY:
                        permission_info.append("• 서버 관리자 권한")
                    if self.config.SAVECODE_ALLOWED_ROLES:
                        roles_text = ", ".join(self.config.SAVECODE_ALLOWED_ROLES)
                        permission_info.append(f"• 허용된 역할: {roles_text}")
                    if self.config.SAVECODE_ALLOWED_USERS:
                        permission_info.append("• 허용된 사용자 목록에 포함")
                    
                    if permission_info:
                        embed.add_field(
                            name="🔐 필요한 권한",
                            value="\n".join(permission_info),
                            inline=False
                        )
                    
                    embed.add_field(
                        name="💡 안내",
                        value="관리자에게 권한 요청을 해주세요.",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    return
                # 입력값 검증
                if lumber < 0:
                    await ctx.send("❌ 나무는 0 이상의 값이어야 합니다.")
                    return
                
                if character_id < 0:
                    await ctx.send("❌ 캐릭터 ID는 0 이상의 값이어야 합니다.")
                    return
                
                if level < 1 or level > 2000:
                    await ctx.send("❌ 캐릭터 레벨은 1~2000 사이의 값이어야 합니다.")
                    return
                
                if strength < 0 or strength > 999999:
                    await ctx.send("❌ 힘 스탯은 0~999999 사이의 값이어야 합니다.")
                    return
                
                if agility < 0 or agility > 999999:
                    await ctx.send("❌ 민첩 스탯은 0~999999 사이의 값이어야 합니다.")
                    return
                
                if intelligence < 0 or intelligence > 999999:
                    await ctx.send("❌ 지능 스탯은 0~999999 사이의 값이어야 합니다.")
                    return
                
                # 아이템 ID 검증 (0~281 범위)
                items = [item1, item2, item3, item4, item5, item6]
                for i, item_id in enumerate(items):
                    if item_id < 0 or item_id > 281:
                        await ctx.send(f"❌ 아이템{i+1} ID는 0~281 사이의 값이어야 합니다. (입력값: {item_id})")
                        return
                
                # 캐릭터 이름 조회
                import json
                try:
                    with open('CharList_by_id.json', 'r', encoding='utf-8') as f:
                        char_list = json.load(f)
                    character_name = char_list.get(str(character_id), f"Unknown Character({character_id})")
                except:
                    character_name = f"Character ID {character_id}"
                
                # 기본 로드 데이터 생성 (원본 게임과 동일한 16개 배열)
                load_data = [0] * len(self.config.UDG_SAVE_VALUE_LENGTH)
                
                # 게임 데이터 구조에 맞게 설정 (원본 게임과 동일)
                # 인덱스 0은 사용하지 않고, 1~15 사용
                scale_factor = 100
                
                load_data[1] = 0                           # 골드 (기본값 0) - load[1]
                load_data[15] = lumber // scale_factor     # 나무 (100으로 나누어 저장) - load[15]
                load_data[14] = character_id               # 캐릭터 타입 ID - load[14]
                load_data[13] = level                      # 레벨 - load[13]
                load_data[11] = 0                          # 경험치 (기본값 0) - load[11]
                
                # 스탯 설정 (추정되는 인덱스, 실제 게임 구조에 맞게 조정 필요)
                load_data[3] = strength                    # 힘 스탯 - load[3]
                load_data[5] = agility                     # 민첩 스탯 - load[5] 
                load_data[7] = intelligence                # 지능 스탯 - load[7]
                
                # 아이템 슬롯들에 아이템 ID 설정: load_data[2], [4], [6], [8], [10], [12] (원본 게임과 동일)
                items = [item1, item2, item3, item4, item5, item6]
                item_slots = [2, 4, 6, 8, 10, 12]  # 아이템 슬롯 인덱스
                
                for i, item_id in enumerate(items):
                    if i < len(item_slots) and item_id > 0:  # 0보다 큰 아이템 ID만 설정
                        load_data[item_slots[i]] = item_id
                
                # 세이브코드 생성
                savecode = self.encoder.encode_savecode(load_data, player_name, summon_chunk_n=0)
                display_code = "-".join([savecode[i:i+5] for i in range(0, len(savecode), 5)])
                
                # 검증 (하이픈 유무 무관)
                is_valid = self.decoder.validate_savecode(savecode, player_name)
                
                embed = discord.Embed(
                    title="✅ 세이브코드 생성 완료" if is_valid else "⚠️ 세이브코드 생성됨 (검증 실패)",
                    description=f"**플레이어**: {player_name}\n**캐릭터**: {character_name} (ID: {character_id})",
                    color=0x00ff00 if is_valid else 0xffaa00
                )
                
                embed.add_field(
                    name="🔮 생성된 세이브코드",
                    value=f"```{display_code}```",
                    inline=False
                )
                
                # 입력된 아이템들의 이름 가져오기
                item_names = []
                for item_id in items:
                    if item_id > 0:
                        item_name = self.item_db.get_item_name(item_id)
                        item_names.append(f"{item_id}: {item_name}")
                
                embed.add_field(
                    name="📊 설정된 값들",
                    value=f"🌳 나무: {lumber:,}\n💰 골드: 0 (기본값)\n👤 캐릭터: {character_name}\n📈 레벨: {level}",
                    inline=False
                )
                
                embed.add_field(
                    name="💪 스탯 정보",
                    value=f"💪 힘: {strength}\n🏃 민첩: {agility}\n🧠 지능: {intelligence}",
                    inline=True
                )
                
                # 아이템이 있는 경우 아이템 정보 추가
                if item_names:
                    embed.add_field(
                        name="🎒 설정된 아이템들",
                        value="\n".join(item_names) if item_names else "아이템 없음",
                        inline=False
                    )
                
                embed.add_field(
                    name="✅ 검증 결과",
                    value="세이브코드가 유효합니다." if is_valid else "⚠️ 검증에 실패했지만 코드는 생성되었습니다.",
                    inline=False
                )
                
                embed.set_footer(text=f"캐릭터 ID: {character_id} | 생성 시간: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                await ctx.send(embed=embed)
                
            except ValueError as e:
                await ctx.send(f"❌ 잘못된 입력값입니다. 캐릭터 ID와 나무는 숫자여야 합니다.\n오류: {e}")
            except Exception as e:
                logger.error(f"세이브코드 생성 중 오류: {e}")
                await ctx.send(f"❌ 세이브코드 생성 중 오류 발생: {e}")
        
        @self.bot.command(name='캐릭터', help='캐릭터 이름으로 ID를 검색합니다. 부분 검색도 지원합니다. 사용법: /캐릭터 [캐릭터이름]')
        async def character_search_command(ctx: commands.Context, *, character_name: str):
            """캐릭터 검색 명령어"""
            try:
                from character_searcher import CharacterSearcher

                # CharacterSearcher 인스턴스 생성
                searcher = CharacterSearcher()
                
                # 캐릭터 검색 실행
                results = searcher.search_character(character_name)
                
                if results['success']:
                    characters = results['results']
                    
                    if len(characters) == 1:
                        # 정확히 하나의 결과
                        char_id, char_name = characters[0]
                        embed = discord.Embed(
                            title="🔍 캐릭터 검색 결과",
                            description=f"'{character_name}'에 대한 검색 결과입니다.",
                            color=0x00ff00
                        )
                        
                        embed.add_field(
                            name="✅ 찾은 캐릭터",
                            value=f"```yaml\n캐릭터: {char_name}\nID: {char_id}\n```",
                            inline=False
                        )
                        
                        embed.add_field(
                            name="💡 사용법",
                            value=f"`/세이브생성 플레이어이름 {char_id} 나무수치 [레벨] [힘] [민첩] [지능] [아이템1~6]`로 세이브코드를 생성할 수 있습니다.",
                            inline=False
                        )
                        
                    elif len(characters) <= 10:
                        # 여러 결과이지만 10개 이하
                        embed = discord.Embed(
                            title="🔍 캐릭터 검색 결과",
                            description=f"'{character_name}'에 대한 검색 결과입니다. ({len(characters)}개 발견)",
                            color=0x3498db
                        )
                        
                        result_text = ""
                        for i, (char_id, char_name) in enumerate(characters, 1):
                            result_text += f"**{i}.** `{char_name}` **[ID: {char_id}]**\n"
                        
                        embed.add_field(
                            name="📋 검색 결과",
                            value=result_text,
                            inline=False
                        )
                        
                        embed.add_field(
                            name="💡 사용법",
                            value="원하는 캐릭터의 ID를 사용하여 `/세이브생성 플레이어이름 [ID] 나무수치 [레벨] [힘] [민첩] [지능] [아이템1~6]`로 세이브코드를 생성하세요.",
                            inline=False
                        )
                        
                    else:
                        # 결과가 너무 많음 (10개 초과)
                        embed = discord.Embed(
                            title="🔍 캐릭터 검색 결과",
                            description=f"'{character_name}'에 대한 검색 결과가 너무 많습니다. ({len(characters)}개 발견)",
                            color=0xff9900
                        )
                        
                        # 처음 10개만 표시
                        result_text = ""
                        for i, (char_id, char_name) in enumerate(characters[:10], 1):
                            result_text += f"**{i}.** `{char_name}` **[ID: {char_id}]**\n"
                        
                        embed.add_field(
                            name="📋 검색 결과 (처음 10개)",
                            value=result_text,
                            inline=False
                        )
                        
                        embed.add_field(
                            name="⚠️ 알림",
                            value=f"총 {len(characters)}개의 결과가 있습니다. 더 구체적인 이름으로 검색해보세요.",
                            inline=False
                        )
                        
                        embed.add_field(
                            name="💡 사용법",
                            value="원하는 캐릭터의 ID를 사용하여 `/세이브생성 플레이어이름 [ID] 나무수치 [레벨] [힘] [민첩] [지능] [아이템1~6]`로 세이브코드를 생성하세요.",
                            inline=False
                        )
                    
                    embed.set_footer(text=f"검색어: '{character_name}' | 요청자: {ctx.author.display_name}")
                    await ctx.send(embed=embed)
                    
                else:
                    # 검색 결과 없음
                    embed = discord.Embed(
                        title="❌ 검색 결과 없음",
                        description=f"'{character_name}'과 일치하는 캐릭터를 찾을 수 없습니다.",
                        color=0xff0000
                    )
                    
                    embed.add_field(
                        name="💡 검색 팁",
                        value="• 부분 검색이 가능합니다 (예: '환골' → '환골탈퇴')\n• 띄어쓰기와 특수문자를 확인해보세요\n• 캐릭터 이름의 일부만 입력해도 됩니다",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="🔍 다른 방법",
                        value="캐릭터 ID를 직접 알고 있다면 `/세이브생성` 명령어에서 바로 사용할 수 있습니다.",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"검색어: '{character_name}' | 요청자: {ctx.author.display_name}")
                    await ctx.send(embed=embed)
                    
            except ImportError:
                await ctx.send("❌ 캐릭터 검색 모듈을 찾을 수 없습니다. 개발자에게 문의해주세요.")
                logger.error("character_searcher 모듈을 import할 수 없습니다.")
            except Exception as e:
                logger.error(f"캐릭터 검색 중 오류: {e}")
                await ctx.send(f"❌ 캐릭터 검색 중 오류 발생: {e}")
        
        @self.bot.command(name='세이브', help='UI를 통해 세이브코드를 생성합니다.')
        async def save_ui_command(ctx: commands.Context):
            """UI 기반 세이브코드 생성 명령어"""
            try:
                # 권한 검사
                if not self._check_savecode_permission(ctx):
                    embed = discord.Embed(
                        title="❌ 권한 없음",
                        description="세이브코드 생성 권한이 없습니다.",
                        color=0xff0000
                    )
                    
                    permission_info = []
                    if self.config.SAVECODE_ADMIN_ONLY:
                        permission_info.append("• 서버 관리자 권한")
                    if self.config.SAVECODE_ALLOWED_ROLES:
                        roles_text = ", ".join(self.config.SAVECODE_ALLOWED_ROLES)
                        permission_info.append(f"• 허용된 역할: {roles_text}")
                    if self.config.SAVECODE_ALLOWED_USERS:
                        permission_info.append("• 허용된 사용자 목록에 포함")
                    
                    if permission_info:
                        embed.add_field(
                            name="🔐 필요한 권한",
                            value="\n".join(permission_info),
                            inline=False
                        )
                    
                    embed.add_field(
                        name="💡 안내",
                        value="관리자에게 권한 요청을 해주세요.",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    return
                
                # 안내 메시지와 함께 모달 열기 버튼 제공
                embed = discord.Embed(
                    title="🔮 세이브코드 생성 UI",
                    description="버튼을 클릭하여 세이브코드 생성 폼을 열어보세요!",
                    color=0x3498db
                )
                
                embed.add_field(
                    name="📋 입력할 정보",
                    value="• 플레이어 이름\n• 캐릭터 ID (0~100)\n• 나무 수량\n• 레벨, 힘, 민첩, 지능 (선택)\n• 아이템 ID 최대 6개 (선택)",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 팁",
                    value="• 캐릭터 ID를 모르면 `/캐릭터` 명령어로 검색\n• 아이템 ID를 모르면 `/값` 명령어로 검색\n• 선택 필드는 비워둬도 됩니다",
                    inline=False
                )
                
                view = SaveCodeUIView(self)
                await ctx.send(embed=embed, view=view)
                
            except Exception as e:
                logger.error(f"세이브 UI 명령어 처리 중 오류: {e}")
                await ctx.send(f"❌ 세이브 UI 명령어 처리 중 오류 발생: {e}")
        
        @self.bot.command(name='쿠폰', help='쿠폰을 사용하여 골드와 나무를 받습니다.')
        async def coupon_command(ctx: commands.Context):
            """쿠폰 사용 UI 명령어"""
            try:
                # 안내 메시지와 함께 모달 열기 버튼 제공
                embed = discord.Embed(
                    title="🎫 쿠폰 사용하기",
                    description="쿠폰 코드를 입력하여 골드와 나무를 받아보세요!\n버튼을 클릭하여 쿠폰 입력 폼을 열어보세요.",
                    color=0xf39c12
                )
                
                embed.add_field(
                    name="📋 입력할 정보",
                    value="• 쿠폰 코드\n• 플레이어 이름\n• 현재 세이브코드",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 안내",
                    value="• 처리 결과는 개인 DM으로 발송됩니다\n• 세이브코드는 MasinSaveV2_ 형식 또는 원본 게임 형식 모두 지원\n• 한 번 사용된 쿠폰은 다시 사용할 수 없습니다",
                    inline=False
                )
                
                embed.add_field(
                    name="🔒 개인정보 보호",
                    value="입력하신 정보는 쿠폰 처리에만 사용되며 저장되지 않습니다.",
                    inline=False
                )
                
                # 쿠폰 UI 버튼 뷰 생성
                view = CouponUIView()
                await ctx.send(embed=embed, view=view)
                
            except Exception as e:
                logger.error(f"쿠폰 UI 명령어 처리 중 오류: {e}")
                await ctx.send(f"❌ 쿠폰 UI 명령어 처리 중 오류 발생: {e}")
        
        @self.bot.command(name='쿠폰생성', help='새로운 쿠폰을 생성합니다. (관리자 전용)')
        async def coupon_create_command(ctx: commands.Context):
            """쿠폰 생성 UI 명령어 (관리자 전용)"""
            try:
                # 관리자 권한 확인
                if not ctx.author.guild_permissions.administrator:
                    embed = discord.Embed(
                        title="❌ 권한 없음",
                        description="쿠폰 생성은 서버 관리자만 사용할 수 있습니다.",
                        color=0xff0000
                    )
                    await ctx.send(embed=embed)
                    return
                
                # 안내 메시지와 함께 모달 열기 버튼 제공
                embed = discord.Embed(
                    title="🎫 쿠폰 생성하기",
                    description="새로운 쿠폰을 생성하여 사용자들에게 골드와 나무를 지급하세요!\n버튼을 클릭하여 쿠폰 생성 폼을 열어보세요.",
                    color=0xe74c3c
                )
                
                embed.add_field(
                    name="📋 입력할 정보",
                    value="• 나무 수량\n• 골드 수량",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 안내",
                    value="• 생성된 쿠폰 코드는 개인 DM으로 발송됩니다\n• 쿠폰 코드는 10자리 랜덤 문자열로 생성됩니다\n• 생성된 쿠폰은 `/쿠폰` 명령어로 사용할 수 있습니다",
                    inline=False
                )
                
                embed.add_field(
                    name="⚠️ 주의사항",
                    value="• 0 이상 99,999,999 이하의 값만 입력 가능합니다\n• 생성된 쿠폰은 한 번만 사용할 수 있습니다",
                    inline=False
                )
                
                # 쿠폰 생성 UI 버튼 뷰 생성
                view = CouponCreateUIView()
                await ctx.send(embed=embed, view=view)
                
            except Exception as e:
                logger.error(f"쿠폰 생성 UI 명령어 처리 중 오류: {e}")
                await ctx.send(f"❌ 쿠폰 생성 UI 명령어 처리 중 오류 발생: {e}")
        
        # 기존 명령어들은 주석 처리 (현재는 버튼 기반 시스템 사용)
        # @self.bot.command(name='대기', help='레이드 대기 목록에 등록합니다')
        # async def raid_wait_command(ctx: commands.Context):
        #     """레이드 대기 등록 명령어"""
        #     try:
        #         user_id = ctx.author.id
        #         
        #         # 현재 대기 중인 레이드 확인
        #         current_raids = []
        #         for raid_name, waiting_users in self.raid_system.get_all_waiting_lists().items():
        #             if user_id in waiting_users:
        #                 current_raids.append(raid_name)
        #         
        #         embed = discord.Embed(
        #             title="🎯 레이드 대기 등록",
        #             description="참여하고 싶은 레이드를 선택해주세요.\n토글 버튼으로 ON/OFF 할 수 있습니다.",
        #             color=0x3498db
        #         )
        #         
        #         if current_raids:
        #             current_list = "\n".join([f"• {raid}" for raid in current_raids])
        #             embed.add_field(
        #                 name="현재 대기 중인 레이드",
        #                 value=current_list,
        #                 inline=False
        #             )
        #         
        #         view = RaidSelectionView(self.raid_system, user_id)
        #         await ctx.send(embed=embed, view=view, ephemeral=True)
        #         
        #     except Exception as e:
        #         logger.error(f"레이드 대기 등록 중 오류: {e}")
        #         await ctx.send(f"❌ 레이드 대기 등록 중 오류 발생: {e}", ephemeral=True)
        # 
        # @self.bot.command(name='대기방', help='각 레이드별 대기자 목록을 확인합니다')
        # async def raid_room_command(ctx: commands.Context):
        #     """레이드 대기방 조회 명령어"""
        #     try:
        #         all_waiting_lists = self.raid_system.get_all_waiting_lists()
        #         
        #         embed = discord.Embed(
        #             title="🏛️ 레이드 대기방 현황",
        #             description="각 레이드별 대기자 목록입니다",
        #             color=0x9b59b6
        #         )
        #         
        #         active_raids = 0
        #         
        #         for raid_name, waiting_users in all_waiting_lists.items():
        #             if waiting_users:
        #                 active_raids += 1
        #                 
        #                 # 사용자 이름 목록 생성
        #                 user_list = []
        #                 for user_id in waiting_users:
        #                     try:
        #                         # 1. 길드 멤버로 먼저 시도 (더 정확한 정보)
        #                         member = ctx.guild.get_member(user_id) if ctx.guild else None
        #                         if member:
        #                             user_list.append(member.display_name)
        #                             continue
        #                         
        #                         # 2. 봇 캐시에서 사용자 정보 가져오기
        #                         user = self.bot.get_user(user_id)
        #                         if user:
        #                             user_list.append(user.display_name)
        #                             continue
        #                         
        #                         # 3. API를 통해 사용자 정보 가져오기 (비동기)
        #                         try:
        #                             user = await self.bot.fetch_user(user_id)
        #                             if user:
        #                                 user_list.append(user.display_name)
        #                                 continue
        #                         except:
        #                             pass
        #                         
        #                         # 4. 모든 방법이 실패한 경우
        #                         user_list.append(f"User#{user_id}")
        #                         
        #                     except Exception as e:
        #                         logger.warning(f"사용자 정보 가져오기 실패 (ID: {user_id}): {e}")
        #                         user_list.append(f"User#{user_id}")
        #                 
        #                 user_text = "\n".join([f"• {name}" for name in user_list[:10]])  # 최대 10명만 표시
        #                 if len(user_list) > 10:
        #                     user_text += f"\n... 외 {len(user_list) - 10}명"
        #                 
        #                 embed.add_field(
        #                     name=f"{raid_name} ({len(waiting_users)}명)",
        #                     value=user_text or "대기자 없음",
        #                     inline=True
        #                 )
        #             else:
        #                 embed.add_field(
        #                     name=f"{raid_name} (0명)",
        #                     value="대기자 없음",
        #                     inline=True
        #                 )
        #         
        #         embed.set_footer(text=f"활성 레이드: {active_raids}개 | 서버: {ctx.guild.name if ctx.guild else 'DM'}")
        #         await ctx.send(embed=embed, ephemeral=True)
        #         
        #     except Exception as e:
        #         logger.error(f"레이드 대기방 조회 중 오류: {e}")
        #         await ctx.send(f"❌ 레이드 대기방 조회 중 오류 발생: {e}", ephemeral=True)
    
    async def _send_raid_control_message(self):
        """레이드 컨트롤 메시지를 지정된 채널에 보내기"""
        try:
            # View가 아직 생성되지 않았으면 생성
            if self.raid_control_view is None:
                self.raid_control_view = RaidControlView(self.raid_system)
                self.bot.add_view(self.raid_control_view)
            
            # 특정 채널 ID가 설정되어 있으면 해당 채널에만 보내기
            if self.config.RAID_CHANNEL_ID > 0:
                target_channel = self.bot.get_channel(self.config.RAID_CHANNEL_ID)
                if target_channel and target_channel.permissions_for(target_channel.guild.me).send_messages:
                    embed = discord.Embed(
                        title="🎯 레이드 시스템",
                        description="아래 버튼을 사용하여 레이드 대기 등록 및 현황을 확인하세요!",
                        color=0x3498db
                    )
                    embed.add_field(
                        name="🎯 레이드 대기 등록",
                        value="참여하고 싶은 레이드에 대기 등록을 할 수 있습니다.",
                        inline=False
                    )
                    embed.add_field(
                        name="🏛️ 대기방 현황",
                        value="각 레이드별 현재 대기자 목록을 확인할 수 있습니다.",
                        inline=False
                    )
                    embed.set_footer(text="버튼을 클릭하여 기능을 이용하세요!")
                    
                    await target_channel.send(embed=embed, view=self.raid_control_view)
                    logger.info(f"레이드 컨트롤 메시지를 지정된 채널 (ID: {self.config.RAID_CHANNEL_ID})에 전송했습니다.")
                else:
                    logger.error(f"지정된 채널 (ID: {self.config.RAID_CHANNEL_ID})를 찾을 수 없거나 권한이 없습니다.")
                return
            
            # 특정 채널이 설정되지 않은 경우 기존 방식으로 자동 검색
            for guild in self.bot.guilds:
                # 일반적인 채널 이름들 검색
                target_channel = None
                channel_names = ['일반', 'general', '봇', 'bot', '레이드', 'raid']
                
                for channel_name in channel_names:
                    channel = discord.utils.get(guild.text_channels, name=channel_name)
                    if channel and channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break
                
                # 적절한 채널을 찾지 못했으면 첫 번째 가능한 채널 사용
                if not target_channel:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            target_channel = channel
                            break
                
                if target_channel:
                    embed = discord.Embed(
                        title="🎯 레이드 시스템",
                        description="아래 버튼을 사용하여 레이드 대기 등록 및 현황을 확인하세요!",
                        color=0x3498db
                    )
                    embed.add_field(
                        name="🎯 레이드 대기 등록",
                        value="참여하고 싶은 레이드에 대기 등록을 할 수 있습니다.",
                        inline=False
                    )
                    embed.add_field(
                        name="🏛️ 대기방 현황",
                        value="각 레이드별 현재 대기자 목록을 확인할 수 있습니다.",
                        inline=False
                    )
                    embed.set_footer(text="버튼을 클릭하여 기능을 이용하세요!")
                    
                    await target_channel.send(embed=embed, view=self.raid_control_view)
                    logger.info(f"레이드 컨트롤 메시지를 {guild.name}의 #{target_channel.name}에 전송했습니다.")
                else:
                    logger.warning(f"길드 {guild.name}에서 메시지를 보낼 수 있는 채널을 찾을 수 없습니다.")
                    
        except Exception as e:
            logger.error(f"레이드 컨트롤 메시지 전송 중 오류: {e}")
    
    def run(self):
        """봇 실행"""
        try:
            logger.info("봇을 시작합니다...")
            print("봇을 시작합니다...")
            
            # 봇 토큰 확인
            if not self.config.BOT_TOKEN:
                raise ValueError("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
            
            # 봇 실행 - bot.run()은 내부적으로 이벤트 루프를 생성하고 관리합니다
            self.bot.run(self.config.BOT_TOKEN, log_handler=None)
            
        except ValueError as e:
            logger.error(f"설정 오류: {e}")
            print(f"설정 오류: {e}")
            raise
        except KeyboardInterrupt:
            logger.info("봇이 키보드 인터럽트로 중단되었습니다.")
            print("봇이 키보드 인터럽트로 중단되었습니다.")
        except Exception as e:
            logger.error(f"봇 실행 중 오류: {e}")
            print(f"봇 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
            raise


def main():
    """메인 함수"""
    try:
        # Windows에서 이벤트 루프 정책 설정 (Python 3.8+)
        import asyncio
        import sys
        
        if sys.platform == 'win32' and sys.version_info >= (3, 8):
            try:
                # Windows에서 ProactorEventLoop 사용
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except AttributeError:
                pass  # 이전 버전에서는 무시
        
        # Config 유효성 검사
        from config import Config
        Config.validate_config()
        
        # 봇 인스턴스 생성 및 실행
        bot = SaveCodeBot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("봇이 사용자에 의해 중단되었습니다.")
        print("봇이 사용자에 의해 중단되었습니다.")
    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        print(f"설정 오류: {e}")
    except RuntimeError as e:
        if "no running event loop" in str(e):
            logger.error("이벤트 루프 오류가 발생했습니다. 봇을 다시 시작해주세요.")
            print("이벤트 루프 오류가 발생했습니다. 봇을 다시 시작해주세요.")
        else:
            logger.error(f"런타임 오류: {e}")
            print(f"런타임 오류: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        logger.error(f"봇 실행 중 치명적 오류: {e}")
        print(f"봇 실행 중 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
        raise


class SaveCodeUIView(ui.View):
    """세이브코드 생성 UI 버튼 뷰"""
    
    def __init__(self, bot_instance):
        super().__init__(timeout=300)
        self.bot = bot_instance
    
    @ui.button(label="🔮 세이브코드 생성", style=discord.ButtonStyle.primary, emoji="🔮")
    async def open_savecode_modal(self, interaction: discord.Interaction, button: ui.Button):
        """세이브코드 생성 모달 열기"""
        modal = SaveCodeCreationModal(self.bot)
        await interaction.response.send_modal(modal)


class SaveCodeCreationModal(ui.Modal, title='🔮 세이브코드 생성'):
    """세이브코드 생성을 위한 모달"""
    
    def __init__(self, bot_instance):
        super().__init__()
        self.bot = bot_instance
    
    player_name = ui.TextInput(
        label='플레이어 이름',
        placeholder='플레이어 이름을 입력하세요',
        style=discord.TextStyle.short,
        max_length=50,
        required=True
    )
    
    character_id = ui.TextInput(
        label='캐릭터 ID',
        placeholder='0~100 사이의 캐릭터 ID',
        style=discord.TextStyle.short,
        max_length=3,
        required=True
    )
    
    lumber = ui.TextInput(
        label='나무',
        placeholder='나무 수량 (예: 10000)',
        style=discord.TextStyle.short,
        max_length=10,
        required=True
    )
    
    level_stats = ui.TextInput(
        label='레벨 힘 민첩 지능',
        placeholder='예: 15 200000 100000 150000 (공백으로 구분)',
        style=discord.TextStyle.short,
        max_length=50,
        required=False
    )
    
    items = ui.TextInput(
        label='아이템 ID (최대 6개)',
        placeholder='예: 264 266 268 270 272 274 (공백으로 구분)',
        style=discord.TextStyle.paragraph,
        max_length=100,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 처리"""
        try:
            # 권한 검사 (SaveCodeBot의 메서드 사용)
            if not self.bot._check_modal_permission(interaction):
                embed = discord.Embed(
                    title="❌ 권한 없음",
                    description="세이브코드 생성 권한이 없습니다.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # 기본값 설정
            player_name = self.player_name.value.strip()
            character_id = int(self.character_id.value.strip())
            lumber = int(self.lumber.value.strip())
            
            # 레벨과 스탯 파싱
            level = 1
            strength = 0
            agility = 0
            intelligence = 0
            
            if self.level_stats.value.strip():
                stats = self.level_stats.value.strip().split()
                if len(stats) >= 1:
                    level = int(stats[0])
                if len(stats) >= 2:
                    strength = int(stats[1])
                if len(stats) >= 3:
                    agility = int(stats[2])
                if len(stats) >= 4:
                    intelligence = int(stats[3])
            
            # 아이템 파싱
            item1 = item2 = item3 = item4 = item5 = item6 = 0
            if self.items.value.strip():
                items = [int(x) for x in self.items.value.strip().split() if x.isdigit()]
                if len(items) >= 1: item1 = items[0]
                if len(items) >= 2: item2 = items[1]
                if len(items) >= 3: item3 = items[2]
                if len(items) >= 4: item4 = items[3]
                if len(items) >= 5: item5 = items[4]
                if len(items) >= 6: item6 = items[5]
            
            # 입력값 검증
            validation_error = self.bot._validate_savecode_inputs(
                lumber, character_id, level, strength, agility, intelligence, 
                [item1, item2, item3, item4, item5, item6]
            )
            
            if validation_error:
                embed = discord.Embed(
                    title="❌ 입력값 오류",
                    description=validation_error,
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # 세이브코드 생성
            result = await self.bot._create_savecode_internal(
                player_name, character_id, lumber, level, strength, agility, intelligence,
                item1, item2, item3, item4, item5, item6
            )
            
            await interaction.response.send_message(embed=result, ephemeral=False)
            
        except ValueError as e:
            embed = discord.Embed(
                title="❌ 입력값 오류",
                description="숫자 입력 필드에 올바른 숫자를 입력해주세요.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"세이브코드 모달 처리 중 오류: {e}")
            embed = discord.Embed(
                title="❌ 처리 오류",
                description=f"세이브코드 생성 중 오류가 발생했습니다: {e}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class CouponUIView(ui.View):
    """쿠폰 사용 UI 버튼 뷰"""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="🎫 쿠폰 사용하기", style=discord.ButtonStyle.secondary, emoji="🎫")
    async def open_coupon_modal(self, interaction: discord.Interaction, button: ui.Button):
        """쿠폰 처리 모달 열기"""
        modal = CouponProcessModal(None)  # bot_instance는 Modal에서 사용하지 않으므로 None
        await interaction.response.send_modal(modal)


class CouponCreateUIView(ui.View):
    """쿠폰 생성 UI 버튼 뷰"""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="🎫 쿠폰 생성하기", style=discord.ButtonStyle.danger, emoji="🎫")
    async def open_coupon_create_modal(self, interaction: discord.Interaction, button: ui.Button):
        """쿠폰 생성 모달 열기"""
        # 관리자 권한 재확인
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 쿠폰 생성은 서버 관리자만 사용할 수 있습니다.",
                ephemeral=True
            )
            return
            
        modal = CouponCreateModal()
        await interaction.response.send_modal(modal)


if __name__ == "__main__":
    main()
