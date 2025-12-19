#ok沒問題
import pygame as pg
from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.interface.components.overlay import Overlay
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override

class SettingScene(Scene):
	background: BackgroundSprite
	overlay: Overlay

	def __init__(self):
		super().__init__()
		self.background = BackgroundSprite("backgrounds/background1.png")
		self.overlay = Overlay(mode="menu")
		self.overlay.open()  

	@override
	def enter(self) -> None:
		sound_manager.play_bgm("RBY 101 Opening (Part 1).ogg")
		self.overlay.open()

	@override
	def exit(self) -> None:
		self.overlay.close()

	@override
	def update(self, dt: float) -> None:
		self.overlay.update(dt)

	@override
	def draw(self, screen: pg.Surface) -> None:
		self.background.draw(screen)
		self.overlay.draw(screen)