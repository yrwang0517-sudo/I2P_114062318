from __future__ import annotations
from src.utils import Logger, GameSettings, Position, Teleport
import json, os
import pygame as pg
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.maps.map import Map
    from src.entities.player import Player
    from src.entities.enemy_trainer import EnemyTrainer
    from src.data.bag import Bag

class GameManager:
    # Entities
    player: Player | None
    enemy_trainers: dict[str, list[EnemyTrainer]]
    bag: "Bag"
    
    # Map properties
    current_map_key: str
    maps: dict[str, Map]
    
    # Changing Scene properties
    should_change_scene: bool
    next_map: str
    
    def __init__(self, maps: dict[str, Map], start_map: str, 
                 player: Player | None,
                 enemy_trainers: dict[str, list[EnemyTrainer]], 
                 bag: Bag | None = None):
                     
        from src.data.bag import Bag
        # Game Properties
        self.maps = maps
        self.current_map_key = start_map
        self.player = player
        self.enemy_trainers = enemy_trainers
        self.bag = bag if bag is not None else Bag([], [])
        
        # Check If you should change scene
        self.should_change_scene = False
        self.next_map = ""
        
    @property
    def current_map(self) -> Map:
        return self.maps[self.current_map_key]
        
    @property
    def current_enemy_trainers(self) -> list[EnemyTrainer]:
        return self.enemy_trainers[self.current_map_key]
        
    @property
    def current_teleporter(self) -> list[Teleport]:
        return self.maps[self.current_map_key].teleporters
    
    def switch_map(self, target: str, origin_tile: tuple[int,int] | None = None, origin_pair: str | None = None) -> None:
        if target not in self.maps:
            Logger.warning(f"Map '{target}' not loaded; cannot switch.")
            return

        # remember origin so we can find a matching teleporter in the destination map
        try:
            self._switch_origin = self.current_map_key
            # record triggering teleporter info if provided
            self._switch_origin_tile = origin_tile if origin_tile is not None else None
            self._switch_origin_pair = origin_pair if origin_pair is not None else None
        except Exception:
            self._switch_origin = None

        self.next_map = target
        self.should_change_scene = True
            
    

    def try_switch_map(self) -> None:
        if self.should_change_scene:
            self.current_map_key = self.next_map
            self.next_map = ""
            self.should_change_scene = False
            if self.player:
                # Check if there's a navigation target position
                nav_target = getattr(self, '_nav_target_pos', None)
                if nav_target:
                    # Use navigation target position
                    self.player.position = nav_target
                    delattr(self, '_nav_target_pos')
                else:
                    # Preserve player's position when switching maps
                    matching_teleporter = next((tp for tp in self.maps[self.current_map_key].teleporters 
                                                if tp.pair_id == self._switch_origin_pair), None)
                    if matching_teleporter:
                        self.player.position = Position(matching_teleporter.pos.x, matching_teleporter.pos.y)
                    else:
                        self.player.position = self.maps[self.current_map_key].spawn.copy()

                # Set a cooldown timer to avoid immediate bush interaction
                self.player._teleport_cooldown_timer = 1.0

    def check_collision(self, rect: pg.Rect) -> bool:
        if self.maps[self.current_map_key].check_collision(rect):
            return True
        for entity in self.enemy_trainers[self.current_map_key]:
            if rect.colliderect(entity.animation.rect):
                return True
        
        return False
        
    def save(self, path: str) -> None:
        """只覆蓋玩家位置和背包，不動地圖等初始資料，背包內容來自 backpack_overlay"""
        import json
        try:
            # 讀取原始存檔
            with open(path, "r", encoding="utf-8") as f:
                original = json.load(f)
            # 更新玩家位置
            original["player"] = {
                "x": self.player.position.x if self.player else 0,
                "y": self.player.position.y if self.player else 0
            }
            # 背包內容來自 backpack_overlay
            backpack = None
            try:
                from src.core.services import scene_manager
                game_scene = scene_manager._scenes.get("game")
                if hasattr(game_scene, "backpack_overlay"):
                    backpack = game_scene.backpack_overlay
            except Exception:
                backpack = None
            if backpack:
                original["bag"]["monsters"] = list(backpack.get_monsters())
                original["bag"]["items"] = list(getattr(backpack, "items", []))
                # save selected default monster index if available
                try:
                    di = getattr(backpack, 'default_index', None)
                    # only include if not None
                    if di is not None:
                        original["bag"]["default_index"] = di
                except Exception:
                    pass
            else:
                original["bag"] = self.bag.to_dict()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(original, f, indent=2, ensure_ascii=False)
            Logger.info(f"Game saved to {path}")
        except Exception as e:
            Logger.warning(f"Failed to save game: {e}")
             
    @classmethod
    def load(cls, path: str, maps=None, enemy_trainers=None) -> "GameManager | None":
        """Load monsters, items, and player position from save file"""
        if not os.path.exists(path):
            Logger.error(f"No file found: {path}, ignoring load function")
            return None
        with open(path, "r") as f:
            data = json.load(f)
        # If minimal save, need maps/enemy_trainers from outside
        if maps is None or enemy_trainers is None:
            Logger.error("Maps and enemy_trainers required for load")
            return None
        from src.data.bag import Bag
        bag = Bag.from_dict(data.get("bag", {}))
        px = data.get("player", {}).get("x", 0)
        py = data.get("player", {}).get("y", 0)
        from src.entities.player import Player
        player = Player(px, py, None)  # game_manager will be set after
        gm = cls(maps, list(maps.keys())[0], player, enemy_trainers, bag)
        gm.player.game_manager = gm
        return gm

    def to_dict(self) -> dict[str, object]:
        map_blocks: list[dict[str, object]] = []
        for key, m in self.maps.items():
            block = m.to_dict()
            block["enemy_trainers"] = [t.to_dict() for t in self.enemy_trainers.get(key, [])]
            spawn = self.player_spawns.get(key)
            block["player"] = {
                "x": spawn["x"] / GameSettings.TILE_SIZE,
                "y": spawn["y"] / GameSettings.TILE_SIZE
            }
            map_blocks.append(block)
        return {
            "map": map_blocks,
            "current_map": self.current_map_key,
            "player": self.player.to_dict() if self.player is not None else None,
            "bag": self.bag.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "GameManager":
        from src.maps.map import Map
        from src.entities.player import Player
        from src.entities.enemy_trainer import EnemyTrainer
        from src.data.bag import Bag
        
        Logger.info("Loading maps")
        maps_data = data["map"]
        maps: dict[str, Map] = {}
        player_spawns: dict[str, Position] = {}
        trainers: dict[str, list[EnemyTrainer]] = {}

        for entry in maps_data:
            path = entry["path"]
            maps[path] = Map.from_dict(entry)
            sp = entry.get("player")
            if sp:
                player_spawns[path] = Position(
                    sp["x"] * GameSettings.TILE_SIZE,
                    sp["y"] * GameSettings.TILE_SIZE
                )
        current_map = data["current_map"]
        gm = cls(
            maps, current_map,
            None, # Player
            trainers,
            bag=None
        )
        gm.current_map_key = current_map
        
        Logger.info("Loading enemy trainers")
        for m in data["map"]:
            raw_data = m["enemy_trainers"]
            gm.enemy_trainers[m["path"]] = [EnemyTrainer.from_dict(t, gm) for t in raw_data]
        
        Logger.info("Loading Player")
        if data.get("player"):
            gm.player = Player.from_dict(data["player"], gm)
        
        Logger.info("Loading bag")
        from src.data.bag import Bag as _Bag
        gm.bag = Bag.from_dict(data.get("bag", {})) if data.get("bag") else _Bag([], [])

        return gm