import cv2
import numpy as np
import os

# ==================================================
# CONFIG
# ==================================================
VIDEO_IN = "input.mp4"
VIDEO_OUT = "output.avi"
SECRET_FILE = "secret.txt"

BLOCK = 8

# Độ mạnh nhúng
DC_MARGIN = 80.0
AC_MARGIN = 35.0

MAGIC = b"DCACSTEG"


# ==================================================
# BYTES <-> BITS
# ==================================================
def bytes_to_bits(data: bytes) -> str:
    bits = ""

    for b in data:
        bits += format(b, "08b")

    return bits


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
# DC TEMPORAL EMBED
# ==================================================
def embed_dc_temporal(dct1, dct2, bit):
    """
    Nhúng bit bằng quan hệ DC giữa 2 frame liên tiếp.

    bit = 1:
        DC2 - DC1 >= DC_MARGIN

    bit = 0:
        DC2 - DC1 <= -DC_MARGIN

    Drift balancing:
        chỉnh DC1 và DC2 ngược chiều nhau,
        giữ trung bình độ sáng gần như không đổi.
    """

    dc1 = dct1[0, 0]
    dc2 = dct2[0, 0]

    diff = dc2 - dc1

    if bit == "1":
        if diff < DC_MARGIN:
            delta = (DC_MARGIN - diff) / 2.0
            dct2[0, 0] += delta
            dct1[0, 0] -= delta

    else:
        if diff > -DC_MARGIN:
            delta = (diff + DC_MARGIN) / 2.0
            dct2[0, 0] -= delta
            dct1[0, 0] += delta

    return dct1, dct2


# ==================================================
# AC INTRA-FRAME EMBED
# ==================================================
def embed_ac_intra(dct, bit):
    """
    Nhúng bit bằng quan hệ 2 hệ số AC trong cùng block.

    Chọn 2 hệ số trung tần:
        AC1 = DCT[2, 3]
        AC2 = DCT[3, 2]

    bit = 1:
        AC1 - AC2 >= AC_MARGIN

    bit = 0:
        AC2 - AC1 >= AC_MARGIN

    Drift balancing nội frame:
        tăng hệ số này thì giảm hệ số kia,
        giữ tổng năng lượng lệch nhỏ hơn.
    """

    ac1 = dct[2, 3]
    ac2 = dct[3, 2]

    diff = ac1 - ac2

    if bit == "1":
        if diff < AC_MARGIN:
            delta = (AC_MARGIN - diff) / 2.0
            dct[2, 3] += delta
            dct[3, 2] -= delta

    else:
        if diff > -AC_MARGIN:
            delta = (diff + AC_MARGIN) / 2.0
            dct[2, 3] -= delta
            dct[3, 2] += delta

    return dct


# ==================================================
# EMBED 1 BIT INTO 1 BLOCK PAIR
# ==================================================
def embed_bit_into_block_pair(block1, block2, bit):
    """
    block1: block tại frame t
    block2: block tại frame t+1

    Một bit được nhúng bằng cả:
        - DC liên frame
        - AC nội frame ở frame t
        - AC nội frame ở frame t+1

    Khi tách tin sẽ vote 3 nguồn:
        - DC temporal
        - AC frame t
        - AC frame t+1
    """

    dct1 = cv2.dct(np.float32(block1))
    dct2 = cv2.dct(np.float32(block2))

    # 1. Nhúng DC liên frame
    dct1, dct2 = embed_dc_temporal(dct1, dct2, bit)

    # 2. Nhúng AC nội frame trên cả 2 frame
    dct1 = embed_ac_intra(dct1, bit)
    dct2 = embed_ac_intra(dct2, bit)

    # IDCT
    new_block1 = cv2.idct(dct1)
    new_block2 = cv2.idct(dct2)

    new_block1 = np.clip(new_block1, 0, 255).astype(np.uint8)
    new_block2 = np.clip(new_block2, 0, 255).astype(np.uint8)

    return new_block1, new_block2


# ==================================================
# MAIN EMBED
# ==================================================
def main():
    if not os.path.exists(VIDEO_IN):
        print(f"[!] Không thấy video input: {VIDEO_IN}")
        return

    if not os.path.exists(SECRET_FILE):
        print(f"[!] Không thấy file secret: {SECRET_FILE}")
        return

    with open(SECRET_FILE, "rb") as f:
        secret_data = f.read()

    # Payload format:
    # MAGIC 8 bytes + LENGTH 4 bytes + SECRET DATA
    payload = MAGIC + len(secret_data).to_bytes(4, "big") + secret_data
    payload_bits = bytes_to_bits(payload)

    cap = cv2.VideoCapture(VIDEO_IN)

    if not cap.isOpened():
        print("[!] Không mở được video input")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    positions = get_block_positions(h, w)
    blocks_per_pair = len(positions)
    frame_pairs = total_frames // 2

    capacity_bits = blocks_per_pair * frame_pairs

    print(f"[*] Video: {w}x{h}, frames={total_frames}, fps={fps}")
    print(f"[*] Block size: {BLOCK}x{BLOCK}")
    print(f"[*] Blocks per frame pair: {blocks_per_pair}")
    print(f"[*] Frame pairs: {frame_pairs}")
    print(f"[*] Capacity: {capacity_bits} bits / {capacity_bits // 8} bytes")
    print(f"[*] Payload: {len(payload_bits)} bits / {len(payload)} bytes")

    if len(payload_bits) > capacity_bits:
        print("[!] Secret quá dài, video không đủ capacity")
        cap.release()
        return

    # Ghi grayscale video lossless.
    # Không dùng XVID/mp4 vì codec nén sẽ phá hệ số DCT.
    fourcc = cv2.VideoWriter_fourcc(*"FFV1")
    out = cv2.VideoWriter(VIDEO_OUT, fourcc, fps, (w, h), False)

    if not out.isOpened():
        print("[!] Không tạo được output với codec FFV1")
        print("[!] Thử đổi VIDEO_OUT = 'output.mkv' rồi chạy lại")
        cap.release()
        return

    bit_idx = 0
    frame_idx = 0

    while True:
        ret1, frame1 = cap.read()

        if not ret1:
            break

        ret2, frame2 = cap.read()

        if not ret2:
            # Nếu còn lẻ 1 frame cuối thì ghi nguyên frame đó dạng gray
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            out.write(gray1)
            break

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Nhúng trên từng block của cặp frame
        for y, x in positions:
            if bit_idx >= len(payload_bits):
                break

            bit = payload_bits[bit_idx]

            block1 = gray1[y:y + BLOCK, x:x + BLOCK]
            block2 = gray2[y:y + BLOCK, x:x + BLOCK]

            new_block1, new_block2 = embed_bit_into_block_pair(block1, block2, bit)

            gray1[y:y + BLOCK, x:x + BLOCK] = new_block1
            gray2[y:y + BLOCK, x:x + BLOCK] = new_block2

            bit_idx += 1

        out.write(gray1)
        out.write(gray2)

        frame_idx += 2

        # Nếu đã nhúng xong thì copy phần còn lại, không cần xử lý DCT nữa
        if bit_idx >= len(payload_bits):
            while True:
                ret, frame = cap.read()

                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                out.write(gray)

            break

    cap.release()
    out.release()

    print("[+] DONE EMBED")
    print(f"[+] Đã nhúng {bit_idx} bits")
    print(f"[+] Output: {VIDEO_OUT}")


if __name__ == "__main__":
    main()