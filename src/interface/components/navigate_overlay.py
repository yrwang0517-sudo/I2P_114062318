"""
============================================
導航界面組件
============================================
功能: 快速導航到 Start (出生點)、Gym (戰鬥館)、Shop (商店)、Heal (冰山治療點)
特性: 支持跨地圖導航、自動尋路 (BFS)、避開障礙物
使用: 按下導航按鈕 -> 點擊目標位置 -> 自動尋路移動
============================================
"""
import pygame as pg
from src.utils import GameSettings
from src.core.services import input_manager, resource_manager
from .button import Button
from collections import deque

class NavigateOverlay:
    # ===== 導航目標定義 =====
    # 格式: 目標名稱 -> (目標地圖檔案名, 目標瓷磚座標)
    NAVIGATION_TARGETS = {
        "start": ("map.tmx", (16, 30)),        # 出生點 (主地圖左邊)
        "gym": ("map.tmx", (24, 24)),          # 戰鬥館 (主地圖中央)
        "shop": ("map.tmx", (19, 32)),         # 商店 (主地圖下方)
        "heal": ("ice.tmx", (5, 24))           # 治療點 (冰山左上方)
    }
    def __init__(self, game_scene):
        """初始化導航界面
        
        參數:
            game_scene: 遊戲場景，用於存取玩家、地圖等
        """
        self.game_scene = game_scene
        self.is_active = False
        
        # ===== 界面佈局設定 =====
        overlay_w, overlay_h = 900, 520
        overlay_x = (GameSettings.SCREEN_WIDTH - overlay_w) // 2    # 水平居中
        overlay_y = (GameSettings.SCREEN_HEIGHT - overlay_h) // 2   # 垂直居中
        self.overlay_rect = pg.Rect(overlay_x, overlay_y, overlay_w, overlay_h)
        self.bg_color = (255, 165, 48)
        self.border_color = (0, 0, 0)
        
        # ===== 關閉按鈕 (X 按鈕) =====
        self.x_button = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            self.overlay_rect.right - 50,          # 右上角
            self.overlay_rect.top + 10,
            40, 40,
            on_click=self.close
        )
        
        # ===== 導航按鈕佈局 =====
        btn_w, btn_h = 120, 120                    # 按鈕尺寸
        btn_gap = 30                               # 按鈕間距
        btn_x = self.overlay_rect.x + 40           # 左邊距 40px
        btn_y = self.overlay_rect.y + 60           # 上邊距 60px
        
        # Start 按鈕
        self.start_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            btn_x, btn_y, btn_w, btn_h,
            on_click=self._goto_start
        )
        
        # Gym 按鈕
        self.gym_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            btn_x + btn_w + btn_gap, btn_y,        # 向右排列
            btn_w, btn_h,
            on_click=self._goto_gym
        )
        
        # Shop 按鈕
        self.shop_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            btn_x + (btn_w + btn_gap) * 2, btn_y,  # 向右排列
            btn_w, btn_h,
            on_click=self._goto_shop
        )
        
        # Heal 按鈕
        self.heal_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            btn_x + (btn_w + btn_gap) * 3, btn_y,  # 向右排列
            btn_w, btn_h,
            on_click=self._goto_heal
        )
    
    def _bfs_find_path(self, start_tile, goal_tile, current_map):
        """
        ===== 廣度優先搜索 (BFS) 尋路演算法 =====
        
        用途: 在地圖上尋找從起點到終點的最短路徑
        
        參數:
            start_tile: 起始瓷磚座標 (x, y)
            goal_tile: 目標瓷磚座標 (x, y)
            current_map: 當前地圖物件
            
        返回: 路徑瓷磚列表 [start, ..., goal] 或 None (無法到達)
        
        ===== 避開邏輯 =====
        - 碰撞區域 (牆壁、建築物)
        - 傳送點 (除非是目標位置)
        
        ===== 搜索過程 =====
        1. 初始化佇列、已訪問集合、方向向量
        2. 從起點開始，逐步探索相鄰瓷磚
        3. 檢查瓷磚是否可通行 (無碰撞、非傳送點)
        4. 如果到達目標，返回路徑
        5. 如果佇列耗盡（無路可通），返回 None
        """
        from src.utils import GameSettings
        
        # ===== BFS 初始化 =====
        queue = deque([(start_tile, [start_tile])])  # 佇列: (當前瓷磚, 路徑列表)
        visited = {start_tile}                        # 已訪問瓷磚集合
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # 四方向: 上下左右
        
        # ===== 蒐集傳送點位置以便檢查 =====
        teleport_tiles = set()
        for tp in current_map.teleporters:
            tp_tile = (
                int(tp.pos.x) // GameSettings.TILE_SIZE,
                int(tp.pos.y) // GameSettings.TILE_SIZE
            )
            teleport_tiles.add(tp_tile)
        
        # ===== 提取所有傳送點位置 =====
        teleport_tiles = set()
        for teleporter in current_map.teleporters:
            tp_x = int(teleporter.pos.x) // GameSettings.TILE_SIZE
            tp_y = int(teleporter.pos.y) // GameSettings.TILE_SIZE
            teleport_tiles.add((tp_x, tp_y))
        
        # ===== BFS 主循環 =====
        while queue:
            (current_x, current_y), path = queue.popleft()
            
            # 已到達目標
            if (current_x, current_y) == goal_tile:
                return path
            
            # 探索相鄰瓷磚
            for dx, dy in directions:
                next_x = current_x + dx
                next_y = current_y + dy
                next_tile = (next_x, next_y)
                
                # 跳過已訪問的瓷磚
                if next_tile in visited:
                    continue
                
                # ===== 檢查可通行性 =====
                test_rect = pg.Rect(
                    next_x * GameSettings.TILE_SIZE,
                    next_y * GameSettings.TILE_SIZE,
                    GameSettings.TILE_SIZE,
                    GameSettings.TILE_SIZE
                )
                
                # 避開碰撞區域
                if current_map.check_collision(test_rect):
                    continue
                
                # 避開傳送點 (除非是目標)
                if next_tile in teleport_tiles and next_tile != goal_tile:
                    continue
                
                # 加入佇列
                visited.add(next_tile)
                queue.append((next_tile, path + [next_tile]))
        
        # 無可通行路徑
        return None

    def _navigate_to_map(self, target_map, goal_tile):
        """
        導航至不同的地圖
        
        流程:
        1. 尋找通往目標地圖的傳送點
        2. 導航至傳送點
        3. 在傳送後繼續導航至最終目標
        """
        try:
            gm = self.game_scene.game_manager
            if not gm or not gm.player:
                return
            
            from src.utils import GameSettings
            
            # ===== 尋找目標地圖的傳送點 =====
            current_map_obj = gm.current_map
            teleporter_to_use = None
            for tp in current_map_obj.teleporters:
                if tp.destination == target_map:
                    teleporter_to_use = tp
                    break
            
            if not teleporter_to_use:
                return
            
            # ===== 計算玩家位置和傳送點位置 =====
            current_tile = (
                int(gm.player.position.x) // GameSettings.TILE_SIZE,
                int(gm.player.position.y) // GameSettings.TILE_SIZE
            )
            
            tp_tile = (
                int(teleporter_to_use.pos.x) // GameSettings.TILE_SIZE,
                int(teleporter_to_use.pos.y) // GameSettings.TILE_SIZE
            )
            
            # ===== 尋路至傳送點 =====
            path_to_tp = self._bfs_find_path(current_tile, tp_tile, current_map_obj)
            
            if path_to_tp:
                # 設置自動導航路徑至傳送點
                gm.player._auto_path = path_to_tp
                gm.player._auto_path_index = 0
                
                # 儲存傳送後的目標位置
                # (在 player.py 中會在傳送完成後使用)
                gm.player._nav_target_map = target_map
                gm.player._nav_target_tile = goal_tile
            
        except Exception as e:
            print(f"Error in _navigate_to_map: {e}")

    def open(self):
        self.is_active = True

    def close(self):
        try:
            input_manager.reset()
        except Exception:
            pass
        self.is_active = False

    def _navigate_to(self, goal_map, goal_tile):
        """
        通用導航方法 - 避免重複代碼
        
        參數:
            goal_map: 目標地圖 (e.g., "map.tmx")
            goal_tile: 目標座標 (x, y)
        """
        try:
            gm = self.game_scene.game_manager
            if not gm or not gm.player:
                return
            
            from src.utils import GameSettings
            
            if gm.current_map_key != goal_map:
                # 不在目標地圖上 -> 需要傳送
                self._navigate_to_map(goal_map, goal_tile)
            else:
                # 已在目標地圖上 -> 直接導航
                current_tile = (
                    int(gm.player.position.x) // GameSettings.TILE_SIZE,
                    int(gm.player.position.y) // GameSettings.TILE_SIZE
                )
                path = self._bfs_find_path(current_tile, goal_tile, gm.current_map)
                if path:
                    gm.player._auto_path = path
                    gm.player._auto_path_index = 0
            
            self.close()
        except Exception as e:
            print(f"導航錯誤: {e}")
    
    def _goto_start(self):
        """導航至起點 Start (map.tmx, 16, 30)"""
        goal_map, goal_tile = self.NAVIGATION_TARGETS["start"]
        self._navigate_to(goal_map, goal_tile)

    def _goto_gym(self):
        """導航至健身房 Gym (map.tmx, 24, 24)"""
        goal_map, goal_tile = self.NAVIGATION_TARGETS["gym"]
        self._navigate_to(goal_map, goal_tile)

    def _goto_shop(self):
        """導航至商店 Shop (map.tmx, 19, 32)"""
        goal_map, goal_tile = self.NAVIGATION_TARGETS["shop"]
        self._navigate_to(goal_map, goal_tile)
    
    def _goto_heal(self):
        """導航至治療點 Heal (ice.tmx, 5, 24)"""
        goal_map, goal_tile = self.NAVIGATION_TARGETS["heal"]
        self._navigate_to(goal_map, goal_tile)

    def update(self, dt):
        """
        更新導航界面狀態和按鈕交互
        
        參數: dt - 時間增量 (幀時間，用於平滑動畫)
        
        流程:
        1. 檢查界面是否活躍，若非則跳過更新
        2. 逐次更新各個互動按鈕 (響應滑鼠懸停、點擊)
        """
        if not self.is_active:
            return
        
        # ===== 更新所有互動按鈕 =====
        # 每個按鈕處理自己的滑鼠交互 (懸停特效、點擊事件)
        self.x_button.update(dt)          # 關閉按鈕
        self.start_button.update(dt)      # 起點按鈕
        self.gym_button.update(dt)        # 健身房按鈕
        self.shop_button.update(dt)       # 商店按鈕
        self.heal_button.update(dt)       # 治療點按鈕

    def draw(self, screen):
        """
        繪製導航界面及所有 UI 元素
        
        參數: screen - Pygame 繪製表面
        
        繪製順序:
        1. 暗化背景 - 強調導航面板
        2. 橙色面板 + 邊框
        3. 標題文字 "nevigate"
        4. 三個導航按鈕 (Start, Gym, Shop)
        5. 按鈕下方標籤文字
        6. 右上角關閉按鈕 (X)
        """
        if not self.is_active:
            return
        
        # ===== 第一步: 暗化背景 =====
        # 創建半透明黑色覆蓋層，突出導航面板
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(192)                    # 透明度: 0-255 (192 = 約 75% 不透明)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))
        
        # ===== 第二步: 繪製面板框架 =====
        # 填充橙色背景
        pg.draw.rect(screen, self.bg_color, self.overlay_rect)
        # 黑色邊框 (厚度 4px)
        pg.draw.rect(screen, self.border_color, self.overlay_rect, 4)
        
        # ===== 第三步: 繪製標題 =====
        # 標題文字位置: 左上角 (偏移 24px 左, 12px 上)
        title_font = pg.font.SysFont(None, 40)
        title = title_font.render('nevigate', True, (255, 255, 255))  # 白色文字
        screen.blit(title, (self.overlay_rect.x + 24, self.overlay_rect.y + 12))
        
        # ===== 第四步: 繪製導航按鈕 =====
        # 四個大按鈕水平排列，每個 120x120 像素
        self.start_button.draw(screen)
        self.gym_button.draw(screen)
        self.shop_button.draw(screen)
        self.heal_button.draw(screen)
        
        # ===== 第五步: 繪製按鈕下方標籤 =====
        # 準備標籤字體
        label_font = pg.font.SysFont(None, 24)
        start_label = label_font.render('Start', True, (255, 255, 255))
        gym_label = label_font.render('Gym', True, (255, 255, 255))
        shop_label = label_font.render('Shop', True, (255, 255, 255))
        heal_label = label_font.render('Heal', True, (255, 255, 255))
        
        # 計算標籤位置: 每個標籤水平居中於其按鈕，垂直位置在按鈕下方 8px
        start_label_x = self.start_button.hitbox.x + (self.start_button.hitbox.w - start_label.get_width()) // 2
        start_label_y = self.start_button.hitbox.y + self.start_button.hitbox.h + 8
        gym_label_x = self.gym_button.hitbox.x + (self.gym_button.hitbox.w - gym_label.get_width()) // 2
        gym_label_y = self.gym_button.hitbox.y + self.gym_button.hitbox.h + 8
        shop_label_x = self.shop_button.hitbox.x + (self.shop_button.hitbox.w - shop_label.get_width()) // 2
        shop_label_y = self.shop_button.hitbox.y + self.shop_button.hitbox.h + 8
        heal_label_x = self.heal_button.hitbox.x + (self.heal_button.hitbox.w - heal_label.get_width()) // 2
        heal_label_y = self.heal_button.hitbox.y + self.heal_button.hitbox.h + 8
        
        # 繪製標籤
        screen.blit(start_label, (start_label_x, start_label_y))
        screen.blit(gym_label, (gym_label_x, gym_label_y))
        screen.blit(shop_label, (shop_label_x, shop_label_y))
        screen.blit(heal_label, (heal_label_x, heal_label_y))
        
        # ===== 第六步: 繪製關閉按鈕 =====
        # 右上角 X 按鈕 (最後繪製，確保在最上層)
        self.x_button.draw(screen)