import os, json, logging
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个科研选题顾问。你的工作是为本科生提供一个研究方向的结构化分析。

请用中文回答。输出格式必须是严格的JSON，不要包含任何额外文字。格式如下：

{
  "research_overview": "该方向的现状概述（2-3句话）",
  "feasibility_score": 0-100的整数，表示本科生做这个方向的可行性,
  "innovation_gap": "当前研究的空白点，本科生可以切入的地方",
  "first_step": "具体的第一步行动建议（可执行的）",
  "references": [
    {"title": "论文标题", "authors": "作者", "venue": "发表会议/期刊", "url": "链接"}
  ]
}"""


def call_llm(user_prompt: str, max_tokens: int = 2000, temperature: float = 0.7, system_prompt: Optional[str] = None) -> str:
    """通用 LLM 调用，返回文本内容
    system_prompt: 可选，覆盖默认的 SYSTEM_PROMPT
    """
    api_key = os.environ.get("LLM_API_KEY", "")
    api_url = os.environ.get("LLM_API_URL", "")
    model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if not httpx:
        logger.warning("httpx not installed")
        return ""

    if not api_key:
        for key in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "ARK_API_KEY"]:
            if os.environ.get(key):
                api_key = os.environ[key]
                break

    if not api_key or not api_url:
        logger.warning("No API key or URL found")
        return ""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    is_deepseek = "deepseek" in model_name.lower() or "deepseek" in api_url.lower()

    sp = system_prompt if system_prompt else SYSTEM_PROMPT

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": sp},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if not is_deepseek:
        payload["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(api_url, json=payload, headers=headers)

        if resp.status_code != 200:
            logger.error(f"LLM API error: {resp.status_code} {resp.text[:200]}")
            return ""

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ""
