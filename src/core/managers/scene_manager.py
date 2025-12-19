import pygame as pg

from src.scenes.scene import Scene
from src.utils import Logger

class SceneManager:
    
    _scenes: dict[str, Scene]
    _current_scene: Scene | None = None
    _next_scene: str | None = None
    _next_scene_kwargs: dict = {}  # 用來暫存切換場景時要傳給 enter() 的參數
    
    def __init__(self):
        self._scenes = {}
        self._next_scene_kwargs = {}  # 初始化參數暫存
    
    def register_scene(self, name: str, scene: Scene) -> None:
        self._scenes[name] = scene
    
    def change_scene(self, scene_name: str, **kwargs) -> None:
        if scene_name in self._scenes:
            self._next_scene = scene_name
            self._next_scene_kwargs = kwargs  # 暫存要傳給 enter() 的參數
       
    def update(self, dt: float) -> None:
        #換場景
        if self._next_scene is not None:
            self._perform_scene_switch()
            
        if self._current_scene:
            self._current_scene.update(dt)
            
    def draw(self, screen: pg.Surface) -> None:
        if self._current_scene:
            self._current_scene.draw(screen)
            
    def _perform_scene_switch(self) -> None:
        if self._next_scene is None:
            return           
        #退出當前畫面
        if self._current_scene:
            self._current_scene.exit()
        
        self._current_scene = self._scenes[self._next_scene] #當前畫面改成要換的
        
        if self._current_scene:
            #這裡會把 change_scene 時傳入的參數傳給 enter()
            self._current_scene.enter(**self._next_scene_kwargs)

        #清掉該清理的
        self._next_scene = None
        self._next_scene_kwargs = {}
