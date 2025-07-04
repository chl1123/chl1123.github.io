# chl1123.github.io
robot python sdk

```bash
 pip install -r requirements-dev.txt
```

```bash
mkdir .github
cd .github
mkdir workflows
cd workflows
vim ci.yml
```

- `.github/workflows/ci.yml`
```yaml
name: publish site
on: # 在什么时候触发工作流
  push: # 在从本地main分支被push到GitHub仓库时
    branches:
      - main
  pull_request: # 在main分支合并别人提的pr时
    branches:
      - main
jobs: # 工作流的具体内容
  deploy:
    runs-on: ubuntu-latest # 创建一个新的云端虚拟机 使用最新Ubuntu系统
    steps:
      - uses: actions/checkout@v2 # 先checkout到main分支
      - uses: actions/setup-python@v2 # 再安装Python3和相关环境
        with:
          python-version: 3.9
      - run: pip install mkdocs==1.6.1
      - run: pip install mkdocstrings-python==1.11.1
      - run: pip install mkdocs-material==9.6.12
      - run: pip install mdx-include==1.4.2
      - run: pip install mkdocs-gen-files==0.5.0
      - run: pip install griffe-typingdoc==0.2.8
      - run: pip install black==24.8.0
      - run: mkdocs gh-deploy --force # 使用mkdocs-material部署gh-pages分支
```