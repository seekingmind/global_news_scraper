# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import logging
from datetime import datetime
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class NewsScraperPipeline:
    def process_item(self, item, spider):
        return item


class ValidationPipeline:
    """
    数据验证管道
    验证必填字段和数据格式
    """

    required_fields = ["title", "url", "source_name"]

    # 最小内容长度（字符数）
    MIN_TITLE_LENGTH = 10
    MIN_CONTENT_LENGTH = 50

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_item(self, item, spider):
        """
        验证数据完整性

        Args:
            item: NewsItem对象
            spider: Spider对象

        Returns:
            验证通过的Item

        Raises:
            DropItem: 验证失败
        """

        # 验证必填字段
        for field in self.required_fields:
            if not item.get(field):
                raise DropItem(
                    f'❌ 缺少必填字段: {field}, URL: {item.get("url", "unknown")}'
                )

        # 验证标题长度
        title = item.get("title", "")
        if len(title) < self.MIN_TITLE_LENGTH:
            raise DropItem(
                f"❌ 标题过短 ({len(title)} < {self.MIN_TITLE_LENGTH}): {title}"
            )

        # 验证内容长度
        content = item.get("content", "")
        if isinstance(content, list):
            content = " ".join(content)
        if content and len(content) < self.MIN_CONTENT_LENGTH:
            spider.logger.warning(
                f'⚠ 内容较短 ({len(content)} < {self.MIN_CONTENT_LENGTH}): {item.get("url")}'
            )

        # 验证URL格式
        url = item.get("url", "")
        if not url.startswith(("http://", "https://")):
            raise DropItem(f"❌ 无效的URL格式: {url}")

        self.logger.debug(f"✅ 数据完整性验证通过: {title[:50]}...")
        return item


class DeduplicationPipeline:
    """
    去重管道
    基于URL和新闻ID进行内存级去重
    """

    def __init__(self):
        self.seen_ids = set()
        self.seen_urls = set()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.duplicate_count = 0

    def process_item(self, item, spider):
        """
        检查重复

        Args:
            item: NewsItem对象
            spider: Spider对象

        Returns:
            唯一的Item

        Raises:
            DropItem: 发现重复
        """

        # URL 去重
        url = item.get("url", "")
        if url in self.seen_urls:
            self.duplicate_count += 1
            raise DropItem(f"🔄 重复URL: {url}")
        self.seen_urls.add(url)

        # ID去重
        news_id = item.get("news_id", "")
        if news_id in self.seen_ids:
            self.duplicate_count += 1
            raise DropItem(f"🔄 重复新闻ID: {news_id}")
        self.seen_ids.add(news_id)

        self.logger.debug(f'✅ 新内容: {item.get("title", "")[:50]}...')
        return item

    def close_spider(self, spider):
        """
        爬虫关闭时输出去重统计

        Args:
            spider: Spider对象
        """
        self.logger.info(f"去重统计: 发现 {self.duplicate_count} 条重复数据")


