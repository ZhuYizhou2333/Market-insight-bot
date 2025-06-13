# Market-insight-bot
日内交易Agent，基于新闻、价格行为（PA）、订单流数据进行自动分析与交易

## 项目结构

```
Market-insight-bot/
├── data_modules/               # 数据获取与整理模块
│   ├── news/                   # 新闻数据处理
│   │   ├── fetcher.py          # 新闻数据获取器
│   │   └── processor.py        # 新闻数据处理器
│   │   └── __init__.py
│   ├── price_action/           # 价格行为数据处理
│   │   ├── fetcher.py          # 价格行为数据获取器
│   │   └── processor.py        # 价格行为数据处理器
│   │   └── __init__.py
│   ├── order_flow/             # 订单流数据处理
│   │   ├── fetcher.py          # 订单流数据获取器
│   │   └── processor.py        # 订单流数据处理器
│   │   └── __init__.py
│   └── __init__.py
├── ai_analyzers/               # AI分析模块
│   ├── news_analyzer.py        # 新闻数据AI分析器
│   ├── price_action_analyzer.py # 价格行为数据AI分析器
│   ├── order_flow_analyzer.py  # 订单流数据AI分析器
│   └── __init__.py
├── decision_engine/            # 交易决策引擎
│   ├── position_control_ai.py  # 仓位控制AI
│   ├── trader.py               # 交易执行模块
│   └── __init__.py
├── communication/              # 通信模块
│   ├── zmq_manager.py          # ZeroMQ 通信管理器
│   └── __init__.py
├── workflow/                   # 工作流管理模块
│   ├── main_orchestrator.py    # 主工作流协调器
│   └── __init__.py
├── agent/                      # Agent模块
│   ├── scheduler.py            # 任务调度器
│   └── __init__.py
├── config/                     # 配置模块
│   ├── settings.py             # 项目配置信息
│   └── __init__.py
├── utils/                      # 通用工具模块
│   └── __init__.py
├── tests/                      # 测试模块
│   └── __init__.py
├── main.py                     # 项目主入口
├── requirements.txt            # Python依赖包列表
└── README.md                   # 项目说明文档
```

## 文件功能边界与依赖关系

### 1. `main.py`
*   **功能**: 项目的启动入口。负责初始化各个模块，并启动主工作流。
*   **依赖**: `agent.scheduler`, `workflow.main_orchestrator`, `config.settings`。

### 2. `data_modules/`
    各子模块负责特定类型市场数据的获取和初步整理。每个子模块通常包含：
    *   `fetcher.py`:
        *   **功能**: 从外部数据源（API、数据库、文件等）获取原始数据。
        *   **依赖**: `config.settings` (获取API密钥、数据源地址等)，外部库 (如 `requests`)。
    *   `processor.py`:
        *   **功能**: 对获取到的原始数据进行清洗、格式化、转换，使其符合后续AI分析模块的输入要求。
        *   **依赖**: `fetcher.py` (获取数据)，`pandas` 或其他数据处理库。

    *   **`data_modules/news/`**: 处理新闻数据。
    *   **`data_modules/price_action/`**: 处理K线、成交量等价格行为数据。
    *   **`data_modules/order_flow/`**: 处理买卖盘、逐笔成交等订单流数据。

### 3. `ai_analyzers/`
    包含针对不同类型市场数据进行分析的AI模型或算法。
    *   `news_analyzer.py`:
        *   **功能**: 分析处理后的新闻数据，提取市场情绪、关键事件等信息。
        *   **依赖**: `data_modules.news.processor` (获取新闻数据)，AI库 `openai`。
    *   `price_action_analyzer.py`:
        *   **功能**: 分析处理后的价格行为数据，识别趋势、支撑阻力、形态等。
        *   **依赖**: `data_modules.price_action.processor` (获取价格数据)，AI库，技术分析库。
    *   `order_flow_analyzer.py`:
        *   **功能**: 分析处理后的订单流数据，判断市场买卖压力、大单行为等。
        *   **依赖**: `data_modules.order_flow.processor` (获取订单流数据)，AI库。

### 4. `decision_engine/`
    负责整合各AI分析器的结果，并做出最终的交易决策。
    *   `position_control_ai.py`:
        *   **功能**: 核心决策AI。接收来自各 `ai_analyzers` 的分析结果，结合风险管理策略、资金管理规则，决定是否开仓、平仓以及具体的仓位大小。
        *   **依赖**: `ai_analyzers` (获取分析信号)，`config.settings` (获取交易参数、风险参数)。
    *   `trader.py`:
        *   **功能**: 负责与实际的交易接口（交易所API、券商API）进行交互，执行由 `position_control_ai.py` 生成的交易指令（买入、卖出）。
        *   **依赖**: `position_control_ai.py` (获取交易指令)，`config.settings` (获取交易账户API密钥)，交易所/券商API库。

### 5. `communication/`
    *   `zmq_manager.py`:
        *   **功能**: 封装ZeroMQ的通信逻辑，用于各模块/进程间的消息传递。例如，Agent通过ZMQ请求数据，数据模块通过ZMQ发送处理好的数据，分析模块通过ZMQ发送分析结果。
        *   **依赖**: `pyzmq` 库。

### 6. `workflow/`
    *   `main_orchestrator.py`:
        *   **功能**: 协调整个交易决策流程。当被 `agent.scheduler` 触发时，它会依次调用数据获取模块、AI分析模块和决策引擎模块，并通过 `communication.zmq_manager` 进行数据流转和结果汇总。
        *   **依赖**: `data_modules`, `ai_analyzers`, `decision_engine`, `communication.zmq_manager`, `config.settings`。

### 7. `agent/`
    *   `scheduler.py`:
        *   **功能**: 定时任务调度器。按照预设的时间间隔（例如每30分钟）触发 `workflow.main_orchestrator` 执行一次完整的市场分析和交易决策流程。
        *   **依赖**: `workflow.main_orchestrator`, `schedule` 库或类似的调度库。

### 8. `config/`
    *   `settings.py`:
        *   **功能**: 存储项目的所有配置信息，如API密钥、数据库连接信息、ZMQ服务器地址和端口、交易参数、模型参数、日志级别等。
        *   **依赖**: 无。

### 9. `utils/`
    *   `__init__.py` (或其他 `.py` 文件):
        *   **功能**: 存放项目中通用的辅助函数或类，例如日志记录、日期时间处理、数据格式化工具、自定义异常等。
        *   **依赖**: 根据具体工具函数而定。

### 10. `tests/`
    *   **功能**: 存放单元测试和集成测试代码，确保各模块功能的正确性和整体流程的稳定性。
    *   **依赖**: `unittest` 或 `pytest` 等测试框架，以及被测试的模块。

### 11. `requirements.txt`
    *   **功能**: 列出项目运行所需的所有Python第三方库及其版本。
    *   **依赖**: 无。
