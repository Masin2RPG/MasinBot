def get_nine_n(m):
    n = 0
    j = 1
    for _ in range(m):
        n += j * 9
        j *= 10
    return n

def get_string_index(data_source, data_search, data_byte, plus_value):
    length = len(data_source) // data_byte
    for i in range(length):
        if data_search == data_source[i * data_byte:(i + 1) * data_byte]:
            return i + 1 + plus_value
    return -1

# 🔵 ASCII용 함수
def get_string_value_ascii(temp_string):
    data_source = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890~`!#$^&*()-_=+|{}[]:;<>,.?@"
    temp_string = temp_string.upper()
    temp_value = 0
    for i, c in enumerate(temp_string):
        index = get_string_index(data_source, c, 1, 0)
        temp_value += index * (i + 1)
    return temp_value

# 🔴 한글(UTF-8)용 함수
def get_string_value_utf8(temp_string):
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

# ✅ 자동 분기: 한글/영어 자동 처리
def get_string_value(temp_string):
    try:
        temp_string.encode('ascii')  # ASCII로 변환 가능하면 영어
        return get_string_value_ascii(temp_string)
    except UnicodeEncodeError:
        return get_string_value_utf8(temp_string)

def code_str2int(value, play_type=True):
    if play_type:
        char_map = "1O7EC43VPRN8FXKDTSUQ026HWA5YIM9BJLGZ"
    else:
        char_map = "OBX6RAGZKT71N435YDEVPF92LUWQ0IMSCHJ8"
    result = 0
    strlen = len(value)
    for i in range(strlen):
        check_char = value[i]
        index = char_map.index(check_char)
        if i != strlen - 1:
            result = (index * 36)
        else:
            result += index
    return result

def decode_savecode2(code, player_name):
    # 기본 설정값
    game_version = 7
    play_type = True
    save_value_length = [0, 6, 3, 6, 3, 6, 3, 6, 3, 3, 3, 2, 3, 4, 2, 4]
    save_size = len(save_value_length) - 1

    # 코드 전처리
    code = code.upper().replace("-", "")
    temp2 = ""
    i = 0
    while i < len(code):
        temp2 += f"{code_str2int(code[i:i + 2], play_type):03}"
        i += 2

    # 디코드
    cut_string = [""] * (save_size + 1)
    load = [0] * (save_size + 1)
    temp_value = 0
    for i in range(1, save_size + 1):
        length = save_value_length[i]
        cut_string[i] = temp2[temp_value:temp_value + length]
        load[i] = int(cut_string[i])
        temp_value += length

    # CheckNum 계산
    checknum = 0
    for i in range(1, save_size + 1):
        if i != 9:
            checknum += load[i] * i

    # gameVersion 보정
    if game_version > 99:
        checknum += game_version % ord('d')
    else:
        checknum += game_version

    # 플레이어 이름 기반 가산
    getstringvalue_result = get_string_value(player_name)
    checknum += getstringvalue_result
    checknum %= get_nine_n(save_value_length[9])

    # 검증 결과
    return checknum == load[9]

def extract_save_data(code, player_name):
    """
    세이브코드에서 골드, 나무, 영웅 타입 인덱스를 추출
    """
    # 기본 설정값 (JavaScript 코드와 동일)
    game_version = 7
    play_type = True
    save_value_length = [0, 6, 3, 6, 3, 6, 3, 6, 3, 3, 3, 2, 3, 4, 2, 4]
    save_size = len(save_value_length) - 1

    # 코드 전처리
    code = code.upper().replace("-", "")
    temp2 = ""
    i = 0
    while i < len(code):
        temp2 += f"{code_str2int(code[i:i + 2], play_type):03}"
        i += 2

    # 디코드
    cut_string = [""] * (save_size + 1)
    load = [0] * (save_size + 1)
    temp_value = 0
    for i in range(1, save_size + 1):
        length = save_value_length[i]
        cut_string[i] = temp2[temp_value:temp_value + length]
        load[i] = int(cut_string[i])
        temp_value += length

    # 스케일 복원 (JavaScript와 동일)
    scale_factor = 100
    gold = load[1] * scale_factor      # saveData[1] * 100
    lumber = load[15] * scale_factor   # saveData[15] * 100
    hero_type_index = load[14]         # saveData[14]
    
    # 추가 데이터
    level = load[13]
    exp_compact = load[11]
    
    return {
        'gold': gold,
        'lumber': lumber, 
        'hero_type_index': hero_type_index,
        'level': level,
        'exp_compact': exp_compact,
        'items': [load[2], load[4], load[6], load[8], load[10], load[12]],
        'checksum': load[9],
        'raw_data': load
    }