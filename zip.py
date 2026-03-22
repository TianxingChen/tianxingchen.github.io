import os
from io import BytesIO
from PIL import Image, ImageOps

# ================== 全局参数 ==================
TARGET_SIZE = 1 * 1024 * 1024  # 目标大小：1MB
MIN_QUALITY = 20               # 最低质量（有损）
QUALITY_STEP = 5               # 每次降低的质量步长
DOWNSCALE_RATIO = 0.9          # 每轮等比缩小比例
ALLOW_PNG_TO_WEBP = True       # 允许带透明 PNG 转为 WebP（保留透明）

# ================== 工具函数 ==================
def has_alpha(img: Image.Image) -> bool:
    """判断是否带透明通道"""
    return ("A" in img.getbands()) or (img.mode in ("LA", "RGBA", "PA"))

def _try_save_to_bytes(img: Image.Image, fmt: str, **save_kwargs) -> bytes:
    """不落盘，先存到内存看大小，避免反复写盘"""
    buf = BytesIO()
    img.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()

def _format_supports_quality(fmt: str) -> bool:
    """格式是否支持 quality 参数（Pillow 常见）"""
    fmt = (fmt or "").lower()
    return fmt in ("jpeg", "jpg", "webp", "avif", "heif", "heic", "jxl")

def _progressive_compress(
    img: Image.Image,
    fmt: str,
    *,
    initial_quality=95,
    min_quality=MIN_QUALITY,
    quality_step=QUALITY_STEP,
    downscale_ratio=DOWNSCALE_RATIO,
    **save_kwargs,
) -> bytes:
    """
    先尝试降质量，若仍超标再按比例缩图；返回最终字节内容（不写盘）
    save_kwargs 直接传给 PIL 的 save，比如 optimize、progressive、method、lossless 等
    """
    work = img.copy()
    fmt_l = (fmt or "").lower()
    supports_quality = _format_supports_quality(fmt_l)

    while True:
        # 1) 降质量（仅当格式支持）
        if supports_quality:
            q = initial_quality
            while True:
                data = _try_save_to_bytes(work, fmt, quality=q, **save_kwargs)
                if len(data) <= TARGET_SIZE or q <= min_quality:
                    if len(data) <= TARGET_SIZE:
                        return data
                    break
                q -= quality_step
        else:
            # 不支持 quality：直接看看当前尺寸存出来是否满足
            data = _try_save_to_bytes(work, fmt, **save_kwargs)
            if len(data) <= TARGET_SIZE:
                return data
            # 否则进入缩放

        # 2) 缩小分辨率后重试
        w, h = work.size
        new_size = (max(1, int(w * downscale_ratio)), max(1, int(h * downscale_ratio)))
        if new_size == work.size or min(new_size) <= 1:
            # 已无法继续缩放；返回当前尽力结果
            if supports_quality:
                q = max(min_quality, 10)
                return _try_save_to_bytes(work, fmt, quality=q, **save_kwargs)
            else:
                return _try_save_to_bytes(work, fmt, **save_kwargs)
        work = work.resize(new_size, Image.LANCZOS)
        # 回到循环顶端：先降质量，再缩放

