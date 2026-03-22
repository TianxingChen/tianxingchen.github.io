from PIL import Image
import numpy as np


def rgb_to_gray(rgb):
    """
    将 RGB 转为灰度亮度值
    """
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def estimate_background_color(img_rgba):
    """
    用四个角的像素估计背景色
    适合大多数背景较统一的 logo 图
    """
    h, w, _ = img_rgba.shape
    corners = np.array([
        img_rgba[0, 0, :3],
        img_rgba[0, w - 1, :3],
        img_rgba[h - 1, 0, :3],
        img_rgba[h - 1, w - 1, :3],
    ], dtype=np.float32)
    bg_color = np.mean(corners, axis=0)
    return bg_color


def logo_to_black_white_keep_bg(
    input_path,
    output_path,
    mode="gray",              # "gray" 或 "bw"
    bg_tolerance=35,          # 越大越容易认为是背景
    contrast=1.4,             # 前景对比度增强
    gray_levels=None          # e.g. [0, 80, 170, 255]，None 表示连续灰度
):
    """
    背景保持不变，logo 转成黑白/灰阶
    
    参数说明：
    - mode="gray"：保留灰度
    - mode="bw"：纯黑白
    - bg_tolerance：背景色容忍阈值
    - contrast：前景灰度对比增强
    - gray_levels：离散灰度级，可做更设计感的中间色
    """
    img = Image.open(input_path).convert("RGBA")
    arr = np.array(img).astype(np.float32)

    rgb = arr[..., :3]
    alpha = arr[..., 3]

    # 估计背景色
    bg_color = estimate_background_color(arr)

    # 计算每个像素和背景色的距离
    dist = np.linalg.norm(rgb - bg_color[None, None, :], axis=2)

    # 透明区域也视为背景，不做改动
    bg_mask = (dist < bg_tolerance) | (alpha == 0)
    fg_mask = ~bg_mask

    result = arr.copy()

    # 前景转灰度
    gray = rgb_to_gray(rgb)

    # 只对前景做归一化增强
    if np.any(fg_mask):
        fg_gray = gray[fg_mask]

        gmin = fg_gray.min()
        gmax = fg_gray.max()

        if gmax > gmin:
            norm = (gray - gmin) / (gmax - gmin)
        else:
            norm = gray / 255.0

        # 对比度增强，中心在 0.5
        norm = (norm - 0.5) * contrast + 0.5
        norm = np.clip(norm, 0, 1)

        if mode == "bw":
            out_gray = (norm > 0.5).astype(np.float32) * 255.0
        else:
            out_gray = norm * 255.0
            if gray_levels is not None and len(gray_levels) > 0:
                levels = np.array(gray_levels, dtype=np.float32)
                out_gray = levels[np.argmin(np.abs(out_gray[..., None] - levels), axis=-1)]

        # 前景替换为黑白灰，背景不动
        result[..., 0][fg_mask] = out_gray[fg_mask]
        result[..., 1][fg_mask] = out_gray[fg_mask]
        result[..., 2][fg_mask] = out_gray[fg_mask]

    result = np.clip(result, 0, 255).astype(np.uint8)
    Image.fromarray(result, mode="RGBA").save(output_path)
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    # 示例 1：保留高级灰
    logo_to_black_white_keep_bg(
        input_path="/Users/tianxingchen/Downloads/academic-homepage 3/assets/files/institute/szu.jpg",
        output_path="output_gray.png",
        mode="gray",
        bg_tolerance=35,
        contrast=1.5,
        gray_levels=[0, 90, 170, 255]   # 可改成 None 获取连续灰度
    )

    # 示例 2：纯黑白
    # logo_to_black_white_keep_bg(
    #     input_path="input.png",
    #     output_path="output_bw.png",
    #     mode="bw",
    #     bg_tolerance=35,
    #     contrast=1.5
    # )