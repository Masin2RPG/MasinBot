#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
쿠폰 통합 처리 모듈
쿠폰 체크 -> 사용 -> 세이브코드 수정까지 전체 워크플로우를 처리
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import requests

from lumber_modifier import LumberModifier

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CouponCheckResponse:
    """쿠폰 체크 API 응답 데이터 클래스"""
    is_success: bool
    is_usable: bool
    coupon_code: str
    error_message: str
    lumber: int
    gold: int
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CouponCheckResponse':
        """딕셔너리에서 CouponCheckResponse 객체 생성"""
        return cls(
            is_success=data.get('isSuccess', False),
            is_usable=data.get('isUsable', False),
            coupon_code=data.get('couponCode', ''),
            error_message=data.get('errorMessage', ''),
            lumber=data.get('lumber', 0),
            gold=data.get('gold', 0)
        )


@dataclass
class CouponUseResponse:
    """쿠폰 사용 API 응답 데이터 클래스"""
    is_success: bool
    lumber: int
    gold: int
    coupon_code: str
    error_message: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CouponUseResponse':
        """딕셔너리에서 CouponUseResponse 객체 생성"""
        return cls(
            is_success=data.get('isSuccess', False),
            lumber=data.get('lumber', 0),
            gold=data.get('gold', 0),
            coupon_code=data.get('couponCode', ''),
            error_message=data.get('errorMessage', '')
        )


@dataclass
class CouponCreateResponse:
    """쿠폰 생성 API 응답 데이터 클래스"""
    is_success: bool
    coupon_code: str
    lumber: int
    gold: int
    error_message: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CouponCreateResponse':
        """딕셔너리에서 CouponCreateResponse 객체 생성"""
        return cls(
            is_success=data.get('isSuccess', False),
            coupon_code=data.get('couponCode', ''),
            lumber=data.get('lumber', 0),
            gold=data.get('gold', 0),
            error_message=data.get('errorMessage', '')
        )


@dataclass
class CouponProcessResult:
    """쿠폰 처리 결과"""
    success: bool
    original_savecode: str
    modified_savecode: str
    gold_gained: int
    lumber_gained: int
    coupon_code: str
    error_message: str


