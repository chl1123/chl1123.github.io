import os


def read_files(path):
    """
    读取python模块或pyi，不需要递归

    参数：
    path (str): 文件路径

    返回值：
    list: 包含所有文件的列表
    """
    files = []
    for file in os.listdir(path):
        if (file.endswith('.py') or file.endswith('.pyi')) and not file.startswith('__init__'):
            files.append(file.split('.')[0])
    return files


def write_module(module_list):
    """
        ---
        title: module_name
        tags:
          - API
        hide:
        #- navigation # 显示右侧导航
        #- toc #显示左侧导航
        ---

        ::: syspy.module_name
    """
    # 将上述字符串写入文件
    for module in module_list:
        with open(f'./api/{module}.md', 'w') as f:
            f.write(
                f'---\n'
                f'title: {module}\n'
                f'tags:\n'
                f'  - API\n'
                f'hide:\n'
                f'#- navigation # 显示右侧导航\n'
                f'#- toc #显示左侧导航\n'
                f'---\n\n'
                f'::: syspy.{module}\n')
            f.close()
            print(f'{module}.md 文件已生成')


def write_message(message_list):
    """
        ---
        title: message_name
        tags:
          - Message
        hide:
        #- navigation # 显示右侧导航
        #- toc #显示左侧导航
        ---

        ::: syspy.protobuf.message.message_name
    """
    nav_list = []
    # 将上述字符串写入文件
    for message in message_list:
        # if message in ["XXX"]:  # 排除
        #     continue
        with open(f'./api/message/{message}.md', 'w') as f:
            # 去除message前面的"message_"和后面的"_pb2"
            message_title = message.replace('message_', '').replace('_pb2', '')
            f.write(
                f'---\n'
                f'title: {message_title}\n'
                f'tags:\n'
                f'  - Message\n'
                f'hide:\n'
                f'#- navigation # 显示右侧导航\n'
                f'#- toc #显示左侧导航\n'
                f'---\n\n'
                f'::: syspy.protobuf.pyi.{message}\n')
            f.close()
            nav_list.append(f'api/message/{message}.md')

    for nav in nav_list:
        print(nav)


if __name__ == '__main__':
    # module_list = read_files('../syspy')
    # print(module_list)
    # write_module(module_list)

    # module_list = read_files('../syspy/lib')
    # print(module_list)
    # write_module(module_list)

    message_list = read_files('../syspy/protobuf/pyi')
    print(message_list)
    write_message(message_list)

"""Generate the code reference pages and navigation."""
# from pathlib import Path
#
# import mkdocs_gen_files
#
# nav = mkdocs_gen_files.Nav()
# mod_symbol = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'
#
# root = Path(__file__).parent
# src = root / "syspy"
# print("src", src)
# for path in sorted(src.rglob("*.py")):
#     module_path = path.relative_to(src).with_suffix("")
#     print("module_path", module_path)
#
#     doc_path = path.relative_to(src).with_suffix(".md")
#     print("doc_path", doc_path)
#     full_doc_path = Path("api", doc_path)
#     print("full_doc_path", full_doc_path)
#     parts = tuple(module_path.parts)
#     print("parts", parts)
#     new_parts = parts
#     if parts[-1] == "__init__":
#         new_parts = parts[:-1] or ("",)
#         print("parts", parts)
#         doc_path = doc_path.with_name("index.md")
#         full_doc_path = full_doc_path.with_name("index.md")
#     elif parts[-1].startswith("_"):
#         continue
#     elif parts[0] in ["battery_Can", "battery_Serial", "canLogger", "dmx512"]:
#         print("continue")
#         continue
#     nav_parts = [f"{mod_symbol} {part}" for part in new_parts]
#     print("nav_parts: ", nav_parts)
#     nav[tuple(nav_parts)] = doc_path.as_posix()
#
#     with mkdocs_gen_files.open(full_doc_path, "w") as fd:
#         if parts[-1] == "__init__":
#             parts = parts[:-1] or ("",)
#             print("full_doc_path parts", parts)
#             ident = ".".join(parts)
#             if len(parts) == 0 or (parts[0] == ""):
#                 print("len(parts) == 0")
#                 fd.write(f"---\ntitle: syspy\n---\n\n::: syspy")
#             else:
#                 fd.write(f"---\ntitle: {ident}\n---\n\n::: syspy.{ident}")
#         elif len(parts) == 1:
#             ident = ".".join(parts)
#             fd.write(f"---\ntitle: {ident}\n---\n\n::: syspy.{ident}")
#
#     mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path.relative_to(root))
#
# with mkdocs_gen_files.open("api/SUMMARY.md", "w") as nav_file:
#     nav_file.writelines(nav.build_literate_nav())
