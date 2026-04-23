# coding=utf-8
#!/usr/bin/python
import os
import json

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(current_dir, 'wang.json')

# 读取 JSON 文件
try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print("错误：未找到 wang.json 文件")
    exit(1)
except json.JSONDecodeError as e:
    print(f"错误：JSON 格式错误 - {e}")
    exit(1)

# 提取 sites 列表
sites = data.get('sites') 

# 提取 key 和 name 字段
key_name_pairs = []
for site in sites:
    if isinstance(site, dict):
        name = site.get('name', '').strip()
        api = site.get('api', '').strip()
        key_name_pairs.append(f"{api}-----{name}-----")

# 保存为纯文本
output_txt = os.path.join(current_dir, 'site_names.txt')
with open(output_txt, 'w', encoding='utf-8') as f:
    f.write('\n'.join(key_name_pairs))

# 打印每个 key:name 对（一行一个）
print("提取到的站点信息：")
for pair in key_name_pairs:
    print(pair)

# 输出提示
print(f"\n成功提取 {len(key_name_pairs)} 个站点信息")
print(f"纯文本已保存至: {os.path.abspath(output_txt)}")