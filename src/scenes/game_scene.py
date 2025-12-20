import pygame as pg
import threading
import time

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position, Direction
from src.core.services import sound_manager
from src.sprites import Sprite, Animation
from src.interface.components import ChatOverlay
from typing import override

class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    
    def __init__(self):
        super().__init__()
        self.online_manager = None

        from src.data.bag import Bag
        from src.entities.player import Player
        from src.core.managers.game_manager import GameManager
        from src.maps.map import Map
        from src.utils import Teleport
#--------------------------------------------------

        # Load teleport data from JSON file
        import json
        import os
        
        def load_teleports_from_json(json_path: str) -> dict:
            """Load teleport data from JSON file. Returns dict with map_name as key and list of Teleport objects as value."""
            teleports_by_map = {}
            try:
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Process each map's teleport data
                    map_data = data.get("map", [])
                    for map_info in map_data:
                        map_path = map_info.get("path")
                        teleport_list = map_info.get("teleport", [])
                        
                        if map_path and teleport_list:
                            tps = []
                            for tp_data in teleport_list:
                                x = tp_data.get("x", 0)
                                y = tp_data.get("y", 0)
                                destination = tp_data.get("destination", "")
                                pair_id = tp_data.get("pair_id", None)
                                
                                tp = Teleport(
                                    x * GameSettings.TILE_SIZE,
                                    y * GameSettings.TILE_SIZE,
                                    destination,
                                    pair_id
                                )
                                tps.append(tp)
                            
                            teleports_by_map[map_path] = tps
            except Exception as e:
                Logger.warning(f"Failed to load teleports from JSON: {e}")
            
            return teleports_by_map
        
        def load_enemy_trainers_from_json(json_path: str) -> dict:
            """Load enemy trainers data from JSON file. Returns dict with map_name as key and list of trainer data as value."""
            trainers_by_map = {}
            try:
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Process each map's enemy_trainers data
                    map_data = data.get("map", [])
                    for map_info in map_data:
                        map_path = map_info.get("path")
                        trainer_list = map_info.get("enemy_trainers", [])
                        
                        if map_path:
                            trainers_by_map[map_path] = trainer_list
            except Exception as e:
                Logger.warning(f"Failed to load enemy_trainers from JSON: {e}")
            
            return trainers_by_map
        
        # Load data from game0 copy.json
        teleports_data = load_teleports_from_json("saves/game0 copy.json")
        trainers_data = load_enemy_trainers_from_json("saves/game0 copy.json")

        # 從JSON讀取地圖配置
        from src.maps.map import Map
        maps = {}
        
        map_configs = [
            ("map.tmx", Position(16 * GameSettings.TILE_SIZE, 30 * GameSettings.TILE_SIZE)),
            ("gym.tmx", Position(12 * GameSettings.TILE_SIZE, 12 * GameSettings.TILE_SIZE)),
            ("ice.tmx", Position(2 * GameSettings.TILE_SIZE, 2 * GameSettings.TILE_SIZE))
        ]
        
        for map_path, spawn_pos in map_configs:
            tps = teleports_data.get(map_path, [])
            maps[map_path] = Map(map_path, tps, spawn_pos)
        
