# 抵押贷款定价比较工具

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.31.0-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目简介

抵押贷款定价比较工具是一个专为抵押贷款定价分析设计的应用程序，可以帮助用户比较不同投资者的定价表，找出最佳定价机会，并提供深入的分析功能。

![应用截图](docs/images/app_screenshot.png)

### 主要功能

- **多维筛选分析**：根据FICO、LTV、DSCR等多个维度筛选和分析定价数据
- **结构验证**：验证投资者表格与AAA表格的结构一致性
- **反向定价分析**：识别影响目标利润率的关键因素
- **利润率异常检测**：发现异常高或异常低的利润率场景

## 快速开始

### 安装

```bash
# 克隆仓库
git clone <repository-url> mortgage_pricing_tool
cd mortgage_pricing_tool

# 安装依赖
pip install -r requirements.txt

# 安装开发模式的包（可选）
pip install -e .
```

### 运行应用

```bash
streamlit run app.py
```

应用将在 http://localhost:8501 启动

### 使用流程

1. 上传AAA DSCR和投资者DSCR Excel文件
2. 处理文件并应用筛选条件
3. 分析结果并导出报告

## 文档

- [用户指南](docs/user_guide.md) - 详细的使用说明和功能介绍
- [开发指南](docs/developer_guide.md) - 开发者文档和API参考
- [数据格式要求](docs/data_format.md) - Excel文件格式规范

## 项目结构

```
mortgage_pricing_tool/
├── core/                   # 核心功能模块
│   ├── parser.py           # Ratesheet解析
│   ├── combiner.py         # 情景组合生成
│   ├── calculator.py       # 价格计算
│   ├── analyzer.py         # 多维筛选分析
│   ├── reverse_optimizer.py # 反向定价建议
│   ├── outlier_detector.py # 异常检测
│   └── structure_checker.py # 结构验证
├── utils/                  # 工具模块
│   ├── constants.py        # 常量定义
│   └── io.py               # 文件读写操作
├── docs/                   # 文档
├── app.py                  # 主应用程序
├── requirements.txt        # 依赖项
└── setup.py                # 安装配置
```

## 依赖项

- Python 3.8+
- Streamlit 1.31.0
- Pandas 2.1.0
- NumPy 1.26.0
- Plotly 5.18.0
- Scikit-learn 1.3.0

## 贡献

欢迎贡献代码、报告问题或提出改进建议。

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
