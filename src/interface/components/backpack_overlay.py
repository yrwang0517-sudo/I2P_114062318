#ok沒問題
import pygame as pg
from src.utils import GameSettings, Logger
from src.core.services import input_manager, resource_manager

# Fallback mapping from monster name (lowercase) to sprite file
_NAME_TO_SPRITE = {
    "pikachu": "menu_sprites/menusprite1.png",
    "charizard": "menu_sprites/menusprite2.png",
    "blastoise": "menu_sprites/menusprite3.png",
    "venusaur": "menu_sprites/menusprite4.png",
    "gengar": "menu_sprites/menusprite5.png",
    "dragonite": "menu_sprites/menusprite6.png",
    "alakazam": "menu_sprites/menusprite7.png",
    "machamp": "menu_sprites/menusprite8.png",
    "golem": "menu_sprites/menusprite9.png",
    "arcanine": "menu_sprites/menusprite10.png",
    "lapras": "menu_sprites/menusprite11.png",
    "snorlax": "menu_sprites/menusprite12.png",
    "articuno": "menu_sprites/menusprite13.png",
    "zapdos": "menu_sprites/menusprite14.png",
    "moltres": "menu_sprites/menusprite15.png",
    "mewtwo": "menu_sprites/menusprite16.png",
}

# Level-based sprite evolution groups
_EVOLVE_GROUPS = {
    "1": {
        "base": "menu_sprites/menusprite1.png",
        "mid": "menu_sprites/menusprite2.png",
        "high": "menu_sprites/menusprite3.png",
    },
    "7": {
        "base": "menu_sprites/menusprite7.png",
        "mid": "menu_sprites/menusprite8.png",
        "high": "menu_sprites/menusprite9.png",
    },
    "12": {
        "base": "menu_sprites/menusprite12.png",
        "mid": "menu_sprites/menusprite13.png",
        "high": "menu_sprites/menusprite14.png",
    },
    "16": {
        "base": "menu_sprites/menusprite16.png",
        "mid": "menu_sprites/menusprite16.png",
        "high": "menu_sprites/menusprite16.png",
    },
}

