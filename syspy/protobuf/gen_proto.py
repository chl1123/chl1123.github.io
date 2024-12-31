# 要生成pythonic的proto列表
import os
import re

protos = [
    "message_header",
    "message_bin",
    "message_depthcamera",
    "message_laser",
    "message_battery",
    "message_controller",
    "message_io",
    "CanFrame",
    "message_distancesensor",

    "message_motorinfos",
    "message_odometer",

    "message_movetask",
    "message_localization",
    "message_magnetic",
    "message_navigation",


    "message_pgv",
    "message_rfid",
    "message_sound"
]

def fix_default_value(proto_name):
    # 打开生成的文件
    # 读取文件内容
    with open(f'./messsage/{proto_name}_p2p.py', 'r') as file:
        lines = file.readlines()

    # 定义替换模式
    pattern_field = re.compile(r':\s*(\w+)\s*=\s*Field\(\)')
    replacement_field = r': typing.Optional[\1] = None'

    # 新增替换模式
    pattern_none = re.compile(r'\bNone\s*=\s*(\S+)')
    replacement_none = r'NONE = \1'

    modified_lines = []
    updated_lines = []
    # 进行替换
    for i, line in enumerate(lines):
        new_line = line
        if pattern_field.search(line):
            new_line = pattern_field.sub(replacement_field, line)
        if pattern_none.search(line):
            new_line = pattern_none.sub(replacement_none, new_line)
        if new_line != line:
            modified_lines.append((i + 1, line.strip(), new_line.strip()))
        updated_lines.append(new_line)
    # 打印所有修改的部分
    for line_number, old_line, new_line in modified_lines:
        print(f"Modified line {line_number}: {old_line} -> {new_line}")

    # 写回文件
    with open(f'./messsage/{proto_name}_p2p.py', 'w') as file:
        file.writelines(updated_lines)


def main():
    # 执行python命令
    for proto_name in protos:
        print(f"sudo python3 -m grpc_tools.protoc -I./proto --protobuf-to-pydantic_out=./messsage {proto_name}.proto")
        os.system(
            f"sudo python3 -m grpc_tools.protoc -I./proto --protobuf-to-pydantic_out=./messsage {proto_name}.proto")
        print(f"gen {proto_name} pythonic proto success")
        fix_default_value(proto_name)
        print()


if __name__ == '__main__':
    main()