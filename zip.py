import os
from io import BytesIO
from PIL import Image

TARGET_SIZE = 1 * 1024 * 512  # 目标大小：1MB
MIN_QUALITY = 20               # 有损最低质量
QUALITY_STEP = 5
DOWNSCALE_RATIO = 0.9          # 每轮等比缩小 90%
ALLOW_PNG_TO_WEBP = True       # 允许 PNG（含透明）转为 WebP（保留透明，更好压缩）

def has_alpha(img: Image.Image) -> bool:
    # 判断是否带透明通道
    return ("A" in img.getbands()) or (img.mode in ("LA", "RGBA", "PA"))

def _try_save_to_bytes(img: Image.Image, fmt: str, **save_kwargs) -> bytes:
    """不落盘，先存内存看大小，避免重复写盘降质"""
    buf = BytesIO()
    img.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()

def _progressive_compress(img: Image.Image, fmt: str, quality_first=True, **kwargs) -> bytes:
    """
    先尝试调质量，达不到再按比例缩图；返回最终字节内容（不写盘）
    kwargs 会传给 PIL 的 save，比如 optimize, lossless, method 等
    """
    work = img.copy()
    quality = 95 if quality_first else kwargs.pop("quality", 95)

    while True:
        # 1) 降质量（仅当 fmt 支持 quality）
        q_iter = quality
        while "quality" in Image.SAVE.keys(fmt.upper()) if hasattr(Image, "SAVE") else fmt.lower() in ("jpeg", "webp"):
            data = _try_save_to_bytes(work, fmt, quality=q_iter, **kwargs)
            if len(data) <= TARGET_SIZE or q_iter <= MIN_QUALITY:
                if len(data) <= TARGET_SIZE:
                    return data
                break
            q_iter -= QUALITY_STEP

        # 2) 缩小分辨率
        w, h = work.size
        new_size = (max(1, int(w * DOWNSCALE_RATIO)), max(1, int(h * DOWNSCALE_RATIO)))
        if new_size == work.size:
            # 已无法再缩
            return _try_save_to_bytes(work, fmt, quality=max(MIN_QUALITY, q_iter), **kwargs)
        work = work.resize(new_size, Image.LANCZOS)
        # 回到降质量循环继续尝试（循环直到满足或尺寸太小）

def compress_image(file_path):
    """压缩单张图片到 <= 1MB，保持比例，保留透明（必要时可转 WebP）"""
    try:
        img = Image.open(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".jpg", ".jpeg"):
            # JPEG 不支持透明：直接按质量→缩放
            data = _progressive_compress(
                img.convert("RGB"),
                fmt="JPEG",
                optimize=True,
            )
            with open(file_path, "wb") as f:
                f.write(data)
            return

        if ext == ".png":
            if has_alpha(img):
                # 先尽力用 PNG（无损）压缩 + 缩放（保持透明）
                # 注：PNG 不支持“quality”，只能靠 optimize 和缩放
                work = img.copy()
                # 先试仅 optimize，不缩放
                data = _try_save_to_bytes(work, "PNG", optimize=True, compress_level=9)
                if len(data) <= TARGET_SIZE:
                    with open(file_path, "wb") as f:
                        f.write(data)
                    return

                # 需要进一步缩放（保持透明）
                while True:
                    w, h = work.size
                    new_size = (max(1, int(w * DOWNSCALE_RATIO)), max(1, int(h * DOWNSCALE_RATIO)))
                    if new_size == work.size:
                        break
                    work = work.resize(new_size, Image.LANCZOS)
                    data = _try_save_to_bytes(work, "PNG", optimize=True, compress_level=9)
                    if len(data) <= TARGET_SIZE:
                        with open(file_path, "wb") as f:
                            f.write(data)
                        return

                # 还不够小，考虑转 WebP（支持透明，压缩率高）
                if ALLOW_PNG_TO_WEBP:
                    webp_path = os.path.splitext(file_path)[0] + ".webp"
                    data = _progressive_compress(
                        img,  # 保留 RGBA
                        fmt="WEBP",
                        quality_first=True,
                        method=6,       # 压缩更充分
                        lossless=False, # 有损更容易达标；若想尽量无损可先试 lossless=True
                    )
                    with open(webp_path, "wb") as f:
                        f.write(data)
                    # 可选：删除原 PNG
                    os.remove(file_path)
                    print(f"已转换为带透明的 WebP：{webp_path}")
                    return
                else:
                    # 不允许改格式，只能接受更小分辨率的 PNG
                    with open(file_path, "wb") as f:
                        f.write(data)  # 写入最后一次 PNG 结果（可能仍略大）
                    return
            else:
                # PNG 无透明：可以安全转为 JPEG（体积通常更小）
                data = _progressive_compress(
                    img.convert("RGB"),
                    fmt="JPEG",
                    optimize=True,
                )
                new_path = os.path.splitext(file_path)[0] + ".jpg"
                with open(new_path, "wb") as f:
                    f.write(data)
                os.remove(file_path)
                print(f"无透明 PNG 已转 JPEG：{new_path}")
                return

        if ext == ".webp":
            # WebP：保持原格式，质量→缩放
            data = _progressive_compress(
                img,
                fmt="WEBP",
                quality_first=True,
                method=6,
            )
            with open(file_path, "wb") as f:
                f.write(data)
            return

        # 其他格式：尽量按原格式处理；若失败，退化到 JPEG（会失去透明）
        try:
            data = _progressive_compress(img, fmt=img.format or "PNG", optimize=True)
            with open(file_path, "wb") as f:
                f.write(data)
        except Exception:
            data = _progressive_compress(img.convert("RGB"), fmt="JPEG", optimize=True)
            with open(os.path.splitext(file_path)[0] + ".jpg", "wb") as f:
                f.write(data)

    except Exception as e:
        print(f"压缩 {file_path} 失败: {e}")

def process_folder(folder):
    """递归处理文件夹下的所有 jpg/png/webp"""
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                file_path = os.path.join(root, f)
                size = os.path.getsize(file_path)
                if size > TARGET_SIZE:
                    print(f"正在压缩: {file_path}, 原始大小: {size/1024/1024:.2f} MB")
                    compress_image(file_path)
                    if os.path.exists(file_path):
                        new_size = os.path.getsize(file_path)
                        print(f"压缩后大小: {new_size/1024/1024:.2f} MB\n")
                    else:
                        # 可能改成了 .webp 或 .jpg
                        base = os.path.splitext(file_path)[0]
                        for ext in (".webp", ".jpg", ".jpeg", ".png"):
                            p = base + ext
                            if os.path.exists(p):
                                new_size = os.path.getsize(p)
                                print(f"压缩后文件: {p}, 大小: {new_size/1024/1024:.2f} MB\n")
                                break

if __name__ == "__main__":
    process_folder(".")
