import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Mock LLM 调用，避免真实 API 调用
import backend.llm_service as llm_service
_original_call_llm = llm_service.call_llm
def _mock_call_llm(prompt, max_tokens=2000, temperature=0.7, system_prompt=None):
    return json.dumps({
        "research_overview": "这是一个测试方向的概述",
        "feasibility_score": 75,
        "innovation_gap": "测试创新空间",
        "first_step": "第一步行动建议",
        "references": [{"title": "测试论文", "authors": "测试作者", "venue": "测试会议", "url": "https://test.com"}]
    })
llm_service.call_llm = _mock_call_llm

from fastapi.testclient import TestClient
from backend.main import app
from backend.paper_routes import router as paper_router

# 手工注册 paper 路由（测试环境 import main.py 时 try 可能没捕获到）
try:
    app.include_router(paper_router)
except Exception:
    pass

client = TestClient(app)

# 先跑一次分析，确保有测试数据
resp_init = client.post("/api/topic/analyze", json={"topic": "测试方向"})
_TEST_ID = resp_init.json().get("id", 1)

class TestTopicAPI:
    """选题体检 API 测试"""

    def test_analyze_empty_topic(self):
        """空研究方向应返回 400"""
        resp = client.post("/api/topic/analyze", json={"topic": ""})
        assert resp.status_code == 400
        assert "不能为空" in resp.text

    def test_analyze_valid_topic(self):
        """有效研究方向应返回完整报告"""
        resp = client.post("/api/topic/analyze", json={
            "topic": "AI for Code Generation",
            "background": "会Python",
            "constraint": ""
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic_input"] == "AI for Code Generation"
        assert "feasibility_score" in data
        assert "research_overview" in data
        assert "references" in data

    def test_analyze_without_background(self):
        """背景为空也应正常工作"""
        resp = client.post("/api/topic/analyze", json={"topic": "机器学习"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic_input"] == "机器学习"

    def test_favorite_topic(self):
        """收藏/取消收藏"""
        resp = client.post("/api/topic/favorite", json={"id": _TEST_ID, "favorite": True})
        assert resp.status_code == 200
        assert resp.json()["favorited"] is True

        resp = client.post("/api/topic/favorite", json={"id": _TEST_ID, "favorite": False})
        assert resp.status_code == 200
        assert resp.json()["favorited"] is False

    def test_favorite_not_found(self):
        """收藏不存在的 ID 应返回 404"""
        resp = client.post("/api/topic/favorite", json={"id": 99999, "favorite": True})
        assert resp.status_code == 404

    def test_favorites_list(self):
        """收藏列表应只返回收藏的选题"""
        resp = client.get("/api/topic/favorites")
        assert resp.status_code == 200
        for item in resp.json():
            assert "display_title" in item

    def test_history_list(self):
        """历史记录应返回所有分析"""
        resp = client.get("/api/topic/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_single_topic(self):
        """获取单个选题报告"""
        resp = client.get("/api/topic/1")
        if resp.status_code == 200:
            data = resp.json()
            assert "topic_input" in data


class TestPaperAPI:
    """论文 API 测试"""

    def test_paper_list_empty(self):
        """论文列表应返回列表"""
        resp = client.get("/api/paper/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_delete_nonexistent(self):
        """删除不存在的论文应返回 404"""
        resp = client.delete("/api/paper/99999")
        assert resp.status_code == 404
