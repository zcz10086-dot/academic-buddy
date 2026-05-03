import fitz
from typing import List
import os

def parse_pdf(file_path: str) -> dict:
    """解析PDF，返回 {title, authors, abstract, chunks}"""
    doc = fitz.open(file_path)
    
    # 提取元数据（第一页通常有标题）
    title = ""
    authors = ""
    abstract = ""
    full_text = ""
    
    for i, page in enumerate(doc):
        text = page.get_text()
        full_text += text + "\n"
        
        # 尝试从第一页提取标题
        if i == 0 and not title:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if len(lines) > 0:
                title = lines[0][:200]
            if len(lines) > 1:
                authors = lines[1][:200]
    
    # 尝试提取摘要（找 "Abstract" 标记）
    abs_idx = full_text.lower().find("abstract")
    if abs_idx != -1:
        abs_end = full_text.lower().find("introduction", abs_idx)
        if abs_end == -1:
            abs_end = abs_idx + 2000
        abstract = full_text[abs_idx:abs_end].strip()
    
    # 分块: 每块 ~1000字，按段落边界
    chunks = []
    current = ""
    for para in full_text.split('\n\n'):
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) > 1000:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para
    if current:
        chunks.append(current.strip())
    
    # 限制总块数（太大的论文只保留前50块）
    chunks = chunks[:50]
    
    doc.close()
    
    return {
        "title": title or "未知标题",
        "authors": authors or "未知作者",
        "abstract": abstract or "未提取到摘要",
        "chunks": chunks,
        "total_chunks": len(chunks),
    }
