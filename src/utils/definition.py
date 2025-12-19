from pygame import Rect
from .settings import GameSettings
from dataclasses import dataclass
from enum import Enum
from typing import overload, TypedDict, Protocol

MouseBtn = int
Key = int

Direction = Enum('Direction', ['UP', 'DOWN', 'LEFT', 'RIGHT', 'NONE'])

@dataclass
class Position:
    x: float
    y: float
    
    def copy(self):
        return Position(self.x, self.y)
        
    def distance_to(self, other: "Position") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
        
@dataclass
class PositionCamera:
    x: int
    y: int
    
    def copy(self):
        return PositionCamera(self.x, self.y)
        
    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)
        
    def transform_position(self, position: Position) -> tuple[int, int]:
        return (int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_position_as_position(self, position: Position) -> Position:
        return Position(int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_rect(self, rect: Rect) -> Rect:
        return Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)

@dataclass
class Teleport:
    pos: Position
    destination: str
    pair_id: str | None = None
    
    @overload
    def __init__(self, x: int, y: int, destination: str) -> None: ...
    @overload
    def __init__(self, pos: Position, destination: str) -> None: ...

    def __init__(self, *args, **kwargs):
        # signature: (x:int, y:int, destination:str, pair_id:Optional[str]=None)
        if isinstance(args[0], Position):
            self.pos = args[0]
            self.destination = args[1]
            self.pair_id = args[2] if len(args) > 2 else kwargs.get('pair_id')
        else:
            # allow (x,y,dest) or (x,y,dest,pair_id)
            x = args[0]
            y = args[1]
            dest = args[2]
            pid = args[3] if len(args) > 3 else kwargs.get('pair_id')
            self.pos = Position(x, y)
            self.destination = dest
            self.pair_id = pid
    
    def to_dict(self):
        return {
            "x": self.pos.x // GameSettings.TILE_SIZE,
            "y": self.pos.y // GameSettings.TILE_SIZE,
            "destination": self.destination,
            "pair_id": self.pair_id
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        pid = data.get("pair_id")
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, data["destination"], pid)
    
class Monster(TypedDict):
    name: str
    hp: int
    max_hp: int
    level: int
    sprite_path: str

class Item(TypedDict):
    name: str
    count: int
    sprite_path: str