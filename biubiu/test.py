import json
import re
import jsonpath
import requests

'''
这是一个打印出3中接口的站点名和url的应用
'''
 
# 读取带注释 // /* */ 的json文件
def parse_json(filename):
    f = open(filename, 'r', encoding='utf-8')
    lines = []
    for line in f:
        index = line.find('//')  # 查找注释符号的位置
        if index != -1 and line[(index - 1):index] == ":":
            pass  # 判断是否是://，避免删除http://这类信息
        elif index != -1:
            continue  # 忽略该行即去除//的注释
        line = re.sub(r'/\*[\s\S]*?\*/', '', line)  # 去除/*  */的注释
        lines.append(line)
    return json.loads(''.join(lines))


obj = parse_json(filename='zhushou.json')

print("app接口：\n")
url_list = obj.get('zhuyejiekou')
for num in url_list:
    print(num['name'])
    print(num['url'])

print("采集接口：\n")
url_list = obj.get('caijizhan')
for num in url_list:
    print(num['name'])
    print(num['url'])

print("自定义：\n")
url_list = obj.get('zidingyi')
for num in url_list:
    if 'name' in num:
        print(num['name'])
    else:
        print(num['网站名字'])

    if 'url' in num:
        print(num['url'])
    else:
        print(num['网站地址'])

