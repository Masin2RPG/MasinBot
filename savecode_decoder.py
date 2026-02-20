"""세이브코드 디코딩(버전 10) 헬퍼."""

from typing import Dict, List, Tuple, Optional


DEFAULT_SAVE_VALUE_LENGTH = [0, 6, 3, 6, 3, 6, 3, 6, 3, 3, 3, 2, 3, 4, 2, 4]
DEFAULT_ITEM_SLOTS = [2, 4, 6, 8, 10, 12]
CHAR_MAP_PLAY_TRUE = "1O7EC43VPRN8FXKDTSUQ026HWA5YIM9BJLGZ"
CHAR_MAP_PLAY_FALSE = "OBX6RAGZKT71N435YDEVPF92LUWQ0IMSCHJ8"
D_SCALE = ord('d')


def get_nine_n(m: int) -> int:
    n = 0
    j = 1
    for _ in range(m):
        n += j * 9
        j *= 10
    return n


def get_string_index(data_source: str, data_search: str, data_byte: int, plus_value: int) -> int:
    length = len(data_source) // data_byte
    for i in range(length):
        if data_search == data_source[i * data_byte:(i + 1) * data_byte]:
            return i + 1 + plus_value
    return -1


def get_string_value_ascii(temp_string: str) -> int:
    data_source = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890~`!#$^&*()-_=+|{}[]:;<>,.?@"
    temp_string = temp_string.upper()
    temp_value = 0
    for i, c in enumerate(temp_string):
        index = get_string_index(data_source, c, 1, 0)
        temp_value += index * (i + 1)
    return temp_value


def get_string_value_utf8(temp_string: str) -> int:
    data_source = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890~`!#$^&*()-_=+|{}[]:;<>,.?@"
    temp_bytes = temp_string.upper().encode('utf-8')
    temp_value = 0
    for i, byte in enumerate(temp_bytes):
        char = chr(byte)
        try:
            index = data_source.index(char) + 1
        except ValueError:
            index = -1
        temp_value += index * (i + 1)
    return temp_value


def get_string_value(temp_string: str) -> int:
    if temp_string is None:
        return 0
    try:
        temp_string.encode('ascii')
        return get_string_value_ascii(temp_string)
    except UnicodeEncodeError:
        return get_string_value_utf8(temp_string)


def code_str2int(value: str, play_type: bool = True) -> int:
    char_map = CHAR_MAP_PLAY_TRUE if play_type else CHAR_MAP_PLAY_FALSE
    if len(value) != 2:
        raise ValueError("코드 쌍의 길이가 올바르지 않습니다.")

    result = 0
    for i, check_char in enumerate(value):
        index = char_map.index(check_char)
        if i == 0:
            result = index * 36
        else:
            result += index
    return result


def _split_code_to_numeric(code: str, play_type: bool) -> Tuple[str, int]:
    if not code:
        raise ValueError("코드가 비어 있습니다.")

    clean_code = code.upper().replace("-", "")
    if len(clean_code) % 2 != 0:
        raise ValueError("코드 길이가 짝수가 아닙니다.")

    numeric_chunks: List[str] = []
    for i in range(0, len(clean_code), 2):
        pair = clean_code[i:i + 2]
        numeric_chunks.append(f"{code_str2int(pair, play_type):03d}")

    return "".join(numeric_chunks), len(clean_code)


def _build_length_map(raw_len: int, summon_chunk_n: int, save_value_length: List[int]) -> Tuple[List[int], int, int, int]:
    save_size = len(save_value_length) - 1
    expected_raw_len = 40 + (summon_chunk_n * 2)

    if raw_len == 38:
        save_data_n = save_size
        save_version = 7
        length_map = save_value_length[:]
    elif raw_len == 40:
        save_data_n = save_size + 1
        save_version = 0
        length_map = save_value_length[:] + [0]
        if len(length_map) <= 16:
            length_map += [0] * (17 - len(length_map))
        length_map[16] = 3
    elif raw_len == 42 and expected_raw_len == 42:
        save_data_n = save_size + 2
        save_version = 0
        length_map = save_value_length[:] + [0] * max(0, 18 - len(save_value_length))
        length_map[16] = 3
        length_map[17] = 3
    elif raw_len == 42:
        save_data_n = save_size + 2
        save_version = 9
        length_map = save_value_length[:] + [0] * max(0, 18 - len(save_value_length))
        length_map[16] = 3
        length_map[17] = 3
    elif raw_len == expected_raw_len:
        save_data_n = save_size + 1 + summon_chunk_n
        save_version = 10
        need_len = save_data_n + 1
        length_map = save_value_length[:]
        if len(length_map) < need_len:
            length_map += [0] * (need_len - len(length_map))
        length_map[16] = 3
        for i in range(1, summon_chunk_n + 1):
            length_map[16 + i] = 3
    else:
        raise ValueError("코드의 길이가 맞지 않습니다.")

    return length_map, save_data_n, save_version, expected_raw_len


def _parse_numeric_string(numeric_string: str, length_map: List[int], save_data_n: int) -> List[int]:
    load = [0] * (save_data_n + 1)
    position = 0

    for i in range(1, save_data_n + 1):
        length = length_map[i]
        chunk = numeric_string[position:position + length]
        if len(chunk) != length:
            raise ValueError("코드가 올바르지 않습니다.")
        load[i] = int(chunk) if chunk else 0
        position += length

    return load


