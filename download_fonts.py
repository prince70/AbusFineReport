import os
import urllib.request
import urllib.error

# 创建fonts目录
fonts_dir = "d:\\Code\\find\\production-query\\assets\\vendor\\fonts"
os.makedirs(fonts_dir, exist_ok=True)

# 字体文件下载列表
fonts = [
    ("https://cdn.jsdelivr.net/npm/element-ui@2.15.13/lib/fonts/element-icons.woff", "element-icons.woff"),
    ("https://cdn.jsdelivr.net/npm/element-ui@2.15.13/lib/fonts/element-icons.ttf", "element-icons.ttf"),
]

for url, filename in fonts:
    filepath = os.path.join(fonts_dir, filename)
    print(f"下载 {filename}...")
    try:
        urllib.request.urlretrieve(url, filepath)
        size = os.path.getsize(filepath)
        print(f"✓ 完成: {filename} ({size} 字节)")
    except Exception as e:
        print(f"✗ 失败: {e}")

print("\n已下载的文件:")
for f in os.listdir(fonts_dir):
    size = os.path.getsize(os.path.join(fonts_dir, f))
    print(f"  {f} ({size} 字节)")
