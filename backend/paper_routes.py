import logging, os, json, uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from pdf_parser import parse_pdf

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/paper", tags=["paper"])

DATA_ROOT = os.environ.get("ACADEMIC_BUDDY_DATA", "/opt/academic-buddy/data")
PAPERS_FILE = os.path.join(DATA_ROOT, "papers.json")
UPLOAD_DIR = os.path.join(DATA_ROOT, "papers")

def _load_json(path):
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

class PaperUploadResponse(BaseModel):
    id: int; title: str; authors: str; message: str

class SummarizeRequest(BaseModel):
    level: str

class SummarizeResponse(BaseModel):
    paper_id: int; level: str; content: str

@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    papers = _load_json(PAPERS_FILE)
    paper_id = len(papers) + 1
    ext = os.path.splitext(file.filename or "paper.pdf")[1] or ".pdf"
    file_path = os.path.join(UPLOAD_DIR, f"{paper_id}{ext}")
    content = await file.read()
    with open(file_path, "wb") as f: f.write(content)
    try:
        parsed = parse_pdf(file_path)
    except Exception as e:
        raise HTTPException(400, f"PDF解析失败: {str(e)}")
    
    paper = {
        "id": paper_id, "title": parsed["title"], "authors": parsed["authors"],
        "abstract": parsed["abstract"], "chunks": parsed["chunks"],
        "total_chunks": parsed["total_chunks"], "file_path": file_path,
        "created_at": datetime.now().isoformat(),
    }
    papers.append(paper)
    _save_json(PAPERS_FILE, papers)
    
    # 上传后立即后台启动精读版生成（方案二：并行加速）
    try:
        import threading
        _file_lock = threading.Lock()
        chk = paper.get("chunks", [])
        c = {}
        paper["contents"] = c
        _save_json(PAPERS_FILE, papers)
        
        def _refresh_and_save(k, v):
            with _file_lock:
                try:
                    p = _load_json(PAPERS_FILE)
                    for x in p:
                        if x["id"] == paper_id:
                            x.setdefault("contents", {})[k] = v
                            break
                    _save_json(PAPERS_FILE, p)
                except: pass
        
        # 同步生成摘要版
        if chk:
            def _gen_summary():
                try:
                    ctx = "\n\n".join(chk[:5])[:3000]
                    sp = "你是一个论文摘要助手。用中文生成400字左右的精华摘要，包含研究问题、方法、主要发现和结论。不要输出JSON或markdown。"
                    from llm_service import call_llm
                    r = call_llm(f"将以下论文内容总结为400字左右的精华摘要：\n\n{ctx}", max_tokens=800, system_prompt=sp)
                    if r: _refresh_and_save("summary", r)
                except Exception as e:
                    _logger.error(f"Summary gen failed: {e}")
            _gen_summary()
        
        # 后台立即启动精读版生成
        def _gen_detailed():
            try:
                if not chk: return
                ctx = "\n\n".join(chk[:10])[:6000]
                sp = "你是一个论文精读导师。用中文生成1500字左右的精读报告，包含：研究背景、方法论、实验结果、结论。不要使用markdown。"
                from llm_service import call_llm
                r = call_llm(f"精读分析以下论文内容，生成1500字左右的精读报告：\n\n{ctx}", max_tokens=2000, system_prompt=sp)
                if r: _refresh_and_save("detailed", r)
                _logger.info(f"Paper {paper_id}: detailed generated")
            except Exception as e:
                _logger.error(f"Detailed gen failed: {e}")
        
        t = threading.Thread(target=_gen_detailed, daemon=True)
        t.start()
        _logger.info(f"Paper {paper_id}: summary synced, detailed background started")
    except Exception as e:
        _logger.error(f"Generation init failed: {e}")
    
    return PaperUploadResponse(id=paper_id, title=paper["title"], authors=paper["authors"], message="上传成功")

@router.get("/{paper_id}")
async def get_paper(paper_id: int):
    papers = _load_json(PAPERS_FILE)
    for p in papers:
        if p["id"] == paper_id:
            return {"id": p["id"], "title": p["title"], "authors": p["authors"],
                    "abstract": p["abstract"][:500] if p["abstract"] else "",
                    "total_chunks": p["total_chunks"]}
    raise HTTPException(404, "论文不存在")

@router.get("/")
async def list_papers():
    papers = _load_json(PAPERS_FILE)
    return [{"id": p["id"], "title": p["title"], "authors": p["authors"]} for p in papers]

@router.delete("/{paper_id}")
async def delete_paper(paper_id: int):
    papers = _load_json(PAPERS_FILE)
    for i, p in enumerate(papers):
        if p["id"] == paper_id:
            fp = p.get("file_path")
            if fp and os.path.exists(fp):
                try: os.remove(fp)
                except: pass
            del papers[i]
            _save_json(PAPERS_FILE, papers)
            return {"status": "deleted"}
    raise HTTPException(404, "论文不存在")

@router.post("/{paper_id}/summarize")
async def summarize_paper(paper_id: int, req: SummarizeRequest):
    papers = _load_json(PAPERS_FILE)
    paper = None
    for p in papers:
        if p["id"] == paper_id: paper = p; break
    if not paper: raise HTTPException(404, "论文不存在")
    
    level = req.level
    contents = paper.get("contents", {})
    cached = contents.get(level, "")
    if cached:
        _logger.info(f"Paper {paper_id}: using cached {level}")
        return SummarizeResponse(paper_id=paper_id, level=level, content=cached)
    
    chunks = paper.get("chunks", [])
    if not chunks: raise HTTPException(400, "论文内容为空")
    from llm_service import call_llm
    
    if level == "summary":
        c = "\n\n".join(chunks[:5])[:3000]
        sp = "你是一个论文摘要助手。用中文生成500字左右的精华摘要，包含研究问题、方法、主要发现和结论。不要输出JSON或markdown。只用流畅的段落。"
        result = call_llm(f"将以下论文内容总结为500字左右的精华摘要：\n\n{c}", max_tokens=1000, system_prompt=sp)
    elif level == "detailed":
        c = "\n\n".join(chunks[:10])[:6000]
        sp = "你是一个论文精读导师。用中文生成2000字左右的精读分析，包含：研究背景与意义、方法论详解与创新、实验结果分析、讨论与局限性、结论与未来方向。不要使用markdown。只用中文段落。"
        result = call_llm(f"精读分析以下论文内容，生成2000字左右的精读报告：\n\n{c}", max_tokens=3000, system_prompt=sp)
    elif level == "full":
        # 完整版：LLM翻译全部chunk为中文
        c = "\n\n".join(chunks)[:8000]
        sp = "你是一个翻译助手。将以下英文论文内容逐段翻译为流畅的中文。保留专业术语。不要输出JSON或markdown。"
        result = call_llm(f"将以下论文内容逐段翻译为中文：\n\n{c}", max_tokens=4000, system_prompt=sp)
        if not result:
            # fallback: 直接展示原文
            lines = [f"【全文共 {len(chunks)} 段】"]
            for i, chunk in enumerate(chunks, start=1):
                lines.append(f"—— 第{i}段 ——\n{chunk}")
            result = "\n\n".join(lines)
    else: raise HTTPException(400, "无效的level")
    
    content = result or "生成失败，请稍后重试"
    if content:
        paper["contents"] = contents
        contents[level] = content
        _save_json(PAPERS_FILE, papers)
    
    return SummarizeResponse(paper_id=paper_id, level=level, content=content)
