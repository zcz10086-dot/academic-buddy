import os
from pathlib import Path
import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# 尝试导入 httpx（全局安装可能失败，兼容本地运行）
try:
    import httpx
except ImportError:
    httpx = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="学搭子 - Academic Buddy")

# 静态文件
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "reports.json"

# ---------- 数据层 ----------

def _load_reports() -> list:
    if DB_PATH.exists():
        with open(DB_PATH) as f:
            return json.load(f)
    return []

def _save_reports(reports: list):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

# ---------- 模型 ----------

class TopicRequest(BaseModel):
    topic: str
    background: Optional[str] = ""
    constraint: Optional[str] = ""

class TopicReport(BaseModel):
    id: int
    topic_input: str
    research_overview: str
    feasibility_score: int
    innovation_gap: str
    first_step: str
    references: list
    llm_raw: str  # 原始LLM回复，便于调试
    created_at: str
    disclaimer: str = "⚠️ 以下引用为AI生成，请手动核实后再使用。"

# ---------- LLM Prompt 模板 ----------

SYSTEM_PROMPT = """你是一个科研选题顾问。你的工作是为本科生提供一个研究方向的结构化分析。

请用中文回答。输出格式必须是严格的JSON，不要包含任何额外文字。格式如下：

```json
{
  "research_overview": "该方向的现状概述（2-3句话）",
  "feasibility_score": 0-100的整数，表示本科生做这个方向的可行性,
  "innovation_gap": "创新空间分析，说明还有哪些可以做的事情（2-3句话）",
  "first_step": "最具体的、可执行的第一步建议，比如'先读哪篇论文'或'先实现什么代码'",
  "references": [
    {
      "title": "论文标题",
      "authors": "作者",
      "venue": "会议/期刊/arXiv 年份",
      "url": "arXiv或PDF链接"
    }
  ]
}
```

约束：
- feasibility_score 要考虑：本科生知识背景、计算资源、导师支持需求
- 如果方向太宽泛，请先引导用户聚焦
- 参考文献尽量选择2022年以后的顶会论文
- 如果用户背景为空，在分析中考虑到入门者的水平
- 如果提供约束条件，请尊重用户约束

请只返回JSON，不要添加markdown代码块标记或其他文字。"""

def _build_prompt(req: TopicRequest) -> str:
    parts = [f"研究方向：{req.topic}"]
    if req.background:
        parts.append(f"已有知识背景：{req.background}")
    if req.constraint:
        parts.append(f"限制条件：{req.constraint}")
    return "\n".join(parts)

def _analyze_with_llm(req: TopicRequest) -> dict:
    """调用 LLM API 进行分析"""
    user_prompt = _build_prompt(req)

    # 尝试使用 httpx 调用大模型API
    # 优先读取环境变量中的 API 配置
    api_key = os.environ.get("LLM_API_KEY", "")
    api_url = os.environ.get("LLM_API_URL", "")
    model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    fallback_result = {
        "research_overview": f"关于「{req.topic}」方向的研究现状分析",
        "feasibility_score": 65,
        "innovation_gap": "该方向仍有探索空间，建议查阅最新论文确定具体切入点。",
        "first_step": f"1. 在 arXiv/Google Scholar 搜索「{req.topic}」相关的最新综述论文\n"
                      f"2. 阅读3-5篇高引论文的摘要，了解该方向的子问题\n"
                      f"3. 选择一个具体子问题作为切入点",
        "references": [
            {
                "title": "请手动在 arXiv 搜索相关论文",
                "authors": "—",
                "venue": "—",
                "url": f"https://arxiv.org/search/?query={req.topic.replace(' ', '+')}&searchtype=all"
            }
        ]
    }

    if not httpx:
        logger.warning("httpx not installed, using fallback result")
        return fallback_result

    if not api_key:
        # 尝试从其他变量读取
        for key in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "ARK_API_KEY"]:
            if os.environ.get(key):
                api_key = os.environ[key]
                break

    if not api_key:
        logger.warning("No API key found, using fallback result")
        return fallback_result

    # 构造请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    is_deepseek = "deepseek" in model_name.lower() or "deepseek" in api_url.lower()

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    # DeepSeek 不支持 response_format，用 prompt 约束 JSON 输出
    if not is_deepseek:
        payload["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(api_url, json=payload, headers=headers)

        if resp.status_code != 200:
            logger.error(f"LLM API error: {resp.status_code} {resp.text[:200]}")
            return fallback_result

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # 解析 JSON
        result = json.loads(content)
        # 确保有所有字段
        result.setdefault("feasibility_score", 50)
        result.setdefault("references", [])
        return result

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return fallback_result

def _get_next_id(reports: list) -> int:
    return max([r["id"] for r in reports], default=0) + 1

# ---------- API 路由 ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = frontend_dir / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>学搭子后端已启动</h1><p>前端文件未找到</p>")

@app.post("/api/topic/analyze")
async def analyze_topic(req: TopicRequest):
    """分析一个研究方向（自动记录到历史）"""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="研究方向不能为空")

    result = _analyze_with_llm(req)

    report = {
        "id": _get_next_id(_load_reports()),
        "topic_input": req.topic,
        "background": req.background,
        "constraint": req.constraint,
        "research_overview": result.get("research_overview", ""),
        "feasibility_score": result.get("feasibility_score", 50),
        "innovation_gap": result.get("innovation_gap", ""),
        "first_step": result.get("first_step", ""),
        "references": result.get("references", []),
        "llm_raw": json.dumps(result, ensure_ascii=False),
        "created_at": datetime.now().isoformat(),
        "disclaimer": "⚠️ 以下引用为AI生成，请手动核实后再使用。",
        "favorited": False,
    }

    # 自动保存到记录
    reports = _load_reports()
    reports.append(report)
    _save_reports(reports)

    return report

