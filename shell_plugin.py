      
import json
import os
import sys
import re
import hashlib
import zipfile
from datetime import datetime


DEFAULT_DESCRIPTION = "Monthly release: RBK + navigation plugin + config update"
JSON_NAME = "manifest.json"
PLUGIN_TARGET_PATH = "/opt"


def get_manifest_file_names(json_name=JSON_NAME):
    return [json_name, f"{json_name}.sha256"]


def get_sha256(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def extract_deb_info_from_filename(zip_file_name):
    if not zip_file_name:
        return None
    pattern = r'^([^-]+)-(.+?)(?:[-])([0-9][A-Za-z0-9._@-]*)(?:[_-])(all|arm64|amd64|x86|x64|noarch)(?:-(\d+))?\.zip$'
    match = re.match(pattern, os.path.basename(zip_file_name))
    if not match:
        return None
    if match.group(1) != "plugin":
        return None
    if match.group(4) not in ["all", "arm64", "amd64", "x86", "x64", "noarch"]:
        return None
    return (
        match.group(1),
        match.group(2),
        match.group(3),
        match.group(4),
        match.group(5) or datetime.now().strftime("%Y%m%d"),
    )


def validate_zip_filename(zip_file_name):
    result = extract_deb_info_from_filename(zip_file_name)
    if not result:
        return False, zip_file_name
    return True, result


def rename_zip_file(zip_origin_path, zip_type, package_id, version, arch, date=None, node=None):
    if node:
        version = f"{version}@{node}"
    if date:
        new_name = f"{zip_type}-{package_id}-{version}-{arch}-{date}.zip"
    else:
        new_name = f"{zip_type}-{package_id}-{version}-{arch}.zip"
    new_path = os.path.join(os.path.dirname(zip_origin_path), new_name)
    if os.path.exists(new_path):
        return False, new_name
    os.rename(zip_origin_path, new_path)
    return True, new_name


def build_resource_json(plugin_zip_name, plugin_bytes):
    info = extract_deb_info_from_filename(plugin_zip_name)
    if not info:
        raise ValueError(f"plugin 文件名格式错误: {plugin_zip_name}")

    _, package_id, version, _, _ = info
    node = None
    if "@" in version:
        version = version.split("@")[0]
    return {
        "type": "plugin",
        "order": 1,
        "name": package_id,
        "version": version,
        "method": "zip_extract",
        "fileName": plugin_zip_name,
        "sha256": get_sha256(plugin_bytes),
        "required": True,
        "targetPath": PLUGIN_TARGET_PATH,
    }


def _prompt(text):
    return input(text).strip()


def _choose_zip_path_with_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="选择 plugin zip 文件",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        root.destroy()
        return path or None
    except Exception:
        return None


def _choose_zip_path():
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg and arg.lower() not in {"start", "run", "open"}:
            return arg
    path = _choose_zip_path_with_dialog()
    if path:
        return path
    print("当前环境无法打开文件选择框，已切换为手动输入路径。")
    return _prompt("请输入 plugin zip 文件路径: ")


def _choose_existing_zip_path():
    while True:
        zip_path = _choose_zip_path()
        if not zip_path:
            print("未选择文件。")
            retry = _prompt("是否重新选择？(y/n): ").lower()
            if retry == "y":
                continue
            raise ValueError("用户未选择文件")
        if os.path.isfile(zip_path):
            return zip_path
        print(f"文件不存在: {zip_path}")
        retry = _prompt("是否重新选择？(y/n): ").lower()
        if retry != "y":
            raise FileNotFoundError(f"zip 文件不存在: {zip_path}")


def _ensure_plugin_zip(zip_path):
    if not zip_path:
        raise ValueError("zip 路径不能为空")
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"zip 文件不存在: {zip_path}")

    zip_name = os.path.basename(zip_path)
    valid, info = validate_zip_filename(zip_name)
    if not valid:
        print(f"ZIP 文件名不合法: {zip_name}")
        answer = _prompt("是否重命名后继续？(y/n): ").lower()
        if answer != "y":
            raise ValueError("用户取消重命名")

        zip_type = "plugin"
        package_id = _prompt("packageId: ")
        version = _prompt("version: ")
        arch = _prompt("arch(all/arm64/amd64/x86/x64/noarch): ")
        if '@' in version:
            node = version.split('@')[1]
            version = version.split('@')[0]
        else:
            node = _prompt("node(不填默认为master): ") or None
        date = _prompt("date(可不填): ") or None

        if not package_id or not version or not arch:
            raise ValueError("packageId、version、arch 不能为空")

        renamed, new_name = rename_zip_file(zip_path, zip_type, package_id, version, arch, date,node)
        if not renamed:
            raise FileExistsError(f"重命名失败，目标 zip 已存在")
        zip_path = os.path.join(os.path.dirname(zip_path), new_name)
        zip_name = new_name
        valid, info = validate_zip_filename(zip_name)
        if not valid:
            raise ValueError(f"重命名后仍不合法: {zip_name}")

    zip_type, package_id, version, arch, date = info
    node = None
    if "@" in version:
        version_node = version.split("@")
        version = version_node[0]
        node = version_node[1]
    if zip_type != "plugin":
        raise ValueError(f"该脚本只处理 plugin 类型 zip，当前是: {zip_type}")

    with open(zip_path, "rb") as f:
        plugin_bytes = f.read()

    return zip_path, {
        "zip_type": zip_type,
        "package_id": package_id,
        "version": version,
        "arch": arch,
        "date": date,
        "node": node or "master",
        "plugin_file_name": os.path.basename(zip_path),
        "plugin_bytes": plugin_bytes,
    }


