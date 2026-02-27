"""本地启动脚本 - 一键启动 Web 服务"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# 检查 API key
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("❌ 错误: 未设置 DEEPSEEK_API_KEY 环境变量")
    print("请编辑 .env 文件添加你的 DeepSeek API Key")
    print("示例: DEEPSEEK_API_KEY=sk-f17c2822b60a495f9f5d9d24e0248dd5")
    sys.exit(1)

print("[START] 启动数据源调研平台...")
print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
print(f"   模型: deepseek-reasoner")
print()

# 启动服务
import uvicorn
from orchestrator.api import app

if __name__ == "__main__":
    uvicorn.run(
        "orchestrator.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
