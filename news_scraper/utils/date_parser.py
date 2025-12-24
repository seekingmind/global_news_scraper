"""
多格式日期解析器
"""

import re
import logging
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DateParser:
    """
    多格式日期解析器
    自动识别并解析各种日期时间格式
    """

    # 相对时间关键词映射（英文）
    RELATIVE_PATTERNS = {
        "just now": 0,
        "a moment ago": 0,
        "seconds ago": 0,
        "a second ago": 0,
        "a minute ago": 1,
        "minutes ago": "minutes",
        "an hour ago": 60,
        "hours ago": "hours",
        "a day ago": 1440,
        "days ago": "days",
        "yesterday": 1440,
        "a week ago": 10080,
        "weeks ago": "weeks",
        "a month ago": 43200,
        "months ago": "months",
        "a year ago": 525600,
        "years ago": "years",
    }

    # 月份映射（支持英文全称和缩写）
    MONTH_MAPPING = {
        # 英文全称
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
        # 英文缩写
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "sept": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    @staticmethod
    def parse(date_string: str, parser_type: str = "auto") -> Optional[datetime]:
        """
        统一的日期解析入口

        Args:
            date_string: 日期字符串
            parser_type: 解析器类型
                - auto: 自动检测（默认）
                - iso8601: ISO 8601格式
                - cnn_date: CNN特定格式
                - bbc_date: BBC特定格式
                - relative: 相对时间

        Returns:
            datetime对象，失败返回None

        Examples:
            >>> DateParser.parse('2024-12-21T10:30:00Z')
            datetime(2024, 12, 21, 10, 30, 0)

            >>> DateParser.parse('5 minutes ago')
            datetime(2024, 12, 21, 10, 25, 0)  # 相对于当前时间
        """
        if not date_string:
            return None

        date_string = date_string.strip()

        # 根据类型选择解析器
        if parser_type == "iso8601":
            return DateParser._parse_iso8601(date_string)
        elif parser_type == "cnn_date":
            return DateParser._parse_cnn_date(date_string)
        elif parser_type == "bbc_date":
            return DateParser._parse_bbc_date(date_string)
        elif parser_type == "relative":
            return DateParser._parse_relative_time(date_string)
        else:
            # 自动检测格式
            return DateParser._auto_parse(date_string)

    @staticmethod
    def _parse_iso8601(date_string: str) -> Optional[datetime]:
        """
        解析ISO 8601格式

        支持格式:
            - 2024-12-21T10:30:00Z
            - 2024-12-21T10:30:00+08:00
            - 2024-12-21T10:30:00.123456Z
        """
        try:
            # 移除末尾的Z并替换为+00:00
            if date_string.endswith("Z"):
                date_string = date_string[:-1] + "+00:00"

            return datetime.fromisoformat(date_string)
        except Exception as e:
            logger.debug(f"ISO8601解析失败: {date_string}, {e}")
            return None

    @staticmethod
    def _parse_cnn_date(date_string: str) -> Optional[datetime]:
        """
        解析CNN特有格式

        支持格式:
            - Updated 10:30 AM EST, Thu December 21, 2024
            - Published 3:45 PM GMT, Monday, December 21, 2024
        """
        try:
            # 提取时间和日期部分
            pattern = r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*\w+,\s*(?:\w+,?\s+)?(\w+)\s+(\d{1,2}),\s+(\d{4})"
            match = re.search(pattern, date_string, re.IGNORECASE)

            if match:
                hour, minute, ampm, month_name, day, year = match.groups()

                # 转换12小时制到24小时制
                hour = int(hour)
                if ampm.upper() == "PM" and hour != 12:
                    hour += 12
                elif ampm.upper() == "AM" and hour == 12:
                    hour = 0

                # 获取月份数字
                month = DateParser.MONTH_MAPPING.get(month_name.lower())
                if not month:
                    logger.warning(f"未识别的月份: {month_name}")
                    return None

                return datetime(
                    year=int(year),
                    month=month,
                    day=int(day),
                    hour=hour,
                    minute=int(minute),
                )
        except Exception as e:
            logger.debug(f"CNN日期解析失败: {date_string}, {e}")

        return None

    @staticmethod
    def _parse_bbc_date(date_string: str) -> Optional[datetime]:
        """
        解析BBC特有格式

        支持格式:
            - 21 December 2024
            - 3 hours ago
            - December 21, 2024
        """
        # 先尝试相对时间
        relative_time = DateParser._parse_relative_time(date_string)
        if relative_time:
            return relative_time

        try:
            # 解析绝对时间: DD Month YYYY 或 Month DD, YYYY

            # 格式1: 21 December 2024
            pattern1 = r"(\d{1,2})\s+(\w+)\s+(\d{4})"
            match = re.search(pattern1, date_string)

            if match:
                day, month_name, year = match.groups()
                month = DateParser.MONTH_MAPPING.get(month_name.lower())

                if month:
                    return datetime(year=int(year), month=month, day=int(day))

            # 格式2: December 21, 2024
            pattern2 = r"(\w+)\s+(\d{1,2}),?\s+(\d{4})"
            match = re.search(pattern2, date_string)

            if match:
                month_name, day, year = match.groups()
                month = DateParser.MONTH_MAPPING.get(month_name.lower())

                if month:
                    return datetime(year=int(year), month=month, day=int(day))
        except Exception as e:
            logger.debug(f"BBC日期解析失败: {date_string}, {e}")

        return None

    @staticmethod
    def _parse_relative_time(date_string: str) -> Optional[datetime]:
        """
        解析相对时间

        支持格式:
            - 5 minutes ago
            - 2 hours ago
            - yesterday
            - just now
        """
        date_lower = date_string.lower()

        # 检查固定模式
        for pattern, value in DateParser.RELATIVE_PATTERNS.items():
            if pattern in date_lower:
                if isinstance(value, int):
                    # 固定分钟数
                    return datetime.now() - timedelta(minutes=value)
                else:
                    # 需要提取数字
                    numbers = re.findall(r"\d+", date_string)
                    if numbers:
                        num = int(numbers[0])

                        if value == "minutes":
                            return datetime.now() - timedelta(minutes=num)
                        elif value == "hours":
                            return datetime.now() - timedelta(hours=num)
                        elif value == "days":
                            return datetime.now() - timedelta(days=num)
                        elif value == "weeks":
                            return datetime.now() - timedelta(weeks=num)
                        elif value == "months":
                            # 近似计算，1个月=30天
                            return datetime.now() - timedelta(days=num * 30)
                        elif value == "years":
                            # 近似计算，1年=365天
                            return datetime.now() - timedelta(days=num * 365)

        return None

    @staticmethod
    def _parse_common_formats(date_string: str) -> Optional[datetime]:
        """
        尝试常见日期格式

        支持格式:
            - 2024-12-21 10:30:00
            - 2024-12-21
            - 21/12/2024
            - 12/21/2024
            - December 21, 2024
        """
        common_formats = [
            "%Y-%m-%d %H:%M:%S",  # 2024-12-21 10:30:00
            "%Y-%m-%d",  # 2024-12-21
            "%d/%m/%Y",  # 21/12/2024
            "%m/%d/%Y",  # 12/21/2024 (美式)
            "%d-%m-%Y",  # 21-12-2024
            "%Y/%m/%d",  # 2024/12/21
            "%B %d, %Y",  # December 21, 2024
            "%b %d, %Y",  # Dec 21, 2024
            "%d %B %Y",  # 21 December 2024
            "%d %b %Y",  # 21 Dec 2024
            "%Y-%m-%d %H:%M:%S.%f",  # 2024-12-21 10:30:00.123456
        ]

        for fmt in common_formats:
            try:
                return datetime.strptime(date_string, fmt)
            except:
                continue

        return None

    @staticmethod
    def _auto_parse(date_string: str) -> Optional[datetime]:
        """
        自动检测并解析日期格式
        按优先级尝试各种格式

        Args:
            date_string: 日期字符串

        Returns:
            datetime对象或None
        """
        # 解析器优先级列表
        parsers = [
            DateParser._parse_iso8601,  # ISO标准格式（最常见）
            DateParser._parse_relative_time,  # 相对时间
            DateParser._parse_common_formats,  # 常见格式
            DateParser._parse_cnn_date,  # 特定网站格式
            DateParser._parse_bbc_date,  # 特定网站格式
        ]

        for parser in parsers:
            try:
                result = parser(date_string)
                if result:
                    logger.debug(f"成功解析日期: {date_string} -> {result}")
                    return result
            except Exception as e:
                logger.debug(f"解析器 {parser.__name__} 失败: {e}")
                continue

        logger.warning(f"无法解析日期: {date_string}")
        return None


def parse_date(date_string: str, parser_type: str = "auto") -> Optional[datetime]:
    """
    便捷的日期解析函数

    Args:
        date_string: 日期字符串
        parser_type: 解析器类型（默认auto）

    Returns:
        datetime对象或None

    Examples:
        >>> parse_date('2024-12-21T10:30:00Z')
        datetime(2024, 12, 21, 10, 30, 0)

        >>> parse_date('5 hours ago')
        datetime(...)  # 5小时前的时间
    """
    return DateParser.parse(date_string, parser_type)


if __name__ == "__main__":
    # 测试代码
    test_dates = [
        "2024-12-21T10:30:00Z",
        "5 minutes ago",
        "Updated 10:30 AM EST, Thu December 21, 2024",
        "21 December 2024",
        "December 21, 2024",
        "yesterday",
    ]

    print("日期解析测试:")
    print("-" * 60)
    for date_str in test_dates:
        result = parse_date(date_str)
        print(f"{date_str:45} -> {result}")
