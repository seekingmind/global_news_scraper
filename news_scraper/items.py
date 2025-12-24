# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
import hashlib
import datetime
from itemloaders.processors import MapCompose, TakeFirst
from itemloaders import ItemLoader


def generate_news_id(url: str) -> str:
    """
    根据url生成新闻id
    Args:
        url (str): 新闻url
    Returns:
        str: 新闻id
    """
    if not url:
        return ""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def clean_text(text: str) -> str:
    """
    清理文本，移除多余空白
    Args:
        text (str): 待处理文本
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    return " ".join(text.split()).strip()


class NewsItem(scrapy.Item):
    """
    新闻数据模型
    定义所有可能的新闻字段
    """

    news_id = scrapy.Field(serializer=str)  # 新闻唯一标识符（基于URL的MD5）
    title = scrapy.Field(
        input_processor=MapCompose(clean_text), out_processor=TakeFirst()
    )  # 新闻标题
    url = scrapy.Field(out_processor=TakeFirst())  # 新闻原始URL
    content = scrapy.Field(
        input_processor=MapCompose(clean_text), out_processor=TakeFirst()
    )  # 新闻内容
    summary = scrapy.Field(
        input_processor=MapCompose(clean_text), out_processor=TakeFirst()
    )  # 新闻摘要
    author = scrapy.Field(
        input_processor=MapCompose(clean_text), out_processor=TakeFirst()
    )  # 新闻作者/记者
    publish_time = scrapy.Field(out_processor=TakeFirst())  # 新闻发布时间
    update_time = scrapy.Field(out_processor=TakeFirst())  # 新闻更新时间
    category = scrapy.Field()  # 新闻分类
    images = scrapy.Field()  # 新闻图片URL列表
    videos = scrapy.Field()  # 新闻视频URL列表
    source_name = scrapy.Field(out_processor=TakeFirst())  # 新闻来源
    source_country = scrapy.Field(out_processor=TakeFirst())  # 新闻来源国家
    language = scrapy.Field(out_processor=TakeFirst())  # 新闻语言
    view_count = scrapy.Field(out_processor=TakeFirst())  # 新闻浏览量
    comment_count = scrapy.Field(out_processor=TakeFirst())  # 新闻评论数
    crawl_time = scrapy.Field(out_processor=TakeFirst())  # 抓取时间
    raw_html = scrapy.Field(out_processor=TakeFirst())  # 抓取的HTML源代码


class NewsItemLoader(ItemLoader):
    """
    新闻数据模型数据加载器
    """

    default_item_class = NewsItem
    default_output_processor = TakeFirst()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_item(self):
        """
        加载新闻数据模型并生成对应的新闻ID
        """
        item = super().load_item()

        # 如果没有news_id，则根据URL自动生成
        if not item.get("news_id") and item.get("url"):
            item["news_id"] = generate_news_id(item["url"])

        # 如果没有crawl_time，则使用当前时间
        if not item.get("crawl_time"):
            item["crawl_time"] = datetime.datetime.now().isoformat()

        return item
