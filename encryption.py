"""
For 06 EU STi (DBW)
32-bit SH7058
apparently might be the same on others too
"""

# not sure when this one is used but it was in the ECU code, maybe some other diag auth level
# seed_key_word_list_1 = [
#     0x24B9, 0x9D91, 0xFF0C, 0xB8D5, 0x15BB, 0xF998, 0x8723,
#     0x9E05, 0x7092, 0xD683, 0xBA03, 0x59E1, 0x6136, 0x9B9A,
#     0x9CFB, 0x9DDB
# ]

def encrypt(data, word_list, rounds):
    """
    this is generic and works for all auth/encryption types
    """
    i = 0
    while i < len(data):

        high_word = (data[i+0] << 8) + data[i+1]
        low_word = (data[i+2] << 8) + data[i+3]

        for j in range(rounds):
            idx2 = low_word ^ word_list[len(word_list)-1-j]
            key16 = transformnibbles(idx2)
            # rotate right 3 times
            for _ in range(3):
                rotated_bit = key16 & 0b1
                key16 = (key16 >> 1) + (rotated_bit << 15)
            num = key16 ^ high_word
            high_word = low_word
            low_word = num

        data[i+0] = low_word >> 8
        data[i+1] = low_word & 0xFF
        data[i+2] = high_word >> 8
        data[i+3] = high_word & 0xFF

        i += 4

    return data


def transformnibbles(num):
    """
    this same list of nibbles is used in combo with all word lists
    """
    seed_key_nibbles_list = [
        0x5, 0x6, 0x7, 0x1, 0x9, 0xC, 0xD, 0x8,
        0xA, 0xD, 0x2, 0xB, 0xF, 0x4, 0x0, 0x3,
        0xB, 0x4, 0x6, 0x0, 0xF, 0x2, 0xD, 0x9,
        0x5, 0xC, 0x1, 0xA, 0x3, 0xD, 0xE, 0x8
    ]
    result = 0
    num = num + ((num & 0xFF) << 16)

    for i in range(4):
        result += (seed_key_nibbles_list[(num >> (i*4)) % 32]) << (i*4)

    return result


def generate_0x27_auth_key(data):
    """
    this one seems to be used with 0x27 service for programming session auth at least
    """
    word_list = [
        0x53da, 0x33bc, 0x72eb, 0x437d, 0x7ca3, 0x3382, 0x834f, 0x3608,
        0xafb8, 0x503d, 0xdba3, 0x9d34, 0x3563, 0x6b70, 0x6e74, 0x88f0
    ]
    return encrypt(data, word_list, rounds=16)


def encrypt_0x36(data):
    """
    this is to simplify the encrypt/decrypt functions, it wasn't in the ECU like this
    it's a reversed version of the decrypt one
    used to encrypt data we will send to ECU over 0x36 service
    """
    word_list = [
        0x6E86, 0xF513, 0xCE22, 0x7856
    ]
    return encrypt(data, word_list, rounds=4)


def decrypt_0x36(data):
    """
    this was in the ECU and used to decrypt 0x36 data we send it
    """
    seed_key_word_list_3 = [
        0x7856, 0xCE22, 0xF513, 0x6E86
    ]
    return encrypt(data, seed_key_word_list_3, rounds=4)


assert generate_0x27_auth_key([0x00,0x00,0x00,0x00]) == [0x2a,0x52,0xf9,0x63]
assert decrypt_0x36([0x21, 0x78, 0xb1, 0x0a]) == [0x00, 0x09, 0x00, 0x09]
assert encrypt_0x36([0x00, 0x09, 0x00, 0x09]) == [0x21, 0x78, 0xb1, 0x0a]
