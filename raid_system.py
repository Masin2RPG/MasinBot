"""
레이드 대기 시스템 모듈
Discord 봇의 레이드 대기자 관리 기능을 제공
"""

import time
from typing import Dict, List, Optional, Set

import discord


class PartyRecruitment:
    """파티 모집 정보를 담는 클래스"""
    
    def __init__(self, party_id: str, leader_id: int, raid_name: str, 
                 max_members: int, description: str = "", scheduled_time: str = "", room_title: str = ""):
        self.party_id = party_id
        self.leader_id = leader_id
        self.raid_name = raid_name
        self.max_members = max_members
        self.current_members = {leader_id}  # 리더는 자동으로 포함
        self.description = description
        self.scheduled_time = scheduled_time
        self.room_title = room_title
        self.created_at = time.time()
        self.is_active = True
    
    def add_member(self, user_id: int) -> bool:
        """파티원 추가"""
        if len(self.current_members) < self.max_members and user_id not in self.current_members:
            self.current_members.add(user_id)
            return True
        return False
    
    def remove_member(self, user_id: int) -> bool:
        """파티원 제거 (리더는 제거 불가)"""
        if user_id != self.leader_id and user_id in self.current_members:
            self.current_members.discard(user_id)
            return True
        return False
    
    def is_full(self) -> bool:
        """파티가 가득 찼는지 확인"""
        return len(self.current_members) >= self.max_members
    
    def get_remaining_slots(self) -> int:
        """남은 자리 수 반환"""
        return self.max_members - len(self.current_members)


