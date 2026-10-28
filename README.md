# easy_life

生活与工作中的实用工具集合。

## 子项目

- [easy_office](./easy_office/README.md)：原办公自动化项目，包含 OCR、表格处理等代码和资料。
- [easy_cooker](./easy_cooker/README.md)：小餐厅后厨调度模型、Python 原型及验证脚本。

## 目录结构

```text
easy_life/
├── .git/
├── LICENSE
├── README.md
├── easy_office/
│   ├── README.md
│   ├── source/
│   ├── doc/
│   ├── images/
│   └── ...
└── easy_cooker/
    ├── app/
    ├── tests/
    ├── main.py
    └── ...
```

Git 历史保留在仓库根目录。两个子项目使用各自的运行目录和说明。

## 运行 easy_cooker

```bash
cd easy_cooker
python3 demo.py
python3 main.py
```

原办公项目的相对资源路径保留，使用时进入 `easy_office` 下的相应原运行目录。
