import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
from functools import lru_cache

class SearchEngine:
    def __init__(self, headers: Dict[str, str], proxies: Optional[Dict[str, str]] = None):
        self.headers = headers
        self.proxies = proxies

    @lru_cache(maxsize=100)
    def search(self, query: str, engine: str = 'google', engine_id: int = 1) -> List[Dict[str, str]]:
        search_functions = {
            'google': self._google_search,
            'bing': self._bing_search,
            'baidu': self._baidu_search
        }
        
        search_function = search_functions.get(engine.lower())
        if not search_function:
            raise ValueError(f"Unsupported search engine: {engine}")
        
        return search_function(query, engine_id)

    def _google_search(self, query: str, engine_id: int) -> List[Dict[str, str]]:
        if engine_id == 1:
            url = f"https://www.google.com/search?q={query}"
            soup = self._get_soup(url)
            return self._parse_google_results(soup)
        elif engine_id == 2:
            url = "https://lite.duckduckgo.com/lite/"
            data = {"q": query}
            soup = self._get_soup(url, method='post', data=data)
            return self._parse_duckduckgo_results(soup)
        else:
            raise ValueError(f"Unsupported Google search engine ID: {engine_id}")

    def _bing_search(self, query: str, _: int) -> List[Dict[str, str]]:
        url = f"https://www.bing.com/search?q={query}"
        soup = self._get_soup(url)
        return self._parse_bing_results(soup)

    def _baidu_search(self, query: str, _: int) -> List[Dict[str, str]]:
        url = f"https://www.baidu.com/s?wd={query}"
        soup = self._get_soup(url)
        return self._parse_baidu_results(soup)

    def _get_soup(self, url: str, method: str = 'get', **kwargs) -> BeautifulSoup:
        try:
            if method == 'get':
                response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=30, **kwargs)
            elif method == 'post':
                response = requests.post(url, headers=self.headers, proxies=self.proxies, timeout=30, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logging.error(f"Error fetching URL {url}: {str(e)}")
            raise

    def _parse_google_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        results = []
        for g in soup.find_all('div', class_='g'):
            anchors = g.find_all('a')
            if anchors:
                link = anchors[0]['href']
                if link.startswith('/url?q='):
                    link = link[7:]
                if not link.startswith('http'):
                    continue
                title = g.find('h3').text
                results.append({'title': title, 'link': link})
        return results

    def _parse_duckduckgo_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        results = []
        for g in soup.find_all("a"):
            results.append({'title': g.text, 'link': g['href']})
        return results

    def _parse_bing_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        results = []
        for b in soup.find_all('li', class_='b_algo'):
            anchors = b.find_all('a')
            if anchors:
                link = next((a['href'] for a in anchors if 'href' in a.attrs), None)
                if link:
                    title = b.find('h2').text
                    results.append({'title': title, 'link': link})
        return results

    def _parse_baidu_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        results = []
        for b in soup.find_all('div', class_='result'):
            anchors = b.find_all('a')
            if anchors:
                link = anchors[0]['href']
                title = b.find('h3').text
                if link.startswith('/link?url='):
                    link = "https://www.baidu.com" + link
                results.append({'title': title, 'link': link})
        return results

    def get_content(self, url: str) -> Optional[str]:
        try:
            soup = self._get_soup(url)
            paragraphs = soup.find_all(['p', 'span'])
            content = ' '.join([p.get_text() for p in paragraphs])
            return self._trim_content(content)
        except Exception as e:
            logging.error(f"Error fetching content from {url}: {str(e)}")
            return None

    @staticmethod
    def _trim_content(content: str, max_length: int = 8000) -> str:
        if len(content) <= max_length:
            return content
        start = (len(content) - max_length) // 2
        return content[start:start + max_length]

    def get_summaries(self, query: str, engine: str = 'google', engine_id: int = 1, count: int = 3) -> List[str]:
        search_results = self.search(query, engine, engine_id)
        summaries = []
        for result in search_results[:count]:
            content = self.get_content(result['link'])
            if content and len(content) >= 50:
                summaries.append(content)
        return summaries

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        'Content-Type': 'text/plain',
    }
    proxies = None  # 如果需要代理，请取消注释并填写正确的代理信息
    # proxies = {
    #     "http": "http://127.0.0.1:10809",
    #     "https": "http://127.0.0.1:10809",
    #     "socks5": "socks://127.0.0.1:10808"
    # }

    search_engine = SearchEngine(headers, proxies)
    query = "伊卡洛斯"
    engine = "baidu"
    engine_id = 1
    count = 3

    summaries = search_engine.get_summaries(query, engine, engine_id, count)
    for i, summary in enumerate(summaries, 1):
        print(f"Summary {i}:\n{summary}\n")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()