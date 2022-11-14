cc = [{'container_name': '0', 'desc': '', 'goods_id': '1', 'has_goods': False}, {'container_name': '1', 'desc': '', 'goods_id': '123', 'has_goods': True}, {'container_name': '2', 'desc': 'by script', 'goods_id': 'goods2', 'has_goods': True}]
c = {}
for i in cc:
    c[i['container_name']] = i
print(cc)
print(c)
