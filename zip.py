import os
from PIL import Image

TARGET_SIZE = 1 * 1024 * 1024  # 目标大小：1MB

def compress_image(file_path):
    """压缩单张图片到 <= 1MB，保持比例"""
    try:
        img = Image.open(file_path)
        if img.mode in ("RGBA", "P"):  # PNG带透明通道，先转RGB
            img = img.convert("RGB")

        quality = 95
        while True:
            # 先尝试通过降低质量压缩
            img.save(file_path, optimize=True, quality=quality)
            size = os.path.getsize(file_path)
            if size <= TARGET_SIZE or quality <= 20:
                break
            quality -= 5

        # 如果质量已经很低还是 > 1MB，则再缩小分辨率（保持比例）
        while os.path.getsize(file_path) > TARGET_SIZE:
            w, h = img.size
            new_w, new_h = int(w * 0.9), int(h * 0.9)  # 每次缩小 90%
            img = img.resize((new_w, new_h), Image.LANCZOS)
            img.save(file_path, optimize=True, quality=quality)

    except Exception as e:
        print(f"压缩 {file_path} 失败: {e}")

def process_folder(folder):
    """递归处理文件夹下的所有jpg/png"""
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                file_path = os.path.join(root, f)
                size = os.path.getsize(file_path)
                if size > TARGET_SIZE:
                    print(f"正在压缩: {file_path}, 原始大小: {size/1024/1024:.2f} MB")
                    compress_image(file_path)
                    new_size = os.path.getsize(file_path)
                    print(f"压缩后大小: {new_size/1024/1024:.2f} MB\n")

if __name__ == "__main__":
    process_folder(".")  # 从当前文件夹开始递归
