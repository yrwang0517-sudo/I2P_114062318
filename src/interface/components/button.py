#ok沒問題
from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent

class Button(UIComponent):
    img_button: Sprite
    img_button_default: Sprite
    img_button_hover: Sprite
    hitbox: pg.Rect
    on_click: Callable[[], None] | None

    def __init__(
        self,
        img_path: str, img_hovered_path:str,
        x: int, y: int, width: int, height: int,
        on_click: Callable[[], None] | None = None
    ):
        self.img_button_default = Sprite(img_path, (width, height))
        self.hitbox = pg.Rect(x, y, width, height)

        self.img_button_hover = Sprite(img_hovered_path, (width, height))
        self.img_button = self.img_button_default
        self.on_click = on_click

    @override
    def update(self, dt: float) -> None:
            
        if self.hitbox.collidepoint(input_manager.mouse_pos):
            self.img_button = self.img_button_hover
            if input_manager.mouse_pressed(1) and self.on_click is not None:
                self.on_click()
        else:
            self.img_button = self.img_button_default
    
    @override
    def draw(self, screen: pg.Surface) -> None:        
        screen.blit(self.img_button.image, self.hitbox)