class CouponProcessor:
    """쿠폰 처리 통합 클래스"""
    
    def __init__(self, base_url: str = "http://211.202.189.93:5036"):
        """
        쿠폰 처리기 초기화
        
        Args:
            base_url: API 기본 URL
        """
        self.base_url = base_url.rstrip('/')
        self.check_endpoint = f"{self.base_url}/api/coupon/check"
        self.use_endpoint = f"{self.base_url}/api/coupon/use"
        self.create_endpoint = f"{self.base_url}/api/coupon/create"
        self.timeout = 10
        
        # 세션 생성
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'MasinSavecode-CouponProcessor/1.0'
        })
        
        # 세이브코드 수정기 초기화
        self.modifier = LumberModifier()
    
    def check_coupon(self, coupon_code: str) -> Tuple[bool, CouponCheckResponse]:
        """
        쿠폰 사용 가능 여부 체크
        
        Args:
            coupon_code: 체크할 쿠폰 코드
            
        Returns:
            Tuple[bool, CouponCheckResponse]: (API 호출 성공 여부, 응답 데이터)
        """
        try:
            logger.info(f"쿠폰 체크 요청: {coupon_code}")
            
            # GET 요청으로 쿠폰 체크
            url = f"{self.check_endpoint}/{coupon_code}"
            response = self.session.get(url, timeout=self.timeout)
            
            # HTTP 상태 코드 확인
            response.raise_for_status()
            
            # JSON 응답 파싱
            response_data = response.json()
            check_response = CouponCheckResponse.from_dict(response_data)
            
            logger.info(f"쿠폰 체크 응답: {check_response}")
            
            return True, check_response
            
        except requests.exceptions.Timeout:
            error_msg = "쿠폰 체크 API 요청 시간 초과"
            logger.error(error_msg)
            return False, CouponCheckResponse(
                is_success=False,
                is_usable=False,
                coupon_code=coupon_code,
                error_message=error_msg,
                lumber=0,
                gold=0
            )
            
        except requests.exceptions.ConnectionError:
            error_msg = "쿠폰 체크 API 서버에 연결할 수 없습니다"
            logger.error(error_msg)
            return False, CouponCheckResponse(
                is_success=False,
                is_usable=False,
                coupon_code=coupon_code,
                error_message=error_msg,
                lumber=0,
                gold=0
            )
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"쿠폰 체크 HTTP 오류: {e.response.status_code}"
            logger.error(error_msg)
            return False, CouponCheckResponse(
                is_success=False,
                is_usable=False,
                coupon_code=coupon_code,
                error_message=error_msg,
                lumber=0,
                gold=0
            )
            
        except json.JSONDecodeError:
            error_msg = "쿠폰 체크 API 응답을 파싱할 수 없습니다"
            logger.error(error_msg)
            return False, CouponCheckResponse(
                is_success=False,
                is_usable=False,
                coupon_code=coupon_code,
                error_message=error_msg,
                lumber=0,
                gold=0
            )
            
        except Exception as e:
            error_msg = f"쿠폰 체크 예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            return False, CouponCheckResponse(
                is_success=False,
                is_usable=False,
                coupon_code=coupon_code,
                error_message=error_msg,
                lumber=0,
                gold=0
            )
    
    def use_coupon(self, coupon_code: str) -> Tuple[bool, CouponUseResponse]:
        """
        쿠폰 사용 API 호출
        
        Args:
            coupon_code: 사용할 쿠폰 코드
            
        Returns:
            Tuple[bool, CouponUseResponse]: (API 호출 성공 여부, 응답 데이터)
        """
        try:
            # 요청 데이터 준비
            payload = {
                "couponCode": coupon_code.strip()
            }
            
            logger.info(f"쿠폰 사용 요청: {coupon_code}")
            
            # API 호출
            response = self.session.post(
                self.use_endpoint,
                json=payload,
                timeout=self.timeout
            )
            
            # HTTP 상태 코드 확인
            response.raise_for_status()
            
            # JSON 응답 파싱
            response_data = response.json()
            use_response = CouponUseResponse.from_dict(response_data)
            
            logger.info(f"쿠폰 사용 응답: {use_response}")
            
            return True, use_response
            
        except requests.exceptions.Timeout:
            error_msg = "쿠폰 사용 API 요청 시간 초과"
            logger.error(error_msg)
            return False, CouponUseResponse(
                is_success=False,
                lumber=0,
                gold=0,
                coupon_code=coupon_code,
                error_message=error_msg
            )
            
        except requests.exceptions.ConnectionError:
            error_msg = "쿠폰 사용 API 서버에 연결할 수 없습니다"
            logger.error(error_msg)
            return False, CouponUseResponse(
                is_success=False,
                lumber=0,
                gold=0,
                coupon_code=coupon_code,
                error_message=error_msg
            )
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"쿠폰 사용 HTTP 오류: {e.response.status_code}"
            logger.error(error_msg)
            return False, CouponUseResponse(
                is_success=False,
                lumber=0,
                gold=0,
                coupon_code=coupon_code,
                error_message=error_msg
            )
            
        except json.JSONDecodeError:
            error_msg = "쿠폰 사용 API 응답을 파싱할 수 없습니다"
            logger.error(error_msg)
            return False, CouponUseResponse(
                is_success=False,
                lumber=0,
                gold=0,
                coupon_code=coupon_code,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"쿠폰 사용 예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            return False, CouponUseResponse(
                is_success=False,
                lumber=0,
                gold=0,
                coupon_code=coupon_code,
                error_message=error_msg
            )
    
    def create_coupon(self, lumber: int, gold: int) -> Tuple[bool, CouponCreateResponse]:
        """
        쿠폰 생성 API 호출
        
        Args:
            lumber: 나무 수량
            gold: 골드 수량
            
        Returns:
            Tuple[bool, CouponCreateResponse]: (API 호출 성공 여부, 응답 데이터)
        """
        try:
            # 요청 데이터 준비
            payload = {
                "lumber": lumber,
                "gold": gold
            }
            
            logger.info(f"쿠폰 생성 요청: lumber={lumber:,}, gold={gold:,}")
            
            # API 호출
            response = self.session.post(
                self.create_endpoint,
                json=payload,
                timeout=self.timeout
            )
            
            # HTTP 상태 코드 확인
            response.raise_for_status()
            
            # JSON 응답 파싱
            response_data = response.json()
            create_response = CouponCreateResponse.from_dict(response_data)
            
            logger.info(f"쿠폰 생성 응답: {create_response}")
            
            return True, create_response
            
        except requests.exceptions.Timeout:
            error_msg = "쿠폰 생성 API 요청 시간 초과"
            logger.error(error_msg)
            return False, CouponCreateResponse(
                is_success=False,
                coupon_code="",
                lumber=lumber,
                gold=gold,
                error_message=error_msg
            )
            
        except requests.exceptions.ConnectionError:
            error_msg = "쿠폰 생성 API 서버에 연결할 수 없습니다"
            logger.error(error_msg)
            return False, CouponCreateResponse(
                is_success=False,
                coupon_code="",
                lumber=lumber,
                gold=gold,
                error_message=error_msg
            )
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"쿠폰 생성 HTTP 오류: {e.response.status_code}"
            logger.error(error_msg)
            return False, CouponCreateResponse(
                is_success=False,
                coupon_code="",
                lumber=lumber,
                gold=gold,
                error_message=error_msg
            )
            
        except json.JSONDecodeError:
            error_msg = "쿠폰 생성 API 응답을 파싱할 수 없습니다"
            logger.error(error_msg)
            return False, CouponCreateResponse(
                is_success=False,
                coupon_code="",
                lumber=lumber,
                gold=gold,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"쿠폰 생성 예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            return False, CouponCreateResponse(
                is_success=False,
                coupon_code="",
                lumber=lumber,
                gold=gold,
                error_message=error_msg
            )
    
    def process_coupon_with_savecode(self, coupon_code: str, savecode: str, player_name: str = None) -> CouponProcessResult:
        """
        쿠폰 체크 -> 세이브코드 수정 -> 성공시 쿠폰 사용 처리 전체 워크플로우
        
        Args:
            coupon_code: 쿠폰 코드
            savecode: 원본 세이브코드
            player_name: 플레이어 이름 (원본 게임 세이브코드의 경우 필수)
            
        Returns:
            CouponProcessResult: 처리 결과
        """
        logger.info(f"쿠폰 처리 시작: {coupon_code}")
        
        # 1단계: 쿠폰 체크
        check_success, check_response = self.check_coupon(coupon_code)
        
        if not check_success:
            return CouponProcessResult(
                success=False,
                original_savecode=savecode,
                modified_savecode="",
                gold_gained=0,
                lumber_gained=0,
                coupon_code=coupon_code,
                error_message=f"쿠폰 체크 실패: {check_response.error_message}"
            )
        
        # 쿠폰 체크 API가 성공했지만 사용할 수 없는 경우
        if not check_response.is_success or not check_response.is_usable:
            return CouponProcessResult(
                success=False,
                original_savecode=savecode,
                modified_savecode="",
                gold_gained=0,
                lumber_gained=0,
                coupon_code=coupon_code,
                error_message=check_response.error_message or "사용할 수 없는 쿠폰입니다"
            )
        
        # 2단계: 세이브코드 수정 (쿠폰 체크에서 받은 정보 사용)
        try:
            # 원본 세이브코드 파싱하여 현재 골드/나무 확인
            if savecode.startswith('MasinSaveV2_'):
                # 마신 세이브코드는 골드 수정 미지원
                if check_response.gold > 0:
                    return CouponProcessResult(
                        success=False,
                        original_savecode=savecode,
                        modified_savecode="",
                        gold_gained=0,
                        lumber_gained=0,
                        coupon_code=coupon_code,
                        error_message="마신 세이브코드는 골드 추가를 지원하지 않습니다"
                    )
                
                # 나무만 추가
                original_data = self.modifier.parse_masin_savecode(savecode)
                new_lumber = original_data['lumber'] + check_response.lumber
                modified_savecode = self.modifier.modify_lumber(savecode, new_lumber)
                
            else:
                # 원본 게임 세이브코드
                if player_name is None:
                    return CouponProcessResult(
                        success=False,
                        original_savecode=savecode,
                        modified_savecode="",
                        gold_gained=0,
                        lumber_gained=0,
                        coupon_code=coupon_code,
                        error_message="원본 게임 세이브코드 수정을 위해서는 플레이어 이름이 필요합니다"
                    )
                
                # 현재 골드/나무 확인
                original_data = self.modifier.parse_original_savecode(savecode)
                new_gold = original_data['gold'] + check_response.gold
                new_lumber = original_data['lumber'] + check_response.lumber
                
                # 골드와 나무 모두 수정
                modified_savecode = self.modifier.modify_resources(
                    savecode, 
                    gold_amount=new_gold,
                    lumber_amount=new_lumber,
                    player_name=player_name
                )
            
            # 3단계: 세이브코드 수정이 성공했으므로 쿠폰 사용 처리
            logger.info(f"세이브코드 수정 성공, 쿠폰 사용 처리 진행: {coupon_code}")
            use_success, use_response = self.use_coupon(coupon_code)
            
            if not use_success:
                logger.warning(f"쿠폰 사용 API 호출 실패했지만 세이브코드는 이미 수정됨: {use_response.error_message}")
                # 세이브코드 수정은 성공했으므로 성공으로 반환하되 경고 메시지 포함
                return CouponProcessResult(
                    success=True,
                    original_savecode=savecode,
                    modified_savecode=modified_savecode,
                    gold_gained=check_response.gold,
                    lumber_gained=check_response.lumber,
                    coupon_code=coupon_code,
                    error_message=f"⚠️ 세이브코드는 수정되었지만 쿠폰 사용 처리 실패: {use_response.error_message}"
                )
            
            if not use_response.is_success:
                logger.warning(f"쿠폰 사용 실패했지만 세이브코드는 이미 수정됨: {use_response.error_message}")
                return CouponProcessResult(
                    success=True,
                    original_savecode=savecode,
                    modified_savecode=modified_savecode,
                    gold_gained=check_response.gold,
                    lumber_gained=check_response.lumber,
                    coupon_code=coupon_code,
                    error_message=f"⚠️ 세이브코드는 수정되었지만 쿠폰 사용 처리 실패: {use_response.error_message}"
                )
            
            # 모든 단계 성공
            logger.info(f"쿠폰 처리 완료: {coupon_code}")
            return CouponProcessResult(
                success=True,
                original_savecode=savecode,
                modified_savecode=modified_savecode,
                gold_gained=check_response.gold,
                lumber_gained=check_response.lumber,
                coupon_code=coupon_code,
                error_message=""
            )
            
        except Exception as e:
            logger.error(f"세이브코드 수정 중 오류: {str(e)}")
            return CouponProcessResult(
                success=False,
                original_savecode=savecode,
                modified_savecode="",
                gold_gained=0,
                lumber_gained=0,
                coupon_code=coupon_code,
                error_message=f"세이브코드 수정 중 오류: {str(e)}"
            )
    
    def close(self):
        """세션 종료"""
        if self.session:
            self.session.close()


