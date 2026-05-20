# Giau tin video bang DC/AC temporal drift

## Muc dich

Bai thuc hanh giup sinh vien hieu va ap dung ky thuat giau tin trong video dua tren quan he he so DCT giua hai frame lien tiep. Sinh vien se xem thong so video bang `ffmpeg`, chay chuong trinh Python de nhung thong diep, sau do tach lai thong diep tu video da duoc tao.

Ky thuat chinh cua bai nay la `DC/AC temporal drift`: mot bit duoc bieu dien bang do lech co chu dich cua he so DC giua hai frame lien tiep, ket hop voi quan he AC trong tung block 8x8.

## Yeu cau doi voi sinh vien

Sinh vien can nam cac noi dung sau:

(1) Khai niem co ban ve giau tin trong video.

(2) Khai niem block 8x8 va bien doi DCT.

(3) Y nghia cua he so DC va he so AC trong mien tan so.

(4) Ly do video dau ra can dung codec lossless khi tach tin phu thuoc vao he so DCT.

(5) Cach doc va chay code Python su dung OpenCV.

## Cau hinh bai lab

Bai lab gom 1 container. Trong container co cac file:

- `input.mp4`: video goc.
- `secret.txt`: thong diep bi mat.
- `tao_tin.py`: chuong trinh nhung tin bang DC/AC temporal drift.
- `tach_tin.py`: chuong trinh tach tin tu video da nhung.

Moi truong da cai san:

- Python 3.
- OpenCV.
- NumPy.
- ffmpeg.
- nano.

## Chuan bi moi truong

Tren terminal cua may Labtainer, vao thu muc:

```bash
cd /home/student/labtainer/labtainer-student
```

Tai bai lab:

```bash
imodule https://github.com/minhtamcoc/dcac-temporal-drift-embed/raw/main/dcac-temporal-drift-embed.tar.gz
```

Khoi tao bai lab:

```bash
labtainer dcac-temporal-drift-embed
```

Khi duoc hoi e-mail, sinh vien nhap ma sinh vien cua minh.

## Cac nhiem vu can thuc hien

### Task 1: Xem thong so ky thuat cua video

Muc tieu: xac dinh do phan giai, so frame, fps, codec va thoi luong cua video.

Thuc hien lenh:

```bash
ffmpeg -hide_banner -i input.mp4
```

Ghi lai cac thong so quan trong de doi chieu voi gia tri chuong trinh doc bang OpenCV.

### Task 2: Doc va chay chuong trinh giau tin

Xem thong diep can giau:

```bash
cat secret.txt
```

Mo file `tao_tin.py`:

```bash
nano tao_tin.py
```

Trong file nay can chu y:

- `BLOCK = 8`: kich thuoc block DCT.
- `DC_MARGIN`: do lech toi thieu cua DC giua hai frame.
- `AC_MARGIN`: do lech toi thieu cua hai he so AC trong block.
- `MAGIC = b"DCACSTEG"`: dau hieu nhan dien du lieu da nhung.
- `VIDEO_OUT = "output.avi"`: video dau ra.

Chay chuong trinh giau tin:

```bash
python3 tao_tin.py
```

Khi thanh cong, chuong trinh se hien:

```text
DONE EMBED
Output: output.avi
```

### Task 3: Kiem tra video da nhung tin

Kiem tra file `output.avi`:

```bash
ls -lh output.avi
```

Xem thong so cua video dau ra:

```bash
ffmpeg -hide_banner -i output.avi
```

Trong bai nay, video dau ra duoc ghi o dang grayscale lossless bang FFV1. Khong nen nen lai bang codec lossy vi co the lam sai he so DCT.

### Task 4: Tach lai thong diep bi mat

Mo file `tach_tin.py`:

```bash
nano tach_tin.py
```

Trong file tach tin, chu y:

- Chuong trinh doc video theo tung cap frame.
- Moi cap frame duoc chia thanh cac block 8x8.
- Bit duoc doc lai tu quan he DC lien frame va AC trong block.
- Header gom `MAGIC` va do dai thong diep.

Chay chuong trinh tach tin:

```bash
python3 tach_tin.py
```

Neu tach thanh cong, chuong trinh se in ra thong diep bi mat trong `secret.txt`.

## Kiem tra bai lam

Chay lenh:

```bash
checkwork
```

Bai lab co 4 muc cham:

- `cw1`: da xem thong so video bang `ffmpeg`.
- `cw2`: da chay `python3 tao_tin.py` va tao qua trinh nhung tin.
- `cw3`: da tao file `output.avi`.
- `cw4`: da chay `python3 tach_tin.py` va tach duoc thong diep.

## Ket thuc bai lab

```bash
stoplab dcac-temporal-drift-embed
```

## Khoi dong lai bai lab

```bash
labtainer -r dcac-temporal-drift-embed
```