def _build_manifest(zip_name, plugin_file_name, plugin_bytes, description):
    info = extract_deb_info_from_filename(zip_name)
    if not info:
        raise ValueError(f"zip 文件名格式错误: {zip_name}")

    zip_type, package_id, version, arch, date = info
    node = None
    if "@" in version:
        version_node = version.split("@")
        version = version_node[0]
        node = version_node[1]
    manifest = {
        "manifestVersion": "1.0",
        "metadata": {
            "packageId": package_id,
            "version": version,
            "arch": arch,
            "node": node or "master",
            "type": zip_type,
            "description": description,
        },
        "resources": [],
        "lifecycle": {
            "afterAll": {
                "commands": [
                    "sync",
                    "systemctl reboot"
                ],
                "timeout": 60
            }
        }
    }

    manifest["resources"].append(build_resource_json(plugin_file_name, plugin_bytes))

    return manifest


def _write_manifest_files(zip_path, description):
    zip_name = os.path.basename(zip_path)
    with open(zip_path, "rb") as f:
        plugin_bytes = f.read()
    manifest = _build_manifest(zip_name, os.path.basename(zip_path), plugin_bytes, description)
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    manifest_sha256 = get_sha256(manifest_text.encode("utf-8"))

    out_dir = os.path.dirname(zip_path) or "."
    json_path = os.path.join(out_dir, JSON_NAME)
    sha_path = os.path.join(out_dir, f"{JSON_NAME}.sha256")

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(manifest_text)
    with open(sha_path, "w", encoding="utf-8") as f:
        f.write(f"{manifest_sha256}  {JSON_NAME}")

    print(f"已生成: {json_path}")
    print(f"已生成: {sha_path}")


def _write_zip_with_manifest(zip_path, out_name, description):
    if not out_name.lower().endswith(".zip"):
        out_name = f"{out_name}.zip"

    out_path = os.path.join(os.path.dirname(zip_path) or ".", out_name)
    if os.path.exists(out_path):
        raise FileExistsError(f"目标 zip 已存在: {out_path}")

    with open(zip_path, "rb") as f:
        plugin_bytes = f.read()
    plugin_file_name = os.path.basename(zip_path)
    manifest = _build_manifest(plugin_file_name, plugin_file_name, plugin_bytes, description)
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    manifest_sha256 = get_sha256(manifest_text.encode("utf-8"))

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as dst:
        dst.writestr(plugin_file_name, plugin_bytes)
        dst.writestr(JSON_NAME, manifest_text)
        dst.writestr(f"{JSON_NAME}.sha256", f"{manifest_sha256}  {JSON_NAME}")

    print(f"已生成 zip: {out_path}")


def main():
    try:
        zip_path = _choose_existing_zip_path()
        zip_path, info = _ensure_plugin_zip(zip_path)
        print(f"当前文件: {zip_path}")
        print(f"packageId: {info['package_id']}")
        print(f"version: {info['version']}")
        print(f"arch: {info['arch']}")
        print(f"node: {info['node']}")
        print(f"date: {info['date']}")
        print(f"plugin 文件: {info['plugin_file_name']}")
        print(f"targetPath 固定为: {PLUGIN_TARGET_PATH}")

        description = _prompt(f"description(直接回车使用默认值): ") or DEFAULT_DESCRIPTION

        print("请选择处理方式:")
        print("1. 仅生成 manifest.json 和 manifest.json.sha256")
        print("2. 将manifest.json 和 manifest.json.sha256 ，原有 plugin 文件包含在新的 zip 包中")
        choice = _prompt("输入 1 或 2: ")

        if choice == "1":
            _write_manifest_files(zip_path, description)
        elif choice == "2":
            out_name = _prompt("请输入新 zip 文件名: ")
            if not out_name:
                raise ValueError("新 zip 文件名不能为空")
            _write_zip_with_manifest(zip_path, out_name, description)
        else:
            raise ValueError("无效的选择")

    except Exception as e:
        print(f"处理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

    