@app.post("/api/topic/favorite")
async def favorite_topic(data: dict):
    """收藏/取消收藏选题"""
    reports = _load_reports()
    rid = data.get("id")
    fav = data.get("favorite", True)
    for r in reports:
        if r["id"] == rid:
            r["favorited"] = fav
            _save_reports(reports)
            return {"status": "ok", "favorited": fav}
    raise HTTPException(status_code=404, detail="未找到")

@app.get("/api/topic/favorites")
async def list_favorites():
    """获取所有收藏的选题（首页显示）"""
    reports = _load_reports()
    return [
        {
            "id": r["id"],
            "display_title": r.get("research_overview", r.get("topic_input", ""))[:50],
            "topic_input": r.get("topic_input", ""),
            "feasibility_score": r.get("feasibility_score", 0),
            "created_at": r.get("created_at", ""),
        }
        for r in reversed(reports) if r.get("favorited")
    ]

@app.get("/api/topic/history")
async def list_history():
    """获取所有选题记录"""
    reports = _load_reports()
    return [
        {
            "id": r["id"],
            "topic_input": r.get("topic_input", ""),
            "feasibility_score": r.get("feasibility_score", 0),
            "created_at": r.get("created_at", ""),
        }
        for r in reversed(reports)
    ]

@app.get("/api/topic/{topic_id}")
async def get_topic(topic_id: int):
    """获取单个选题报告"""
    reports = _load_reports()
    for r in reports:
        if r["id"] == topic_id:
            return r
    raise HTTPException(status_code=404, detail="选题报告未找到")

@app.delete("/api/topic/{topic_id}")
async def delete_topic(topic_id: int):
    """删除选题报告"""
    reports = _load_reports()
    for i, r in enumerate(reports):
        if r["id"] == topic_id:
            del reports[i]
            _save_reports(reports)
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="选题报告未找到")

# ---------- Integrity Check (Phase 3) ----------

INTEGRITY_PROMPT = """你是一个学术诚信专家。你的工作是判断一段学术写作行为是否构成学术不端。

给定内容：
{text}

用户意图：{intent}

学校政策：{policy_name}
- 允许范围：{allow}
- 禁止范围：{forbid}

请从以下维度分析：
1. 这段内容/行为是否违反该学校政策
2. 风险等级：safe（安全）/ edge（边缘，建议咨询导师）/ risk（违规风险高）
3. 风险分数：0-100
4. 具体原因（引用政策相关条款）
5. 建议操作

输出严格JSON格式：
{{
  "risk_level": "safe/edge/risk",
  "risk_score": 0-100,
  "explanation": "详细分析原因",
  "suggestion": "具体建议操作",
  "policy_ref": "引用的政策原文"
}}
"""

@app.post("/api/integrity/check")
async def integrity_check(data: dict):
    """AI边界裁判：判断一段学术行为是否违规"""
    text = data.get("text", "")
    intent = data.get("intent", "其他")
    school = data.get("school_policy", "general")

    # 加载学校政策
    policy_path = Path(__file__).parent / "data" / "school_policies.json"
    policies = {}
    if policy_path.exists():
        with open(policy_path) as f:
            policies = json.load(f)
    policy = policies.get(school, policies.get("general", {}))

    if not text.strip():
        return {
            "risk_level": "edge",
            "risk_score": 50,
            "explanation": "没有提供待检测的文本。请选中一段论文内容后再试。",
            "suggestion": "请先选中需要检测的文本段落",
            "policy_ref": ""
        }

    from llm_service import call_llm
    prompt_text = INTEGRITY_PROMPT.format(
        text=text[:2000],
        intent=intent,
        policy_name=policy.get("name", "通用指南"),
        allow=policy.get("allow", "通用"),
        forbid=policy.get("forbid", "通用"),
    )
    sp = "你是一个学术诚信专家。输出严格JSON格式的判断。"
    raw = call_llm(prompt_text, max_tokens=1000, system_prompt=sp)

    if raw:
        try:
            result = json.loads(raw)
        except:
            result = {}
    else:
        result = {}

    return {
        "risk_level": result.get("risk_level", "edge"),
        "risk_score": result.get("risk_score", 50),
        "explanation": result.get("explanation", "无法判断，建议咨询导师或查阅学校政策"),
        "suggestion": result.get("suggestion", "建议咨询导师"),
        "policy_ref": result.get("policy_ref", policy.get("source", "")),
    }

# ---------- Paper Reading Routes (Phase 2) ----------
try:
    from paper_routes import router as paper_router
    app.include_router(paper_router)
    logger.info("[INFO] Paper routes registered")
except Exception as e:
    logger.warning(f"[WARN] Paper routes not loaded: {e}")

# ---------- 启动 ----------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=port)
    except ImportError:
        # 降级: 用标准库 http.server
        import json
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class FastAPIWrapper(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/":
                    html_path = frontend_dir / "index.html"
                    if html_path.exists():
                        self.send_response(200)
                        self.send_header("Content-type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(html_path.read_bytes())
                    else:
                        self.send_response(200)
                        self.send_header("Content-type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(b"<h1>Running</h1>")
                elif self.path.startswith("/api/"):
                    # Route to ASGI app via simple WSGI wrapper
                    self.send_response(200)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "uvicorn required for API"}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def log_message(self, format, *args):
                logger.info(f"{self.client_address[0]} - {format % args}")

        server = HTTPServer(("0.0.0.0", port), FastAPIWrapper)
        logger.info(f"Fallback HTTP server on http://0.0.0.0:{port} (API disabled)")
        server.serve_forever()
