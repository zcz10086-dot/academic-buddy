# 学搭子 (Academic Buddy)

🔥 **大一/大二本科生的科研入门工具**

## 功能

- **选题体检** — 输入研究方向，AI 分析可行性、创新空间、第一步行动
- **论文伴读** — 上传 PDF → 三级阅读（摘要版 / 精读版 / 完整版中文翻译）
- **收藏选题** — 推荐方向直接上首页，所有分析自动记录

## 快速开始

### APK 安装

1. 下载 `学搭子_phase2.apk` 到手机
2. 安装后打开
3. 输入研究方向 → 点分析 → 收藏好选题
4. 右上角📄 → 上传 PDF → 三级阅读

### 后端部署（已有 ECS）

```bash
# 上传 deploy.zip 到服务器
unzip deploy.zip -d /opt/academic-buddy
cd /opt/academic-buddy
bash install.sh
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| LLM_API_KEY | — | DeepSeek API Key |
| LLM_API_URL | https://api.deepseek.com/chat/completions | API 地址 |
| LLM_MODEL | deepseek-v4-flash | 模型名 |
| PORT | 8080 | 服务端口 |

## 技术栈

- **后端:** FastAPI + DeepSeek API
- **前端:** Flutter (Android APK)
- **部署:** ECS / WSL