def _calculate_checksum(load: List[int], length_map: List[int], save_data_n: int, raw_len: int,
                        expected_raw_len: int, save_version: int, player_name: str) -> Tuple[bool, int, int]:
    chk_base = 0
    for i in range(1, save_data_n + 1):
        if i != 9:
            chk_base += load[i] * i

    name_value = get_string_value(player_name or "")
    nine_limit = get_nine_n(length_map[9])
    resolved_version = save_version
    expected_checksum = 0
    checksum_valid = True

    if raw_len == 40:
        chk8 = (chk_base + 8 + name_value) % nine_limit
        chk10 = (chk_base + 10 + name_value) % nine_limit
        if chk10 == load[9]:
            resolved_version = 10
            expected_checksum = chk10
        elif chk8 == load[9]:
            resolved_version = 8
            expected_checksum = chk8
        else:
            checksum_valid = False
    elif raw_len == 42 and expected_raw_len == 42:
        chk9 = (chk_base + 9 + name_value) % nine_limit
        chk10 = (chk_base + 10 + name_value) % nine_limit
        if chk10 == load[9]:
            resolved_version = 10
            expected_checksum = chk10
        elif chk9 == load[9]:
            resolved_version = 9
            expected_checksum = chk9
        else:
            checksum_valid = False
    else:
        expected_checksum = (chk_base + save_version + name_value) % nine_limit
        checksum_valid = expected_checksum == load[9]

    return checksum_valid, expected_checksum, resolved_version


def _calculate_hero_type_index(load: List[int], length_map: List[int], save_data_n: int, save_version: int) -> Tuple[int, bool]:
    hero_type_low = load[14] if len(load) > 14 else 0
    hero_type_high = load[16] if len(load) > 16 else 0
    hero_extra = load[17] if len(load) > 17 else 0

    if save_data_n == len(DEFAULT_SAVE_VALUE_LENGTH) - 1:
        # 기본 포맷(슬롯 16 미포함): low만 사용, 값 검증은 양수만 확인
        valid = hero_type_low > 0
        return hero_type_low if valid else 0, valid

    # 확장 포맷: low/high(/extra) 조합
    if save_version == 9 or hero_extra > 0:
        hero_type_index = hero_type_low + (hero_type_high * 100) + (hero_extra * 100000)
    else:
        hero_type_index = hero_type_low + (hero_type_high * 100)

    valid = hero_type_index > 0
    return hero_type_index, valid


def parse_savecode(code: str, player_name: str = "", play_type: bool = True,
                   save_value_length: List[int] = None, summon_chunk_n: Optional[int] = None,
                   validate_checksum: bool = False) -> Dict:
    lengths = save_value_length or DEFAULT_SAVE_VALUE_LENGTH
    numeric_string, raw_len = _split_code_to_numeric(code, play_type)

    # 소환 청크 자동 감지: rawLen 기준으로 (rawLen-40)/2가 정수면 사용
    auto_chunk = 0
    if raw_len >= 40 and raw_len % 2 == 0:
        diff = raw_len - 40
        if diff >= 0 and diff % 2 == 0:
            auto_chunk = diff // 2

    effective_chunk = summon_chunk_n if summon_chunk_n and summon_chunk_n > 0 else auto_chunk

    length_map, save_data_n, save_version, expected_raw_len = _build_length_map(raw_len, effective_chunk, lengths)

    digits_len = (raw_len // 2) * 3
    if len(numeric_string) != digits_len:
        raise ValueError("코드가 올바르지 않습니다.")

    load = _parse_numeric_string(numeric_string, length_map, save_data_n)

    checksum_valid, expected_checksum, resolved_version = _calculate_checksum(
        load, length_map, save_data_n, raw_len, expected_raw_len, save_version, player_name
    )

    if validate_checksum and not checksum_valid:
        raise ValueError("사용자 혹은 코드가 맞지 않습니다.")

    hero_type_index, hero_type_valid = _calculate_hero_type_index(load, length_map, save_data_n, resolved_version)
    if validate_checksum and not hero_type_valid:
        raise ValueError("캐릭터가 존재하지 않습니다.")

    summon_bits: List[int] = []
    if resolved_version == 10 and summon_chunk_n > 0 and raw_len == expected_raw_len:
        for i in range(1, summon_chunk_n + 1):
            idx = 16 + i
            if idx < len(load):
                summon_bits.append(load[idx])

    items = []
    for slot in DEFAULT_ITEM_SLOTS:
        items.append(load[slot] if slot < len(load) else 0)

    return {
        'raw_data': load,
        'length_map': length_map,
        'raw_len': raw_len,
        'expected_raw_len': expected_raw_len,
        'save_version': resolved_version,
        'checksum_valid': checksum_valid,
        'checksum_expected': expected_checksum,
        'hero_type_index': hero_type_index,
        'hero_type_valid': hero_type_valid,
        'hero_type_low': load[14] if len(load) > 14 else 0,
        'hero_type_high': load[16] if len(load) > 16 else 0,
        'summon_bits': summon_bits,
        'gold': load[1] * D_SCALE if len(load) > 1 else 0,
        'lumber': load[15] * D_SCALE if len(load) > 15 else 0,
        'level': load[13] if len(load) > 13 else 0,
        'exp_compact': load[11] if len(load) > 11 else 0,
        'items': items,
        'checksum_value': load[9] if len(load) > 9 else 0
    }


def decode_savecode2(code: str, player_name: str = "", summon_chunk_n: int = 0) -> bool:
    try:
        parse_savecode(code, player_name, summon_chunk_n=summon_chunk_n, validate_checksum=True)
        return True
    except Exception:
        return False


def extract_save_data(code: str, player_name: str = "", summon_chunk_n: int = 0) -> Dict:
    return parse_savecode(code, player_name, summon_chunk_n=summon_chunk_n, validate_checksum=False)