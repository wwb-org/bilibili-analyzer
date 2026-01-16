"""
B站热门视频封面爬取与斜向网格背景生成脚本

功能：
1. 爬取B站热门视频封面
2. 将封面图片倾斜拼接成网格背景
3. 生成登录页面背景图片
"""

import os
import asyncio
import aiohttp
import math
from PIL import Image
from io import BytesIO
from typing import List, Tuple

# 配置参数
CONFIG = {
    "cover_count": 100,
    "thumb_width": 280,
    "cols": 10,
    "gap": 8,
    "output_width": 2560,
    "output_height": 1440,
    "overlay_opacity": 0.45,
    "output_dir": "../frontend/public",
    "output_filename": "login-bg.jpg",
    "cache_dir": "./cover_cache",
}


async def fetch_popular_videos(count: int = 60) -> List[dict]:
    """获取B站热门视频列表"""
    videos = []
    page = 1
    page_size = 20

    async with aiohttp.ClientSession() as session:
        while len(videos) < count:
            url = "https://api.bilibili.com/x/web-interface/popular"
            params = {"ps": page_size, "pn": page}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com"
            }

            try:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data["code"] == 0:
                            for video in data["data"]["list"]:
                                videos.append({
                                    "bvid": video["bvid"],
                                    "title": video["title"],
                                    "cover": video["pic"]
                                })
                                if len(videos) >= count:
                                    break
                        else:
                            print(f"API error: {data['message']}")
                            break
            except Exception as e:
                print(f"Error fetching videos: {e}")
                break

            page += 1
            await asyncio.sleep(0.5)

    print(f"Fetched {len(videos)} videos")
    return videos


async def download_cover(session: aiohttp.ClientSession, url: str, index: int) -> Tuple[int, bytes]:
    """下载单个封面图片"""
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("http://"):
        url = url.replace("http://", "https://")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com"
    }

    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                return (index, await resp.read())
    except Exception as e:
        print(f"Download cover {index} failed: {e}")

    return (index, None)


async def download_all_covers(videos: List[dict]) -> List[Image.Image]:
    """并发下载所有封面图片"""
    images = [None] * len(videos)
    cache_dir = CONFIG["cache_dir"]
    os.makedirs(cache_dir, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, video in enumerate(videos):
            cache_path = os.path.join(cache_dir, f"{video['bvid']}.jpg")
            if os.path.exists(cache_path):
                try:
                    img = Image.open(cache_path)
                    images[i] = img.copy()
                    img.close()
                    continue
                except:
                    pass
            tasks.append(download_cover(session, video["cover"], i))

        if tasks:
            print(f"Downloading {len(tasks)} covers...")
            results = await asyncio.gather(*tasks)

            for index, data in results:
                if data:
                    try:
                        img = Image.open(BytesIO(data))
                        images[index] = img
                        cache_path = os.path.join(cache_dir, f"{videos[index]['bvid']}.jpg")
                        img.save(cache_path, "JPEG", quality=85)
                    except Exception as e:
                        print(f"Process image {index} failed: {e}")

    valid_images = [img for img in images if img is not None]
    print(f"Got {len(valid_images)} cover images")
    return valid_images


def create_waterfall_background(images: List[Image.Image]) -> Image.Image:
    """创建瀑布流风格背景"""
    import random

    thumb_w = CONFIG["thumb_width"]
    cols = CONFIG["cols"]
    gap = CONFIG["gap"]
    output_w = CONFIG["output_width"]
    output_h = CONFIG["output_height"]

    # 计算每列宽度和起始位置
    total_width = cols * thumb_w + (cols - 1) * gap
    start_x = (output_w - total_width) // 2

    # 创建画布
    canvas = Image.new("RGB", (output_w, output_h), (18, 18, 18))

    # 每列的当前高度
    col_heights = [0] * cols

    # 随机打乱图片顺序
    shuffled = images.copy()
    random.shuffle(shuffled)

    # 循环填充直到所有列都超过画布高度
    img_index = 0
    while min(col_heights) < output_h + 500:
        # 找到最短的列
        min_col = col_heights.index(min(col_heights))

        img = shuffled[img_index % len(shuffled)]

        # 保持原始宽高比，随机高度变化
        orig_w, orig_h = img.size
        ratio = thumb_w / orig_w
        new_h = int(orig_h * ratio * random.uniform(0.9, 1.1))

        resized = img.resize((thumb_w, new_h), Image.Resampling.LANCZOS)

        x = start_x + min_col * (thumb_w + gap)
        y = col_heights[min_col]

        if y < output_h + 200:
            canvas.paste(resized, (x, y))

        col_heights[min_col] += new_h + gap
        img_index += 1

    # 添加黑色遮罩层
    overlay = Image.new("RGBA", (output_w, output_h),
                        (0, 0, 0, int(255 * CONFIG["overlay_opacity"])))
    canvas = canvas.convert("RGBA")
    canvas = Image.alpha_composite(canvas, overlay)
    canvas = canvas.convert("RGB")

    return canvas


def save_output(image: Image.Image):
    """保存输出图片"""
    output_dir = CONFIG["output_dir"]
    output_path = os.path.join(output_dir, CONFIG["output_filename"])
    os.makedirs(output_dir, exist_ok=True)
    image.save(output_path, "JPEG", quality=90)
    print(f"Background saved to: {output_path}")
    return output_path


async def main():
    """主函数"""
    print("=" * 50)
    print("Bilibili Cover Background Generator")
    print("=" * 50)

    print("\n[1/4] Fetching popular videos...")
    videos = await fetch_popular_videos(CONFIG["cover_count"])

    if not videos:
        print("Failed to fetch videos")
        return

    print("\n[2/4] Downloading covers...")
    images = await download_all_covers(videos)

    if len(images) < 10:
        print("Not enough images")
        return

    print("\n[3/4] Creating waterfall background...")
    background = create_waterfall_background(images)

    print("\n[4/4] Saving background...")
    output_path = save_output(background)

    print("\n" + "=" * 50)
    print("Done!")
    print(f"Output: {output_path}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
