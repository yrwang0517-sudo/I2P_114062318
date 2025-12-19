import pygame as pg
from pytmx import load_pygame, TiledMap
from pathlib import Path
from .logger import Logger

ASSETS_DIR = Path("assets")

def load_img(path: str) -> pg.Surface:
    Logger.info(f"Loading image: {path}")
    img = pg.image.load(str(ASSETS_DIR / "images" / path))
    if not img:
        Logger.error(f"Failed to load image: {path}")
    return img.convert_alpha()

def load_sound(path: str) -> pg.mixer.Sound:
    Logger.info(f"Loading sound: {path}")
    sound = pg.mixer.Sound(str(ASSETS_DIR / "sounds" / path))
    if not sound:
        Logger.error(f"Failed to load sound: {path}")
    return sound

def load_font(path: str, size: int) -> pg.font.Font:
    Logger.info(f"Loading font: {path}")
    font = pg.font.Font(str(ASSETS_DIR / "fonts" / path), size)
    if not font:
        Logger.error(f"Failed to load font: {path}")
    return font

def load_tmx(path: str) -> TiledMap:
    # 如果 path 已經有 'maps/' 前綴就不要重複加
    if str(path).startswith("maps/"):
        tmx_path = ASSETS_DIR / path
    else:
        tmx_path = ASSETS_DIR / "maps" / path
    tmxdata = load_pygame(str(tmx_path))
    if tmxdata is None:
        Logger.error(f"Failed to load map: {path}")
    return tmxdata