class BackpackOverlay:
    def __init__(self, items=None, monsters=None):
        self.is_active = False
        # 擴大寬度以容納 3 列怪物 + 物品列（左右各擴寬 75px，總寬度 1250）
        self.overlay_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - 1250) // 2,
            (GameSettings.SCREEN_HEIGHT - 700) // 2,
            1250, 700
        )
        self.items = items or [
            {"name": "hp potion", "img": "ingame_ui/potion.png", "count": 5},
            {"name": "Coins", "img": "ingame_ui/coin.png", "count": 3},
            {"name": "Pokeball", "img": "ingame_ui/ball.png", "count": 10},
            {"name": "attack", "img": "ingame_ui/options1.png", "count": 5},
            {"name": "defense", "img": "ingame_ui/options2.png", "count": 5},
            {"name": "exp potion", "img": "ingame_ui/exp_potion.png", "count": 1},
        ]
        # 怪物陣列，預設只有Pikachu
        self.monsters = monsters or [{"name": "Pikachu", "hp": 85, "max_hp": 100, "level": 25, "sprite_path": "menu_sprites/menusprite1.png"}]
        # Ensure every monster dict has a valid sprite_path (fallback by name)
        try:
            for m in self.monsters:
                if not m.get("sprite_path"):
                    name = (m.get("name") or "").lower()
                    m["sprite_path"] = _NAME_TO_SPRITE.get(name, "menu_sprites/menusprite3.png")
        except Exception:
            pass
        try:
            self._apply_level_sprite_evolution_all()
        except Exception:
            pass
        # fallback mapping for item names/keys -> image path
        self._ITEM_NAME_TO_IMG = {
            "hp potion": "ingame_ui/potion.png",
            "max hp potion": "ingame_ui/potion.png",
            "max_hp_potion": "ingame_ui/potion.png",
            "pokeball": "ingame_ui/ball.png",
            "pokeball": "ingame_ui/ball.png",
            "coin": "ingame_ui/coin.png",
            "coins": "ingame_ui/coin.png",
            "attack": "ingame_ui/options1.png",
            "defense": "ingame_ui/options2.png",
            "exp potion": "ingame_ui/exp_potion.png",
            "exp_potion": "ingame_ui/exp_potion.png",
        }
        # move X button 50px left to avoid overlapping right padding
        self.x_button = pg.Rect(self.overlay_rect.right - 50, self.overlay_rect.top + 40, 40, 40)
        self.dark_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.dark_surface.set_alpha(128)
        self.dark_surface.fill((0, 0, 0))
        # custom cursor for backpack overlay (loaded once)
        try:
            ci = resource_manager.get_image("ingame_ui/options4.png")
            if ci:
                self._cursor_img = pg.transform.smoothscale(ci, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
            else:
                self._cursor_img = None
        except Exception:
            self._cursor_img = None
        # check icon (used both as hover-cursor and placed above selected monster)
        try:
            chk = resource_manager.get_image("UI/raw/UI_Flat_IconCheck01a.png")
            if chk:
                self._check_img = pg.transform.smoothscale(chk, (24, 24))
            else:
                self._check_img = None
        except Exception:
            self._check_img = None
        # index of default monster (only one allowed). default to first monster if exists
        self.default_index = 0 if len(self.monsters) > 0 else None
        # runtime rects for monster entries (recomputed each draw)
        self._monster_rects = []
        # hovered monster index for cursor change
        self._hover_index = None
        # item rects and item-use mode
        self._item_rects = []
        self._item_use_mode = False
        self._selected_item_idx = None
        self._item_cursor_img = None
        # last hovered item index to avoid reloading cursor repeatedly
        self._last_hovered_item_idx = None
        # active cursor image to draw when overlay opened (defaults to options)
        self._active_cursor_img = None
        # level 50 milestone notification
        self._level_50_show_time = 0
        self._level_50_tip_img = None
        self._level_50_stat_text_time = 0

    def add_monster(self, monster):
        #怪物不重複
        name = monster.get("name")
        # Resolve sprite_path: prefer provided, else map by name, else default to blastoise sprite
        provided_sp = monster.get("sprite_path")
        resolved_sp = provided_sp
        if not resolved_sp:
            key = (name or "").lower()
            resolved_sp = _NAME_TO_SPRITE.get(key, "menu_sprites/menusprite3.png")

        if not any(m.get("name") == name for m in self.monsters):
            # 僅保留必要欄位，避免 img 殘留；確保 sprite_path 有合理值
            self.monsters.append({
                "name": name,
                "hp": monster.get("hp", 0),
                "max_hp": monster.get("max_hp", 1),
                "level": monster.get("level", 1),
                "sprite_path": resolved_sp
            })
            try:
                Logger.info(f"Added monster to backpack: name={name}, sprite_path={resolved_sp}")
            except Exception:
                pass

    def get_monsters(self):
        # 回傳目前擁有的怪物陣列
        return self.monsters

    def get_items(self):
        # 回傳目前擁有的物品陣列
        return self.items

    def open(self):
        self.is_active = True
        try:
            pg.mouse.set_visible(False)
        except Exception:
            pass
        # set active cursor to options image when opening bag
        try:
            self._active_cursor_img = getattr(self, '_cursor_img', None)
        except Exception:
            self._active_cursor_img = None
        # reset item-use transient state when opening
        try:
            self._item_use_mode = False
            self._selected_item_idx = None
            self._item_cursor_img = None
            self._last_hovered_item_idx = None
        except Exception:
            pass

    def close(self):
        # when closing overlay, clear transient input to avoid accidental actions
        try:
            input_manager.reset()
        except Exception:
            pass
        try:
            pg.mouse.set_visible(True)
        except Exception:
            pass
        # clear active cursor and transient item state when closing
        try:
            self._active_cursor_img = None
        except Exception:
            pass
        try:
            self._item_use_mode = False
            self._selected_item_idx = None
            self._item_cursor_img = None
            self._last_hovered_item_idx = None
        except Exception:
            pass
        self.is_active = False
    def update(self, dt):
        if not self.is_active:
            return
        # ensure monster rects are computed for hit testing even if draw() hasn't run yet
        try:
            if not self._monster_rects:
                self._compute_monster_rects()
            if not self._item_rects:
                self._compute_item_rects()
        except Exception:
            pass
        # handle close button
        if input_manager.mouse_pressed(1) and self.x_button.collidepoint(input_manager.mouse_pos):
            self.close()
            return
        # handle clicks: item slots or monster entries
        if input_manager.mouse_pressed(1):
            try:
                mx, my = input_manager.mouse_pos
                # first, check item slots
                for idx, r in enumerate(self._item_rects):
                    if r.collidepoint((mx, my)):
                        # enter item-use mode for this item
                        self._item_use_mode = True
                        self._selected_item_idx = idx
                        try:
                            Logger.info(f"BackpackOverlay: Enter item-use mode for item index {idx}")
                        except Exception:
                            pass
                        # prepare item cursor image (with fallback)
                        try:
                            self._prepare_item_cursor(idx)
                        except Exception:
                            self._item_cursor_img = None
                        try:
                            pg.mouse.set_visible(False)
                        except Exception:
                            pass
                        break
                else:
                    # if not clicking an item, check monster entries
                    for idx, r in enumerate(self._monster_rects):
                        if r.collidepoint((mx, my)):
                            # if in item-use-mode, apply item effect to this monster
                            if self._item_use_mode and self._selected_item_idx is not None:
                                try:
                                    self._use_item_on_monster(self._selected_item_idx, idx)
                                except Exception:
                                    pass
                                # exit item-use-mode
                                self._item_use_mode = False
                                self._selected_item_idx = None
                                self._item_cursor_img = None
                                try:
                                    pg.mouse.set_visible(True)
                                except Exception:
                                    pass
                            else:
                                # normal click: set default_index (only when not in item-use-mode)
                                self.default_index = idx
                                try:
                                    Logger.info(f"BackpackOverlay: Set default monster index to {idx}")
                                except Exception:
                                    pass
                            break
            except Exception:
                pass
        try:
            self._apply_level_sprite_evolution_all()
        except Exception:
            pass
        # update hover index for cursor
        try:
            mx, my = input_manager.mouse_pos
            self._hover_index = None
            for idx, r in enumerate(self._monster_rects):
                if r.collidepoint((mx, my)):
                    self._hover_index = idx
                    break
        except Exception:
            self._hover_index = None

    def _use_item_on_monster(self, item_idx: int, monster_idx: int):
        """Apply item effect (potion or max_potion) to monster at monster_idx.
        Decrease item count and log action.
        """
        try:
            item = self.items[item_idx]
        except Exception:
            return
        name = (item.get('name') or '').lower()
        # validate monster exists
        monsters = self.get_monsters() or []
        if not (0 <= monster_idx < len(monsters)):
            return
        m = monsters[monster_idx]
        max_hp = m.get('max_hp', 1)
        cur_hp = m.get('hp', 0)
        healed = 0
        consumed = False
        
        # exp potion must be handled before generic potion checks to avoid substring match
        if name == 'exp potion' or name == 'exp_potion' or ('exp' in name and 'potion' in name):
            # exp potion: 等級提升 10，不影響 HP
            try:
                cur_lv = int(m.get('level', 1))
                m['level'] = cur_lv + 10
                # check if level reaches 50
                if m['level'] >= 50 and cur_lv < 50:
                    self._level_50_show_time = pg.time.get_ticks() + 2000
                    try:
                        self._level_50_tip_img = resource_manager.get_image('menu_sprites/better exp tip.png')
                    except Exception:
                        self._level_50_tip_img = None
                    # Mark monster as reached level 50
                    m['level_50_reached'] = True
                    m['better_icon_img'] = 'menu_sprites/better.png'
                    # Increase stats
                    m['attack'] = m.get('attack', 0) + 20
                    m['max_hp'] = m.get('max_hp', 100) + 100
                    # Restore HP to new max_hp
                    m['hp'] = m['max_hp']
                    # Schedule stat text display after animation ends (2 seconds)
                    self._level_50_stat_text_time = pg.time.get_ticks() + 2000 + 3000  # show for 3 seconds after
            except Exception:
                m['level'] = (m.get('level') or 1) + 10
            consumed = True
        elif name == 'max hp potion' or name == 'max_hp_potion' or ('max' in name and 'hp' in name and 'potion' in name):
            # MAX_POTION: restore to full
            healed = max_hp - cur_hp
            m['hp'] = max_hp
            consumed = True
        elif name == 'hp potion' or ('hp' in name and 'potion' in name):
            # regular potion: +10 HP, not exceeding max
            add = 10
            new_hp = min(max_hp, cur_hp + add)
            healed = new_hp - cur_hp
            m['hp'] = new_hp
            consumed = True
        elif 'attack' in name:
            # attack: 增加攻擊 buff
            if not m.get('attack_buff'):
                m['attack_buff'] = True
                m['attack_buff_img'] = 'ingame_ui/options1.png'
                consumed = True
            else:
                # 已有 buff，不消耗物品
                consumed = False
        elif 'defense' in name:
            # defense: 增加防禦 buff
            if not m.get('defense_buff'):
                m['defense_buff'] = True
                m['defense_buff_img'] = 'ingame_ui/options2.png'
                consumed = True
            else:
                # 已有 buff，不消耗物品
                consumed = False
        else:
            # unsupported item
            return
        
        # consume one if item was used
        if consumed:
            try:
                cnt = int(item.get('count', 0))
                if cnt > 0:
                    item['count'] = max(0, cnt - 1)
                    # if count reaches zero, remove the item from the list
                    if item['count'] == 0:
                        try:
                            # remove by index
                            del self.items[item_idx]
                            # force recompute item rects next frame
                            self._item_rects = []
                            try:
                                Logger.info(f"BackpackOverlay: Item '{item.get('name')}' depleted and removed")
                            except Exception:
                                pass
                        except Exception:
                           pass
            except Exception:
                pass
        try:
            Logger.info(f"Used item '{item.get('name')}' on monster '{m.get('name')}', healed {healed} HP")
        except Exception:
            pass

    def _draw_level_50_tip(self, screen):
        """Draw level 50 milestone tip in the center with scaling animation."""
        import math
        now = pg.time.get_ticks()
        if now > self._level_50_show_time:
            self._level_50_tip_img = None
        else:
            if self._level_50_tip_img:
                try:
                    # Calculate elapsed time and progress (0-1 over 2 seconds)
                    elapsed = now - (self._level_50_show_time - 2000)
                    progress = max(0, min(1, elapsed / 2000.0))
                    # Use sine wave to scale from 1.0 to 1.5 and back to 1.0
                    scale_factor = 1.0 + 0.5 * math.sin(progress * math.pi)
                    # Base size 600x300, apply scaling
                    base_w, base_h = 600, 300
                    scaled_w = int(base_w * scale_factor)
                    scaled_h = int(base_h * scale_factor)
                    img = pg.transform.smoothscale(self._level_50_tip_img, (scaled_w, scaled_h))
                    x = (GameSettings.SCREEN_WIDTH - img.get_width()) // 2
                    y = (GameSettings.SCREEN_HEIGHT - img.get_height()) // 2
                    screen.blit(img, (x, y))
                except Exception:
                    pass
        
        # Draw stat boost text after animation ends (to the right of BAG title, single line)
        if now > self._level_50_show_time and now <= self._level_50_stat_text_time:
            try:
                stat_text = "attack +20  max_hp +100"
                font = pg.font.SysFont("Microsoft JhengHei", 48)
                text_surf = font.render(stat_text, True, (255, 0, 0))
                # Position to the right of BAG text, 25px higher
                x_start = self.overlay_rect.x + 250
                y_start = self.overlay_rect.y + 35 - 25
                screen.blit(text_surf, (x_start, y_start))
            except Exception:
                pass

    def _prepare_item_cursor(self, item_idx: int) -> None:
        """Try to load and set `_item_cursor_img` for item at `item_idx`.
        If loading fails, create a small fallback surface so user still sees a cursor.
        """
        self._item_cursor_img = None
        try:
            item = self.items[item_idx]
        except Exception:
            return
        try:
            imgp = item.get('img')
            ci = None
            if imgp:
                ci = resource_manager.get_image(imgp)
            # fallback: try name-key mapping
            if ci is None:
                key = (item.get('key') or item.get('name') or '').lower()
                imgp2 = self._ITEM_NAME_TO_IMG.get(key)
                if imgp2:
                    ci = resource_manager.get_image(imgp2)
            if ci:
                try:
                    self._item_cursor_img = pg.transform.smoothscale(ci, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
                    Logger.info(f"BackpackOverlay: Loaded cursor image for item '{item.get('name')}'")
                    return
                except Exception:
                    self._item_cursor_img = ci
            # if still None, create a simple fallback surface with first letter
            try:
                surf = pg.Surface((GameSettings.TILE_SIZE, GameSettings.TILE_SIZE), pg.SRCALPHA)
                surf.fill((200, 200, 200, 180))
                font = pg.font.SysFont(None, 20)
                txt = font.render((item.get('name') or '?')[0], True, (0, 0, 0))
                tw, th = txt.get_size()
                surf.blit(txt, ((GameSettings.TILE_SIZE - tw) // 2, (GameSettings.TILE_SIZE - th) // 2))
                self._item_cursor_img = surf
                Logger.info(f"BackpackOverlay: Using fallback cursor for item '{item.get('name')}'")
            except Exception:
                self._item_cursor_img = None
        except Exception:
            self._item_cursor_img = None

    def _compute_monster_rects(self):
        """Compute monster entry rects based on current overlay layout.
        This allows hit-testing during update() even if draw() hasn't been called yet.
        """
        monsters = self.get_monsters() or []
        col_width = 300
        row_height = 80
        max_cols = 3
        max_rows = 6
        base_x = self.overlay_rect.x + 20
        base_y = self.overlay_rect.y + 90
        rects = []
        for idx, _ in enumerate(monsters):
            if idx >= max_cols * max_rows:
                break
            col = idx % max_cols
            row = idx // max_cols
            draw_x = base_x + col * col_width
            draw_y = base_y + row * row_height
            rects.append(pg.Rect(draw_x, draw_y, 300, 70))
        self._monster_rects = rects

    def _compute_item_rects(self):
        """Compute item icon rects based on current overlay layout for hit testing."""
        items = self.get_items() or []
        item_base_x = self.overlay_rect.x + 955
        item_base_y = self.overlay_rect.y + 120
        rects = []
        for i, _ in enumerate(items):
            rects.append(pg.Rect(item_base_x, item_base_y + i * 70, 48, 48))
        self._item_rects = rects

    def _draw_monster_entry(self, screen, poke: dict, base_x: int, base_y: int, is_first: bool = False):
        """Draw one monster entry at (base_x, base_y) keeping relative layout."""
        # banner
        lv_bg_path = poke.get("lv_bg") or "UI/raw/UI_Flat_Banner03a.png"
        lv_bg_img = resource_manager.get_image(lv_bg_path)
        if lv_bg_img:
            bg = pg.transform.smoothscale(lv_bg_img, (300, 70))
            screen.blit(bg, (base_x, base_y))
        # icon
        img_path = poke.get("sprite_path")
        poke_img = resource_manager.get_image(img_path) if img_path else None
        if poke_img:
            icon = pg.transform.smoothscale(poke_img, (64, 64))
            screen.blit(icon, (base_x + 8, base_y + 3))
        # name
        name_font = pg.font.SysFont(None, 24)
        name_text = name_font.render(poke.get("name", "Unknown"), True, (0, 0, 0))
        screen.blit(name_text, (base_x + 80, base_y + 5))
        # HP bar
        bar_x = base_x + 80
        bar_y = base_y + 25
        bar_w = 180
        bar_h = 16
        hp_val = poke.get("hp", 0)
        max_hp_val = poke.get("max_hp", 1)
        pg.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, int(bar_w * hp_val / max_hp_val), bar_h), border_radius=8)
        pg.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h), 2)
        # HP text
        hp_font = pg.font.SysFont(None, 20)
        hp_text = hp_font.render(f'{hp_val}/{max_hp_val}', True, (0, 0, 0))
        screen.blit(hp_text, (bar_x, bar_y + bar_h + 5))
        # Level
        lv_font = pg.font.SysFont(None, 20)
        lv_text = lv_font.render(f'Lv{poke.get("level", "?")}', True, (0, 0, 0))
        screen.blit(lv_text, (bar_x + bar_w + 10, bar_y))
        
        # Draw level 50 better icon overlapping top half of monster icon if present
        if poke.get('level_50_reached'):
            try:
                better_img_path = poke.get('better_icon_img', 'menu_sprites/better.png')
                better_img = resource_manager.get_image(better_img_path)
                if better_img:
                    better_icon = pg.transform.smoothscale(better_img, (64, 32))
                    screen.blit(better_icon, (base_x + 8, base_y + 18))
            except Exception:
                pass
        
        # Draw buff icons above the monster icon if present
        buff_y_offset = base_y + 5
        buff_x_start = base_x + 8
        if poke.get('attack_buff'):
            try:
                buff_img_path = poke.get('attack_buff_img', 'ingame_ui/options1.png')
                buff_img = resource_manager.get_image(buff_img_path)
                if buff_img:
                    buff_icon = pg.transform.smoothscale(buff_img, (24, 24))
                    screen.blit(buff_icon, (buff_x_start, buff_y_offset))
                    buff_x_start += 28
            except Exception:
                pass
        if poke.get('defense_buff'):
            try:
                buff_img_path = poke.get('defense_buff_img', 'ingame_ui/options2.png')
                buff_img = resource_manager.get_image(buff_img_path)
                if buff_img:
                    buff_icon = pg.transform.smoothscale(buff_img, (24, 24))
                    screen.blit(buff_icon, (buff_x_start, buff_y_offset))
            except Exception:
                pass
        
        # If this is the first monster, draw a check icon above the level text
        if is_first:
            try:
                chk_s = getattr(self, '_check_img', None)
                if chk_s:
                    w, h = chk_s.get_size()
                    text_w = lv_text.get_width()
                    icon_x = bar_x + bar_w + 10 + (text_w // 2) - (w // 2)
                    icon_y = bar_y - h - 4
                    screen.blit(chk_s, (icon_x, icon_y))
            except Exception:
                pass

    def draw_monster_at(self, screen, monster: dict, x: int, y: int):
        """Public helper: draw the monster info block at absolute pixel (x,y)."""
        self._draw_monster_entry(screen, monster, x, y, False)
    def draw(self, screen):
        if not self.is_active:
            return
        font2 = pg.font.SysFont(None, 32)
        screen.blit(self.dark_surface, (0, 0))
        pg.draw.rect(screen, (255, 165, 48), self.overlay_rect)
        pg.draw.rect(screen, (0, 0, 0), self.overlay_rect, 4)
        font_title = pg.font.SysFont(None, 48)
        text = font_title.render('BAG', False, (0, 0, 0))
        screen.blit(text, (self.overlay_rect.x + 30, self.overlay_rect.y + 30))

        # 顯示所有怪物資訊 - 3 列排版（每列寬度 300px），6 行
        monsters = self.get_monsters()
        col_width = 300  # 每一列寬度
        row_height = 80   # 每一行高度
        max_cols = 3      # 3 列
        max_rows = 6      # 6 行
        
        base_x = self.overlay_rect.x + 20
        base_y = self.overlay_rect.y + 90
        
        # reset monster rects each draw
        self._monster_rects = []
        for idx, poke in enumerate(monsters):
            if idx >= max_cols * max_rows:  # 最多顯示 18 個（3x6）
                break
            col = idx % max_cols
            row = idx // max_cols
            
            # 計算當前怪物的繪製位置
            draw_x = base_x + col * col_width
            draw_y = base_y + row * row_height
            
            # record rect for hover/click detection (width 300, height 70)
            r = pg.Rect(draw_x, draw_y, 300, 70)
            self._monster_rects.append(r)
            # 使用重構的函式來繪製單個怪物
            self._draw_monster_entry(screen, poke, draw_x, draw_y, idx == self.default_index)

        # 物品放在右邊（調整整體 X 位置）
        item_base_x = self.overlay_rect.x + 955
        item_base_y = self.overlay_rect.y + 120
        
        # reset item rects each draw
        self._item_rects = []
        for i, item in enumerate(self.items):
            # try the item's own img, otherwise fallback by name/key
            item_p = item.get("img") or None
            if not item_p:
                key = (item.get('key') or item.get('name') or '').lower()
                item_p = self._ITEM_NAME_TO_IMG.get(key)
            item_img = resource_manager.get_image(item_p) if item_p else None
            if item_img:
                item_img = pg.transform.smoothscale(item_img, (48, 48))
                screen.blit(item_img, (item_base_x, item_base_y + i * 70))
                # record item icon rect for hit testing (48x48)
                self._item_rects.append(pg.Rect(item_base_x, item_base_y + i * 70, 48, 48))
            else:
                # still record a rect for the slot even if image missing (use text area)
                self._item_rects.append(pg.Rect(item_base_x, item_base_y + i * 70, 48, 48))
            item_text = font2.render(item.get("name", "Item"), True, (0, 0, 0))
            screen.blit(item_text, (item_base_x + 53, item_base_y + i * 70 + 10))
            count_text = font2.render(f'x{item.get("count", 0)}', True, (0, 0, 0))
            screen.blit(count_text, (item_base_x + 210, item_base_y + i * 70 + 10))
            
        # X 按鈕 hover 效果
        x_button_default = resource_manager.get_image("UI/button_x.png")
        x_button_hover = resource_manager.get_image("UI/button_x_hover.png")
        x_img = x_button_hover if self.x_button.collidepoint(input_manager.mouse_pos) else x_button_default
        x_img = pg.transform.smoothscale(x_img, (40, 40))
        screen.blit(x_img, (self.x_button.x, self.x_button.y))
        # draw custom cursor on top when overlay is active
        try:
            mx, my = input_manager.mouse_pos
            # if item-use-mode active, draw item cursor
            if self._item_use_mode and self._item_cursor_img:
                w, h = self._item_cursor_img.get_size()
                screen.blit(self._item_cursor_img, (mx - w // 2, my - h // 2))
            else:
                # if hovering an item, show item cursor (peek item rects)
                hovered_item = None
                try:
                    for idx, r in enumerate(self._item_rects):
                        if r.collidepoint((mx, my)):
                            hovered_item = idx
                            break
                except Exception:
                    hovered_item = None
                if hovered_item is not None:
                    # prepare cursor only when hovered item changed
                    try:
                        if self._last_hovered_item_idx != hovered_item:
                            self._prepare_item_cursor(hovered_item)
                            self._last_hovered_item_idx = hovered_item
                    except Exception:
                        self._item_cursor_img = None
                    if self._item_cursor_img:
                        try:
                            w, h = self._item_cursor_img.get_size()
                            screen.blit(self._item_cursor_img, (mx - w // 2, my - h // 2))
                        except Exception:
                            pass
                    else:
                        # fallback to general cursor
                        if self._hover_index is not None and self._check_img:
                            w, h = self._check_img.get_size()
                            screen.blit(self._check_img, (mx - w // 2, my - h // 2))
                        elif self._cursor_img:
                            w, h = self._cursor_img.get_size()
                            screen.blit(self._cursor_img, (mx - w // 2, my - h // 2))
                else:
                    # if hovering a monster, use check icon as cursor (if available)
                    if self._hover_index is not None and self._check_img:
                        w, h = self._check_img.get_size()
                        screen.blit(self._check_img, (mx - w // 2, my - h // 2))
                    elif self._active_cursor_img is not None:
                        try:
                            w, h = self._active_cursor_img.get_size()
                            screen.blit(self._active_cursor_img, (mx - w // 2, my - h // 2))
                        except Exception:
                            # fallback to original _cursor_img
                            if self._cursor_img:
                                w, h = self._cursor_img.get_size()
                                screen.blit(self._cursor_img, (mx - w // 2, my - h // 2))
                    elif self._cursor_img:
                        w, h = self._cursor_img.get_size()
                        screen.blit(self._cursor_img, (mx - w // 2, my - h // 2))
        except Exception:
            pass
        # Draw level 50 tip on top
        self._draw_level_50_tip(screen)

    def _sprite_group_by_path(self, path: str):
        try:
            p = (path or "").lower()
            if "menusprite" in p:
                for g, mp in _EVOLVE_GROUPS.items():
                    if mp["base"] in p or mp["mid"] in p or mp["high"] in p:
                        return g
                # numeric fallback
                import re
                m = re.search(r"menusprite(\d+)", p)
                if m:
                    n = int(m.group(1))
                    if n in (1, 2, 3):
                        return "1"
                    if n in (7, 8, 9):
                        return "7"
                    if n in (12, 13, 14):
                        return "12"
                    if n == 16:
                        return "16"
        except Exception:
            return None
        return None

    def _apply_level_sprite_evolution(self, monster: dict):
        try:
            lvl = int(monster.get("level", 1))
        except Exception:
            lvl = 1
        sp = monster.get("sprite_path") or ""
        grp = self._sprite_group_by_path(sp)
        if not grp:
            return
        mp = _EVOLVE_GROUPS.get(grp)
        if not mp:
            return
        if lvl >= 100:
            monster["sprite_path"] = mp["high"]
        elif lvl >= 50:
            monster["sprite_path"] = mp["mid"]
        else:
            monster["sprite_path"] = mp["base"]

    def _apply_level_sprite_evolution_all(self):
        mons = self.get_monsters() or []
        for m in mons:
            try:
                self._apply_level_sprite_evolution(m)
            except Exception:
                continue
