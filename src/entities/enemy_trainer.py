from __future__ import annotations
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import override

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera


class EnemyTrainerClassification(Enum):
    STATIONARY = "stationary"

@dataclass
class IdleMovement:
    def update(self, enemy: "EnemyTrainer", dt: float) -> None:
        return

class EnemyTrainer(Entity):
    classification: EnemyTrainerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
    ) -> None:
        super().__init__(x, y, game_manager)
        self.classification = classification
        self.max_tiles = max_tiles
        if classification == EnemyTrainerClassification.STATIONARY:
            self._movement = IdleMovement()
            if facing is None:
                raise ValueError("Idle EnemyTrainer requires a 'facing' Direction at instantiation")
            self._set_direction(facing)
        else:
            raise ValueError("Invalid classification")
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False

    @override
    def update(self, dt: float) -> None:
        self._movement.update(self, dt)
        self._has_los_to_player()
        from src.utils import Logger
        if self.detected:
            Logger.info("EnemyTrainer: player detected (exclamation shown)")
            # When detected (exclamation shown), pressing SPACE/E should enter battle
            if (
                input_manager.key_pressed(pygame.K_SPACE)
                or input_manager.key_pressed(pygame.K_e)
                or input_manager.key_down(pygame.K_SPACE)
                or input_manager.key_down(pygame.K_e)
            ):
                Logger.info("EnemyTrainer: detected player and input pressed, switching to battle")
                # Try to pass a reasonable enemy monster from bag, else let BattleScene default
                enemy_data = None
                try:
                    bag = getattr(self.game_manager, 'bag', None)
                    monsters = getattr(bag, '_monsters_data', []) if bag else []
                    # prefer Blastoise if present, else first monster
                    for m in monsters:
                        if m.get("name") == "Blastoise":
                            enemy_data = m
                            break
                    if enemy_data is None and monsters:
                        enemy_data = monsters[0]
                except Exception:
                    enemy_data = None
                scene_manager.change_scene("battle", is_npc_battle=True, enemy=enemy_data)
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera):
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)

    def _set_direction(self, direction: Direction):
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
        self.los_direction = self.direction

    def _get_los_rect(self) -> pygame.Rect | None:
        '''
        TODO: Create hitbox to detect line of sight of the enemies towards the player
        '''
        return None

    def _has_los_to_player(self) -> None:
        # Simple LOS: player within 3 tiles in the facing direction
        player = self.game_manager.player
        if player is None:
            self.detected = False
            return

        px = int(player.position.x) // GameSettings.TILE_SIZE
        py = int(player.position.y) // GameSettings.TILE_SIZE
        nx = int(self.position.x) // GameSettings.TILE_SIZE
        ny = int(self.position.y) // GameSettings.TILE_SIZE

        dir = getattr(self, 'direction', Direction.DOWN)
        name = dir.name if hasattr(dir, 'name') else str(dir).upper()
        max_dist = 3

        detected = False
        if name == 'DOWN':
            detected = (px == nx) and (py > ny) and (py - ny <= max_dist)
        elif name == 'UP':
            detected = (px == nx) and (py < ny) and (ny - py <= max_dist)
        elif name == 'LEFT':
            detected = (py == ny) and (px < nx) and (nx - px <= max_dist)
        elif name == 'RIGHT':
            detected = (py == ny) and (px > nx) and (px - nx <= max_dist)

        self.detected = detected

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "EnemyTrainer":
        classification = EnemyTrainerClassification(data.get("classification", "stationary"))
        max_tiles = data.get("max_tiles")
        facing_val = data.get("facing")
        facing: Direction | None = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                facing = Direction[facing_val]
            elif isinstance(facing_val, Direction):
                facing = facing_val
        if facing is None and classification == EnemyTrainerClassification.STATIONARY:
            facing = Direction.DOWN
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            classification,
            max_tiles,
            facing,
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = super().to_dict()
        base["classification"] = self.classification.value
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        return base