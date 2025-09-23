# 需要安装 /usr/local/bin/protoc
# 需要安装 pip install protoletariat 将 import 从绝对转换为相对
# https://github.com/cpcloud/protoletariat
# https://github.com/protocolbuffers/protobuf/issues/1491

import glob
import os
import subprocess
import sys


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 compile_proto.py <input_dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = "./message"

    for file in glob.glob(os.path.join(output_dir, "*_pb2.py")):
        os.remove(file)

    proto_files = glob.glob(os.path.join(input_dir, "*.proto"))
    subprocess.call(
        [
            "protoc",
            "--proto_path",
            input_dir,
            "--python_out",
            output_dir,
        ]
        + proto_files
    )
    subprocess.call(
        [
            "protol",
            "--create-package",
            "--in-place",
            "--python-out",
            output_dir,
            "protoc",
            "--proto-path",
            input_dir,
        ]
        + proto_files
    )
    subprocess.call(
        [
            "black",
            "--quiet",
            output_dir,
        ]
    )