# 편의 함수
def process_coupon_simple(coupon_code: str, savecode: str, player_name: str = None) -> CouponProcessResult:
    """
    쿠폰 처리 간편 함수
    
    Args:
        coupon_code: 쿠폰 코드
        savecode: 세이브코드
        player_name: 플레이어 이름 (원본 게임 세이브코드의 경우 필수)
        
    Returns:
        CouponProcessResult: 처리 결과
    """
    processor = CouponProcessor()
    try:
        return processor.process_coupon_with_savecode(coupon_code, savecode, player_name)
    finally:
        processor.close()


def create_coupon_simple(lumber: int, gold: int) -> Tuple[bool, CouponCreateResponse]:
    """
    쿠폰 생성 간편 함수
    
    Args:
        lumber: 나무 수량
        gold: 골드 수량
        
    Returns:
        Tuple[bool, CouponCreateResponse]: (성공 여부, 응답 데이터)
    """
    processor = CouponProcessor()
    try:
        return processor.create_coupon(lumber, gold)
    finally:
        processor.close()


def format_coupon_create_result(success: bool, response: CouponCreateResponse) -> str:
    """
    쿠폰 생성 결과를 사용자 친화적 문자열로 포맷팅
    
    Args:
        success: API 호출 성공 여부
        response: 쿠폰 생성 응답 데이터
        
    Returns:
        str: 포맷된 문자열
    """
    if success and response.is_success:
        return (
            f"🎉 쿠폰 생성 성공!\n"
            f"🎫 쿠폰 코드: `{response.coupon_code}`\n"
            f"💰 골드: {response.gold:,}\n"
            f"🌲 나무: {response.lumber:,}\n"
            f"💬 {response.error_message}\n\n"
            f"📋 사용법: `/쿠폰` 명령어로 이 코드를 사용할 수 있습니다!"
        )
    else:
        return (
            f"❌ 쿠폰 생성 실패\n"
            f"💰 요청 골드: {response.gold:,}\n"
            f"🌲 요청 나무: {response.lumber:,}\n"
            f"💬 {response.error_message}"
        )


