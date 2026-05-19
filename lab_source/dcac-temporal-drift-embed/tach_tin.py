import cv2
import numpy as np
import os

# ==================================================
# CONFIG
# ==================================================
VIDEO = "output.avi"

BLOCK = 8

MAGIC = b"DCACSTEG"
HEADER_SIZE = len(MAGIC) + 4

# Ngưỡng tin cậy DC.
# Với output hiện tại của bro, DC diff thường khoảng +/-40 đến +/-60.
DC_CONFIDENCE = 10.0


# ==================================================
# BITS <-> BYTES
# ==================================================
def bits_to_bytes(bits: str) -> bytes:
    data = bytearray()

    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]

        if len(byte) == 8:
            data.append(int(byte, 2))

    return bytes(data)


# ==================================================
# BLOCK UTILS
# ==================================================
def get_block_positions(h, w):
    positions = []

    for y in range(0, h - BLOCK + 1, BLOCK):
        for x in range(0, w - BLOCK + 1, BLOCK):
            positions.append((y, x))

    return positions


# ==================================================
# EXTRACT BIT SOURCES
# ==================================================
def extract_dc_temporal(dct1, dct2):
    dc1 = dct1[0, 0]
    dc2 = dct2[0, 0]

    diff = dc2 - dc1

    bit = "1" if diff >= 0 else "0"

    return bit, abs(diff)


def extract_ac_intra(dct):
    ac1 = dct[2, 3]
    ac2 = dct[3, 2]

    diff = ac1 - ac2

    bit = "1" if diff >= 0 else "0"

    return bit, abs(diff)


def majority_vote(bits):
    ones = bits.count("1")
    zeros = bits.count("0")

    return "1" if ones >= zeros else "0"


# ==================================================
# EXTRACT 1 BIT FROM 1 BLOCK PAIR
# ==================================================
def extract_bit_from_block_pair(block1, block2):
    dct1 = cv2.dct(np.float32(block1))
    dct2 = cv2.dct(np.float32(block2))

    # 1. DC temporal
    b_dc, conf_dc = extract_dc_temporal(dct1, dct2)

    # 2. AC intra-frame frame t
    b_ac1, conf_ac1 = extract_ac_intra(dct1)

    # 3. AC intra-frame frame t+1
    b_ac2, conf_ac2 = extract_ac_intra(dct2)

    # Quan trọng:
    # DC liên frame ổn định hơn AC sau khi IDCT + uint8 + ghi video.
    # Nếu DC đủ rõ thì ưu tiên DC.
    if conf_dc >= DC_CONFIDENCE:
        return b_dc

    # Nếu DC yếu thì mới fallback sang vote 3 nguồn.
    return majority_vote([b_dc, b_ac1, b_ac2])


# ==================================================
# BIT STREAM GENERATOR
# ==================================================
def bit_stream_from_video(cap):
    """
    Đọc bit liên tục theo đúng thứ tự lúc nhúng:

        frame 0 + frame 1
            block 0
            block 1
            block 2
            ...

        frame 2 + frame 3
            block 0
            block 1
            block 2
            ...
    """

    while True:
        ret1, frame1 = cap.read()

        if not ret1:
            break

        ret2, frame2 = cap.read()

        if not ret2:
            break

        # OpenCV có thể đọc grayscale video thành BGR
        if len(frame1.shape) == 3:
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        else:
            gray1 = frame1

        if len(frame2.shape) == 3:
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        else:
            gray2 = frame2

        h, w = gray1.shape
        positions = get_block_positions(h, w)

        for y, x in positions:
            block1 = gray1[y:y + BLOCK, x:x + BLOCK]
            block2 = gray2[y:y + BLOCK, x:x + BLOCK]

            bit = extract_bit_from_block_pair(block1, block2)

            yield bit


def read_n_bits(bit_gen, n_bits):
    bits = ""

    for _ in range(n_bits):
        try:
            bits += next(bit_gen)
        except StopIteration:
            break

    return bits


# ==================================================
# MAIN EXTRACT
# ==================================================
def main():
    if not os.path.exists(VIDEO):
        print(f"[!] Không thấy video: {VIDEO}")
        return

    cap = cv2.VideoCapture(VIDEO)

    if not cap.isOpened():
        print("[!] Không mở được video")
        return

    bit_gen = bit_stream_from_video(cap)

    # Đọc header
    header_bits_needed = HEADER_SIZE * 8
    header_bits = read_n_bits(bit_gen, header_bits_needed)

    if len(header_bits) < header_bits_needed:
        print("[!] Không đọc đủ header")
        cap.release()
        return

    header = bits_to_bytes(header_bits)

    magic = header[:len(MAGIC)]
    msg_len_bytes = header[len(MAGIC):len(MAGIC) + 4]

    if magic != MAGIC:
        print("[!] Magic không hợp lệ")
        print(f"[DEBUG] Magic đọc được: {magic}")
        print("[!] Có thể video bị nén lại hoặc extractor đang lệch bit")
        cap.release()
        return

    msg_len = int.from_bytes(msg_len_bytes, "big")
    msg_bits_needed = msg_len * 8

    print(f"[*] Message length: {msg_len} bytes")

    # Đọc message
    msg_bits = read_n_bits(bit_gen, msg_bits_needed)

    cap.release()

    if len(msg_bits) < msg_bits_needed:
        print("[!] Không đọc đủ message")
        return

    secret_data = bits_to_bytes(msg_bits)

    try:
        secret_text = secret_data.decode("utf-8")
    except UnicodeDecodeError:
        secret_text = secret_data.decode("utf-8", errors="replace")

    print("===== SECRET MESSAGE =====")
    print(secret_text)
    print("==========================")


if __name__ == "__main__":
    main()