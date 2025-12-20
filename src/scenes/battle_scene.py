# ============================================
# 進階戰鬥場景模組
# 功能: 回合制戰鬥、屬性相剋、技能效果
# 特性: 戰鬥動畫、傷害計算、勝敗判定
# ============================================

import pygame as pg
import os

from src.scenes.scene import Scene
from src.sprites import BackgroundSprite, Sprite
from src.interface.components import Button
from src.core.services import input_manager
from src.utils import GameSettings
from typing import Optional, Tuple, List

class BattleScene(Scene):
    """進階戰鬥場景
    
    責任:
    - 顯示玩家和敵人怪物
    - 實施回合制戰鬥邏輯
    - 計算屬性相剋傷害倍率
    - 顯示戰鬥結果和動畫效果
    """
    
    # ===== 屬性相剋表 =====
    # 格式: 攻擊方屬性 -> {防守方屬性: 傷害倍率}
    # 倍率: 2.0 (超級有效)、1.0 (正常)、0.5 (不太有效)、0 (無效果)
    TYPE_EFFECTIVENESS = {
        "Grass":    {"Water": 2, "Fire": 0.5, "Grass": 0.5, "Flying": 0.5},
        "Fire":     {"Grass": 2, "Ice": 2, "Fire": 0.5, "Water": 0.5},
        "Water":    {"Fire": 2, "Grass": 0.5, "Water": 0.5},
        "Electric": {"Water": 2, "Flying": 2, "Grass": 0.5, "Electric": 0.5},
        "Ice":      {"Grass": 2, "Flying": 2, "Fire": 0.5, "Water": 0.5, "Ice": 0.5},
        "Flying":   {"Grass": 2, "Electric": 0.5},
        "Ghost":    {"Ghost": 2, "Normal": 0},
        "Normal":   {"Ghost": 0},
    }

    # ===== 精靈圖片與屬性對應 =====
    # 格式: 精靈檔案名 -> [屬性列表]
    # 怪物可能有多個屬性 (如草/毒、鋼/飛等)
    SPRITE_TYPES = {
        "advancebattlemenusprite1.png": ["Grass"],
        "menusprite1.png": ["Grass"],
        "menusprite2.png": ["Grass"],
        "menusprite3.png": ["Grass"],
        "menusprite4.png": ["Normal"],
        "menusprite5.png": ["Flying"],
        "menusprite6.png": ["Ice"],
        "menusprite7.png": ["Fire"],
        "menusprite8.png": ["Fire"],
        "menusprite9.png": ["Fire", "Flying"],
        "menusprite10.png": ["Ghost"],
        "menusprite11.png": ["Electric"],
        "menusprite12.png": ["Water"],
        "menusprite13.png": ["Water"],
        "menusprite14.png": ["Water", "Ice"],
        "menusprite15.png": ["Grass"],
        "menusprite16.png": ["Grass", "Flying"],
    }
    bush_monster_index = 0  # 靜態變數，記錄灌木怪物輪換索引

    def __init__(self) -> None:
        """初始化戰鬥場景"""
        super().__init__()
        # ===== 背景精靈 =====
        self.background = BackgroundSprite("backgrounds/background1.png")

        # ===== 字體初始化 =====
        pg.font.init()
        from src.utils.loader import load_font
        self.small_font = load_font("Minecraft.ttf", 40)          # 小文字
        self.medium_font = load_font("Minecraft.ttf", 50)         # 中文字
        self.info_font = load_font("Minecraft.ttf", 28)           # 資訊文字
        self.msjh_font = pg.font.SysFont("Microsoft JhengHei", 40)  # 中文系統字體
        # ===== 效果提示用大字體（放大約 2 倍，紅字，顯示屬性倍率） =====
        self.effect_font = pg.font.SysFont("Microsoft JhengHei", 80)

        # ===== UI 精靈 =====
        self.enemy_sprite = None  # type: Optional[Sprite]  # 敵人怪物精靈
        self.menusprite3 = Sprite("menu_sprites/menusprite3.png")  # 預設敵人圖片
        self.banner = Sprite("UI/raw/UI_Flat_Banner03a.png")       # 背景橫幅

        # ===== 下方四個按鈕設定 =====
        btn_w, btn_h = 180, 56                   # 按鈕寬度、高度
        spacing = 16                             # 按鈕間距
        total_w = 4 * btn_w + 3 * spacing        # 四個按鈕總寬度
        start_x = (GameSettings.SCREEN_WIDTH - total_w) // 2   # 第一個按鈕起始位置 (水平居中)
        y = GameSettings.SCREEN_HEIGHT - btn_h - 24  # 按鈕距離底部距離


        self.buttons = [] 
        # ===== 創建四個戰鬥按鈕 =====
        # "Fight" (攻擊)、"ITEM" (道具)、"Catch" (捕捉)、"Run" (逃跑)
        for i, label in enumerate(["Fight", "ITEM", "Catch", "Run"]):
            x = start_x + i * (btn_w + spacing)
            cb = getattr(self, f"_on_{label.lower()}") if hasattr(self, f"_on_{label.lower()}") else self._on_run
            btn = Button("UI/raw/UI_Flat_Button01a_4.png", "UI/raw/UI_Flat_Button01a_1.png", x, y, btn_w, btn_h, cb)
            self.buttons.append((btn, label))

        # ===== 敵人初始狀態設定 =====
        # 預設為與助教 GIF 中相同的角色資訊
        self.step = 0                      # 當前戰鬥步驟 (玩家/敵人回合)
        self.is_npc_battle = True          # 是否與 NPC 戰鬥 (True) 或灌木野生怪物 (False)
        self.enemy_monster = None          # type: Optional[dict]  # 敵人怪物資料
        self.enemy_name = "Blastoise"      # 敵人名稱
        self.enemy_level = 32              # 敵人等級
        self.enemy_max_hp = 180            # 敵人最大 HP
        self.enemy_hp = 120                # 敵人當前 HP
        self.enemy_sprite = Sprite("menu_sprites/menusprite3.png")  # 敵人圖片

        # ===== 玩家狀態初始化 =====
        self.player_max_hp = 201           # 玩家怪物最大 HP
        self.player_hp = 180               # 玩家怪物當前 HP
        self.waiting_for_enemy = False     # 是否等待敵人攻擊
        self.enemy_attack_timer = 0.0      # 敵人攻擊計時器
        self.custom_bottom_text = None     # type: Optional[str]  # 自訂底部文字
        self.effect_text = None            # 攻擊效果提示文字（顯示於畫面上方）
        self.effect_multiplier = 1.0       # 本場戰鬥的屬性倍率

    def enter(self, is_npc_battle: bool = True, enemy: Optional[dict] = None) -> None:
        self.step = 0
        self.is_npc_battle = is_npc_battle

        # 默認敵人屬性
        self.enemy_monster = None
        # 野生戰鬥自動輪流選怪
        if not is_npc_battle:
            import json
            try:
                with open("saves/game0 copy.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                monsters = data.get("bag", {}).get("monsters", [])
            except Exception as e:
                monsters = []
            if monsters:
                idx = BattleScene.bush_monster_index % len(monsters)
                m = monsters[idx]
                BattleScene.bush_monster_index += 1
                self.enemy_monster = m
                self.enemy_name = m.get("name", "Blastoise")
                self.enemy_level = m.get("level", 32)
                self.enemy_max_hp = m.get("max_hp", 180)
                self.enemy_hp = m.get("hp", self.enemy_max_hp)
                sprite_path = m.get("sprite_path") or m.get("img") or "menu_sprites/menusprite3.png"
                self.enemy_sprite = Sprite(sprite_path)
            else:
                self.enemy_name = "Blastoise"
                self.enemy_level = 32
                self.enemy_max_hp = 180
                self.enemy_hp = 120
                self.enemy_sprite = Sprite("menu_sprites/menusprite3.png")
        else:
            # Prefer Pikachu from the in-memory backpack overlay (if game scene exists)
            pikachu = None
            try:
                from src.core.services import scene_manager
                game_scene = scene_manager._scenes.get("game")
                if game_scene and hasattr(game_scene, "backpack_overlay"):
                    monsters = game_scene.backpack_overlay.get_monsters()
                else:
                    monsters = []
            except Exception:
                monsters = []

            for m in monsters:
                if m.get("name", "").lower() == "pikachu":
                    pikachu = m
                    break

            if pikachu:
                self.enemy_name = pikachu.get("name", "Pikachu")
                self.enemy_level = pikachu.get("level", 1)
                self.enemy_max_hp = pikachu.get("max_hp", 100)
                self.enemy_hp = pikachu.get("hp", self.enemy_max_hp)
                sprite_path = pikachu.get("sprite_path") or pikachu.get("img") or "menu_sprites/menusprite3.png"
                self.enemy_sprite = Sprite(sprite_path)
            else:
                # fallback to default
                self.enemy_name = "Blastoise"
                self.enemy_level = 32
                self.enemy_max_hp = 180
                self.enemy_hp = 120
                self.enemy_sprite = Sprite("menu_sprites/menusprite3.png")

        # 重置玩家屬性
        # Player monster: prefer Pikachu from in-memory backpack overlay
        self.player_monster = None
        try:
            from src.core.services import scene_manager
            game_scene = scene_manager._scenes.get("game")
            monsters = []
            if game_scene and hasattr(game_scene, "backpack_overlay"):
                monsters = game_scene.backpack_overlay.get_monsters()
            # prefer explicit default_index from backpack overlay, else pick Pikachu if exists, otherwise first monster
            chosen = None
            try:
                default_idx = getattr(game_scene.backpack_overlay, 'default_index', None)
                if default_idx is not None and 0 <= default_idx < len(monsters):
                    chosen = monsters[default_idx]
            except Exception:
                chosen = None
            if chosen is None:
                pikachu = None
                for m in monsters:
                    if m.get("name", "").lower() == "pikachu":
                        pikachu = m
                        break
                chosen = pikachu or (monsters[0] if monsters else None)
            self.player_monster = chosen
            try:
                from src.utils import Logger
                Logger.info(f"BattleScene.enter: backpack default_index={getattr(game_scene.backpack_overlay, 'default_index', None)}")
                names = [m.get('name') for m in monsters]
                Logger.info(f"BattleScene.enter: monsters={names}, chosen={(self.player_monster.get('name') if self.player_monster else None)}")
            except Exception:
                pass
        except Exception:
            self.player_monster = None

        if self.player_monster:
            self.player_max_hp = self.player_monster.get("max_hp", 1)
            self.player_hp = self.player_monster.get("hp", self.player_max_hp)
        else:
            self.player_max_hp = 201
            self.player_hp = 180
        self.waiting_for_enemy = False
        self.enemy_attack_timer = 0.0
        self.custom_bottom_text = None
        # catching / pokeball state
        self.enemy_defeated = False
        self.catching = False
        self.pokeball_sprite = None
        self._pokeball_state = None  # 'travel','stay','leave' or None
        self._pokeball_progress = 0.0
        self._pokeball_travel_time = 0.6
        self._pokeball_stay_time = 2.0
        self._pokeball_leave_time = 0.6
        self._pokeball_start_pos = (0, 0)
        self._pokeball_target_pos = (0, 0)
        self._pokeball_leave_target = (0, -100)

        # 進入戰鬥時立即計算相剋文字與倍率
        try:
            self._init_effect_text_and_multiplier()
        except Exception:
            self.effect_text = None
            self.effect_multiplier = 1.0

    def update(self, dt: float) -> None:
        """更新場景邏輯"""
        # 如果背包打开，优先处理背包的更新和输入
        try:
            from src.core.services import scene_manager
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, 'backpack_overlay'):
                if game_scene.backpack_overlay.is_active:
                    game_scene.backpack_overlay.update(dt)
                    return  # 背包打开时阻止战斗场景的其他更新
        except Exception:
            pass
        
        if input_manager.key_pressed(pg.K_SPACE):
            self.step = min(3, self.step + 1)  #最大為3

        if self.step == 3:
            for b, _ in self.buttons:
                b.update(dt)

        if self.waiting_for_enemy:
            self.enemy_attack_timer += dt         #紀錄時間
            if self.enemy_attack_timer >= 2.0:
                # 計算敵人攻擊傷害（基礎 40，考慮防禦 buff）
                base_damage = 40
                defense_reduction = 0
                try:
                    if getattr(self, 'player_monster', None) is not None:
                        pm = self.player_monster
                        if pm.get('defense_buff'):
                            defense_reduction = 5  # 防禦 buff 減少 5 點傷害
                except Exception:
                    pass
                actual_damage = max(1, base_damage - defense_reduction)
                
                self.player_hp = max(0, self.player_hp - actual_damage)
                # sync damage back to backpack monster if present
                try:
                    if getattr(self, 'player_monster', None) is not None:
                        pm = self.player_monster
                        pm['hp'] = max(0, pm.get('hp', self.player_hp) - actual_damage)
                except Exception:
                    pass
                self.waiting_for_enemy = False              
                self.enemy_attack_timer = 0.0
                
                # 檢查玩家怪物是否被擊敗
                if self.player_hp <= 0:
                    # 嘗試切換到下一只怪物
                    switched = self._switch_to_next_monster()
                    if not switched:
                        # 沒有更多怪物可用，戰鬥失敗
                        from src.core.services import scene_manager
                        scene_manager.change_scene("game")

        if self.catching and self.pokeball_sprite is not None:
            if self._pokeball_state == 'travel':
                self._pokeball_progress += dt / max(1e-6, self._pokeball_travel_time)
                t = min(1.0, self._pokeball_progress)
                sx, sy = self._pokeball_start_pos
                tx, ty = self._pokeball_target_pos
                nx = sx + (tx - sx) * t
                ny = sy + (ty - sy) * t
                self.pokeball_sprite.rect.center = (round(nx), round(ny))
                if t >= 1.0:
                    self._pokeball_state = 'stay'
                    self._pokeball_progress = 0.0
                    self._pokeball_stay_elapsed = 0.0
            elif self._pokeball_state == 'stay':
                self._pokeball_stay_elapsed += dt
                if self._pokeball_stay_elapsed >= self._pokeball_stay_time:
                    # begin leave
                    curx, cury = self.pokeball_sprite.rect.center
                    self._pokeball_leave_start = (curx, cury)
                    self._pokeball_leave_target = (curx, -100)
                    self._pokeball_state = 'leave'
                    self._pokeball_progress = 0.0
            elif self._pokeball_state == 'leave':
                self._pokeball_progress += dt / max(1e-6, self._pokeball_leave_time)
                t = min(1.0, self._pokeball_progress)
                sx, sy = self._pokeball_leave_start
                tx, ty = self._pokeball_leave_target
                nx = sx + (tx - sx) * t
                ny = sy + (ty - sy) * t
                self.pokeball_sprite.rect.center = (round(nx), round(ny))
                if t >= 1.0:
                    # finish catching animation
                    self.catching = False
                    self._pokeball_state = None
                    self.pokeball_sprite = None
                    # after catch animation complete, actually handle defeated monster
                    self._handle_enemy_defeated()

    def draw(self, screen: pg.Surface) -> None:
        """繪製場景"""
        self.background.draw(screen)
        bar_h = GameSettings.SCREEN_HEIGHT // 5
        bar_y = GameSettings.SCREEN_HEIGHT - bar_h
        pg.draw.rect(screen, (60, 60, 60), (0, bar_y, GameSettings.SCREEN_WIDTH, bar_h))

        # 底部文字
        text_map_npc = [
            "Rival challenged you to a battle!",
            "Rival sent out Leogreen!",
            "Go, Florion!",
            "What will Florion do?",
        ]
        text_map_bush = [
            "Wild Florion appear!",
            "Rival sent out Leogreen!",
            "Go, Florion!",
            "What will Florion do?",
        ]
        #---------判斷是否為npc 決定要用的字典-----------------
        if self.is_npc_battle:
            text_map = text_map_npc
        else:
            text_map = text_map_bush
        #---------判斷是否為npc 決定要用的字典-----------------

        if self.custom_bottom_text is not None:
            # custom_bottom_text 使用微軟正黑體
            txt = self.msjh_font.render(self.custom_bottom_text, True, (255, 255, 255))
        else:
            txt = self.small_font.render(text_map[self.step] if self.step < 3 else text_map[3], True, (255, 255, 255))
        screen.blit(txt, (8, bar_y + 8))

        if self.step < 3:
            hint = self.small_font.render("Press SPACE to continue..", True, (255, 215, 0))
            hx = GameSettings.SCREEN_WIDTH - hint.get_width() - 8
            hy = GameSettings.SCREEN_HEIGHT - hint.get_height() - 8
            screen.blit(hint, (hx, hy))

        if self.step == 3:
            for b, label in self.buttons:
                b.draw(screen)
                lbl = self.small_font.render(label, True, (0, 0, 0))
                bx, by, bw, bh = b.hitbox
                lx = bx + (bw - lbl.get_width()) // 2
                ly = by + (bh - lbl.get_height()) // 2
                screen.blit(lbl, (lx, ly))

        if self.step >= 1 or not self.is_npc_battle:
            self._draw_enemy_info(screen)
        if self.step >= 2 or not self.is_npc_battle:
            self._draw_player_info(screen)
        # 顯示屬性相剋提示文字（置於上方中央）
        if self.effect_text:
            eff_surface = self.effect_font.render(self.effect_text, True, (255, 0, 0))
            eff_x = (GameSettings.SCREEN_WIDTH - eff_surface.get_width()) // 2
            eff_y = 8
            screen.blit(eff_surface, (eff_x, eff_y))
        if self.pokeball_sprite is not None:
            self.pokeball_sprite.draw(screen)
        
        # 绘制背包界面（如果已打开）
        try:
            from src.core.services import scene_manager
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, 'backpack_overlay'):
                if game_scene.backpack_overlay.is_active:
                    game_scene.backpack_overlay.draw(screen)
        except Exception:
            pass

    def _draw_enemy_info(self, screen: pg.Surface) -> None:
        """繪製敵人信息"""
        bar_w, bar_h = 320, 80
        bar_x = GameSettings.SCREEN_WIDTH - bar_w - 70
        bar_y = 50
        banner_img = pg.transform.scale(self.banner.image, (bar_w, bar_h))
        screen.blit(banner_img, (bar_x, bar_y))
        # 只顯示精靈 icon，不顯示其他裝飾
        icon_img = self.enemy_sprite.image
        icon = pg.transform.scale(icon_img, (78, 78))
        screen.blit(icon, (bar_x + 8, bar_y - 10))
        name = self.info_font.render(self.enemy_name, True, (0, 0, 0))
        screen.blit(name, (bar_x + 90, bar_y + 6))
        max_hp = self.enemy_max_hp
        hp = max(0, self.enemy_hp)
        hp_w = int(120 * hp / max_hp)
        pg.draw.rect(screen, (180, 220, 180), (bar_x + 90, bar_y + 28, 120, 12))
        pg.draw.rect(screen, (80, 200, 80), (bar_x + 90, bar_y + 28, hp_w, 12))
        hp_text = self.info_font.render(f"{hp}/{max_hp}", True, (0, 0, 0))
        screen.blit(hp_text, (bar_x + 90, bar_y + 44))

        lv = self.info_font.render(f"Lv.{self.enemy_level}", True, (0, 0, 0))
        screen.blit(lv, (bar_x + 220, bar_y + 28))
        
        # 下方大型精靈圖 - 只顯示精靈圖片，不顯示 better 等裝飾
        ms2_big = pg.transform.scale(self.enemy_sprite.image, (120, 120))
        screen.blit(ms2_big, (GameSettings.SCREEN_WIDTH // 2 + 200, GameSettings.SCREEN_HEIGHT // 2 - ms2_big.get_height() // 2 - 40))

    def _draw_player_info(self, screen: pg.Surface) -> None:
        """繪製玩家信息"""
        bar_w, bar_h = 320, 80
        bar_x = 32
        bar_y = 50
        banner_img = pg.transform.scale(self.banner.image, (bar_w, bar_h))
        screen.blit(banner_img, (bar_x, bar_y))
        # Try to use Pikachu from the in-memory backpack overlay (game scene)
        # Prefer the actual selected player monster for this battle if available
        try:
            from src.core.services import scene_manager, resource_manager
            icon_img = None
            name_text_s = None
            max_hp = None
            hp = None
            level_val = None
            # if player_monster was set during enter(), use it
            if getattr(self, 'player_monster', None) is not None:
                pm = self.player_monster
                icon_img = resource_manager.get_image(pm.get('sprite_path') or pm.get('img') or 'menu_sprites/menusprite3.png')
                name_text_s = pm.get('name', 'Player')
                max_hp = max(1, pm.get('max_hp', 1))
                hp = max(0, pm.get('hp', max_hp))
                level_val = pm.get('level', '?')
            else:
                # fallback to previous behavior: try to use Pikachu from backpack overlay
                game_scene = scene_manager._scenes.get("game")
                pikachu = None
                if game_scene and hasattr(game_scene, "backpack_overlay"):
                    monsters = game_scene.backpack_overlay.get_monsters()
                    for m in monsters:
                        if m.get("name", "").lower() == "pikachu":
                            pikachu = m
                            break
                if pikachu:
                    icon_img = resource_manager.get_image(pikachu.get("sprite_path") or pikachu.get("img") or "menu_sprites/menusprite1.png")
                    name_text_s = pikachu.get("name", "Pikachu")
                    max_hp = max(1, pikachu.get("max_hp", 1))
                    hp = max(0, pikachu.get("hp", max_hp))
                    level_val = pikachu.get("level", "?")
                else:
                    icon_img = self.menusprite3.image
                    name_text_s = "Florion"
                    max_hp = max(1, self.player_max_hp)
                    hp = max(0, self.player_hp)
                    level_val = 20
        except Exception:
            icon_img = self.menusprite3.image
            name_text_s = "Florion"
            max_hp = max(1, self.player_max_hp)
            hp = max(0, self.player_hp)
            level_val = 20

        # 只顯示精靈 icon，不顯示其他裝飾
        if icon_img:
            icon = pg.transform.scale(icon_img, (78, 78))
            screen.blit(icon, (bar_x + 8, bar_y - 10))
        name = self.info_font.render(name_text_s, True, (0, 0, 0))
        screen.blit(name, (bar_x + 90, bar_y + 6))
        hp_w = int(120 * hp / max_hp)
        pg.draw.rect(screen, (180, 220, 180), (bar_x + 90, bar_y + 28, 120, 12))
        pg.draw.rect(screen, (80, 200, 80), (bar_x + 90, bar_y + 28, hp_w, 12))
        hp_text = self.info_font.render(f"{hp}/{max_hp}", True, (0, 0, 0))
        screen.blit(hp_text, (bar_x + 90, bar_y + 44))
        lv = self.info_font.render(f"Lv.{level_val}", True, (0, 0, 0))
        screen.blit(lv, (bar_x + 220, bar_y + 28))
        
        # Draw buff icons above player info banner if present
        try:
            pm = getattr(self, 'player_monster', None)
            if pm:
                buff_x_start = bar_x + 8
                buff_y = bar_y - 30
                if pm.get('attack_buff'):
                    buff_img_path = pm.get('attack_buff_img', 'ingame_ui/options1.png')
                    buff_img = resource_manager.get_image(buff_img_path)
                    if buff_img:
                        buff_icon = pg.transform.smoothscale(buff_img, (24, 24))
                        screen.blit(buff_icon, (buff_x_start, buff_y))
                        buff_x_start += 28
                if pm.get('defense_buff'):
                    buff_img_path = pm.get('defense_buff_img', 'ingame_ui/options2.png')
                    buff_img = resource_manager.get_image(buff_img_path)
                    if buff_img:
                        buff_icon = pg.transform.smoothscale(buff_img, (24, 24))
                        screen.blit(buff_icon, (buff_x_start, buff_y))
        except Exception:
            pass
        
        # 下方大型精靈圖 - 只顯示精靈圖片，不顯示 better 等裝飾
        try:
            ms3 = pg.transform.scale(icon_img, (120, 120))
            ms3 = pg.transform.flip(ms3, True, False)
            x = 80
            y = GameSettings.SCREEN_HEIGHT // 2 - ms3.get_height() // 2 + 40
            screen.blit(ms3, (x, y))
        except Exception:
            pass

    def _on_fight(self) -> None:
        """玩家選擇戰鬥"""
        if self.enemy_hp <= 0:
            return
        # 使用進入戰鬥時計算好的倍率與提示，不再此時更新
        multiplier = getattr(self, "effect_multiplier", 1.0)
        base_damage = 100
        
        # 檢查攻擊 buff
        attack_bonus = 0
        try:
            if getattr(self, 'player_monster', None) is not None:
                pm = self.player_monster
                if pm.get('attack_buff'):
                    attack_bonus = 20  # 攻擊 buff 增加 20 點傷害
        except Exception:
            pass
        
        damage = int(base_damage * multiplier) + attack_bonus
        if damage <= 0:
            # 確保顯示「完全沒有效果！」並不扣血
            damage = 0
            self.effect_text = "完全沒有效果！"
            self.effect_multiplier = 0
        self.enemy_hp = max(0, self.enemy_hp - damage)
        if self.enemy_hp <= 0:
            # mark defeated but defer leaving until pokeball throw
            self.enemy_defeated = True
            self.custom_bottom_text = "Enemy fainted! Press Catch to throw Pokeball."
            return
        self.waiting_for_enemy = True
        self.enemy_attack_timer = 0.0

    def _on_item(self) -> None:
        """玩家選擇使用道具 (打開背包)"""
        # 打開背包界面
        try:
            from src.core.services import scene_manager
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, 'backpack_overlay'):
                if game_scene.backpack_overlay.is_active:
                    game_scene.backpack_overlay.close()
                    self.custom_bottom_text = "Closed bag"
                else:
                    game_scene.backpack_overlay.open()
                    self.custom_bottom_text = "Opening bag..."
            else:
                self.custom_bottom_text = "Bag not available"
        except Exception as e:
            from src.utils import Logger
            Logger.error(f"Failed to open bag: {e}")
            self.custom_bottom_text = "Error opening bag"

    def _on_catch(self) -> None:
        """玩家選擇捕捉 (丟出寶貝球)"""
        #血量到0才能捕捉
        if not self.enemy_defeated and self.enemy_hp > 0:
            self.custom_bottom_text = "Can't catch yet!"
            return
        if self.catching:
            return
        #做球
        self.pokeball_sprite = Sprite("ingame_ui/ball.png", size=(48, 48))
        #處理球的位置
        ms3 = pg.transform.scale(self.menusprite3.image, (120, 120))
        player_x = 80 + ms3.get_width() // 2
        player_y = GameSettings.SCREEN_HEIGHT // 2 - ms3.get_height() // 2 + 40 + ms3.get_height() // 2
        # enemy pos used in _draw_enemy_info: center +200 x
        enemy_img = pg.transform.scale(self.enemy_sprite.image, (120, 120))
        enemy_x = GameSettings.SCREEN_WIDTH // 2 + 200 + enemy_img.get_width() // 2
        enemy_y = GameSettings.SCREEN_HEIGHT // 2 - enemy_img.get_height() // 2 - 40 + enemy_img.get_height() // 2
        # initialize pokeball movement
        self._pokeball_start_pos = (player_x, player_y)
        self._pokeball_target_pos = (enemy_x, enemy_y - 40)  # slightly above enemy
        self.pokeball_sprite.rect.center = (round(player_x), round(player_y))
        self.catching = True
        self._pokeball_state = 'travel'
        self._pokeball_progress = 0.0
        self.custom_bottom_text = "Throwing Pokeball..."

    def _on_run(self) -> None:
        """玩家選擇逃跑"""
        # 清除戰鬥 buff
        try:
            if getattr(self, 'player_monster', None) is not None:
                pm = self.player_monster
                pm.pop('attack_buff', None)
                pm.pop('attack_buff_img', None)
                pm.pop('defense_buff', None)
                pm.pop('defense_buff_img', None)
        except Exception:
            pass
        from src.core.services import scene_manager
        scene_manager.change_scene("game")

    # ====== 屬性提示計算 ======
    def _set_effect_text_from_multiplier(self, multiplier: float) -> None:
        if multiplier == 0:
            self.effect_text = "完全沒有效果！"
        elif multiplier > 1:
            self.effect_text = "效果拔群！"
        elif multiplier < 1:
            self.effect_text = "效果不太好……"
        else:
            self.effect_text = "不相剋"
        self.effect_multiplier = multiplier if multiplier is not None else 1.0

    # ====== 屬性判定與倍率計算 ======
    def _get_monster_types(self, monster: Optional[dict]) -> list:
        """由怪物資料或當前精靈圖片推斷屬性，若無則回傳 ["Normal"]"""
        if monster is None:
            return ["Normal"]
        # 先嘗試怪物字典中直接給的屬性
        types = []
        try:
            t = monster.get("type") or monster.get("types")
            if isinstance(t, str):
                types = [t]
            elif isinstance(t, (list, tuple)):
                types = list(t)
        except Exception:
            types = []

        # 若未指定，依 sprite_path 判斷
        if not types:
            sp = None
            try:
                sp = monster.get("sprite_path") or monster.get("img")
            except Exception:
                sp = None
            if sp:
                filename = os.path.basename(sp).lower()
                for key, val in BattleScene.SPRITE_TYPES.items():
                    if filename == key.lower():
                        types = val
                        break
        return types or ["Normal"]

    def _compute_type_multiplier(self, attacker_types: list, defender_types: list) -> float:
        """計算屬性相剋倍率（複數屬性時相乘）"""
        if not attacker_types:
            attacker_types = ["Normal"]
        if not defender_types:
            defender_types = ["Normal"]
        total = 1.0
        for atk in attacker_types:
            atk_table = BattleScene.TYPE_EFFECTIVENESS.get(atk, {})
            for d in defender_types:
                total *= atk_table.get(d, 1.0)
        return total

    def _init_effect_text_and_multiplier(self) -> None:
        """開戰時預先計算相剋提示與倍率（未行動前即顯示，Fight 不再重算）"""
        attacker_types = self._get_monster_types(self.player_monster)
        defender_types = self._get_monster_types(self.enemy_monster)
        multiplier = self._compute_type_multiplier(attacker_types, defender_types)
        self._set_effect_text_from_multiplier(multiplier)

    def _switch_to_next_monster(self) -> bool:
        """切換到下一只可用的怪物
        
        返回:
            True: 成功切換到下一只怪物
            False: 沒有更多可用怪物
        """
        try:
            from src.core.services import scene_manager
            game_scene = scene_manager._scenes.get("game")
            if not game_scene or not hasattr(game_scene, "backpack_overlay"):
                return False
            
            monsters = game_scene.backpack_overlay.get_monsters()
            if not monsters:
                return False
            
            # 找到當前怪物索引
            current_index = -1
            if self.player_monster:
                for i, m in enumerate(monsters):
                    if m.get('name') == self.player_monster.get('name'):
                        current_index = i
                        break
            
            # 尋找下一只 HP > 0 的怪物
            start_index = (current_index + 1) % len(monsters)
            for offset in range(len(monsters)):
                check_index = (start_index + offset) % len(monsters)
                candidate = monsters[check_index]
                if candidate.get('hp', 0) > 0:
                    # 找到可用怪物，切換過去
                    self.player_monster = candidate
                    self.player_max_hp = candidate.get('max_hp', 100)
                    self.player_hp = candidate.get('hp', self.player_max_hp)
                    
                    # 更新背包的 default_index
                    game_scene.backpack_overlay.default_index = check_index
                    
                    # 重新計算屬性相剋
                    try:
                        self._init_effect_text_and_multiplier()
                    except Exception:
                        self.effect_text = None
                        self.effect_multiplier = 1.0
                    
                    # 顯示切換提示
                    self.custom_bottom_text = f"切換到 {candidate.get('name', 'Unknown')}！"
                    return True
            
            # 沒有找到任何 HP > 0 的怪物
            return False
            
        except Exception as e:
            try:
                from src.utils import Logger
                Logger.error(f"切換怪物時發生錯誤: {e}")
            except Exception:
                pass
            return False
    
    def _handle_enemy_defeated(self) -> None:
        """處理敵人被擊敗"""
        # 清除戰鬥 buff
        try:
            if getattr(self, 'player_monster', None) is not None:
                pm = self.player_monster
                pm.pop('attack_buff', None)
                pm.pop('attack_buff_img', None)
                pm.pop('defense_buff', None)
                pm.pop('defense_buff_img', None)
        except Exception:
            pass
        
        from src.core.services import scene_manager
        monster = {
            "name": self.enemy_name,
            "hp": self.enemy_max_hp,
            "max_hp": self.enemy_max_hp,
            "level": self.enemy_level,
        }

        # resolve sprite_path whether enemy_monster is a dict or an object
        sp = None
        try:
            if isinstance(self.enemy_monster, dict):
                sp = self.enemy_monster.get("sprite_path") or self.enemy_monster.get("img")
            else:
                sp = getattr(self.enemy_monster, "sprite_path", None) or getattr(self.enemy_monster, "img", None)
        except Exception:
            sp = None

        monster["sprite_path"] = sp or "menu_sprites/menusprite3.png"
        # 加到backpack overlay那邊
        scene_manager._scenes.get("game").backpack_overlay.add_monster(monster)
        scene_manager.change_scene("game")