def format_coupon_result(result: CouponProcessResult) -> str:
    """
    쿠폰 처리 결과를 사용자 친화적 문자열로 포맷팅
    
    Args:
        result: 쿠폰 처리 결과
        
    Returns:
        str: 포맷된 문자열
    """
    if result.success:
        return (
            f"🎉 쿠폰 적용 완료!\n"
            f"🎫 쿠폰: {result.coupon_code}\n"
            f"💰 골드: +{result.gold_gained:,}\n"
            f"🌲 나무: +{result.lumber_gained:,}\n"
            f"\n📋 수정된 세이브코드:\n"
            f"`{result.modified_savecode}`"
        )
    else:
        return (
            f"❌ 쿠폰 처리 실패\n"
            f"🎫 쿠폰: {result.coupon_code}\n"
            f"💬 오류: {result.error_message}"
        )


# 테스트 코드
if __name__ == "__main__":
    print("🧪 쿠폰 통합 처리 테스트")
    print("=" * 50)
    
    # 테스트용 데이터
    test_coupon = "ABC123"
    test_savecode = "7C0W3-AYYYY-V6YYY-YVTYY-YY3GH-I4814-OC1OF-WFS"
    test_player_name = "테스터"
    
    print(f"쿠폰 코드: {test_coupon}")
    print(f"세이브코드: {test_savecode}")
    print(f"플레이어: {test_player_name}")
    print("-" * 50)
    
    # 쿠폰 처리 실행
    result = process_coupon_simple(test_coupon, test_savecode, test_player_name)
    
    # 결과 출력
    print("📋 처리 결과:")
    print(format_coupon_result(result))
    
    if result.success:
        print(f"\n🔍 상세 정보:")
        print(f"   원본 세이브코드: {result.original_savecode}")
        print(f"   수정된 세이브코드: {result.modified_savecode}")
        print(f"   골드 증가: {result.gold_gained:,}")
        print(f"   나무 증가: {result.lumber_gained:,}")