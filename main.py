import requests
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Optional
from functools import lru_cache
from urllib.parse import quote_plus
import time


class SearchEngine:
    """
    搜索引擎类，用于执行网络搜索并获取结果摘要。
    支持Google、Bing和Baidu搜索引擎。
    """

    # 类级别常量
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_BACKOFF = 1  # 秒，指数退避基数

    def __init__(self, headers: Optional[Dict[str, str]] = None, proxies: Optional[Dict[str, str]] = None):
        """
        初始化搜索引擎实例。

        :param headers: 请求头，用于模拟浏览器行为（未提供时使用默认值）
        :param proxies: 代理设置（可选）
        """
        self.headers = {**self.DEFAULT_HEADERS, **(headers or {})}
        self.proxies = proxies

    @lru_cache(maxsize=100)
    def search(self, query: str, engine: str = 'google', engine_id: int = 1) -> List[Dict[str, str]]:
        """
        执行搜索并返回结果。

        :param query: 搜索查询
        :param engine: 搜索引擎名称（google、bing或baidu）
        :param engine_id: 搜索引擎ID（仅用于Google）
        :return: 搜索结果列表，每个结果包含标题和链接
        """
        search_functions = {
            'google': self._google_search,
            'bing': self._bing_search,
            'baidu': self._baidu_search
        }

        search_function = search_functions.get(engine.lower())
        if not search_function:
            raise ValueError(f"不支持的搜索引擎：{engine}")

        return search_function(query, engine_id)

    def _google_search(self, query: str, engine_id: int) -> List[Dict[str, str]]:
        """执行Google搜索"""
        encoded_query = quote_plus(query)
        if engine_id == 1:
            url = f"https://www.google.com/search?q={encoded_query}"
            soup = self._get_soup(url)
            return self._parse_google_results(soup)
        elif engine_id == 2:
            url = "https://lite.duckduckgo.com/lite/"
            data = {"q": query}
            soup = self._get_soup(url, method='post', data=data)
            return self._parse_duckduckgo_results(soup)
        else:
            raise ValueError(f"不支持的Google搜索引擎ID：{engine_id}")

    def _bing_search(self, query: str, _: int) -> List[Dict[str, str]]:
        """执行Bing搜索"""
        encoded_query = quote_plus(query)
        url = f"https://www.bing.com/search?q={encoded_query}"
        soup = self._get_soup(url)
        return self._parse_bing_results(soup)

    def _baidu_search(self, query: str, _: int) -> List[Dict[str, str]]:
        """执行百度搜索"""
        encoded_query = quote_plus(query)
        url = f"https://www.baidu.com/s?wd={encoded_query}"
        soup = self._get_soup(url)
        return self._parse_baidu_results(soup)

    def _get_soup(self, url: str, method: str = 'get', **kwargs) -> BeautifulSoup:
        """
        获取网页内容并解析为BeautifulSoup对象，带重试机制。

        :param url: 目标URL
        :param method: HTTP方法（get或post）
        :param kwargs: 其他请求参数
        :return: BeautifulSoup对象
        """
        last_exception = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self._do_request(url, method, **kwargs)
                self._check_content_type(response, url)
                return BeautifulSoup(response.content, 'html.parser')

            except requests.exceptions.HTTPError as e:
                # 4xx 客户端错误不重试
                if 400 <= e.response.status_code < 500:
                    logger.warning(f"HTTP {e.response.status_code} 访问 {url}: {e.response.reason}")
                    raise
                # 5xx 服务器错误，继续重试
                last_exception = e
                logger.warning(f"HTTP {e.response.status_code} 访问 {url}，第 {attempt}/{self.MAX_RETRIES} 次重试")

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"连接错误访问 {url}，第 {attempt}/{self.MAX_RETRIES} 次重试: {e}")

            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"超时访问 {url}，第 {attempt}/{self.MAX_RETRIES} 次重试: {e}")

            except requests.exceptions.RequestException as e:
                # 其他请求异常不重试
                logger.error(f"访问 {url} 时发生不可恢复错误：{str(e)}")
                raise

            # 指数退避
            if attempt < self.MAX_RETRIES:
                wait_time = self.RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.info(f"等待 {wait_time}s 后重试...")
                time.sleep(wait_time)

        # 所有重试都失败了
        raise last_exception  # type: ignore[misc]

    def _do_request(self, url: str, method: str = 'get', **kwargs) -> requests.Response:
        """执行单次 HTTP 请求"""
        if method == 'get':
            response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=self.DEFAULT_TIMEOUT, **kwargs)
        elif method == 'post':
            response = requests.post(url, headers=self.headers, proxies=self.proxies, timeout=self.DEFAULT_TIMEOUT, **kwargs)
        else:
            raise ValueError(f"不支持的HTTP方法：{method}")

        response.raise_for_status()
        return response

    @staticmethod
    def _check_content_type(response: requests.Response, url: str):
        """检查响应的 Content-Type 是否为 HTML"""
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type and 'application/xhtml' not in content_type:
            logger.warning(f"URL {url} 返回了非HTML内容 (Content-Type: {content_type})")

    def _parse_google_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析Google搜索结果"""
        results = []
        for g in soup.find_all('div', class_='g'):
            anchors = g.find_all('a')
            if anchors:
                link = anchors[0]['href']
                if link.startswith('/url?q='):
                    link = link[7:]
                if not link.startswith('http'):
                    continue
                title_tag = g.find('h3')
                if not title_tag:
                    continue  # 跳过没有标题的结果
                title = title_tag.text
                results.append({'title': title, 'link': link})
        return results

    def _parse_duckduckgo_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析DuckDuckGo搜索结果"""
        results = []
        seen_links = set()  # 去重

        for a in soup.find_all("a", href=True):
            href = a['href']
            text = (a.text or '').strip()

            # 排除 DuckDuckGo 内部导航链接
            if href.startswith('/search?q=') or href.startswith('//duckduckgo.com'):
                continue

            # 必须有有效文本才保留
            if not text or len(text) < 2:
                continue

            # 去重
            if href in seen_links:
                continue
            seen_links.add(href)

            results.append({'title': text, 'link': href})

        return results

    def _parse_bing_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析Bing搜索结果"""
        results = []
        for b in soup.find_all('li', class_='b_algo'):
            anchors = b.find_all('a')
            if anchors:
                link = next((a['href'] for a in anchors if 'href' in a.attrs), None)
                if link:
                    h2_tag = b.find('h2')
                    if not h2_tag:
                        continue  # 跳过没有标题的结果
                    title = h2_tag.text
                    results.append({'title': title, 'link': link})
        return results

    def _parse_baidu_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析百度搜索结果"""
        results = []
        # 百度实际使用的结果类名：result-op 和 c-container
        for b in soup.find_all('div', class_=lambda c: c and c in ('result-op', 'c-container')):
            # result-op 通常直接有 h3，c-container 需要额外判断
            title_tag = b.find('h3')
            if not title_tag:
                continue  # 跳过没有标题的结果

            anchors = b.find_all('a')
            if not anchors:
                continue

            link = anchors[0]['href']
            title = title_tag.text

            # 处理百度的链接跳转问题
            if link.startswith('/link?url='):
                link = "https://www.baidu.com" + link
            elif link.startswith('/url?'):
                # /url?q=xxx&sa=... 格式
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(link)
                params = parse_qs(parsed.query)
                if 'q' in params:
                    link = params['q'][0]
                else:
                    continue

            results.append({'title': title, 'link': link})
        return results

    def get_content(self, url: str) -> Optional[str]:
        """
        获取网页内容。

        :param url: 目标URL
        :return: 网页内容文本，如果发生错误则返回None
        """
        try:
            soup = self._get_soup(url)
            # 移除脚本和样式标签
            for tag in soup(['script', 'style']):
                tag.extract()
            paragraphs = soup.find_all(['p', 'span'])
            content = ' '.join([p.get_text() for p in paragraphs])
            return self._trim_content(content)
        except Exception as e:
            logger.error(f"从 {url} 获取内容时发生错误：{str(e)}")
            return None

    @staticmethod
    def _trim_content(content: str, max_length: int = 8000) -> str:
        """
        裁剪内容至指定最大长度。

        :param content: 原始内容
        :param max_length: 最大长度
        :return: 裁剪后的内容
        """
        if len(content) <= max_length:
            return content
        start = (len(content) - max_length) // 2
        return content[start:start + max_length]

    def get_summaries(self, query: str, engine: str = 'google', engine_id: int = 1, count: int = 3) -> List[str]:
        """
        获取搜索结果的摘要。

        :param query: 搜索查询
        :param engine: 搜索引擎名称
        :param engine_id: 搜索引擎ID
        :param count: 需要获取的摘要数量
        :return: 摘要列表
        """
        search_results = self.search(query, engine, engine_id)
        summaries = []
        for result in search_results[:count]:
            content = self.get_content(result['link'])
            if content and len(content) >= 50:
                summaries.append(content)
        return summaries


def main():
    """主函数，演示搜索引擎的使用"""
    # headers 已在 SearchEngine 中使用默认值，可按需覆盖
    proxies = None  # 如果需要代理，请取消注释并填写正确的代理信息
    # proxies = {
    #     "http": "http://127.0.0.1:10809",
    #     "https": "http://127.0.0.1:10809"
    # }

    search_engine = SearchEngine(proxies=proxies)
    query = "伊卡洛斯"
    engine = "baidu"
    engine_id = 1
    count = 3

    logger.info(f"开始搜索：{query}（使用{engine}引擎）")
    summaries = search_engine.get_summaries(query, engine, engine_id, count)
    for i, summary in enumerate(summaries, 1):
        logger.info(f"摘要 {i}:\n{summary}\n")


if __name__ == '__main__':
    logger.add("日志.txt", rotation="500 MB", retention="30 days", compression="zip", encoding="utf-8")
    logger.info("搜索引擎程序启动")
    main()
    logger.info("搜索引擎程序结束")
