from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager, scene_manager
from src.utils import Position, PositionCamera, GameSettings, Logger
from src.core import GameManager
import math
from typing import override

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE *1.5
    game_manager: GameManager

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)
        # track whether player was in a bush last frame to avoid repeated triggers
        self._in_bush = False
        self._last_teleport_pos = None  # Track position of last triggered teleport
        # Auto navigation path
        self._auto_path = None  # List of (x, y) tile positions
        self._auto_path_index = 0  # Current index in path
        # 用於追蹤玩家是否在移動（用於線上同步）
        self.is_moving = False

    @override
    def update(self, dt: float) -> None:
        dis = Position(0, 0)
        # manage teleport cooldown (set when GameManager.try_switch_map moves player)
        skip_teleport = False
        try:
            timer = getattr(self, '_teleport_cooldown_timer', 0.0)
            if timer > 0:
                timer -= dt
                setattr(self, '_teleport_cooldown_timer', timer)
                skip_teleport = True if timer > 0 else False
                if timer <= 0:
                    try:
                        delattr = delattr
                        delattr(self, '_teleport_cooldown_timer')
                    except Exception:
                        pass
        except Exception:
            skip_teleport = False
        
        # Check if we have an auto navigation path
        auto_navigation = False
        if hasattr(self, '_auto_path') and self._auto_path and hasattr(self, '_auto_path_index'):
            if self._auto_path_index < len(self._auto_path):
                auto_navigation = True
                # Get target tile
                target_tile = self._auto_path[self._auto_path_index]
                target_x = target_tile[0] * GameSettings.TILE_SIZE
                target_y = target_tile[1] * GameSettings.TILE_SIZE
                
                # Calculate direction to target
                dx = target_x - self.position.x
                dy = target_y - self.position.y
                
                # Check if we reached the target tile (within a small threshold)
                threshold = GameSettings.TILE_SIZE * 0.1
                if abs(dx) < threshold and abs(dy) < threshold:
                    # Snap to exact position
                    self.position.x = target_x
                    self.position.y = target_y
                    # Move to next tile in path
                    self._auto_path_index += 1
                    if self._auto_path_index >= len(self._auto_path):
                        # Reached end of path
                        self._auto_path = None
                        self._auto_path_index = 0
                else:
                    # Move towards target
                    length = math.sqrt(dx * dx + dy * dy)
                    if length > 0:
                        dis.x = dx / length
                        dis.y = dy / length
                        
                        # Set animation direction
                        if abs(dx) > abs(dy):
                            last_dir = "right" if dx > 0 else "left"
                        else:
                            last_dir = "down" if dy > 0 else "up"
                        self.animation.switch(last_dir)
        
        # Manual control (only if not auto-navigating)
        if not auto_navigation:
            last_dir = None
            if input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
                dis.x -= 1
                last_dir = "left"
            if input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
                dis.x += 1
                last_dir = "right"
            if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
                dis.y -= 1
                last_dir = "up"
            if input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
                dis.y += 1
                last_dir = "down"
            if last_dir:
                self.animation.switch(last_dir)
        
        #print(f"x,y: {dis.x,dis.y}")
        length = math.sqrt(dis.x * dis.x + dis.y * dis.y)
        # 記錄玩家是否在移動（用於線上同步）
        self.is_moving = (length != 0)
        if length!=0:
            dis.x /= length
            dis.y /= length
        move_x = dis.x * self.speed * dt
        move_y = dis.y * self.speed * dt

        '''self.position.x += move_x
        self.position.y += move_y'''
        
        #先用x
        old_x = self.position.x
        self.position.x += move_x

        #檢查撞牆
        player_rect = pg.Rect(
            self.position.x,
            self.position.y,
            GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE
        )
        if self.game_manager.check_collision(player_rect):
            self.position.x = Entity._snap_to_grid(old_x)

        #換y
        old_y = self.position.y
        self.position.y += move_y

        player_rect = pg.Rect(
            self.position.x,
            self.position.y,
            GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE
        )
        if self.game_manager.check_collision(player_rect):
            self.position.y = Entity._snap_to_grid(old_y)
        
        # 看傳送點（若傳送冷卻中則暫時跳過，以避免剛傳送進來就被再觸發）
        if not skip_teleport:
            tp = self.game_manager.current_map.check_teleport(self.position)
            if tp:
                # Check if player has moved away from the last teleport position
                tp_tile = (int(tp.pos.x) // GameSettings.TILE_SIZE, int(tp.pos.y) // GameSettings.TILE_SIZE)
                current_tile = (int(self.position.x) // GameSettings.TILE_SIZE, int(self.position.y) // GameSettings.TILE_SIZE)
                
                # Only trigger if this is a new teleport or player has moved away from last one
                if self._last_teleport_pos is None or self._last_teleport_pos != tp_tile:
                    dest = tp.destination
                    # pass origin teleporter info so destination can pick correct paired landing
                    try:
                        tx = int(tp.pos.x) // GameSettings.TILE_SIZE
                        ty = int(tp.pos.y) // GameSettings.TILE_SIZE
                        pid = getattr(tp, 'pair_id', None)
                        self.game_manager.switch_map(dest, origin_tile=(tx, ty), origin_pair=pid)
                        self._last_teleport_pos = tp_tile  # Remember this teleport position
                    except Exception:
                        self.game_manager.switch_map(dest)
                        self._last_teleport_pos = tp_tile
            else:
                # Player is not on any teleport tile, reset tracking
                self._last_teleport_pos = None
        
        # After teleportation, check if we need to continue navigation
        if (hasattr(self, '_nav_target_map') and 
            hasattr(self, '_nav_target_tile') and
            self.game_manager.current_map_key == self._nav_target_map):
            # We've reached the target map, now navigate to the goal tile
            try:
                target_tile = self._nav_target_tile
                current_tile = (
                    int(self.position.x) // GameSettings.TILE_SIZE,
                    int(self.position.y) // GameSettings.TILE_SIZE
                )
                
                # Use BFS to find path to goal
                from collections import deque
                queue = deque([(current_tile, [current_tile])])
                visited = {current_tile}
                directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
                
                path = None
                while queue:
                    (cx, cy), p = queue.popleft()
                    if (cx, cy) == target_tile:
                        path = p
                        break
                    
                    for dx, dy in directions:
                        next_tile = (cx + dx, cy + dy)
                        if next_tile in visited:
                            continue
                        
                        test_rect = pg.Rect(
                            next_tile[0] * GameSettings.TILE_SIZE,
                            next_tile[1] * GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE
                        )
                        
                        # Skip teleports unless it's the goal
                        teleport_tiles = set()
                        for tp in self.game_manager.current_map.teleporters:
                            tp_x = int(tp.pos.x) // GameSettings.TILE_SIZE
                            tp_y = int(tp.pos.y) // GameSettings.TILE_SIZE
                            teleport_tiles.add((tp_x, tp_y))
                        
                        if next_tile in teleport_tiles and next_tile != target_tile:
                            continue
                        
                        if not self.game_manager.check_collision(test_rect):
                            visited.add(next_tile)
                            queue.append((next_tile, p + [next_tile]))
                
                if path:
                    self._auto_path = path
                    self._auto_path_index = 0
                
                # Clean up nav target
                try:
                    del self._nav_target_map
                except:
                    pass
                try:
                    del self._nav_target_tile
                except:
                    pass
            except Exception as e:
                print(f"Error continuing navigation after teleport: {e}")
                # Clean up on error too
                try:
                    del self._nav_target_map
                except:
                    pass
                try:
                    del self._nav_target_tile
                except:
                    pass
        
        #檢查是否在bush
        try:
            in_bush = self.game_manager.current_map.check_bush(self.position)
            # If we're under teleport cooldown, treat as already-in-bush to avoid immediate battle
            if getattr(self, '_teleport_cooldown_timer', 0.0) > 0:
                # set _in_bush to True if spawn is in a bush, so change isn't triggered
                self._in_bush = bool(in_bush)
            else:
                if in_bush and not self._in_bush:
                    print("PokemonBush")
                    scene_manager.change_scene("battle", is_npc_battle=False)
                self._in_bush = in_bush
        except Exception:
            pass
        
        # 列印玩家目前座標（tile格式）
        tile_x = int(self.position.x) // GameSettings.TILE_SIZE
        tile_y = int(self.position.y) // GameSettings.TILE_SIZE
        print(f"Player position: ({tile_x}, {tile_y})")
                
        super().update(dt)

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        # Draw navigation arrows along the auto path (if any)
        try:
            if hasattr(self, '_auto_path') and self._auto_path and len(self._auto_path) > 1:
                # Lazy-load arrow texture (right arrow as base). If missing, create vector arrow.
                if not hasattr(self, '_nav_arrow_img'):
                    self._nav_arrow_img = None
                if self._nav_arrow_img is None:
                    try:
                        # Primary location: UI/raw
                        self._nav_arrow_img = pg.image.load("assets/images/UI/raw/arrow.png").convert_alpha()
                    except Exception:
                        # Fallback: draw a simple right-pointing arrow on a small surface
                        size = int(GameSettings.TILE_SIZE * 0.3)
                        surf = pg.Surface((size, size), pg.SRCALPHA)
                        color = (0, 200, 255, 180)  # cyan-ish with alpha
                        w, h = size, size
                        # Triangle arrow pointing right
                        pg.draw.polygon(surf, color, [(0, h//2), (w-6, 6), (w-6, h-6)])
                        # Tail rectangle
                        pg.draw.rect(surf, color, (0, h//2 - 4, w//2, 8))
                        self._nav_arrow_img = surf
                arrow_base = self._nav_arrow_img
                if arrow_base:
                    tile_size = GameSettings.TILE_SIZE
                    # Scale arrow to 30% of tile size
                    target_size = (int(tile_size * 0.3), int(tile_size * 0.3))
                    try:
                        scaled_base = pg.transform.smoothscale(arrow_base, target_size)
                    except Exception:
                        scaled_base = pg.transform.scale(arrow_base, target_size)
                    # Draw arrows from current index onward
                    start_idx = max(getattr(self, '_auto_path_index', 0) - 1, 0)
                    for i in range(start_idx, len(self._auto_path) - 1):
                        (x1, y1) = self._auto_path[i]
                        (x2, y2) = self._auto_path[i + 1]
                        dx = x2 - x1
                        dy = y2 - y1
                        # Determine rotation: base is right arrow (0 deg)
                        angle = 0
                        if dx == 1 and dy == 0:
                            angle = 0
                        elif dx == -1 and dy == 0:
                            angle = 180
                        elif dx == 0 and dy == -1:
                            angle = 90  # up
                        elif dx == 0 and dy == 1:
                            angle = -90 # down
                        arrow_img = pg.transform.rotate(scaled_base, angle)
                        # Center arrow in tile
                        px = x1 * tile_size - camera.x + (tile_size - arrow_img.get_width()) // 2
                        py = y1 * tile_size - camera.y + (tile_size - arrow_img.get_height()) // 2
                        screen.blit(arrow_img, (px, py))
        except Exception:
            pass
        # Draw player sprite last so it stays on top
        super().draw(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)