# ================== 主压缩逻辑 ==================
def compress_image(file_path: str):
    """压缩单张图片到 <= 1MB，保持比例；PNG 透明优先保留，必要时可转 WebP"""
    try:
        img = Image.open(file_path)
        # 处理 EXIF 方向，避免有些手机照片方向错乱
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".jpg", ".jpeg"):
            # JPEG：直接按 质量→缩放
            data = _progressive_compress(
                img.convert("RGB"),
                fmt="JPEG",
                initial_quality=95,
                min_quality=MIN_QUALITY,
                quality_step=QUALITY_STEP,
                downscale_ratio=DOWNSCALE_RATIO,
                optimize=True,
                progressive=True,  # 渐进式 JPEG 更省
            )
            with open(file_path, "wb") as f:
                f.write(data)
            return

        if ext == ".png":
            if has_alpha(img):
                # 透明 PNG：优先用 PNG（无损）+ 缩放，尽量保留透明
                work = img.copy()
                # 先只用 optimize 最大压缩，不缩放
                data = _try_save_to_bytes(work, "PNG", optimize=True, compress_level=9)
                if len(data) <= TARGET_SIZE:
                    with open(file_path, "wb") as f:
                        f.write(data)
                    return

                # 需要进一步缩放（保持透明）
                while True:
                    w, h = work.size
                    new_size = (max(1, int(w * DOWNSCALE_RATIO)), max(1, int(h * DOWNSCALE_RATIO)))
                    if new_size == work.size or min(new_size) <= 1:
                        break
                    work = work.resize(new_size, Image.LANCZOS)
                    data = _try_save_to_bytes(work, "PNG", optimize=True, compress_level=9)
                    if len(data) <= TARGET_SIZE:
                        with open(file_path, "wb") as f:
                            f.write(data)
                        return

                # 还不够小：考虑转 WebP（保留透明，压缩率高）
                if ALLOW_PNG_TO_WEBP:
                    webp_path = os.path.splitext(file_path)[0] + ".webp"
                    data = _progressive_compress(
                        img,  # 保留 RGBA
                        fmt="WEBP",
                        initial_quality=95,
                        min_quality=MIN_QUALITY,
                        quality_step=QUALITY_STEP,
                        downscale_ratio=DOWNSCALE_RATIO,
                        method=6,        # 0-6，越大越省
                        lossless=False,  # 有损更容易达标（仍保透明）
                    )
                    with open(webp_path, "wb") as f:
                        f.write(data)
                    # 删除原 PNG（如果不想删除，可注释掉）
                    os.remove(file_path)
                    print(f"已转换为带透明的 WebP：{webp_path}")
                    return
                else:
                    # 不允许改格式，只能接受更小分辨率的 PNG（可能仍略大）
                    with open(file_path, "wb") as f:
                        f.write(data)
                    return
            else:
                # 无透明 PNG：可安全转为 JPEG（通常体积小很多）
                data = _progressive_compress(
                    img.convert("RGB"),
                    fmt="JPEG",
                    initial_quality=95,
                    min_quality=MIN_QUALITY,
                    quality_step=QUALITY_STEP,
                    downscale_ratio=DOWNSCALE_RATIO,
                    optimize=True,
                    progressive=True,
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
                initial_quality=95,
                min_quality=MIN_QUALITY,
                quality_step=QUALITY_STEP,
                downscale_ratio=DOWNSCALE_RATIO,
                method=6,
            )
            with open(file_path, "wb") as f:
                f.write(data)
            return

        # 其他格式：尽量按原格式处理；若失败，退化到 JPEG（会失去透明）
        try:
            fmt_guess = img.format or "PNG"
            data = _progressive_compress(
                img,
                fmt=fmt_guess,
                initial_quality=95,
                min_quality=MIN_QUALITY,
                quality_step=QUALITY_STEP,
                downscale_ratio=DOWNSCALE_RATIO,
                optimize=True,
            )
            with open(file_path, "wb") as f:
                f.write(data)
        except Exception:
            data = _progressive_compress(
                img.convert("RGB"),
                fmt="JPEG",
                initial_quality=95,
                min_quality=MIN_QUALITY,
                quality_step=QUALITY_STEP,
                downscale_ratio=DOWNSCALE_RATIO,
                optimize=True,
                progressive=True,
            )
            new_path = os.path.splitext(file_path)[0] + ".jpg"
            with open(new_path, "wb") as f:
                f.write(data)
            # 原文件保留（以免误删非图像容器）；如需删除原文件可自行添加 os.remove(file_path)

    except Exception as e:
        print(f"压缩 {file_path} 失败: {e}")

def process_folder(folder: str):
    """递归处理文件夹下的所有 jpg/png/webp"""
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                file_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(file_path)
                except FileNotFoundError:
                    # 可能在前一次循环中被改名/删除
                    continue
                if size > TARGET_SIZE:
                    print(f"正在压缩: {file_path}, 原始大小: {size/1024/1024:.2f} MB")
                    compress_image(file_path)
                    # 可能改了后缀（如 PNG->WEBP / PNG->JPG）
                    base = os.path.splitext(file_path)[0]
                    candidates = [
                        file_path,               # 原路径（若未改名）
                        base + ".webp",
                        base + ".jpg",
                        base + ".jpeg",
                        base + ".png",
                    ]
                    for p in candidates:
                        if os.path.exists(p):
                            new_size = os.path.getsize(p)
                            print(f"压缩后文件: {p}, 大小: {new_size/1024/1024:.2f} MB\n")
                            break

if __name__ == "__main__":
    process_folder(".")
