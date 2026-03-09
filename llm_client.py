import os
import json
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from openai import OpenAI


# 加载环境变量（如 ARK_API_KEY、ARK_BASE_URL 等）
load_dotenv()


_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """
    统一获取底层大模型客户端。
    未来如果要切换到其他厂商，只需在这里替换实现。
    """
    global _client
    if _client is None:
        # 优先使用火山方舟 Ark / 豆包的配置
        base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        api_key = os.getenv("ARK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("未找到 ARK_API_KEY（或 OPENAI_API_KEY）环境变量，请先在 .env 或系统环境中配置。")

        _client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
    return _client


def chat_json(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    封装后的统一大模型调用接口（豆包 / 火山方舟，兼容 OpenAI SDK 调用方式）。

    - 入参：标准 OpenAI 风格的 messages 列表。
    - 出参：自动将模型返回的 JSON 字符串解析为 Python dict。
    - 模型名称：
        - 优先使用显式传入的 model 参数；
        - 否则使用环境变量 ARK_MODEL；
        - 如果都未设置，则抛错提醒配置。
    """
    client = _get_client()

    # 模型名称优先级：参数 > 环境变量
    final_model = model or os.getenv("ARK_MODEL")
    if not final_model:
        raise RuntimeError(
            "未配置豆包模型名称：请在调用 chat_json 时传入 model，"
            "或在环境变量 / .env 中设置 ARK_MODEL 为推理接入点 ID（如 ep-xxxx）。"
        )

    try:
        # 尝试使用 JSON Mode (OpenAI 兼容接口)
        completion = client.chat.completions.create(
            model=final_model,
            messages=messages,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        # 如果模型不支持 JSON Mode (例如某些旧版本)，尝试普通文本生成
        print(f"Warning: JSON Mode failed ({e}), retrying without response_format...")
        completion = client.chat.completions.create(
            model=final_model,
            messages=messages,
        )

    content = completion.choices[0].message.content
    
    # 清理可能存在的 Markdown 代码块标记
    if content.strip().startswith("```json"):
        content = content.strip().removeprefix("```json").removesuffix("```").strip()
    elif content.strip().startswith("```"):
        content = content.strip().removeprefix("```").removesuffix("```").strip()
        
    return json.loads(content)

