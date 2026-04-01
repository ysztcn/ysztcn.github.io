import os
import json

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(current_dir, 'tv.json')

# === 1. 读取 JSON 文件 ===
try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"❌ 未找到 data.json 文件: {json_path}")
    exit(1)
except json.JSONDecodeError as e:
    print(f"❌ JSON 格式错误: {e}")
    exit(1)

# === 2. 提取 sites 列表 ===
sites = data.get('sites') or data.get('site') or []
if not isinstance(sites, list):
    sites = []

# === 3. 只提取 name 字段 ===
names = []
for site in sites:
    if isinstance(site, dict) and 'name' in site:
        names.append(str(site['name']).strip())

# === 4. 打印每个 name（一行一个）===
print("🔍 提取到的站点名称：")
for name in names:
    print(name)

# === 5. 保存为纯文本（推荐用于简单列表）===
output_txt = os.path.join(current_dir, 'site_names.txt')
with open(output_txt, 'w', encoding='utf-8') as f:
    f.write('\n'.join(names))

# === 6. 输出提示 ===
print(f"\n✅ 成功提取 {len(names)} 个站点名称")
print(f"📄 纯文本已保存至: {os.path.abspath(output_txt)}")