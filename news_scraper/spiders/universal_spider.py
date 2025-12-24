import scrapy
from scrapy.loader import ItemLoader
from datetime import datetime, timedelta
from typing import Optional


# 尝试导入项目模块
try:
    from news_scraper.items import NewsItem, NewsItemLoader, generate_news_id
    from news_scraper.utils.extractor import MultiSiteExtractor
except ImportError:
    # 如果在开发环境，添加路径
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from news_scraper.items import NewsItem, NewsItemLoader
    from news_scraper.utils.extractor import MultiSiteExtractor


class UniversalNewsSpider(scrapy.Spider):
    """
    通用新闻爬虫
    通过配置文件支持多个新闻网站，无需为每个网站写独立爬虫

    使用示例:
        # 爬取所有启用的新闻源
        scrapy crawl universal_news

        # 爬取指定新闻源
        scrapy crawl universal_news -a sources=cnn,bbc

        # 爬取近7天的新闻
        scrapy crawl universal_news -a days_back=7

        # 组合使用
        scrapy crawl universal_news -a sources=cnn -a days_back=3
    """

    name = "universal_news"

    # 自定义设置
    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "ROBOTSTXT_OBEY": False,
    }

    def __init__(
        self,
        sources: Optional[str] = None,
        days_back: int = 1,
        config_path: str = "config/news_sources.json",
        *args,
        **kwargs,
    ):
        """
        初始化爬虫

        Args:
            sources: 指定要爬取的新闻源，逗号分隔，如 'cnn,bbc'
                    如果为None则爬取所有启用的源
            days_back: 爬取多少天内的新闻，默认1天
            config_path: 配置文件路径
        """
        super().__init__(*args, **kwargs)

        # 加载字段提取器
        self.multi_extractor = MultiSiteExtractor(config_path)

        # 确定要采集到新闻源
        if sources:
            self.target_sources = [s.strip() for s in sources.split(",")]
            available = self.multi_extractor.get_all_sources()
            invalid = [s for s in self.target_sources if s not in available]
            if invalid:
                self.logger.warning(f'以下新闻源不存在或未启用: {", ".join(invalid)}')
            self.target_sources = [s for s in self.target_sources if s in available]
        else:
            self.target_sources = self.multi_extractor.get_all_sources()

        if not self.target_sources:
            raise ValueError("没有可用的新闻源！请检查配置文件或sources参数")

        self.days_back = int(days_back)
        self.start_date = datetime.now() - timedelta(days=self.days_back)

        # 输出启动信息
        self.logger.info("=" * 60)
        self.logger.info(f"通用新闻爬虫启动")
        self.logger.info(
            f'目标新闻源 ({len(self.target_sources)}): {", ".join(self.target_sources)}'
        )
        self.logger.info(
            f'时间范围: 最近 {self.days_back} 天 (从 {self.start_date.strftime("%Y-%m-%d")} 起)'
        )
        self.logger.info("=" * 60)

        # 动态设置allowed_domains和start_urls
        self._setup_urls()

        # 统计信息
        self.stats = {
            "pages_crawled": 0,
            "articles_found": 0,
            "articles_scraped": 0,
            "articles_failed": 0,
        }

    def start_requests(self):
        """
        生成初始请求
        """
        for url in self.start_urls:
            # 识别新闻源
            source_id = self._identify_source(url)

            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,
                meta={"source_id": source_id, "page_type": "list"},
                dont_filter=True,
            )

    def parse(self, response):
        """
        解析列表页，提取文章链接

        Args:
            response: Scrapy Response对象
        """
        self.stats["pages_crawled"] += 1

        # 从meta中获取新闻源ID
        source_id = response.meta.get("source_id")
        if not source_id:
            source_id = self._identify_source(response.url)
        if not source_id:
            self.logger.warning(f"❌ 无法识别新闻源: {response.url}")
            return

        extractor = self.multi_extractor.get_extractor(source_id)
        config = self.multi_extractor.get_config(source_id)

        if not extractor or not config:
            self.logger.error(f"❌ 找不到新闻源配置: {source_id}")
            return

        self.logger.info(f'📄 解析列表页: {response.url} ({config.get("name")})')

        # 提取文章链接
        links_config = config.get("selectors", {}).get("article_links", {})
        article_links = extractor.extract_field(response, "article_links", links_config)
        if not article_links:
            self.logger.warning(f"⚠ 未提取到文章链接: {response.url}")
            return
        if isinstance(article_links, str):
            article_links = [article_links]

        self.logger.info(f"📰 找到 {len(article_links)} 个文章链接")
        self.stats["articles_found"] += len(article_links)

        # 遍历链接
        for link in article_links:
            # 构建完整URL
            article_url = response.urljoin(link)

            # 验证是否为有效文章URL
            if not extractor.is_valid_article_url(article_url):
                continue

            # 发起详情页请求
            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                errback=self.handle_error,
                meta={
                    "source_id": source_id,
                    "source_config": config,
                    "page_type": "article",
                },
                dont_filter=False,
            )

    def parse_article(self, response):
        """
        解析文章详情页
        使用配置化的提取器自动提取所有字段

        Args:
            response: Scrapy Response对象
        """
        # 从meta中获取新闻源ID和配置
        source_id = response.meta["source_id"]
        source_config = response.meta["source_config"]

        try:
            # 查看是否有对应的字段提取器
            extractor = self.multi_extractor.get_extractor(source_id)
            if not extractor:
                self.logger.error(f"❌ 找不到提取器: {source_id}")
                return

            self.logger.info(f"📖 解析文章: {response.url}")

            # 使用提取器提取所有字段
            extracted_data = extractor.extract_all_fields(response)

            # 检查必填字段
            if not extracted_data.get("title"):
                self.logger.error(f"❌ 标题提取失败，跳过: {response.url}")
                self.stats["articles_failed"] += 1
                return

            if not extracted_data.get("content"):
                self.logger.warning(f"⚠ 内容提取失败，但继续处理: {response.url}")

            # 构建Item
            loader = NewsItemLoader(item=NewsItem(), response=response)
            loader.add_value("news_id", generate_news_id(response.url))
            loader.add_value("url", response.url)
            loader.add_value("crawl_time", datetime.now().isoformat())
            loader.add_value("source_name", source_config.get("name"))
            loader.add_value("source_country", source_config.get("country"))
            loader.add_value("language", source_config.get("language"))
            category = self._extract_category(response.url, source_config)
            if category:
                loader.add_value("category", category)

            # 添加提取到的字段
            allowed_fields = set(NewsItem.fields.keys())
            excluded_fields = {"article_links", "list_page_url"}
            for field_name, field_value in extracted_data.items():
                # 跳过排除的字段
                if field_name in excluded_fields:
                    continue
                if field_name in allowed_fields:
                    loader.add_value(field_name, field_value)

            # 检查日期有效性
            publish_time = extracted_data.get("publish_time")
            if publish_time and not self._is_valid_date(publish_time):
                self.logger.info(f"⏰ 文章过旧，跳过: {response.url}")
                return

            item = loader.load_item()
            self.stats["articles_scraped"] += 1
            self.logger.info(f'✅ 成功提取: {item.get("title", "")[:50]}...')

            yield item
        except KeyError as e:
            self.logger.error(f"❌ 字段错误 {str(e)} - {response.url}")
            self.stats["articles_failed"] += 1
        except Exception as e:
            self.logger.error(f"❌ {e.__class__.__name__}: {str(e)[:50]}")
            self.stats["articles_failed"] += 1

    def handle_error(self, failure):
        """
        统一错误处理

        Args:
            failure: Twisted Failure对象
        """
        request = failure.request
        self.logger.error(f"❌ 请求失败: {request.url}")
        self.logger.error(f"   错误类型: {failure.type.__name__}")
        self.logger.error(f"   错误信息: {failure.value}")

        if request.meta.get("page_type") == "article":
            self.stats["articles_failed"] += 1

    def closed(self, reason):
        """
        爬虫关闭时的回调
        输出统计信息

        Args:
            reason: 关闭原因
        """
        self.logger.info("=" * 60)
        self.logger.info(f"爬虫关闭: {reason}")
        self.logger.info("统计信息:")
        self.logger.info(f'  列表页爬取: {self.stats["pages_crawled"]} 页')
        self.logger.info(f'  文章发现: {self.stats["articles_found"]} 篇')
        self.logger.info(f'  文章成功: {self.stats["articles_scraped"]} 篇')
        self.logger.info(f'  文章失败: {self.stats["articles_failed"]} 篇')
        if self.stats["articles_found"] > 0:
            success_rate = (
                self.stats["articles_scraped"] / self.stats["articles_found"]
            ) * 100
            self.logger.info(f"  成功率: {success_rate:.1f}%")
        self.logger.info("=" * 60)

    def _setup_urls(self):
        """
        根据配置动态设置allowed_domains和start_urls
        """
        self.allowed_domains = []
        self.start_urls = []

        for source_id in self.target_sources:
            config = self.multi_extractor.get_config(source_id)
            if not config:
                continue

            # 添加域名
            domain = config.get("domain")
            if domain and domain not in self.allowed_domains:
                self.allowed_domains.append(domain)

            # 添加起始URL
            list_pages = config.get("list_pages", [])
            for page in list_pages:
                url = page.get("url")
                if url and url not in self.start_urls:
                    self.start_urls.append(url)

        self.logger.info(f"已配置 {len(self.allowed_domains)} 个域名")
        self.logger.info(f"已配置 {len(self.start_urls)} 个起始URL")

    def _identify_source(self, url: str) -> Optional[str]:
        """
        根据URL识别新闻源

        Args:
            url: 网站URL

        Returns:
            新闻源ID，如果无法识别返回None
        """
        for source_id in self.target_sources:
            config = self.multi_extractor.get_config(source_id)
            if not config:
                continue

            domain = config.get("domain")
            if domain and domain in url:
                return source_id

        return None

    def _extract_category(self, url: str, config: dict) -> Optional[str]:
        """
        从URL或配置中提取分类

        Args:
            url: 文章URL
            config: 新闻源配置

        Returns:
            分类名称
        """
        # 从list_pages配置中匹配分类
        list_pages = config.get("list_pages", [])
        for page in list_pages:
            page_url = page.get("url", "")
            category = page.get("category", "general")

            # 简单匹配：如果文章URL包含list_page的路径
            if page_url:
                page_path = page_url.split("/")[-1]
                if page_path and page_path in url:
                    return category

        # 默认分类
        return "general"

    def _is_valid_date(self, date_string: str) -> bool:
        """
        检查日期是否在有效范围内

        Args:
            date_string: ISO格式日期字符串

        Returns:
            是否有效
        """
        try:
            publish_time = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            return publish_time >= self.start_date
        except:
            return True  # 如果解析失败，默认采集
