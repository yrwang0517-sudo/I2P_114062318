#ok沒問題
from __future__ import annotations
import pygame as pg
from typing import override
from .component import UIComponent
from .button import Button
from src.utils import GameSettings, Logger
from src.core.services import input_manager, scene_manager, sound_manager

class Overlay(UIComponent):

    is_active: bool
    overlay_rect: pg.Rect
    back_button: Button | None
    dark_surface: pg.Surface
    mute: bool
    mode: str
    volume: float = GameSettings.AUDIO_VOLUME  # 預設音量

    def __init__(self, width: int = 600, height: int = 400, mode: str = "menu", game_manager=None, save_callback=None, load_callback=None):
        self.is_active = False
        self.overlay_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - width) // 2,
            (GameSettings.SCREEN_HEIGHT - height) // 2,
            width,
            height
        )
        self.mode = mode
        self.game_manager = game_manager
        self.save_callback = save_callback
        self.load_callback = load_callback
        self.mute = False
        self.volume = GameSettings.AUDIO_VOLUME    #初始化聲音大小(用內建的)
        self.dark_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.dark_surface.set_alpha(128)
        self.dark_surface.fill((0, 0, 0))
        if mode == "menu":
            self.back_button = Button(
                "UI/button_back.png",
                "UI/button_back_hover.png",
                self.overlay_rect.x + 30,
                self.overlay_rect.bottom - 94,
                64, 64,
                on_click=self.return_to_menu  
            )
        elif mode == "game":
            self.back_button = None
            self.setting_buttons = []
            button_paths = ["UI/button_save.png", "UI/button_load.png", "UI/button_back.png"]
            button_hover_paths = ["UI/button_save_hover.png", "UI/button_load_hover.png", "UI/button_back_hover.png"]
            btn_y = self.overlay_rect.y + 180
            btn_x = self.overlay_rect.x + 30
            btn_gap = 20
            btn_size = 64
            for i in range(3):
                bx = btn_x + i * (btn_size + btn_gap)
                button = Button(
                    button_paths[i],
                    button_hover_paths[i],
                    bx, btn_y,
                    btn_size, btn_size,
                    on_click=self.handle_button_click(i)
                )
                self.setting_buttons.append(button)
        elif mode == "game_setting":
            self.setting_buttons = []
            button_paths = ["UI/button_save.png", "UI/button_load.png", "UI/button_back.png"]
            button_hover_paths = ["UI/button_save_hover.png", "UI/button_load_hover.png", "UI/button_back_hover.png"]
            btn_y = self.overlay_rect.y + 180
            btn_x = self.overlay_rect.x + 30
            btn_gap = 20
            btn_size = 64
            for i in range(3):
                bx = btn_x + i * (btn_size + btn_gap)
                button = Button(
                    button_paths[i],
                    button_hover_paths[i],
                    bx, btn_y,
                    btn_size, btn_size,
                    on_click=self.handle_button_click(i)
                )
                self.setting_buttons.append(button)  #所以現在setting_buttons有三個按鈕了
            # 定義 back_button 行為
            self.back_button = Button(
                "UI/button_back.png",
                "UI/button_back_hover.png",
                self.overlay_rect.x + 30,
                self.overlay_rect.bottom - 94,
                64, 64,
                on_click=self.return_to_menu
            )
        # X 按鈕（右上角）
        self.x_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            self.overlay_rect.right - 50,
            self.overlay_rect.top + 10,
            40, 40,
            on_click=self.return_to_menu if mode == "menu" else self.close
        )

    def handle_button_click(self, index: int):
        def click_action():
            if index == 0:
                # 先同步 UI 背包怪物到 game_manager.bag
                if self.game_manager and hasattr(self.game_manager, "bag"):
                    backpack = None
                    # 嘗試從 game_scene 取得 backpack_overlay
                    
                    from src.core.services import scene_manager
                    game_scene = scene_manager._scenes.get("game")
                    if hasattr(game_scene, "backpack_overlay"):
                        backpack = game_scene.backpack_overlay
 
                    if backpack:
                        self.game_manager.bag._monsters_data = list(backpack.get_monsters())
                if self.save_callback:
                    self.save_callback()
            elif index == 1:
                if self.load_callback:
                    self.load_callback()
                    # Clear transient input immediately after loading to avoid input replay
                    try:
                        input_manager.reset()
                    except Exception:
                        pass

            elif index == 2:
                self.close()
                self.return_to_menu()
        return click_action

    def return_to_menu(self):
        scene_manager.change_scene("menu")
        self.close()

    def open(self) -> None:
        self.is_active = True

    def close(self) -> None:
        self.is_active = False

    def get_volume(self):
        return self.volume

    def set_volume(self, v: float):
        self.volume = max(0.0, min(1.0, v))    
        sound_manager.set_volume(self.volume)
        
    @override
    def update(self, dt: float) -> None:
        if self.is_active:
            self.x_button.update(dt)  # 更新 X 按鈕狀態
            if self.mode == "menu" and self.back_button:
                self.back_button.update(dt)
            elif self.mode == "game" or self.mode == "game_setting":
                for button in self.setting_buttons:
                    button.update(dt)
                if self.back_button:
                    self.back_button.update(dt)
            # Mute 按鈕互動
            if self.mode == "menu":
                bar_x = self.overlay_rect.x + 30
                bar_y = self.overlay_rect.y + 180
                mute_x = bar_x + 150
                mute_y = bar_y
                mute_rect = pg.Rect(mute_x, mute_y, 64, 32)
                if input_manager.mouse_pressed(1):
                    mouse_pos = input_manager.mouse_pos
                    if mute_rect.collidepoint(mouse_pos):
                        self.mute = not self.mute                       
                        sound_manager.set_volume(0.0 if self.mute else self.volume)
                        

    @override
    def draw(self, screen: pg.Surface) -> None:
        if not self.is_active:
            return
        screen.blit(self.dark_surface, (0, 0))
        pg.draw.rect(screen, (255, 165, 48), self.overlay_rect)
        pg.draw.rect(screen, (0, 0, 0), self.overlay_rect, 4)
        font_title = pg.font.SysFont(None, 48)
        text = font_title.render('SETTINGS', True, (255, 255, 255))
        screen.blit(text, (self.overlay_rect.x + 30, self.overlay_rect.y + 30))

        #音量百分比與滑動條
        font2 = pg.font.SysFont(None, 32)
        vol_percent = int(self.get_volume() * 100)
        vol_text = font2.render(f'Volume: {vol_percent}%', True, (255, 255, 255))
        screen.blit(vol_text, (self.overlay_rect.x + 30, self.overlay_rect.y + 90))
        bar_x = self.overlay_rect.x + 30
        bar_y = self.overlay_rect.y + 130
        bar_w = self.overlay_rect.width - 60
        bar_h = 16
        pg.draw.rect(screen, (230, 230, 230), (bar_x, bar_y, bar_w, bar_h), border_radius=8)
        handle_img = pg.image.load("assets/images/UI/raw/UI_Flat_Handle01a.png").convert_alpha()
        handle_size = 32
        handle_img = pg.transform.smoothscale(handle_img, (handle_size, handle_size))
        #計算滑塊位置
        slider_x = bar_x + int(bar_w * self.get_volume()) - handle_size // 2
        slider_y = bar_y + bar_h // 2 - handle_size // 2
        screen.blit(handle_img, (slider_x, slider_y))

        slider_rect = pg.Rect(bar_x, bar_y, bar_w, bar_h + handle_size)
        if pg.mouse.get_pressed()[0]:
            mouse_pos = pg.mouse.get_pos()
            if slider_rect.collidepoint(mouse_pos):
                rel_x = max(0, min(mouse_pos[0] - bar_x, bar_w))
                self.set_volume(rel_x / bar_w)

        self.x_button.draw(screen)  # Draw X button
        if self.mode == "menu":
            mute_text = font2.render(f"Mute: {'On' if self.mute else 'Off'}", True, (255, 255, 255))
            screen.blit(mute_text, (bar_x, bar_y + 50))
            mute_img_path = "assets/images/UI/raw/UI_Flat_ToggleLeftOn01a.png" if self.mute else "assets/images/UI/raw/UI_Flat_ToggleLeftOff01a.png"
            mute_img = pg.image.load(mute_img_path).convert_alpha()
            mute_img = pg.transform.smoothscale(mute_img, (64, 32))
            mute_x = bar_x + 150
            mute_y = bar_y + 50
            screen.blit(mute_img, (mute_x, mute_y))
            # 只顯示 Back 按鈕
            if self.back_button:
                self.back_button.draw(screen)
        elif self.mode == "game_setting":
            # 標題
            font_title = pg.font.SysFont(None, 48)
            text = font_title.render('SETTINGS', True, (255, 255, 255))
            screen.blit(text, (self.overlay_rect.x + 30, self.overlay_rect.y + 30))
            # 音量百分比與滑動條（只顯示一次，且可拖曱）
            font2 = pg.font.SysFont(None, 32)
            vol_percent = int(self.get_volume() * 100)
            vol_text = font2.render(f'Volume: {vol_percent}%', True, (255, 255, 255))
            screen.blit(vol_text, (self.overlay_rect.x + 30, self.overlay_rect.y + 90))
            bar_x = self.overlay_rect.x + 30
            bar_y = self.overlay_rect.y + 130
            bar_w = self.overlay_rect.width - 60
            bar_h = 16
            pg.draw.rect(screen, (230, 230, 230), (bar_x, bar_y, bar_w, bar_h), border_radius=8)
            handle_img = pg.image.load("assets/images/UI/raw/UI_Flat_Handle01a.png").convert_alpha()
            handle_size = 32
            handle_img = pg.transform.smoothscale(handle_img, (handle_size, handle_size))
            slider_x = bar_x + int(bar_w * self.get_volume()) - handle_size // 2
            slider_y = bar_y + bar_h // 2 - handle_size // 2
            screen.blit(handle_img, (slider_x, slider_y))
            # Mute
            mute_text = font2.render(f"Mute: {'On' if self.mute else 'Off'}", True, (255, 255, 255))
            mute_text_x = bar_x
            mute_text_y = bar_y + 50
            screen.blit(mute_text, (mute_text_x, mute_text_y))
            mute_img_path = "assets/images/UI/raw/UI_Flat_ToggleLeftOn01a.png" if self.mute else "assets/images/UI/raw/UI_Flat_ToggleLeftOff01a.png"
            mute_img = pg.image.load(mute_img_path).convert_alpha()
            mute_img = pg.transform.smoothscale(mute_img, (64, 32))
            mute_x = mute_text_x + 120
            mute_y = mute_text_y - 4
            screen.blit(mute_img, (mute_x, mute_y))
            # 點擊 mute 開關
            mute_rect = pg.Rect(mute_x, mute_y, 64, 32)
            if input_manager.mouse_pressed(1):
                mouse_pos = input_manager.mouse_pos
                if mute_rect.collidepoint(mouse_pos):
                    self.mute = not self.mute
                    try:
                        sound_manager.set_volume(0.0 if self.mute else self.volume)
                    except Exception:
                        pass
            # 三個大按鈕往下移動，並置中
            btn_y = mute_y + 100
            btn_width = 64
            btn_gap = 40
            total_width = len(self.setting_buttons) * btn_width + (len(self.setting_buttons) - 1) * btn_gap
            btn_x = self.overlay_rect.x + (self.overlay_rect.width - total_width) // 2
            for i, button in enumerate(self.setting_buttons):
                draw_x = btn_x + i * (btn_width + btn_gap)
                draw_y = btn_y
                button.hitbox.topleft = (draw_x, draw_y)
                button.draw(screen)
            # ESC 說明
            esc_text = font2.render('Press ESC to close', True, (255, 255, 255))
            screen.blit(esc_text, (self.overlay_rect.x + 30, self.overlay_rect.bottom - 40))
        elif self.mode == "game":
            for button in self.setting_buttons:
                button.draw(screen)
            if self.back_button:
                self.back_button.draw(screen)
