# ============================================
# 迷你地圖 (小地圖) 組件
# 功能: 實時顯示當前地圖和玩家位置
# 特性: 自動縮放、玩家標記、動態更新
# ============================================
import pygame as pg
from src.utils import GameSettings
from src.core.services import resource_manager

class Minimap:
    """迷你地圖 (小地圖) 組件
    
    顯示位置: 螢幕左上角
    大小: 螢幕寬度的約 1/5
    內容: 完整地圖的縮小版本 + 玩家位置標記
    
    依賴 GameScene 提供:
    - current_map: 地圖物件，需具有 width、height、surface 等屬性
    - player_tile_pos: (tx, ty) 玩家的瓷磚座標
    
    說明: 使用 pytmx 或自訂地圖物件時，需調整 _get_map_surface() 邏輯
    """

    def __init__(self, game_scene):
        """初始化迷你地圖
        
        參數:
            game_scene: 遊戲場景，用於存取地圖和玩家位置
        """
        self.game_scene = game_scene
        
        # ===== 尺寸和位置設定 =====
        # 迷你地圖寬度約為螢幕寬度的 1/5
        self.width = max(120, GameSettings.SCREEN_WIDTH // 5)
        # 高度根據地圖寬高比動態計算
        self.height = self.width
        # 位置: 左上角，稍微向下向右以避開邊界
        self.x = 10
        self.y = 10
        self.padding = 6  # 邊框內邊距
        
        # ===== 顏色設定 =====
        self.bg_color = (30, 30, 30, 200)      # 背景: 深灰色半透明
        self.border_color = (0, 0, 0)          # 邊框: 黑色
        
        # ===== 地圖快取 =====
        # 存儲渲染後的地圖表面，避免每幀重新渲染
        self._last_map_id = None               # 上次渲染的地圖 ID
        self._map_surf = None                  # 快取的地圖表面

    def _get_map_surface(self):
        """取得或構建地圖表面 (整個地圖的像素圖片)
        
        嘗試多種方法獲取地圖表面:
        1. 檢查地圖物件是否有預渲染的表面 (_surface 或 surface 屬性)
        2. 呼叫地圖的 render_to_surface() 方法
        3. 從瓷磚資料手動構建簡單的棋盤表面
        
        返回: pygame.Surface 物件或 None (無法構建)
        
        快取策略: 根據地圖 ID 快取表面，避免每幀重新渲染
        """
        gs = self.game_scene
        if not gs:
            return None

        current_map = getattr(gs, 'current_map', None)
        if not current_map:
            return None

        # ===== 地圖 ID 識別 =====
        # 用於判斷地圖是否改變，決定是否使用快取
        map_id = getattr(current_map, 'name', None) or getattr(current_map, 'map_id', None) or id(current_map)
        if map_id == self._last_map_id and self._map_surf is not None:
            # 地圖未改變，直接返回快取表面
            return self._map_surf

        # ===== 方法 1: 使用地圖物件的表面屬性 =====
        surf = None
        # 支援公開屬性 'surface' 和內部屬性 '_surface'
        if hasattr(current_map, '_surface') and isinstance(getattr(current_map, '_surface'), pg.Surface):
            surf = current_map._surface
        elif hasattr(current_map, 'surface') and isinstance(getattr(current_map, 'surface'), pg.Surface):
            surf = current_map.surface
        
        # ===== 方法 2: 呼叫地圖的渲染方法 =====
        elif hasattr(current_map, 'render_to_surface'):
            try:
                surf = current_map.render_to_surface()
            except Exception:
                surf = None
        
        # ===== 方法 3: 手動構建瓷磚棋盤 =====
        if surf is None:
            try:
                tw = getattr(current_map, 'width', None)              # 地圖瓷磚寬度
                th = getattr(current_map, 'height', None)             # 地圖瓷磚高度
                tile_size = getattr(current_map, 'tile_size', getattr(GameSettings, 'TILE_SIZE', 32))
                if tw and th:
                    # 建立地圖表面
                    surf = pg.Surface((tw * tile_size, th * tile_size))
                    surf.fill((80, 80, 80))  # 背景顏色
                    # 繪製棋盤式瓷磚（用於視覺化）
                    col1 = (100, 150, 100)  # 淡綠色
                    col2 = (80, 120, 80)    # 深綠色
                    for y in range(th):
                        for x in range(tw):
                            r = pg.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
                            c = col1 if (x + y) % 2 == 0 else col2
                            pg.draw.rect(surf, c, r)
                else:
                    surf = None
            except Exception:
                surf = None

        # ===== 快取並更新尺寸 =====
        self._map_surf = surf
        # 如果成功建立表面，根據寬高比更新迷你地圖高度
        if surf is not None:
            try:
                sw, sh = surf.get_size()
                # 計算高度以保持寬高比
                self.height = max(48, int((self.width * sh) / max(1, sw)))
            except Exception:
                pass
        self._last_map_id = map_id
        return surf

    def update(self, dt):
        """更新迷你地圖 (目前為空，地圖表面快取於 _get_map_surface)"""
        pass

    def draw(self, screen):
        # draw background box
        box_w = self.width + self.padding * 2
        box_h = self.height + self.padding * 2
        box_surf = pg.Surface((box_w, box_h), pg.SRCALPHA)
        box_surf.fill(self.bg_color)
        screen.blit(box_surf, (self.x, self.y))
        # border
        pg.draw.rect(screen, self.border_color, pg.Rect(self.x, self.y, box_w, box_h), 2)

        # map surface scaled to fit
        map_surf = self._get_map_surface()
        if map_surf:
            try:
                scaled = pg.transform.smoothscale(map_surf, (self.width, self.height))
                screen.blit(scaled, (self.x + self.padding, self.y + self.padding))
            except Exception:
                pass

        # draw player marker
        try:
            gs = self.game_scene
            if not gs:
                return
            player_pos = getattr(gs, 'player_tile_pos', None)
            current_map = getattr(gs, 'current_map', None)
            if player_pos and current_map and map_surf:
                tw = getattr(current_map, 'width', map_surf.get_width() // getattr(current_map, 'tile_size', GameSettings.TILE_SIZE))
                th = getattr(current_map, 'height', map_surf.get_height() // getattr(current_map, 'tile_size', GameSettings.TILE_SIZE))
                px = int((player_pos[0] / max(1, tw)) * self.width)
                py = int((player_pos[1] / max(1, th)) * self.height)
                # small red dot
                pg.draw.circle(screen, (220, 40, 40), (self.x + self.padding + px, self.y + self.padding + py), 4)
        except Exception:
            pass
