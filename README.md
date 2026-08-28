# 前言

联网通过搜索引擎搜索指定内容，进入对应页面获取文本内容。  
支持**百度、搜狗、必应、360** 多个国内主流搜索引擎，内置自动降级机制——任一引擎被反爬拦截时自动切换下一个。

---

# 开发环境

python：3.10.10  
操作系统：win11  

---

# 功能特性

- **多引擎支持**：百度 / 搜狗 / 必应 / 360（通过 `config.json` 配置优先级）
- **自动降级**：搜索引擎触发验证码或返回空结果时，自动尝试下一个引擎
- **广告过滤**：自动识别并跳过推广页、PDF 文件、低质量站点
- **智能缓存**：搜索结果可配置 LRU 缓存，减少重复请求
- **详细日志**：基于 loguru，支持终端彩色输出 + 文件持久化

---

# 使用

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置文件

根目录新建 `config.json`，示例如下：

```json
{
  "engine": "baidu",
  "engine_id": 1,
  "engine_priority": ["baidu", "sogou", "bing", "so"],
  "count": 3,
  "proxies": {
    "http": "",
    "https": ""
  },
  "request": {
    "timeout": 30,
    "max_retries": 3,
    "retry_backoff": 1,
    "min_content_length": 200,
    "max_content_length": 8000
  }
}
```

### 配置项说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `engine` | 默认使用的搜索引擎 | `"baidu"` |
| `engine_id` | Google 专用 ID（1=Google, 2=DuckDuckGo） | `1` |
| `engine_priority` | 搜索引擎优先级列表，按顺序尝试 | `["baidu", "sogou", "bing", "so"]` |
| `count` | 每次搜索获取的摘要数量 | `3` |
| `proxies.http` | HTTP 代理地址（留空不使用代理） | `""` |
| `proxies.https` | HTTPS 代理地址（留空不使用代理） | `""` |
| `request.timeout` | HTTP 请求超时时间（秒） | `30` |
| `request.max_retries` | 单次请求最大重试次数 | `3` |
| `request.retry_backoff` | 重试退避间隔（秒，指数增长） | `1` |
| `request.min_content_length` | 最低有效内容长度（字符数），低于此值视为垃圾内容 | `200` |
| `request.max_content_length` | 单条摘要最大长度（字符数），超出则截断 | `8000` |

## 运行

```bash
python main.py
```

程序会：
1. 读取 `config.json` 中的配置
2. 按 `engine_priority` 顺序尝试搜索引擎
3. 若当前引擎被验证码拦截/返回空结果，自动降级到下一个
4. 成功获取搜索结果后，抓取每个结果的正文内容
5. 将摘要打印到终端，同时写入 `日志.txt`

## 代码调用示例

```python
from main import SearchEngine, load_config
from utils.config import load_config

# 方式 1：使用配置文件
config = load_config("config.json")
se = SearchEngine(config=config)

# 方式 2：编程式调用
se = SearchEngine(
    proxies={"http": "http://127.0.0.1:10809"},
    config={"request": {"timeout": 60}}
)

# 指定单个引擎搜索
results = se.search("人工智能", engine="baidu")
for r in results[:5]:
    print(r['title'], r['link'])

# 使用降级搜索（推荐）
results = se.search_with_fallback(
    "人工智能",
    engine_priority=["baidu", "sogou", "bing"]
)

# 获取带降级的摘要
summaries = se.get_summaries_with_fallback(
    "人工智能",
    engine_priority=["baidu", "sogou", "bing", "so"],
    count=3
)
```

---

# 更新日志

## 2024-XX-XX（最新）
- **新增多引擎支持**：搜狗、360 搜索器已实现并通过测试
- **配置文件驱动**：`config.json` 统一管理引擎优先级、代理、超时等参数
- **自动降级机制**：引擎 A 失败自动切换引擎 B，提升可用性
- **百度搜索优化**：增加验证码页面检测，触发反爬时抛出明确异常而非静默返回空结果
- **必应 URL 解码**：从 tracking link 的 base64 参数中还原真实 URL，避免抓取中间页
- **广告与低质过滤**：跳过 PDF/EPUB 下载链接、百度百科反爬站、广告空壳页
- **内容质量提升**：有效内容阈值提升至 200 字，过滤登录页/403 页面
- 端到端测试结果：必应 7/7 全中，搜狗/360 正常可用

## 2024-9-27
- 更换日志为 loguru
- 完善注释

## 2024-9-26
- 补充百度和 bing，bing 暂有 bug
- 一键规范源码并封装

## 2024-2-20
- 初版发布

---

# 借鉴项目

- [NetworkPlugin](https://github.com/haikerapples/NetworkPlugin)
- [chatgptplugin](https://github.com/CatAnd-Dog/chatgptplugin)