"""
通用数据提取器
根据配置自动提取数据，支持多选择器降级机制
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from scrapy.http import Response


class DataExtractor:
    """
    单站点数据提取器
    根据配置使用CSS或XPath选择器提取数据
    支持选择器降级和数据处理
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化提取器

        Args:
            config: 新闻源配置字典，包含selectors、url_patterns等
        """
        self.config = config
        self.logger = logging.getLogger(
            f'{self.__class__.__name__}.{config.get("name", "unknown")}'
        )

    def extract_field(
        self, response: Response, field_name: str, field_config: Dict[str, Any]
    ) -> Any:
        """
        提取单个字段数据，支持多选择器降级

        Args:
            response: Scrapy Response对象
            field_name: 字段名称
            field_config: 字段配置，包含css、xpath、priority等

        Returns:
            提取到的数据，如果失败返回None

        Examples:
            >>> field_config = {
            ...     "css": ["h1.title::text", "h1::text"],
            ...     "priority": "css",
            ...     "required": True
            ... }
            >>> extractor.extract_field(response, 'title', field_config)
            'News Title'
        """
        # 确定使用CSS还是XPath
        priority = field_config.get("priority", "css")
        selectors = field_config.get(priority, [])

        # 如果优先选择器没有配置，使用另一种
        if not selectors:
            priority = "xpath" if priority == "css" else "css"
            selectors = field_config.get(priority, [])

        if not selectors:
            self.logger.warning(f"字段 {field_name} 没有配置选择器")
            return None

        # 确保selectors是列表
        if isinstance(selectors, str):
            selectors = [selectors]

        # 依次尝试每个选择器（降级机制）
        for i, selector in enumerate(selectors, 1):
            try:
                if priority == "css":
                    result = response.css(selector).getall()
                else:
                    result = response.xpath(selector).getall()

                # 如果提取到数据
                if result:
                    # 处理结果
                    result = self._process_result(result, field_config, field_name)

                    if result:
                        self.logger.debug(
                            f"✓ 字段 {field_name} 使用选择器#{i} 提取成功: {selector[:50]}"
                        )
                        return result
                else:
                    self.logger.debug(f"✗ 选择器#{i} 未提取到数据: {selector[:50]}")

            except Exception as e:
                self.logger.error(f"✗ 选择器#{i} 执行失败: {selector[:50]}, 错误: {e}")
                continue

        # 所有选择器都失败
        if field_config.get("required", False):
            self.logger.error(f"❌ 必填字段 {field_name} 提取失败")
        else:
            self.logger.debug(f"⚠ 可选字段 {field_name} 提取失败")

        return None

    def _process_result(
        self, result: List[str], config: Dict[str, Any], field_name: str
    ) -> Any:
        """
        处理提取结果

        处理步骤:
        1. 清理空白
        2. 应用过滤器
        3. 应用解析器（如日期解析）
        4. 合并或取第一个

        Args:
            result: 提取到的原始数据列表
            config: 字段配置
            field_name: 字段名称

        Returns:
            处理后的数据
        """
        if not result:
            return None

        # 清理数据 - 移除空白
        result = [item.strip() for item in result if item and item.strip()]

        if not result:
            return None

        # 应用过滤器
        filter_name = config.get("filter")
        if filter_name:
            result = self._apply_filter(result, filter_name, field_name)

        if not result:
            return None

        # 应用解析器（用于日期等特殊格式）
        parser_name = config.get("parser")
        if parser_name and result:
            parsed_result = []
            for item in result:
                parsed = self._apply_parser(item, parser_name)
                if parsed:
                    parsed_result.append(parsed)
            result = parsed_result

        if not result:
            return None

        # 合并或取第一个
        join_str = config.get("join")
        if join_str is not None:
            # 合并所有结果
            return join_str.join(str(item) for item in result if item)
        else:
            # 返回第一个或整个列表
            return result[0] if len(result) == 1 else result

    def _apply_filter(
        self, data: List[str], filter_name: str, field_name: str
    ) -> List[str]:
        """
        数据过滤

        支持的过滤器:
        - valid_image: 过滤无效图片URL
        - remove_empty: 移除空字符串
        - unique: 去重

        Args:
            data: 待过滤数据
            filter_name: 过滤器名称
            field_name: 字段名称

        Returns:
            过滤后的数据
        """
        if filter_name == "valid_image":
            # 过滤无效图片
            invalid_patterns = [
                "icon",
                "logo",
                "placeholder",
                "avatar",
                "sprite",
                "blank",
                "spacer",
                "pixel",
            ]
            filtered = [
                url
                for url in data
                if not any(p in url.lower() for p in invalid_patterns)
                and len(url) > 20  # 排除过短的URL
                and url.startswith(("http://", "https://", "//"))  # 有效的URL格式
            ]
            self.logger.debug(f"图片过滤: {len(data)} -> {len(filtered)}")
            return filtered

        elif filter_name == "remove_empty":
            # 移除空字符串
            return [item for item in data if item and item.strip()]

        elif filter_name == "unique":
            # 去重，保持顺序
            seen = set()
            unique_data = []
            for item in data:
                if item not in seen:
                    seen.add(item)
                    unique_data.append(item)
            return unique_data

        else:
            self.logger.warning(f"未知过滤器: {filter_name}")
            return data

    def _apply_parser(self, data: str, parser_name: str) -> Optional[str]:
        """
        应用数据解析器

        Args:
            data: 待解析数据
            parser_name: 解析器名称

        Returns:
            解析后的数据（ISO格式字符串）
        """
        # 导入日期解析器
        try:
            from news_scraper.utils.date_parser import parse_date
        except ImportError:
            # 如果在开发环境
            import sys

            sys.path.insert(0, str(Path(__file__).parent))
            from date_parser import parse_date

        if "date" in parser_name.lower() or parser_name in [
            "auto",
            "iso8601",
            "cnn_date",
            "bbc_date",
        ]:
            try:
                parsed_date = parse_date(data, parser_name)
                if parsed_date:
                    return parsed_date.isoformat()
            except Exception as e:
                self.logger.error(f"日期解析失败: {data}, 错误: {e}")
                return None

        return data

    def extract_all_fields(self, response: Response) -> Dict[str, Any]:
        """
        提取所有配置的字段

        Args:
            response: Scrapy Response对象

        Returns:
            包含所有成功提取字段的字典
        """
        selectors_config = self.config.get("selectors", {})
        extracted_data = {}

        for field_name, field_config in selectors_config.items():
            data = self.extract_field(response, field_name, field_config)
            if data is not None:
                extracted_data[field_name] = data

        return extracted_data

    def is_valid_article_url(self, url: str) -> bool:
        """
        检查URL是否为有效文章链接

        检查步骤:
        1. 匹配article正则模式
        2. 排除exclude列表中的模式

        Args:
            url: 待检查的URL

        Returns:
            是否有效
        """
        url_patterns = self.config.get("url_patterns", {})

        # 检查是否匹配文章URL模式
        article_pattern = url_patterns.get("article")
        if article_pattern:
            if not re.search(article_pattern, url):
                self.logger.debug(f"URL不匹配article模式: {url}")
                return False

        # 检查排除模式
        exclude_patterns = url_patterns.get("exclude", [])
        for pattern in exclude_patterns:
            if pattern in url.lower():
                self.logger.debug(f'URL匹配排除模式 "{pattern}": {url}')
                return False

        return True


class MultiSiteExtractor:
    """
    多站点提取器管理器
    管理多个新闻源的配置和提取器实例
    """

    def __init__(self, config_path: str = "config/news_sources.json"):
        """
        初始化多站点提取器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.extractors = {}
        self.configs = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._load_configs()

    def _load_configs(self):
        """加载所有新闻源配置"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            self.logger.error(f"配置文件不存在: {self.config_path}")
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                configs = json.load(f)

            loaded_count = 0
            for source_id, config in configs.items():
                if config.get("enabled", True):
                    self.configs[source_id] = config
                    self.extractors[source_id] = DataExtractor(config)
                    loaded_count += 1
                    self.logger.info(
                        f'✓ 加载新闻源: {source_id} ({config.get("name")})'
                    )
                else:
                    self.logger.info(f"✗ 跳过禁用的新闻源: {source_id}")

            self.logger.info(f"成功加载 {loaded_count} 个新闻源配置")

        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件JSON格式错误: {e}")
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")

    def get_extractor(self, source_id: str) -> Optional[DataExtractor]:
        """
        获取指定新闻源的提取器

        Args:
            source_id: 新闻源ID

        Returns:
            数据提取器实例，如果不存在返回None
        """
        return self.extractors.get(source_id)

    def get_config(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定新闻源的配置

        Args:
            source_id: 新闻源ID

        Returns:
            配置字典，如果不存在返回None
        """
        return self.configs.get(source_id)

    def get_all_sources(self) -> List[str]:
        """
        获取所有启用的新闻源ID列表

        Returns:
            新闻源ID列表
        """
        return list(self.extractors.keys())

    def reload_configs(self):
        """重新加载配置文件"""
        self.extractors.clear()
        self.configs.clear()
        self._load_configs()
        self.logger.info("配置文件已重新加载")


if __name__ == "__main__":
    # 测试代码
    import sys

    # 创建测试配置
    test_config = {
        "name": "Test Site",
        "domain": "example.com",
        "selectors": {
            "title": {
                "css": ["h1.title::text", "h1::text"],
                "priority": "css",
                "required": True,
            },
            "content": {
                "css": ["div.content p::text"],
                "priority": "css",
                "join": "\n",
            },
        },
        "url_patterns": {
            "article": r"^https://example\.com/news/\d+",
            "exclude": ["video", "gallery"],
        },
    }

    # 创建提取器
    extractor = DataExtractor(test_config)

    # 测试URL验证
    test_urls = [
        "https://example.com/news/12345",
        "https://example.com/video/12345",
        "https://example.com/article/test",
    ]

    print("URL验证测试:")
    print("-" * 60)
    for url in test_urls:
        is_valid = extractor.is_valid_article_url(url)
        print(f'{url:50} -> {"✓ 有效" if is_valid else "✗ 无效"}')
