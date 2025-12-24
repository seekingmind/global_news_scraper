# 1. 项目简介
本项目是一个基于Scrapy框架的全球新闻网站数据采集系统，采用配置化驱动的设计理念，通过JSON配置文件即可快速适配不同新闻网站，无需为每个网站编写独立爬虫代码。
此类数据采集项目价值不大，主要为了再次熟悉scrapy框架。

# 2. 核心特性
- 配置化采集：通过JSON配置定义选择器规则
- 智能降级：多选择器自动回退机制，提高数据提取成功率
- 统一数据模型：标准化的新闻数据结构，便于后续处理
- 多格式日期解析：自动识别并解析20+种常见日期格式
- 数据存储：存储在 MongoDB 数据库中
- 易于扩展：新增网站只需配置，平均10分钟完成适配

# 3. 项目目录结构
```
global-news-scraper/
│
├── README.md                          # 项目说明
├── requirements.txt                   # Python依赖
├── scrapy.cfg                         # Scrapy配置文件
│
├── config/                            # 配置文件目录
│   ├── __init__.py
│   ├── news_sources.json              # 【核心】新闻源配置
│   ├── settings.py                    # 全局配置
│   └── database.py                    # 数据库配置
│
|—— news_scraper/                      # Scrapy项目主目录
│   ├── __init__.py
│   ├── settings.py                    # Scrapy设置
│   ├── items.py                       # 【核心】数据模型定义
│   ├── pipelines.py                   # 【核心】数据处理管道
│   ├── middlewares.py                 # 中间件（User-Agent等）
│   │
│   ├── spiders/                       # 爬虫目录
│   │   ├── __init__.py
│   │   └── universal_spider.py        # 【核心】通用爬虫
│   │
│   ├── utils/                         # 工具函数
│   │   ├── __init__.py
│   │   ├── extractor.py               # 【核心】数据提取器
│   │   ├── date_parser.py             # 【核心】日期解析器
│   │   ├── text_cleaner.py            # 文本清洗
│   │   └── url_handler.py             # URL处理
│   │
│   └── extensions/                    # 扩展功能
│       ├── __init__.py
│       └── stats_collector.py         # 统计收集
│
├── tools/                             # 辅助工具
│   ├── __init__.py
│   ├── analyze_site.py                # 网站结构分析工具
│   ├── test_selectors.py              # 选择器测试工具
│   └── config_validator.py            # 配置文件验证工具
│
├── logs/                              # 日志目录
|
├── data/                              # 本地保存数据的目录
│
├── tests/                             # 测试目录
│   ├── __init__.py
│   ├── test_extractor.py
│   ├── test_date_parser.py
│   └── test_pipelines.py
│
└── scripts/                           # 运行脚本
    ├── run_spider.sh                  # Linux运行脚本
    ├── run_spider.bat                 # Windows运行脚本
    └── schedule_crawl.py              # 定时任务脚本
```
