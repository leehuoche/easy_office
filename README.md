# easy_office

办公与生活中的实用工具集合。

## 子项目

- [easy_image_ocr](./easy_image_ocr/README.md)：原办公自动化项目，包含图像 OCR、表格处理等代码和资料。
- [easy_cooker](./easy_cooker/README.md)：小餐厅后厨调度模型、Python 原型及验证脚本。

## 目录结构

```text
easy_office/
├── .git/
├── LICENSE
├── README.md
├── easy_image_ocr/
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

仓库名称和远端保持为 `leehuoche/easy_office`，Git 历史保留在根目录。

## 运行 easy_cooker

```bash
cd easy_cooker
python3 demo.py
python3 main.py
```

原办公项目的文件内容和相对资源结构保留，使用时进入 `easy_image_ocr` 下的相应原运行目录。原文档中的 `easy_office` 项目名称及 Conda 环境名称保留。
