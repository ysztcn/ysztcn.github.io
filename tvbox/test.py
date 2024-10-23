import json

# 假设你的JSON文件名为'config.json'
filename = 'C:\\Users\\dingyong\\Documents\\leidian9\\Pictures\\tvbox\\ysztcn\\config.json'
# 打开文件并读取内容
with open(filename, 'r', encoding='utf-8') as f:
    data = f.read()

# 解析JSON数据
config = json.loads(data)

# 提取sites列表
sites = config.get('sites', [])

# 遍历sites列表并打印每个网站的name
for site in sites:
    print(site.get('name', 'Unknown Site Name'))
