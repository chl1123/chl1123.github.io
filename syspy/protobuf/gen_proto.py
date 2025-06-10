import os
import re
import shutil

# 要生成pythonic的proto列表
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
    "message_sound",
    "message_dmx512",
    "message_script",
]


def gen_protobuf():
    out_folder_name = "./message"
    for proto_name in protos:
        command = f"protoc --proto_path=./proto --python_out={out_folder_name} ./proto/{proto_name}.proto"
        print(command)
        os.system(command)
        print(f"gen '{proto_name}' protobuf success")
        print()


def fix_default_value(proto_name):
    # 打开生成的文件
    # 读取文件内容
    with open(f"./new_pb/{proto_name}_p2p.py", "r") as file:
        lines = file.readlines()

    # 替换
    pattern_field = re.compile(r":\s*(\w+)\s*=\s*Field\(\)")
    replacement_field = r": typing.Optional[\1] = None"

    # 替换
    pattern_none = re.compile(r"\bNone\s*=\s*(\S+)")
    replacement_none = r"NONE = \1"

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
    with open(f"./new_message/{proto_name}_p2p.py", "w") as file:
        file.writelines(updated_lines)


def gen_pandantic():
    out_folder_name = "new_pydantic"
    # 执行python命令
    for proto_name in protos:
        print(
            f"sudo python3 -m grpc_tools.protoc -I./proto --protobuf-to-pydantic_out=./{out_folder_name} {proto_name}.proto")
        os.system(
            f"sudo python3 -m grpc_tools.protoc -I./proto --protobuf-to-pydantic_out=./{out_folder_name} {proto_name}.proto")
        print(f"gen {proto_name} pythonic proto success")
        fix_default_value(proto_name)
        print()


def gen_models():
    out_folder_name = "models"
    # for proto_name in protos:
    command = f"protoc -I ./proto --python_betterproto_out={out_folder_name} ./proto/*.proto"
    print(command)
    os.system(command)
    print("gen model success")


def gen_pyi():
    out_folder_name = "./message"
    for proto_name in protos:
        command = f"protoc -I ./proto --pyi_out={out_folder_name} ./proto/{proto_name}.proto"
        print(command)
        os.system(command)
        print(f"gen {proto_name} pyi success")
        print()
    # todo 待自动修复 "None: "


def gen_mkdocs_pyi():
    # 如果pyi路径不存在则创建
    if not os.path.exists("./pyi"):
        os.mkdir("./pyi")
    # 复制message/*.pyi文件到pyi文件夹下
    for proto_name in protos:
        # 源文件路径
        source_file = f"./message/{proto_name}_pb2.pyi"
        # 目标文件路径
        target_file = f"./pyi/{proto_name}_pb2.pyi"
        # 使用python接口复制文件
        shutil.copyfile(source_file, target_file)
        print(f"cp {source_file} -> {target_file}")


if __name__ == "__main__":
    # gen_protobuf()
    # gen_pandantic()
    # gen_models()
    # gen_pyi()
    gen_mkdocs_pyi()
