# 开发者指南

## 项目架构

抵押贷款定价比较工具采用模块化设计，由以下主要组件构成：

### 核心模块

1. **Parser (parser.py)**
   - 负责解析Excel文件中的LLPA调整表和基础价格表
   - 处理不同格式的表格并标准化数据

2. **Combiner (combiner.py)**
   - 生成所有可能的借款人场景组合
   - 根据业务规则过滤无效场景

3. **Calculator (calculator.py)**
   - 计算每个场景的最终价格
   - 计算不同投资者之间的利润率差异

4. **Analyzer (analyzer.py)**
   - 提供多维筛选功能
   - 分析筛选后的数据并生成统计结果

5. **Reverse Optimizer (reverse_optimizer.py)**
   - 分析目标利润率范围内的场景
   - 识别影响目标利润率的关键因素

6. **Outlier Detector (outlier_detector.py)**
   - 检测异常高或异常低的利润率
   - 生成异常报告和统计信息

7. **Structure Checker (structure_checker.py)**
   - 验证投资者表格与AAA表格的结构一致性
   - 检查模块、LTV范围和基础价格行的匹配情况

### 工具模块

1. **Constants (constants.py)**
   - 定义全局常量和默认值
   - 配置筛选排除字段

2. **IO (io.py)**
   - 处理文件读写操作
   - 提供数据导出功能

### 主应用程序

**App (app.py)**
   - 提供Streamlit用户界面
   - 集成所有核心模块的功能
   - 处理用户交互和数据流

## 数据流

1. 用户上传AAA和投资者Excel文件
2. Parser模块解析文件并提取LLPA调整和基础价格
3. Combiner模块生成所有可能的场景组合
4. Calculator模块计算每个场景的价格和利润率
5. 用户应用筛选条件
6. Analyzer模块分析筛选后的数据
7. 用户可以使用其他功能（结构验证、反向定价、异常检测）

## 开发指南

### 环境设置

1. 克隆仓库并安装依赖
```bash
git clone <repository-url> mortgage_pricing_tool
cd mortgage_pricing_tool
pip install -r requirements.txt
pip install -e .
```

2. 安装开发工具（可选）
```bash
pip install pytest pytest-cov black flake8
```

### 代码风格

项目遵循PEP 8代码风格指南。可以使用以下命令检查和格式化代码：

```bash
# 检查代码风格
flake8 mortgage_pricing_tool

# 格式化代码
black mortgage_pricing_tool
```

### 添加新功能

1. 在适当的模块中添加新功能
2. 更新相关的测试
3. 在app.py中集成新功能（如需要）
4. 更新文档

### 测试

项目使用pytest进行测试。运行测试的命令：

```bash
# 运行所有测试
pytest

# 运行特定模块的测试
pytest tests/test_parser.py

# 生成覆盖率报告
pytest --cov=mortgage_pricing_tool
```

## API参考

### PricingDataParser

```python
from core.parser import PricingDataParser

# 初始化解析器
parser = PricingDataParser()

# 解析工作簿
llpa_adjustments, base_prices = parser.parse_workbooks(aaa_data, investor_data)
```

### ScenarioGenerator

```python
from core.combiner import ScenarioGenerator

# 初始化生成器
generator = ScenarioGenerator(llpa_adjustments)

# 生成所有场景
scenarios = generator.generate_all_scenarios()
```

### PriceCalculator

```python
from core.calculator import PriceCalculator

# 初始化计算器
calculator = PriceCalculator(llpa_adjustments, base_prices)

# 计算所有价格
pricing_results = calculator.calculate_all_prices(scenarios)
```

### DataFilterAnalyzer

```python
from core.analyzer import DataFilterAnalyzer

# 初始化分析器
analyzer = DataFilterAnalyzer(pricing_results)

# 获取可用维度
dimensions = analyzer.get_available_dimensions()

# 获取维度值
values = analyzer.get_dimension_values(dimension)

# 筛选和分析
results = analyzer.filter_and_analyze(filters)
```

### ReversePricingAnalyzer

```python
from core.reverse_optimizer import ReversePricingAnalyzer

# 初始化分析器
optimizer = ReversePricingAnalyzer(pricing_results)

# 分析目标利润率
results = optimizer.analyze_target_margin(min_margin, max_margin, investor)

# 创建影响图表
fig = optimizer.create_influence_chart()
```

### MarginAnomalyDetector

```python
from core.outlier_detector import MarginAnomalyDetector

# 初始化检测器
detector = MarginAnomalyDetector(pricing_results)

# 查找异常
anomalies = detector.find_margin_outliers(min_margin, max_margin)

# 获取异常DataFrame
df = detector.get_anomalies_dataframe()
```

### StructureValidator

```python
from core.structure_checker import StructureValidator

# 初始化验证器
validator = StructureValidator(llpa_adjustments, base_prices)

# 验证所有表格
results = validator.validate_all_sheets()
```

## 扩展指南

### 添加新的筛选维度

1. 确保新维度在场景生成过程中被包含
2. 更新`EXCLUDED_FILTER_FIELDS`常量（如果需要）
3. 在app.py中添加新的筛选控件

### 添加新的分析指标

1. 在`DataFilterAnalyzer`类中添加新的分析方法
2. 更新`_analyze_results`方法以包含新指标
3. 在app.py中添加新指标的显示

### 添加新的可视化

1. 创建新的可视化函数（建议使用Plotly）
2. 在相应的分析器类中添加方法
3. 在app.py中添加新的可视化显示

## 故障排除

### 常见开发问题

1. **导入错误**
   - 确保使用正确的导入路径
   - 检查是否安装了所有依赖项

2. **数据处理错误**
   - 检查输入数据的格式和结构
   - 添加日志记录以跟踪数据流

3. **性能问题**
   - 对大型数据集使用分批处理
   - 考虑使用缓存来提高性能

## 部署指南

### 本地部署

```bash
streamlit run app.py
```

### Docker部署

1. 构建Docker镜像
```bash
docker build -t mortgage-pricing-tool .
```

2. 运行容器
```bash
docker run -p 8501:8501 mortgage-pricing-tool
```

### 云部署

项目可以部署到Streamlit Cloud、Heroku或其他支持Python的云平台。

#### Streamlit Cloud

1. 将代码推送到GitHub仓库
2. 在Streamlit Cloud中连接仓库
3. 指定app.py作为主应用程序文件

## 性能优化

1. 使用缓存减少重复计算
2. 对大型数据集使用分批处理
3. 考虑使用并行处理来加速计算
4. 优化数据结构以减少内存使用
