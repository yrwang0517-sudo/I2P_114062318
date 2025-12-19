import pygame as pg
from src.utils import GameSettings
from src.core.services import resource_manager

class Minimap:
    """Simple minimap: given a map object that exposes width,height and a surface or tile rendering,
    we will render a scaled-down representation and a player marker.

    This implementation expects the GameScene to provide:
    - current_map: an object with attributes `width`, `height`, and a method `render_to_surface()`
      or a surface at `current_map.surface`. If such methods aren't present, the minimap will
    try to build a basic grid using tile size.
    - player_tile_pos: (tx, ty) tile coordinates of the player on the current map.

    If the project uses pytmx or custom map objects, adjust `get_map_surface` accordingly.
    """

    def __init__(self, game_scene):
        self.game_scene = game_scene
        # minimap width is ~1/5 of screen width
        self.width = max(120, GameSettings.SCREEN_WIDTH // 5)
        # height will be computed based on current map aspect ratio; default to width
        self.height = self.width
        # position at top-left with some padding
        self.x = 10
        self.y = 10
        self.padding = 6
        # background color and border
        self.bg_color = (30, 30, 30, 200)
        self.border_color = (0, 0, 0)
        # cache last map id to avoid rebuilding surface each frame
        self._last_map_id = None
        self._map_surf = None

    def _get_map_surface(self):
        """Try to get or build a surface representing the entire map. Tries several fallbacks.
        Returns a pygame.Surface or None.
        """
        gs = self.game_scene
        if not gs:
            return None

        current_map = getattr(gs, 'current_map', None)
        if not current_map:
            return None

        map_id = getattr(current_map, 'name', None) or getattr(current_map, 'map_id', None) or id(current_map)
        if map_id == self._last_map_id and self._map_surf is not None:
            return self._map_surf

        # Attempt 1: if map has a pre-rendered surface attribute (Map._surface)
        surf = None
        # support both public 'surface' and internal '_surface'
        if hasattr(current_map, '_surface') and isinstance(getattr(current_map, '_surface'), pg.Surface):
            surf = current_map._surface
        elif hasattr(current_map, 'surface') and isinstance(getattr(current_map, 'surface'), pg.Surface):
            surf = current_map.surface
        # Attempt 2: if map has method to render to surface
        elif hasattr(current_map, 'render_to_surface'):
            try:
                surf = current_map.render_to_surface()
            except Exception:
                surf = None
        # Attempt 3: try to render from tile data (basic colored grid)
        if surf is None:
            try:
                tw = getattr(current_map, 'width', None)
                th = getattr(current_map, 'height', None)
                tile_size = getattr(current_map, 'tile_size', getattr(GameSettings, 'TILE_SIZE', 32))
                if tw and th:
                    surf = pg.Surface((tw * tile_size, th * tile_size))
                    surf.fill((80, 80, 80))
                    # draw simple grid blocks as placeholder
                    col1 = (100, 150, 100)
                    col2 = (80, 120, 80)
                    for y in range(th):
                        for x in range(tw):
                            r = pg.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
                            c = col1 if (x + y) % 2 == 0 else col2
                            pg.draw.rect(surf, c, r)
                else:
                    surf = None
            except Exception:
                surf = None

        # cache and remember map id
        self._map_surf = surf
        # if we got a real surf, update minimap height to maintain aspect ratio
        if surf is not None:
            try:
                sw, sh = surf.get_size()
                # compute height preserving aspect ratio
                self.height = max(48, int((self.width * sh) / max(1, sw)))
            except Exception:
                pass
        self._last_map_id = map_id
        return surf

    def update(self, dt):
        # nothing heavy here; map surface cached in _get_map_surface
        pass

    def draw(self, screen):
        # draw background box
        box_w = self.width + self.padding * 2
        box_h = self.height + self.padding * 2
        box_surf = pg.Surface((box_w, box_h), pg.SRCALPHA)
        box_surf.fill(self.bg_color)
        screen.blit(box_surf, (self.x, self.y))
        # border
        pg.draw.rect(screen, self.border_color, pg.Rect(self.x, self.y, box_w, box_h), 2)

        # map surface scaled to fit
        map_surf = self._get_map_surface()
        if map_surf:
            try:
                scaled = pg.transform.smoothscale(map_surf, (self.width, self.height))
                screen.blit(scaled, (self.x + self.padding, self.y + self.padding))
            except Exception:
                pass

        # draw player marker
        try:
            gs = self.game_scene
            if not gs:
                return
            player_pos = getattr(gs, 'player_tile_pos', None)
            current_map = getattr(gs, 'current_map', None)
            if player_pos and current_map and map_surf:
                tw = getattr(current_map, 'width', map_surf.get_width() // getattr(current_map, 'tile_size', GameSettings.TILE_SIZE))
                th = getattr(current_map, 'height', map_surf.get_height() // getattr(current_map, 'tile_size', GameSettings.TILE_SIZE))
                px = int((player_pos[0] / max(1, tw)) * self.width)
                py = int((player_pos[1] / max(1, th)) * self.height)
                # small red dot
                pg.draw.circle(screen, (220, 40, 40), (self.x + self.padding + px, self.y + self.padding + py), 4)
        except Exception:
            pass
