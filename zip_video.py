import os
import subprocess
from PIL import Image

# 目标大小 (3MB)
TARGET_SIZE = 3 * 1024 * 1024  

def compress_video(file_path):
    """使用 ffmpeg 压缩 mp4，直到小于目标大小"""
    tmp_path = file_path + ".tmp.mp4"
    crf = 28  # 初始压缩参数
    while True:
        subprocess.run([
            "ffmpeg", "-i", file_path,
            "-vcodec", "libx264", "-crf", str(crf), "-preset", "veryfast",
            "-acodec", "aac", "-b:a", "96k", tmp_path, "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if os.path.getsize(tmp_path) <= TARGET_SIZE or crf >= 40:
            os.replace(tmp_path, file_path)  # 覆盖原文件
            print(f"✅ 视频压缩完成: {file_path}, 新大小: {os.path.getsize(file_path)/1024/1024:.2f}MB")
            break
        else:
            crf += 2  # 增加压缩力度

def compress_gif(file_path):
    """使用 Pillow 压缩 GIF，直到小于目标大小"""
    tmp_path = file_path + ".tmp.gif"
    quality = 80  # 初始质量
    while True:
        with Image.open(file_path) as im:
            im.save(tmp_path, save_all=True, optimize=True, quality=quality)

        if os.path.getsize(tmp_path) <= TARGET_SIZE or quality <= 10:
            os.replace(tmp_path, file_path)  # 覆盖原文件
            print(f"✅ GIF压缩完成: {file_path}, 新大小: {os.path.getsize(file_path)/1024/1024:.2f}MB")
            break
        else:
            quality -= 10  # 逐步降低质量

def scan_and_compress(root_dir):
    """递归查找并压缩文件"""
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if filename.lower().endswith(".mp4") or filename.lower().endswith(".gif"):
                size = os.path.getsize(file_path)
                if size > TARGET_SIZE:
                    print(f"发现大文件: {file_path}, 大小: {size/1024/1024:.2f}MB")
                    if filename.lower().endswith(".mp4"):
                        compress_video(file_path)
                    elif filename.lower().endswith(".gif"):
                        compress_gif(file_path)

if __name__ == "__main__":
    scan_and_compress(".")  # 当前目录递归扫描