class DataCleaningPipeline:
    """
    数据清洗管道
    标准化和清洗各类数据
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_item(self, item, spider):
        """
        清洗数据

        Args:
            item: NewsItem对象
            spider: Spider对象

        Returns:
            清洗后的Item
        """
        # 清洗标题
        if item.get("title"):
            item["title"] = self._clean_title(item["title"])

        # 清洗内容
        if item.get("content"):
            item["content"] = self._clean_content(item["content"])

        # 清洗摘要
        if item.get("summary"):
            item["summary"] = self._clean_text(item["summary"])

        # 标准化时间格式
        for time_field in ["publish_time", "update_time", "crawl_time"]:
            if item.get(time_field):
                item[time_field] = self._standardize_time(item[time_field])

        # 清洗URL
        if item.get("url"):
            item["url"] = self._clean_url(item["url"])

        # 清洗图片列表
        if item.get("images"):
            item["images"] = self._clean_image_list(item["images"])

        # 清洗标签列表
        if item.get("tags"):
            item["tags"] = self._clean_tags(item["tags"])

        return item

    def _clean_title(self, title: str) -> str:
        """
        清洗标题

        Args:
            title: 标题字符串

        Returns:
            清洗后的标题字符串
        """
        if not title:
            return ""
        # 移除多余空格
        title = " ".join(title.split())
        # 移除特殊字符
        title = title.strip("\n\r\t")
        # 移除常见的标题后缀（如网站名）
        for suffix in [" - CNN", " - BBC News", " | Reuters"]:
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
        return title

    def _clean_content(self, content) -> str:
        """
        清洗正文

        Args:
            content: 正文字符串或列表

        Returns:
            清洗后的正文字符串
        """
        if isinstance(content, list):
            content = "\n".join(content)
        if not content:
            return ""
        # 移除多余空白，保留段落结构
        lines = content.split("\n")
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return "\n".join(cleaned_lines)

    def _clean_text(self, text: str) -> str:
        """
        清洗文章摘要文本

        Args:
            text: 文章摘要文本

        Returns:
            清洗后的文章摘要文本
        """
        if not text:
            return ""
        return " ".join(text.split()).strip()

    def _standardize_time(self, time_str) -> str:
        """
        标准化时间格式为ISO 8601

        Args:
            time_str: 时间字符串

        Returns:
            标准时间字符串
        """
        if isinstance(time_str, datetime):
            return time_str.isoformat()

        # 如果已经是ISO格式，直接返回
        if isinstance(time_str, str):
            return time_str.strip()
        return str(time_str)

    def _clean_url(self, url: str) -> str:
        """
        清洗URL，移除追踪参数

        Args:
            url: URL字符串

        Returns:
            清洗后的URL字符串
        """
        if not url:
            return ""
        url = url.strip()

        if "?" in url:
            url = url.split("?")[0]

        return url

    def _clean_image_list(self, images) -> list:
        """
        清洗图片URL列表

        Args:
            images: 图片URL列表

        Returns:
            清洗后的图片URL列表
        """
        if not images:
            return []

        if isinstance(images, str):
            images = [images]

        cleaned = []
        for img_url in images:
            img_url = img_url.strip()
            # 确保是有效的URL
            if img_url.startswith(("http://", "https://", "//")):
                # 处理协议相对URL
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                cleaned.append(img_url)

        return cleaned

    def _clean_tags(self, tags) -> list:
        """
        清洗标签列表

        Args:
            tags: 标签列表

        Returns:
            清洗后的标签列表
        """
        if not tags:
            return []

        if isinstance(tags, str):
            tags = [tags]

        # 清洗并去重
        cleaned = []
        seen = set()
        for tag in tags:
            tag = tag.strip().lower()
            if tag and tag not in seen:
                seen.add(tag)
                cleaned.append(tag)

        return cleaned


class MongoDBPipeline:
    """
    MongoDB存储管道
    将数据存储到MongoDB数据库
    """

    def __init__(self, mongo_uri, mongo_db, collection_name):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.saved_count = 0
        self.updated_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        """
        从Scrapy settings中读取配置

        Args:
            crawler: Scrapy爬虫对象

        Returns:
            MongoDBPipeline实例
        """
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI", "mongodb://localhost:27017"),
            mongo_db=crawler.settings.get("MONGO_DATABASE", "news_scraper"),
            collection_name=crawler.settings.get("MONGO_COLLECTION", "news"),
        )

    def open_spider(self, spider):
        """
        爬虫开启时连接数据库

        Args:
            spider: Scrapy爬虫对象
        """
        try:
            import pymongo

            self.client = pymongo.MongoClient(self.mongo_uri)
            self.db = self.client[self.mongo_db]
            self.collection = self.db[self.collection_name]

            # 创建索引
            self.collection.create_index("url", unique=True)
            self.collection.create_index("news_id", unique=True)
            self.collection.create_index("publish_time")
            self.collection.create_index("source_name")
            self.collection.create_index("category")
            self.collection.create_index([("source_name", 1), ("publish_time", -1)])

            spider.logger.info(
                f"✅ MongoDB连接成功: {self.mongo_db}.{self.collection_name}"
            )
        except ImportError:
            spider.logger.error("❌ pymongo未安装，MongoDB Pipeline已禁用")
            spider.logger.error("   安装命令: pip install pymongo")
            raise
        except Exception as e:
            spider.logger.error(f"❌ MongoDB连接失败: {e}")
            raise

    def close_spider(self, spider):
        """
        爬虫关闭时断开连接

        Args:
            spider: Scrapy爬虫对象
        """
        if self.client:
            self.client.close()
            spider.logger.info("✅ MongoDB连接已关闭")
            spider.logger.info(
                f"存储统计: 新增 {self.saved_count} 条, 更新 {self.updated_count} 条"
            )

    def process_item(self, item, spider):
        """
        存储数据到MongoDB

        Args:
            item: Scrapy Item对象
            spider: Scrapy爬虫对象
        """
        try:
            # 转换为字典
            data = dict(item)

            # 使用upsert避免重复
            result = self.collection.update_one(
                {"url": data["url"]}, {"$set": data}, upsert=True
            )

            if result.upserted_id:
                self.saved_count += 1
                spider.logger.debug(f'💾 新增: {data.get("title", "")[:50]}...')
            else:
                self.updated_count += 1
                spider.logger.debug(f'🔄 更新: {data.get("title", "")[:50]}...')

        except Exception as e:
            spider.logger.error(f"❌ MongoDB存储失败: {e}")
            spider.logger.error(f'   URL: {item.get("url")}')
            raise DropItem(f'存储失败: {item.get("url")}')

        return item
