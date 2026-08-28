import json
import os
from typing import Any, Optional


def load_config(config_file: str = "config.json") -> dict:
    """
    加载配置文件，文件不存在或格式错误时返回空字典。

    :param config_file: 配置文件路径
    :return: 配置字典
    """
    if not os.path.exists(config_file):
        return {}
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"配置文件 {config_file} 解析失败：{e}")
        return {}


class Config:
    config = None

    def __init__(self, config_file):
        if self.config is None:
            with open(config_file, 'r', encoding="utf-8") as f:
                self.config = json.load(f)

    def get(self, *keys):
        result = self.config
        for key in keys:
            result = result.get(key, None)
            if result is None:
                break
        return result