#--------------------------------------------------
        player = Player(16 * GameSettings.TILE_SIZE, 30 * GameSettings.TILE_SIZE, None)
        bag = Bag([], [])
        enemy_trainers = {"map.tmx": [], "gym.tmx": [], "ice.tmx": []}
        self.game_manager = GameManager(maps, "map.tmx", player, enemy_trainers, bag)
        self.game_manager.player.game_manager = self.game_manager
        # starting money for shop purchases
        self.money = 100
        # If player spawn is already inside a bush, mark _in_bush True
        try:
            if self.game_manager.current_map.check_bush(self.game_manager.player.position):
                self.game_manager.player._in_bush = True
        except Exception:
            pass

        # Create NPCs from JSON data
        from src.entities.entity import Entity
        self.npcs = []
        from src.utils import Direction
        from src.core.services import resource_manager
        from src.sprites import Sprite
        # load full sheet once
        sheet = resource_manager.get_image("character/ow2.png")
        # assumption: rows = ["down","left","right","up"] and 4 columns
        sheet_w, sheet_h = sheet.get_size()
        frame_w = sheet_w // 4
        frame_h = sheet_h // 4
        row_map = {"DOWN": 0, "LEFT": 1, "RIGHT": 2, "UP": 3}
        
        # Helper function to create NPC sprite
        def create_npc_sprite(facing):
            r = row_map.get(facing.upper(), 0)
            try:
                frame = sheet.subsurface(pg.Rect(0, r * frame_h, frame_w, frame_h)).copy()
                frame = pg.transform.scale(frame, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
                s = Sprite("character/ow2.png")
                s.image = frame
                s.rect = frame.get_rect()
                return s
            except Exception:
                return None
        
        # Create NPCs for all maps from JSON
        for map_name in ["map.tmx", "gym.tmx", "ice.tmx"]:
            trainers = trainers_data.get(map_name, [])
            for trainer_data in trainers:
                x = trainer_data.get("x", 0)
                y = trainer_data.get("y", 0)
                facing = trainer_data.get("facing", "DOWN")
                npc = Entity(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE, self.game_manager)
                # create static sprite
                sprite = create_npc_sprite(facing)
                if sprite:
                    sprite.update_pos(npc.position)
                    npc.animation = sprite
                else:
                    npc.animation = npc.animation
                # set logical direction
                try:
                    npc.direction = Direction[facing]
                except Exception:
                    npc.direction = Direction.DOWN
                self.npcs.append(npc)

        # Set the first trainer as main npc (for interaction)
        if self.npcs:
            self.npc = self.npcs[0]
        else:
            self.npc = None
            
        # create a shop NPC at tile (19,32)
        try:
            shop_x, shop_y = 19, 32
            shop_npc = Entity(shop_x * GameSettings.TILE_SIZE, shop_y * GameSettings.TILE_SIZE, self.game_manager)
            # use same sprite sheet logic to create a static sprite
            try:
                # use DOWN facing frame
                r = row_map.get("DOWN", 0)
                frame = sheet.subsurface(pg.Rect(0, r * frame_h, frame_w, frame_h)).copy()
                frame = pg.transform.scale(frame, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
                s = Sprite("character/ow2.png")
                s.image = frame
                s.rect = frame.get_rect()
                s.update_pos(shop_npc.position)
                shop_npc.animation = s
            except Exception:
                shop_npc.animation = shop_npc.animation
            shop_npc.direction = Direction.DOWN
            self.npcs.append(shop_npc)
            self.shop_npc = shop_npc
        except Exception:
            self.shop_npc = None
        # Online Manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
        else:
            self.online_manager = None
        
        # 為在線玩家創建動畫精靈（而不是靜態圖標）
        # 使用字典為每個玩家ID維護單獨的動畫實例
        self.online_player_animations = {}
        self.sprite_online = Sprite("ingame_ui/options1.png", (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
        
        # 初始化聊天系統 - 聊天頻道用於遊戲中玩家間的交流
        # 設定發送聊天訊息和獲取最近訊息的回調函數
        send_callback = None
        get_messages_callback = None
        if self.online_manager:
            send_callback = self.online_manager.send_chat
            get_messages_callback = self.online_manager.get_recent_chat
        self.chat_overlay = ChatOverlay(send_callback=send_callback, get_messages=get_messages_callback)


        from src.interface.components.overlay import Overlay
        from src.interface.components.button import Button
        self.overlay = Overlay(mode="game_setting", game_manager=self.game_manager, save_callback=self.save_game, load_callback=self.load_game)
        self.overlay_button = Button(
            "UI/button_setting.png",
            "UI/button_setting_hover.png",
            GameSettings.SCREEN_WIDTH - 60,
            20,
            40, 40,
            on_click=self.overlay.open
        )
        self.backpack_button = Button(
            "UI/button_backpack.png", "UI/button_backpack_hover.png",
            GameSettings.SCREEN_WIDTH - 120, 20, 40, 40,
            on_click=self.open_backpack
        )
        # 聊天按鈕 - 用於開啟/關閉聊天系統
        self.chat_button = Button(
            "UI/button_setting.png", "UI/button_setting_hover.png",
            GameSettings.SCREEN_WIDTH - 180, 20, 40, 40,
            on_click=self.chat_overlay.toggle
        ) if self.online_manager else None
        # Navigation quick button left of chat button
        try:
            nav_x = GameSettings.SCREEN_WIDTH - 240 if self.chat_button else GameSettings.SCREEN_WIDTH - 180
            self.nav_button = Button(
                "UI/button_setting.png", "UI/button_setting_hover.png",
                nav_x, 20, 40, 40,
                on_click=self._open_navigate
            )
        except Exception:
            self.nav_button = None
        from src.interface.components.backpack_overlay import BackpackOverlay
        # On startup, load initial backpack from `saves/initial.json` if present
        items = None
        monsters = None
        initial_default = None
        try:
            import os, json
            initial_path = os.path.join('saves', 'initial.json')
            if os.path.exists(initial_path):
                with open(initial_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                bag = data.get('bag', {})
                monsters = bag.get('monsters', None)
                items = bag.get('items', None)
                initial_default = bag.get('default_index', None)
        except Exception:
            pass

        self.backpack_overlay = BackpackOverlay(items=items, monsters=monsters)
        # restore default from initial if provided
        try:
            if initial_default is not None:
                self.backpack_overlay.default_index = int(initial_default)
        except Exception:
            pass
        # Sync GameScene.money with backpack Coins if available
        try:
            coins = 0
            bi = self.backpack_overlay.get_items()
            if bi:
                for it in bi:
                    name = (it.get('name') or '').lower()
                    if name in ('coins', 'coin'):
                        coins = int(it.get('count', 0))
                        break
            if coins > 0:
                self.money = coins
        except Exception:
            pass
        # Shop overlay
        try:
            from src.interface.components.shop_overlay import ShopOverlay
            self.shop_overlay = ShopOverlay(game_scene=self)
        except Exception:
            self.shop_overlay = None

        # Navigate overlay
        try:
            from src.interface.components.navigate_overlay import NavigateOverlay
            self.navigate_overlay = NavigateOverlay(self)
        except Exception:
            self.navigate_overlay = None

        # Minimap (top-left)
        try:
            from src.interface.components.minimap import Minimap
            self.minimap = Minimap(self)
            # ensure current_map reference used by minimap
            self.current_map = self.game_manager.current_map
            # initial player tile pos
            ppos = self.game_manager.player.position if self.game_manager.player else None
            if ppos:
                self.player_tile_pos = (int(ppos.x) // GameSettings.TILE_SIZE, int(ppos.y) // GameSettings.TILE_SIZE)
            else:
                self.player_tile_pos = (0, 0)
        except Exception:
            self.minimap = None
            self.current_map = None
            self.player_tile_pos = (0, 0)
        
        # Ice map special locations
        self.heal_trigger_pos = (5, 24)  # ice.tmx heal location
        self.ice_shop_trigger_pos = (4, 36)  # ice.tmx shop location
        self.show_heal_hint = False
        self.show_ice_shop_hint = False
        self.heal_timer = 0.0
        self.healing_in_progress = False
        
        # Exp potion pickup locations
        self.exp_potion_locations = [(19, 16), (20, 7), (28, 5), (29, 18)]
        self.collected_exp_potions = set()  # Track collected positions
        self.show_pickup_message = False
        self.pickup_message_timer = 0.0
        self.pickup_message = ""

    def save_game(self):
        # Save current game state to save_temp.json (includes bag/monsters/items)
        self.game_manager.save("saves/save_temp.json")
        try:
            from src.core.services import input_manager
            input_manager.reset()
        except Exception:
            pass

    def load_game(self):
        import os
        # Load from save_temp.json if present
        if os.path.exists("saves/save_temp.json"):
            from src.core.managers.game_manager import GameManager
            from src.maps.map import Map
            # 重新載入地圖與遊戲狀態
            maps = self.game_manager.maps
            enemy_trainers = self.game_manager.enemy_trainers
            gm = GameManager.load("saves/save_temp.json", maps, enemy_trainers)
            if gm:
                self.game_manager = gm
                self.game_manager.player.game_manager = self.game_manager
                # 讀取 save_temp.json 的怪物和物品，載到 backpack_overlay
                import json
                try:
                    with open("saves/save_temp.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    bag = data.get("bag", {})
                    monsters = bag.get("monsters", None)
                    items = bag.get("items", None)
                    if monsters is not None:
                        self.backpack_overlay.monsters = list(monsters)
                    # restore default selected monster index if present
                    try:
                        default_idx = bag.get("default_index", None)
                        if default_idx is not None:
                            self.backpack_overlay.default_index = int(default_idx)
                    except Exception:
                        pass
                    if items is not None:
                        self.backpack_overlay.items = list(items)
                    # sync money from loaded backpack
                    try:
                        coins = 0
                        for it in (self.backpack_overlay.get_items() or []):
                            if (it.get('name') or '').lower() in ('coins', 'coin'):
                                coins = int(it.get('count', 0))
                                break
                        if coins > 0:
                            self.money = coins
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    from src.core.services import input_manager
                    input_manager.reset()
                except Exception:
                    pass

    def _player_near_npc(self):        # 判斷玩家是否靠近NPC
        # Only show exclamation when player is within 3 tiles in the NPC's facing direction
        player_pos = self.game_manager.player.position
        npc_pos = self.npc.position
        px = int(player_pos.x) // GameSettings.TILE_SIZE
        py = int(player_pos.y) // GameSettings.TILE_SIZE
        nx = int(npc_pos.x) // GameSettings.TILE_SIZE
        ny = int(npc_pos.y) // GameSettings.TILE_SIZE

        dir = getattr(self.npc, 'direction', Direction.DOWN)
        name = dir.name if hasattr(dir, 'name') else str(dir).upper()

        max_dist = 3
        if name == 'DOWN':
            return (px == nx) and (py > ny) and (py - ny <= max_dist)
        if name == 'UP':
            return (px == nx) and (py < ny) and (ny - py <= max_dist)
        if name == 'LEFT':
            return (py == ny) and (px < nx) and (nx - px <= max_dist)
        if name == 'RIGHT':
            return (py == ny) and (px > nx) and (px - nx <= max_dist)
        return False

    def _npc_in_facing_range(self, npc) -> bool:
        """Return True if player is within 3 tiles in the npc's facing direction."""
        player_pos = self.game_manager.player.position
        npc_pos = npc.position
        px = int(player_pos.x) // GameSettings.TILE_SIZE
        py = int(player_pos.y) // GameSettings.TILE_SIZE
        nx = int(npc_pos.x) // GameSettings.TILE_SIZE
        ny = int(npc_pos.y) // GameSettings.TILE_SIZE

        dir = getattr(npc, 'direction', Direction.DOWN)
        name = dir.name if hasattr(dir, 'name') else str(dir).upper()

        max_dist = 3
        if name == 'DOWN':
            return (px == nx) and (py > ny) and (py - ny <= max_dist)
        if name == 'UP':
            return (px == nx) and (py < ny) and (ny - py <= max_dist)
        if name == 'LEFT':
            return (py == ny) and (px < nx) and (nx - px <= max_dist)
        if name == 'RIGHT':
            return (py == ny) and (px > nx) and (px - nx <= max_dist)
        return False

    def _get_teleport_npc_pos(self):
        #npc設定在下方三格再往右一格
        teleporters = self.game_manager.current_map.teleporters
        if not teleporters:
            # 若地圖沒有teleporters，預設 (0,0)
            return 0, 0
        tp = teleporters[0]
        tile_x = int(tp.pos.x // GameSettings.TILE_SIZE)
        tile_y = int(tp.pos.y // GameSettings.TILE_SIZE)
        return tile_x + 1, tile_y + 3

    def open_backpack(self):
        self.backpack_overlay.open()

    def _open_navigate(self):
        try:
            if hasattr(self, 'navigate_overlay') and self.navigate_overlay:
                self.navigate_overlay.open()
                try:
                    from src.core.services import input_manager
                    input_manager.reset()
                except Exception:
                    pass
        except Exception:
            pass

    @override
    def enter(self):
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        if self.online_manager:
            self.online_manager.enter()
        
    @override
    def exit(self):
        if self.online_manager:
            self.online_manager.exit()
        
    @override
    def update(self, dt: float):
        # 玩家靠近NPC且按下E或SPACE時切換到戰鬥場景或商店（若靠近 shop_npc）
        from src.core.services import input_manager, scene_manager
        
        # check shop npc first
        try:
            shop_exists = hasattr(self, 'shop_npc') and self.shop_npc is not None
            in_range = False
            if shop_exists:
                # consider player near if within 1 tile (Manhattan distance) of the shop NPC
                player_pos = self.game_manager.player.position if self.game_manager.player else None
                if player_pos:
                    px_tile = int(player_pos.x) // GameSettings.TILE_SIZE
                    py_tile = int(player_pos.y) // GameSettings.TILE_SIZE
                    sx_tile = int(self.shop_npc.position.x) // GameSettings.TILE_SIZE
                    sy_tile = int(self.shop_npc.position.y) // GameSettings.TILE_SIZE
                    manhattan = abs(px_tile - sx_tile) + abs(py_tile - sy_tile)
                    in_range = manhattan <= 1
                # proximity check result available in 'in_range'
            if (input_manager.key_pressed(pg.K_e) or input_manager.key_pressed(pg.K_SPACE)):
                Logger.info("Detected E/SPACE key press in GameScene.update")
            if shop_exists and in_range and (input_manager.key_pressed(pg.K_e) or input_manager.key_pressed(pg.K_SPACE)):
                if hasattr(self, 'shop_overlay') and self.shop_overlay:
                    Logger.info("Opening shop overlay")
                    self.shop_overlay.open()
                    # short-circuit to avoid triggering battle
        except Exception:
            Logger.info("Exception while checking shop npc interaction")
            pass

        # Re-enable battle trigger when player is in NPC's facing range and presses E/SPACE.
        # This corresponds to the exclamation state shown by NPC.
        try:
            player_pos = self.game_manager.player.position if self.game_manager.player else None
            if player_pos:
                from src.core.services import input_manager, scene_manager
                for npc in self.npcs:
                    if hasattr(self, 'shop_npc') and npc == self.shop_npc:
                        continue
                    if self._npc_in_facing_range(npc):
                        if input_manager.key_pressed(pg.K_e) or input_manager.key_pressed(pg.K_SPACE):
                            # pick a reasonable enemy monster
                            enemy_data = None
                            monsters = getattr(self.game_manager.bag, "_monsters_data", [])
                            for m in monsters:
                                if m.get("name") == "Blastoise":
                                    enemy_data = m
                                    break
                            if enemy_data is None and monsters:
                                enemy_data = monsters[0]
                            Logger.info("GameScene: NPC facing-range + input, switching to battle")
                            scene_manager.change_scene("battle", is_npc_battle=True, enemy=enemy_data)
                            break
        except Exception:
            pass

        if self.overlay.is_active:
            self.overlay.update(dt)
            return

        # If shop overlay active, update and block other interactions
        if hasattr(self, 'shop_overlay') and self.shop_overlay and self.shop_overlay.is_active:
            self.shop_overlay.update(dt)
            return

        # Check ice map special triggers
        self._check_ice_triggers(dt)
        
        # update minimap state: current_map and player tile pos
        try:
            self.current_map = self.game_manager.current_map
            if self.game_manager.player:
                ppos = self.game_manager.player.position
                self.player_tile_pos = (int(ppos.x) // GameSettings.TILE_SIZE, int(ppos.y) // GameSettings.TILE_SIZE)
            # forward update to minimap
            if hasattr(self, 'minimap') and self.minimap:
                self.minimap.update(dt)
        except Exception:
            pass

        self.game_manager.try_switch_map()

        # Update player and other data
        if self.game_manager.player:
            self.game_manager.player.update(dt)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.update(dt)

        # 更新所有 NPC
        if hasattr(self, "npcs"):
            for npc in self.npcs:
                npc.update(dt)

        # Update others
        self.game_manager.bag.update(dt)

        if self.game_manager.player is not None and self.online_manager is not None:
            # 取得玩家目前的方向（從動畫系統）
            player_direction = self.game_manager.player.animation.cur_row
            # 判斷玩家是否在移動（檢查player.is_moving標記）
            is_moving = self.game_manager.player.is_moving
            
            _ = self.online_manager.update(
                self.game_manager.player.position.x, 
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name,
                direction=player_direction,
                is_moving=is_moving
            )

        
        self.overlay_button.update(dt) 
        self.backpack_button.update(dt)
        # 更新聊天系統
        if self.chat_overlay:
            self.chat_overlay.update(dt)
        if hasattr(self, 'chat_button') and self.chat_button:
            self.chat_button.update(dt)
        if hasattr(self, 'nav_button') and self.nav_button:
            self.nav_button.update(dt)
        self.backpack_overlay.update(dt)
        if hasattr(self, 'shop_overlay') and self.shop_overlay:
            self.shop_overlay.update(dt)
        if hasattr(self, 'navigate_overlay') and self.navigate_overlay:
            self.navigate_overlay.update(dt)
        
    @override
    def draw(self, screen: pg.Surface):
        overlay_active = hasattr(self, "overlay") and self.overlay.is_active

        if self.game_manager.player:
            camera = self.game_manager.player.camera
            self.game_manager.current_map.draw(screen, camera)
            
            # Draw exp_potion pickups on ice map
            self._draw_exp_potions(screen, camera)
            
            self.game_manager.player.draw(screen, camera)
            # 畫所有 NPC，並在符合朝向範圍時顯示驚嘆號
            if hasattr(self, "npcs"):
                for npc in self.npcs:
                    npc.draw(screen, camera)
            for enemy in self.game_manager.current_enemy_trainers:
                enemy.draw(screen, camera)
        else:
            camera = PositionCamera(0, 0)
            self.game_manager.current_map.draw(screen, camera)
            for enemy in self.game_manager.current_enemy_trainers:
                enemy.draw(screen, camera)

        self.game_manager.bag.draw(screen)

        if self.online_manager and self.game_manager.player:
            # 渲染其他玩家
            # 從線上管理器獲取其他玩家的位置、方向、移動狀態資訊
            try:
                list_online = self.online_manager.get_list_players()
                # 調試：打印在線玩家列表
                current_map_name = self.game_manager.current_map.path_name
                # Logger.info(f"[Draw] Online players count: {len(list_online)}, Current map: '{current_map_name}'")
                for p in list_online:
                    same_map = "✓" if p['map'] == current_map_name else "✗"
                    Logger.info(f"  {same_map} Player {p['id']}: pos=({p['x']}, {p['y']}), map='{p['map']}', dir={p['direction']}, moving={p['is_moving']}")
                
                for player in list_online:
                    if player["map"] == self.game_manager.current_map.path_name:
                        player_id = player["id"]
                        cam = self.game_manager.player.camera
                        pos = cam.transform_position_as_position(Position(player["x"], player["y"]))
                        
                        # 為此玩家ID創建或獲取動畫實例
                        if player_id not in self.online_player_animations:
                            self.online_player_animations[player_id] = Animation(
                                "character/ow1.png", ["down", "left", "right", "up"], 4,
                                (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
                            )
                        
                        anim = self.online_player_animations[player_id]
                        
                        # 取得玩家的方向和移動狀態
                        # 方向決定動畫的朝向，移動狀態決定是否顯示移動動畫
                        player_direction = player.get("direction", "down")
                        is_moving = player.get("is_moving", False)
                        
                        # 根據方向改變動畫朝向
                        anim.switch(player_direction)
                        # 更新動畫位置
                        anim.update_pos(pos)
                        # 根據移動狀態更新動畫播放（移動中播放動畫，靜止時停留在第一幀）
                        if is_moving:
                            # 移動中的玩家：播放動畫
                            anim.update(0.016)  # 60fps約16.6ms
                        # 位置已經通過相機轉換，直接繪製（不再傳遞相機）
                        anim.draw(screen)
            except Exception as e:
                Logger.error(f"Error rendering online players: {e}")


        self.overlay_button.draw(screen)

        # draw nav button (with label 'N' above)
        try:
            if hasattr(self, 'nav_button') and self.nav_button:
                # label above
                try:
                    font = pg.font.SysFont(None, 20)
                    lbl = font.render('N', True, (255,255,255))
                    lx = self.nav_button.hitbox.x + (self.nav_button.hitbox.w - lbl.get_width()) // 2
                    ly = self.nav_button.hitbox.y - lbl.get_height() - 4
                    screen.blit(lbl, (lx, ly))
                except Exception:
                    pass
                self.nav_button.draw(screen)
        except Exception:
            pass

        self.backpack_button.draw(screen)
        
        # 繪製聊天按鈕（用於開啟/關閉聊天系統）
        if hasattr(self, 'chat_button') and self.chat_button:
            self.chat_button.draw(screen)

        if overlay_active:
            self.overlay.draw(screen)

        self.backpack_overlay.draw(screen)
        if hasattr(self, 'shop_overlay') and self.shop_overlay:
            self.shop_overlay.draw(screen)
        if hasattr(self, 'navigate_overlay') and self.navigate_overlay:
            self.navigate_overlay.draw(screen)
        # 繪製聊天系統 UI（顯示聊天窗口和訊息）
        if hasattr(self, 'chat_overlay') and self.chat_overlay:
            self.chat_overlay.draw(screen)
        
        # Draw ice map hints
        self._draw_ice_hints(screen)
        
        # draw minimap above overlays (top-left) unless backpack or shop overlays are open
        try:
            backpack_open = hasattr(self, 'backpack_overlay') and self.backpack_overlay and self.backpack_overlay.is_active
            shop_open = hasattr(self, 'shop_overlay') and self.shop_overlay and self.shop_overlay.is_active
            if hasattr(self, 'minimap') and self.minimap and not (backpack_open or shop_open):
                self.minimap.draw(screen)
        except Exception:
            pass

    def _check_ice_triggers(self, dt: float):
        """Check if player is at ice map special locations and handle SPACE key"""
        try:
            if not self.game_manager or not self.game_manager.player:
                return
            
            current_map_name = self.game_manager.current_map.path_name if self.game_manager.current_map else ""
            if current_map_name != "ice.tmx":
                self.show_heal_hint = False
                self.show_ice_shop_hint = False
                return
            
            player_pos = self.game_manager.player.position
            px_tile = int(player_pos.x) // GameSettings.TILE_SIZE
            py_tile = int(player_pos.y) // GameSettings.TILE_SIZE
            
            from src.core.services import input_manager
            
            # Check heal trigger
            if (px_tile, py_tile) == self.heal_trigger_pos:
                self.show_heal_hint = True
                if input_manager.key_pressed(pg.K_SPACE) and not self.healing_in_progress:
                    self._trigger_heal()
            else:
                self.show_heal_hint = False
            
            # Check shop trigger
            if (px_tile, py_tile) == self.ice_shop_trigger_pos:
                self.show_ice_shop_hint = True
                if input_manager.key_pressed(pg.K_SPACE):
                    if hasattr(self, 'shop_overlay') and self.shop_overlay:
                        self.shop_overlay.open()
            else:
                self.show_ice_shop_hint = False
            
            # Check exp_potion pickups
            player_tile = (px_tile, py_tile)
            if player_tile in self.exp_potion_locations and player_tile not in self.collected_exp_potions:
                self._collect_exp_potion(player_tile)
            
            # Update heal timer
            if self.healing_in_progress:
                self.heal_timer += dt
                if self.heal_timer >= 0.5:
                    self._complete_heal()
                    self.healing_in_progress = False
                    self.heal_timer = 0.0
            
            # Update pickup message timer
            if self.show_pickup_message:
                self.pickup_message_timer += dt
                if self.pickup_message_timer >= 2.0:  # Show for 2 seconds
                    self.show_pickup_message = False
                    self.pickup_message_timer = 0.0
        except Exception as e:
            Logger.error(f"Error in _check_ice_triggers: {e}")
    
    def _trigger_heal(self):
        """Open backpack and start heal timer"""
        try:
            self.open_backpack()
            self.healing_in_progress = True
            self.heal_timer = 0.0
        except Exception as e:
            Logger.error(f"Error in _trigger_heal: {e}")
    
    def _complete_heal(self):
        """Heal all monsters to max HP"""
        try:
            # Update both bag and backpack_overlay monsters
            if hasattr(self.game_manager, 'bag') and self.game_manager.bag:
                monsters = self.game_manager.bag._monsters_data
                for monster in monsters:
                    max_hp = monster.get('max_hp', 100)
                    monster['hp'] = max_hp
            
            # Also update backpack_overlay's monsters list
            if hasattr(self, 'backpack_overlay') and self.backpack_overlay:
                for monster in self.backpack_overlay.monsters:
                    max_hp = monster.get('max_hp', 100)
                    monster['hp'] = max_hp
            
            Logger.info("All monsters healed to max HP")
        except Exception as e:
            Logger.error(f"Error in _complete_heal: {e}")
    
    def _collect_exp_potion(self, position: tuple):
        """Collect exp_potion at given position"""
        try:
            # Mark as collected
            self.collected_exp_potions.add(position)
            
            # Add to backpack_overlay items
            if hasattr(self, 'backpack_overlay') and self.backpack_overlay:
                # Find exp_potion in items and increase count
                found = False
                for item in self.backpack_overlay.items:
                    if item.get('name') == 'exp potion':
                        item['count'] = item.get('count', 0) + 1
                        found = True
                        break
                
                # If not found, add new item
                if not found:
                    self.backpack_overlay.items.append({
                        'name': 'exp potion',
                        'img': 'ingame_ui/exp_potion.png',
                        'count': 1
                    })
            
            # Show pickup message
            self.show_pickup_message = True
            self.pickup_message = "get one exp_potion!"
            self.pickup_message_timer = 0.0
            
            Logger.info(f"Collected exp_potion at {position}")
        except Exception as e:
            Logger.error(f"Error in _collect_exp_potion: {e}")
    
    def _draw_ice_hints(self, screen: pg.Surface):
        """Draw hint text at bottom right corner"""
        try:
            font = pg.font.SysFont(None, 28)
            hint_text = None
            
            # Pickup message has priority
            if self.show_pickup_message:
                hint_text = self.pickup_message
            elif self.show_heal_hint:
                hint_text = "Press SPACE to heal"
            elif self.show_ice_shop_hint:
                hint_text = "Press SPACE to shop"
            
            if hint_text:
                text_surface = font.render(hint_text, True, (200, 200, 200))
                # Dark gray background
                padding = 10
                bg_rect = pg.Rect(0, 0, text_surface.get_width() + padding * 2, text_surface.get_height() + padding * 2)
                bg_rect.bottomright = (GameSettings.SCREEN_WIDTH - 20, GameSettings.SCREEN_HEIGHT - 20)
                
                # Draw semi-transparent dark background
                bg_surface = pg.Surface((bg_rect.width, bg_rect.height))
                bg_surface.fill((40, 40, 40))
                bg_surface.set_alpha(200)
                screen.blit(bg_surface, bg_rect.topleft)
                
                # Draw text
                text_rect = text_surface.get_rect(center=bg_rect.center)
                screen.blit(text_surface, text_rect)
        except Exception as e:
            Logger.error(f"Error in _draw_ice_hints: {e}")
    
    def _draw_exp_potions(self, screen: pg.Surface, camera: PositionCamera):
        """Draw exp_potion sprites at uncollected locations on ice map"""
        try:
            # Only draw on ice map
            current_map_name = self.game_manager.current_map.path_name if self.game_manager.current_map else ""
            if current_map_name != "ice.tmx":
                return
            
            from src.core.services import resource_manager
            # Load exp_potion image
            potion_img = resource_manager.get_image("ingame_ui/exp_potion.png")
            potion_img = pg.transform.scale(potion_img, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
            
            # Draw each uncollected potion
            for pos in self.exp_potion_locations:
                if pos not in self.collected_exp_potions:
                    # Convert tile position to pixel position
                    pixel_x = pos[0] * GameSettings.TILE_SIZE
                    pixel_y = pos[1] * GameSettings.TILE_SIZE
                    
                    # Apply camera transform
                    screen_pos = camera.transform_position(Position(pixel_x, pixel_y))
                    screen.blit(potion_img, screen_pos)
        except Exception as e:
            Logger.error(f"Error in _draw_exp_potions: {e}")
            backpack_open = hasattr(self, 'backpack_overlay') and self.backpack_overlay and self.backpack_overlay.is_active
            shop_open = hasattr(self, 'shop_overlay') and self.shop_overlay and self.shop_overlay.is_active
            if not backpack_open and not shop_open:
                    if hasattr(self, 'minimap') and self.minimap:
                        try:
                            # hide minimap if backpack, shop, or navigate overlays are open
                            backpack_open = hasattr(self, 'backpack_overlay') and self.backpack_overlay and self.backpack_overlay.is_active
                            shop_open = hasattr(self, 'shop_overlay') and self.shop_overlay and self.shop_overlay.is_active
                            nav_open = hasattr(self, 'navigate_overlay') and self.navigate_overlay and self.navigate_overlay.is_active
                            if not (backpack_open or shop_open or nav_open):
                                self.minimap.draw(screen)
                        except Exception:
                            pass
        except Exception:
            pass
