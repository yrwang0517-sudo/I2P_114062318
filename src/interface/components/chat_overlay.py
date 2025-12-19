from __future__ import annotations
import pygame as pg
from typing import Optional, Callable, List, Dict
from .component import UIComponent
from src.core.services import input_manager
from src.utils import Logger


class ChatOverlay(UIComponent):
    """Lightweight chat UI similar to Minecraft: toggle with a key, type, press Enter to send."""
    is_open: bool
    _input_text: str
    _cursor_timer: float
    _cursor_visible: bool
    _just_opened: bool
    _send_callback: Callable[[str], bool] | None    #  NOTE: This is a callable function, you need to give it a function that sends the message
    _get_messages: Callable[[int], list[dict]] | None # NOTE: This is a callable function, you need to give it a function that gets the messages
    _font_msg: pg.font.Font
    _font_input: pg.font.Font

    def __init__(
        self,
        send_callback: Callable[[str], bool] | None = None,
        get_messages: Callable[[int], list[dict]] | None = None,
        *,
        font_path: str = "assets/fonts/Minecraft.ttf"
    ) -> None:
        self.is_open = False
        self._input_text = ""
        self._cursor_timer = 0.0
        self._cursor_visible = True
        self._just_opened = False
        self._send_callback = send_callback
        self._get_messages = get_messages

        # 初始化字型用於訊息和輸入框
        try:
            self._font_msg = pg.font.Font(font_path, 16)
            self._font_input = pg.font.Font(font_path, 14)
        except Exception:
            # 如果字型檔案不存在，使用系統字型
            self._font_msg = pg.font.SysFont(None, 16)
            self._font_input = pg.font.SysFont(None, 14)

    def open(self) -> None:
        if not self.is_open:
            self.is_open = True
            self._cursor_timer = 0.0
            self._cursor_visible = True
            self._just_opened = True

    def close(self) -> None:
        self.is_open = False
    
    def toggle(self) -> None:
        """切換聊天視窗的開啟/關閉狀態"""
        if self.is_open:
            self.close()
        else:
            self.open()

    def _handle_typing(self) -> None:
        """
        處理文本輸入
        - 字母、數字、特殊字符：添加到聊天框
        - Backspace：刪除最後一個字元
        - Enter：發送聊天訊息
        - Escape：關閉聊天框
        """
        # 處理字母輸入（大小寫）
        shift = input_manager.key_down(pg.K_LSHIFT) or input_manager.key_down(pg.K_RSHIFT)
        for k in range(pg.K_a, pg.K_z + 1):
            if input_manager.key_pressed(k):
                ch = chr(ord('a') + (k - pg.K_a))
                self._input_text += (ch.upper() if shift else ch)
        
        # 處理數字輸入
        for k in range(pg.K_0, pg.K_9 + 1):
            if input_manager.key_pressed(k):
                if shift:
                    # Shift + 數字對應的特殊字符
                    special_chars = {pg.K_0: ')', pg.K_1: '!', pg.K_2: '@', pg.K_3: '#', 
                                   pg.K_4: '$', pg.K_5: '%', pg.K_6: '^', pg.K_7: '&', 
                                   pg.K_8: '*', pg.K_9: '('}
                    self._input_text += special_chars.get(k, str(k - pg.K_0))
                else:
                    self._input_text += str(k - pg.K_0)
        
        # 處理空格
        if input_manager.key_pressed(pg.K_SPACE):
            self._input_text += " "
        
        # 處理其他常見字符
        if input_manager.key_pressed(pg.K_PERIOD):
            self._input_text += "."
        if input_manager.key_pressed(pg.K_COMMA):
            self._input_text += ","
        if input_manager.key_pressed(pg.K_MINUS):
            self._input_text += "-" if not shift else "_"
        if input_manager.key_pressed(pg.K_EQUALS):
            self._input_text += "=" if not shift else "+"
        if input_manager.key_pressed(pg.K_SLASH):
            self._input_text += "/" if not shift else "?"
        
        # 處理退格鍵
        if input_manager.key_pressed(pg.K_BACKSPACE):
            self._input_text = self._input_text[:-1]
        
        # 處理 Enter 鍵發送聊天訊息
        if input_manager.key_pressed(pg.K_RETURN):
            txt = self._input_text.strip()
            # 檢查輸入不為空且有發送回調函數
            if txt and self._send_callback:
                ok = False
                try:
                    # 調用發送回調函數發送聊天訊息
                    ok = self._send_callback(txt)
                except Exception as e:
                    Logger.error(f"Failed to send chat message: {e}")
                    ok = False
                if ok:
                    # 發送成功則清空輸入框
                    self._input_text = ""

    def update(self, dt: float) -> None:
        """更新聊天系統狀態"""
        if not self.is_open:
            return
        
        # 按 Escape 鍵關閉聊天框
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return
        
        # 處理文本輸入
        if self._just_opened:
            # 剛打開時跳過第一幀，防止意外輸入
            self._just_opened = False
        else:
            self._handle_typing()
        
        # 更新遊標閃爍效果（0.5秒閃爍週期）
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def draw(self, screen: pg.Surface) -> None:
        """繪製聊天系統UI"""
        # 獲取最近8條聊天訊息（只在聊天框打開時顯示）
        sw, sh = screen.get_size()
        x = 10
        # 輸入框位置（聊天框開啟時的輸入框）
        box_h = 28
        box_y_input = sh - box_h - 6
        # 訊息容器固定高度（在輸入框上方）
        container_h = 120
        container_y = box_y_input - container_h
        
        # 繪製訊息顯示區域（只在聊天框打開時顯示）
        if self.is_open:
            msgs = self._get_messages(8) if self._get_messages else []
        else:
            msgs = []
        
        if msgs:
            # 訊息容器寬度為螢幕寬度的60%
            container_w = max(100, int((sw - 20) * 0.6))
            
            # 如果聊天框開啟則更透明，否則保持半透明
            bg = pg.Surface((container_w, container_h), pg.SRCALPHA)
            bg.fill((0, 0, 0, 90 if self.is_open else 60))
            _ = screen.blit(bg, (x, container_y))
            
            # 建立裁剪區域，防止訊息超出容器
            clip_rect = pg.Rect(x, container_y, container_w, container_h)
            old_clip = screen.get_clip()
            screen.set_clip(clip_rect)
            
            # 繪製最後8條訊息，從下往上排列
            lines = list(msgs)[-8:]
            # 計算總高度，從下方開始往上排列
            total_h = sum(self._font_msg.get_height() + 4 for _ in lines) + 8
            draw_y = container_y + container_h - 8
            
            # 從最後一條訊息開始從下往上顯示
            for m in reversed(lines):
                # 訊息格式：[發送者]: 訊息內容
                sender = str(m.get("from", ""))
                text = str(m.get("text", ""))
                surf = self._font_msg.render(f"{sender}: {text}", True, (255, 255, 255))
                # 從下往上排列
                draw_y -= surf.get_height() + 4
                if draw_y >= container_y + 4:
                    _ = screen.blit(surf, (x + 10, draw_y))
            
            # 恢復裁剪區域
            screen.set_clip(old_clip)
        
        # 如果聊天框未開啟，跳過輸入框繪製
        if not self.is_open:
            return
        
        # 繪製輸入框
        box_w = max(100, int((sw - 20) * 0.6))
        box_y = box_y_input
        
        # 輸入框背景
        bg2 = pg.Surface((box_w, box_h), pg.SRCALPHA)
        bg2.fill((0, 0, 0, 160))
        _ = screen.blit(bg2, (x, box_y))
        
        # 繪製使用者輸入的文本
        txt = self._input_text
        # 限制顯示寬度，避免超出邊界
        display_text = txt
        text_surf = self._font_input.render(display_text, True, (255, 255, 255))
        # 如果文本太長，從末尾開始顯示
        max_width = box_w - 16
        if text_surf.get_width() > max_width:
            while display_text and self._font_input.render(display_text, True, (255, 255, 255)).get_width() > max_width:
                display_text = display_text[1:]
            text_surf = self._font_input.render(display_text, True, (255, 255, 255))
        
        _ = screen.blit(text_surf, (x + 8, box_y + 4))
        
        # 繪製遊標（閃爍效果）
        if self._cursor_visible:
            # 遊標位置在文本末尾
            cx = x + 8 + text_surf.get_width() + 2
            cy = box_y + 6
            # 繪製一條豎線作為遊標
            pg.draw.rect(screen, (255, 255, 255), pg.Rect(cx, cy, 2, box_h - 12))