class RaidWaitingSystem:
    """레이드 대기자 관리 시스템"""
    
    def __init__(self):
        # 레이드별 대기자 목록 {raid_name: set(user_ids)}
        self.waiting_lists = {
            "🔮 완전한플뤼톤": set(),
            "🌋 델모크": set(),
            "⚡ 아몬": set(),
            "📖 묵시록(노말)": set(),
            "🔥 묵시록(인페르날)": set(),
            "😇 라파엘": set(),
            "🛡️ 가브리엘": set(),
            "⚔️ 우리엘": set(),
            "🌊 노아": set()
        }
        
        # 헬퍼 대기자 목록
        self.helper_waiting_list = set()
        
        # 파티 모집 목록 {party_id: PartyRecruitment}
        self.party_recruitments = {}
        self._party_counter = 0
    
    def add_to_raid(self, raid_name: str, user_id: int) -> bool:
        """특정 레이드에 유저 추가"""
        if raid_name in self.waiting_lists:
            self.waiting_lists[raid_name].add(user_id)
            return True
        return False
    
    def remove_from_raid(self, raid_name: str, user_id: int) -> bool:
        """특정 레이드에서 유저 제거"""
        if raid_name in self.waiting_lists:
            self.waiting_lists[raid_name].discard(user_id)
            return True
        return False
    
    def toggle_raid_participation(self, raid_name: str, user_id: int) -> bool:
        """레이드 참여 상태 토글 (추가/제거)"""
        if raid_name not in self.waiting_lists:
            return False
        
        if user_id in self.waiting_lists[raid_name]:
            self.waiting_lists[raid_name].discard(user_id)
            return False  # 제거됨
        else:
            self.waiting_lists[raid_name].add(user_id)
            return True   # 추가됨
    
    def get_raid_participants(self, raid_name: str) -> Set[int]:
        """특정 레이드의 참여자 목록 반환"""
        return self.waiting_lists.get(raid_name, set()).copy()
    
    def get_all_raids(self) -> list:
        """모든 레이드 이름 목록 반환"""
        return list(self.waiting_lists.keys())
    
    def get_user_raids(self, user_id: int) -> list:
        """특정 유저가 참여한 레이드 목록 반환"""
        user_raids = []
        for raid_name, participants in self.waiting_lists.items():
            if user_id in participants:
                user_raids.append(raid_name)
        return user_raids
    
    def clear_raid(self, raid_name: str) -> bool:
        """특정 레이드의 모든 참여자 초기화"""
        if raid_name in self.waiting_lists:
            self.waiting_lists[raid_name].clear()
            return True
        return False
    
    def clear_all_raids(self):
        """모든 레이드의 참여자 초기화"""
        for raid_name in self.waiting_lists:
            self.waiting_lists[raid_name].clear()
    
    def add_to_helper(self, user_id: int) -> bool:
        """헬퍼 대기 목록에 유저 추가"""
        self.helper_waiting_list.add(user_id)
        return True
    
    def remove_from_helper(self, user_id: int) -> bool:
        """헬퍼 대기 목록에서 유저 제거"""
        self.helper_waiting_list.discard(user_id)
        return True
    
    def toggle_helper_participation(self, user_id: int) -> bool:
        """헬퍼 참여 상태 토글 (추가/제거)"""
        if user_id in self.helper_waiting_list:
            self.helper_waiting_list.discard(user_id)
            return False  # 제거됨
        else:
            self.helper_waiting_list.add(user_id)
            return True   # 추가됨
    
    def get_helper_participants(self) -> Set[int]:
        """헬퍼 대기자 목록 반환"""
        return self.helper_waiting_list.copy()
    
    def get_helper_count(self) -> int:
        """헬퍼 대기자 수 반환"""
        return len(self.helper_waiting_list)
    
    def clear_helper_list(self):
        """헬퍼 대기 목록 초기화"""
        self.helper_waiting_list.clear()
    
    def format_helper_list(self, guild: discord.Guild = None) -> str:
        """헬퍼 대기자 목록을 포맷된 문자열로 반환"""
        if not self.helper_waiting_list:
            return "🤝 헬퍼: 대기자 없음"
        
        participant_list = []
        for user_id in self.helper_waiting_list:
            if guild:
                member = guild.get_member(user_id)
                if member:
                    participant_list.append(member.display_name)
                else:
                    participant_list.append(f"<@{user_id}>")
            else:
                participant_list.append(f"<@{user_id}>")
        
        return f"🤝 헬퍼: {', '.join(participant_list)} ({len(self.helper_waiting_list)}명)"
    
    def get_raid_count(self, raid_name: str) -> int:
        """특정 레이드의 참여자 수 반환"""
        return len(self.waiting_lists.get(raid_name, set()))
    
    def format_raid_list(self, raid_name: str, guild: discord.Guild = None) -> str:
        """레이드 참여자 목록을 포맷된 문자열로 반환"""
        participants = self.waiting_lists.get(raid_name, set())
        
        if not participants:
            return f"{raid_name}: 대기자 없음"
        
        participant_list = []
        for user_id in participants:
            if guild:
                member = guild.get_member(user_id)
                if member:
                    participant_list.append(member.display_name)
                else:
                    participant_list.append(f"<@{user_id}>")
            else:
                participant_list.append(f"<@{user_id}>")
        
        return f"{raid_name}: {', '.join(participant_list)} ({len(participants)}명)"
    
    def format_all_raids(self, guild: discord.Guild = None) -> str:
        """모든 레이드의 참여자 목록을 포맷된 문자열로 반환 (헬퍼 포함)"""
        raid_info = []
        for raid_name in self.waiting_lists:
            raid_info.append(self.format_raid_list(raid_name, guild))
        
        # 헬퍼 목록 추가
        raid_info.append(self.format_helper_list(guild))
        
        return "\n".join(raid_info)
    
    # 파티 모집 관련 메서드들
    def create_party_recruitment(self, leader_id: int, raid_name: str, 
                               max_members: int, description: str = "", 
                               scheduled_time: str = "", room_title: str = "") -> str:
        """파티 모집 생성"""
        self._party_counter += 1
        party_id = f"party_{self._party_counter}"
        
        recruitment = PartyRecruitment(
            party_id=party_id,
            leader_id=leader_id,
            raid_name=raid_name,
            max_members=max_members,
            description=description,
            scheduled_time=scheduled_time,
            room_title=room_title
        )
        
        self.party_recruitments[party_id] = recruitment
        return party_id
    
    def get_party_recruitment(self, party_id: str) -> Optional[PartyRecruitment]:
        """파티 모집 정보 반환"""
        return self.party_recruitments.get(party_id)
    
    def join_party(self, party_id: str, user_id: int) -> bool:
        """파티 참가"""
        if party_id in self.party_recruitments:
            return self.party_recruitments[party_id].add_member(user_id)
        return False
    
    def leave_party(self, party_id: str, user_id: int) -> bool:
        """파티 탈퇴"""
        if party_id in self.party_recruitments:
            return self.party_recruitments[party_id].remove_member(user_id)
        return False
    
    def close_party_recruitment(self, party_id: str) -> bool:
        """파티 모집 종료"""
        if party_id in self.party_recruitments:
            self.party_recruitments[party_id].is_active = False
            return True
        return False
    
    def delete_party_recruitment(self, party_id: str) -> bool:
        """파티 모집 삭제"""
        if party_id in self.party_recruitments:
            del self.party_recruitments[party_id]
            return True
        return False
    
    def get_active_parties(self, raid_name: str = None) -> List[PartyRecruitment]:
        """활성 파티 모집 목록 반환"""
        active_parties = []
        for recruitment in self.party_recruitments.values():
            if recruitment.is_active and not recruitment.is_full():
                if raid_name is None or recruitment.raid_name == raid_name:
                    active_parties.append(recruitment)
        
        # 생성 시간 순으로 정렬
        active_parties.sort(key=lambda x: x.created_at)
        return active_parties
    
    def get_user_led_parties(self, user_id: int) -> List[PartyRecruitment]:
        """특정 유저가 리더인 파티 목록 반환"""
        user_parties = []
        for recruitment in self.party_recruitments.values():
            if recruitment.leader_id == user_id and recruitment.is_active:
                user_parties.append(recruitment)
        return user_parties
    
    def get_user_joined_parties(self, user_id: int) -> List[PartyRecruitment]:
        """특정 유저가 참가 중인 파티 목록 반환"""
        joined_parties = []
        for recruitment in self.party_recruitments.values():
            if recruitment.is_active and user_id in recruitment.current_members:
                joined_parties.append(recruitment)
        return joined_parties
    
    def format_party_info(self, party: PartyRecruitment, guild: discord.Guild = None) -> str:
        """파티 정보를 포맷된 문자열로 반환"""
        # 리더 정보
        leader_name = "Unknown"
        if guild:
            leader_member = guild.get_member(party.leader_id)
            if leader_member:
                leader_name = leader_member.display_name
        
        # 파티원 목록
        member_names = []
        for user_id in party.current_members:
            if guild:
                member = guild.get_member(user_id)
                if member:
                    member_names.append(member.display_name)
                else:
                    member_names.append(f"<@{user_id}>")
            else:
                member_names.append(f"<@{user_id}>")
        
        info = f"**{party.raid_name}** 파티\n"
        info += f"👑 리더: {leader_name}\n"
        info += f"👥 인원: {len(party.current_members)}/{party.max_members}\n"
        info += f"🏷️ ID: {party.party_id}\n"
        
        if party.room_title:
            info += f"🏠 방제: {party.room_title}\n"
        
        if party.scheduled_time:
            info += f"⏰ 시간: {party.scheduled_time}\n"
        
        if party.description:
            info += f"📝 설명: {party.description}\n"
        
        if len(member_names) > 1:
            info += f"👥 파티원: {', '.join(member_names)}"
        
        return info