# Scrapy settings for news_scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "news_scraper"

SPIDER_MODULES = ["news_scraper.spiders"]
NEWSPIDER_MODULE = "news_scraper.spiders"

ADDONS = {}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "news_scraper (+http://www.yourdomain.com)"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concurrency and throttling settings
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30

# Disable cookies (enabled by default)
COOKIES_ENABLED = True
COOKIES_DEBUG = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    "news_scraper.middlewares.NewsScraperSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    "news_scraper.middlewares.NewsScraperDownloaderMiddleware": 543,
# }

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
    # 核心状态收集器
    "scrapy.extensions.corestats.CoreStats": 0,
    # 日志统计
    "scrapy.extensions.logstats.LogStats": 0,
}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    # 1. 数据验证（必需字段、格式检查）
    "news_scraper.pipelines.ValidationPipeline": 100,
    # 2. 数据去重（基于URL和ID）
    "news_scraper.pipelines.DeduplicationPipeline": 200,
    # 3. 数据清洗（文本清理、格式标准化）
    "news_scraper.pipelines.DataCleaningPipeline": 300,
    # 4. 数据保存（保存到MongoDB）
    "news_scraper.pipelines.MongoDBPipeline": 400,
}

# ============================================
# MongoDB配置
# ============================================
# MongoDB连接URI
MONGO_URI = "mongodb://localhost:27017"
# 数据库名
MONGO_DATABASE = "news_scraper"
# 集合名
MONGO_COLLECTION = "news"
# MongoDB连接参数
# MONGO_URI = 'mongodb://username:password@host:port/database?authSource=admin'

# ============================================
# 日志配置
# ============================================
# 日志级别
# CRITICAL: 严重错误
# ERROR: 错误
# WARNING: 警告
# INFO: 信息（推荐）
# DEBUG: 调试（详细输出）
LOG_LEVEL = "INFO"
# 日志文件路径
LOG_FILE = "logs/scrapy.log"
# LOG_FILE = None
# 日志编码
LOG_ENCODING = "utf-8"
# 日志格式
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 1
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 10
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# ============================================
# 重试配置
# ============================================
# 重试次数
RETRY_TIMES = 3
# 需要重试的HTTP状态码
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# ============================================
# 重定向配置
# ============================================
# 最大重定向次数
REDIRECT_MAX_TIMES = 5
# 重定向优先级调整
REDIRECT_PRIORITY_ADJUST = +2

# ============================================
# 统计信息收集
# ============================================
# 启用统计信息收集
STATS_DUMP = True

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# 是否导出空字段
FEED_EXPORT_FIELDS = None

# DNS解析超时
DNS_TIMEOUT = 60
# DNS缓存
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000

# 新闻源配置文件路径
NEWS_SOURCES_CONFIG = "config/news_sources.json"

# 默认爬取天数
DEFAULT_DAYS_BACK = 1
