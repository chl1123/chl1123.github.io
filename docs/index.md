# Welcome to Seer Syspy

[mkdocs.org](https://www.mkdocs.org)

## 生成mkdocs文档

- 安装python3.9及以上
- 安装syspy和mkdocs的依赖

```shell
cd ./srcipts
sudo python3 -m pip install -r requirements-dev.txt
```

- 生成mkdocs文档

```shell
mkdocs build
```

* `mkdocs new [dir-name]` - 创建一个新的mkdocs项目。
* `mkdocs serve` - 启动实时加载文档服务器。
* `mkdocs build` - 构建文档，生成网页。
* `mkdocs -h` - 打印帮助信息并退出。

## mkdocs项目布局

    mkdocs.yml    # mkdocs配置文件
    docs/
        index.md  # 文档主页
        ...       # 其他markdown、图像和文件
