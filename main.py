# ============================================
# 遊戲主程式入口點
# ============================================
from src.core.engine import Engine

if __name__ == "__main__":
    # 初始化遊戲引擎
    engine = Engine()
    # 啟動遊戲循環
    engine.run()
