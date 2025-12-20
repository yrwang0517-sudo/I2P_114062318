# ============================================
# 商店界面管理模組
# 功能: 顯示商品、購買/出售道具、金幣管理
# 特性: 道具價格表、購買限制檢查、聊天字體支援
# ============================================
import os
import re
import pygame as pg
from src.utils import GameSettings, Logger
from src.core.services import input_manager, resource_manager

class ShopOverlay:
    """商店界面類
    
    責任:
    - 顯示可購買的道具列表
    - 管理 BUY/SELL 頁籤
    - 同步玩家金幣 (Coins)
    - 處理購買交易和道具添加
    """
    def __init__(self, game_scene=None):
        """初始化商店界面
        
        參數:
            game_scene: 遊戲場景物件，用於存取金幣、背包、怪物等
        """
        self.is_active = False
        # ===== 界面佈局 (與背包界面相同尺寸 1250 x 700) =====
        self.overlay_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - 1250) // 2,   # 水平居中
            (GameSettings.SCREEN_HEIGHT - 700) // 2,   # 垂直居中
            1250, 700
        )
        self.game_scene = game_scene
        
        # ===== 購買/出售按鈕圖片 =====
        # 按鈕狀態圖片: 未點擊 vs 懸停
        self.buy_btn_img = resource_manager.get_image("UI/raw/UI_Flat_Button01a_4.png")   # 默認樣式
        self.buy_btn_img_h = resource_manager.get_image("UI/raw/UI_Flat_Button01a_1.png")  # 懸停樣式

        # ===== 按鈕位置 (左上方) =====
        btn_w, btn_h = 180, 56             # 按鈕寬度、高度
        padding = 20                       # 內邊距
        self.buy_rect = pg.Rect(self.overlay_rect.x + padding, self.overlay_rect.y + padding, btn_w, btn_h)
        # 出售按鈕在購買按鈕右邊（視覺用，尚未實裝出售功能）
        self.sell_btn_img = resource_manager.get_image("UI/raw/UI_Flat_Button01a_4.png")
        self.sell_btn_img_h = resource_manager.get_image("UI/raw/UI_Flat_Button01a_1.png")
        self.sell_rect = pg.Rect(self.overlay_rect.x + padding + btn_w + 10, self.overlay_rect.y + padding, btn_w, btn_h)

        # ===== 商品列表 =====
        # 每項包含: key, name（顯示名), img（圖片路徑), price（購買價格）
        self.items = [
            {"key": "hp_potion", "name": "hp potion", "img": "ingame_ui/potion.png", "price": 2},
            {"key": "max_hp_potion", "name": "max hp potion", "img": "ingame_ui/potion.png", "price": 5},
            {"key": "pokeball", "name": "Pokeball", "img": "ingame_ui/ball.png", "price": 3},
            {"key": "attack", "name": "attack", "img": "ingame_ui/options1.png", "price": 2},
            {"key": "defense", "name": "defense", "img": "ingame_ui/options2.png", "price": 2},
            {"key": "exp_potion", "name": "exp potion", "img": "ingame_ui/exp_potion.png", "price": 5},
        ]

        # ===== UI 組件 =====
        self.item_bg = resource_manager.get_image("UI/raw/UI_Flat_Banner03a.png")  # 商品背景圖
        self.shop_btn_img = resource_manager.get_image("UI/button_shop.png")        # 購買按鈕圖
        self.shop_btn_img_h = resource_manager.get_image("UI/button_shop_hover.png") # 購買按鈕懸停圖
        
        # ===== 狀態 =====
        self.tab = "buy"  # 當前頁籤: "buy" 或 "sell"

        # ===== 關閉按鈕 (X) =====
        self.x_button = pg.Rect(self.overlay_rect.right - 100, self.overlay_rect.top + 10, 40, 40)

        # ===== 提示訊息 =====
        self.hint_text = ""        # 提示文字（購買成功、金幣不足等）
        self.hint_expire = 0       # 提示過期時間戳
        self.hint_duration = 2000  # 提示顯示時長（毫秒）

        # ===== 字體快取 =====
        # 存儲已加載字體以避免重複加載
        self._font_cache = {}
        # Minecraft 字體路徑
        self._minecraft_ttf = os.path.join('assets', 'fonts', 'Minecraft.ttf')
        # 中文字符檢測正規表達式 (CJK 統一表意文字)
        self._cjk_re = re.compile(r'[\u4e00-\u9fff]')

    def _get_font_for_text(self, text: str, size: int):
        """根據文字內容選擇適當字體 (中文用微軟正黑體、英文用 Minecraft 字體)
        
        參數:
            text: 要渲染的文字
            size: 字體大小 (像素)
            
        返回: pygame Font 物件 (已快取，避免重複加載)
        
        邏輯:
            1. 檢測文字是否包含中文字符 (CJK)
            2. 中文 -> 微軟正黑體 / 英文 -> Minecraft TTF
            3. 字體快取提升性能
        """
        try:
            # 檢測中文字符
            use_cjk = bool(self._cjk_re.search(text or ''))
        except Exception:
            use_cjk = False

        # 快取鍵: (字體類型, 大小)
        key = ('jhenghei' if use_cjk else 'minecraft', size)
        if key in self._font_cache:
            return self._font_cache[key]

        font_obj = None
        if use_cjk:
            # 優先使用微軟正黑體 (繁體中文字體)
            try:
                font_obj = pg.font.SysFont('Microsoft JhengHei', size)
            except Exception:
                font_obj = pg.font.SysFont(None, size)  # 降級為系統默認字體
        else:
            # 英文使用 Minecraft 字體
            try:
                if os.path.exists(self._minecraft_ttf):
                    font_obj = pg.font.Font(self._minecraft_ttf, size)
                else:
                    font_obj = pg.font.SysFont(None, size)
            except Exception:
                font_obj = pg.font.SysFont(None, size)

        self._font_cache[key] = font_obj
        return font_obj

    def _sync_coins_with_bag(self):
        """同步遊戲場景的金幣 (GameScene.money) 與背包中的 Coins 道具
        
        功能:
        - 確保 bag 和 backpack_overlay 中的 Coins 數量與 game_scene.money 一致
        - 如果找不到 Coins，則添加新的 Coins 道具
        - 用於購買後更新金幣顯示
        """
        try:
            gs = self.game_scene
            if not gs:
                return
            coins = int(getattr(gs, 'money', 0))
            # update Bag if present
            bag = getattr(gs, 'bag', None)
            if bag is not None:
                try:
                    # bag may store items in _items_data
                    items_list = None
                    if hasattr(bag, '_items_data'):
                        items_list = bag._items_data
                    elif hasattr(bag, 'items'):
                        items_list = bag.items
                    if items_list is not None:
                        found = False
                        for it in items_list:
                            if (it.get('name') or '').lower() in ('coins', 'coin') or (it.get('key') or '').lower() in ('coins','coin'):
                                it['count'] = coins
                                found = True
                                break
                        if not found:
                            try:
                                items_list.append({'name': 'Coins', 'key': 'coins', 'img': 'ingame_ui/coin.png', 'count': coins})
                            except Exception:
                                pass
                except Exception:
                    pass
            # update BackpackOverlay if present
            try:
                if hasattr(gs, 'backpack_overlay') and gs.backpack_overlay is not None:
                    bi = gs.backpack_overlay.get_items() or gs.backpack_overlay.items
                    found = False
                    for it in bi:
                        if (it.get('name') or '').lower() in ('coins', 'coin') or (it.get('key') or '').lower() in ('coins','coin'):
                            it['count'] = coins
                            found = True
                            break
                    if not found:
                        try:
                            bi.append({'name': 'Coins', 'key': 'coins', 'img': 'ingame_ui/coin.png', 'count': coins})
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def open(self):
        self.is_active = True

    def close(self):
        try:
            from src.core.services import input_manager
            input_manager.reset()
        except Exception:
            pass
        self.is_active = False

    def toggle_tab(self, tab_name: str):
        # allow switching between buy and sell
        if tab_name in ("buy", "sell"):
            self.tab = tab_name

    def update(self, dt):
        if not self.is_active:
            return
        # handle close click
        if input_manager.mouse_pressed(1) and self.x_button.collidepoint(input_manager.mouse_pos):
            self.close()
            return
        
        # handle buy/sell tab clicks
        if input_manager.mouse_pressed(1):
            if self.buy_rect.collidepoint(input_manager.mouse_pos):
                self.toggle_tab("buy")
                return
            if self.sell_rect.collidepoint(input_manager.mouse_pos):
                self.toggle_tab("sell")
                return
        
        # handle buy actions: clicking shop cart button
        if self.tab == "buy" and input_manager.mouse_pressed(1):
            base_x = self.overlay_rect.x + 60
            base_y = self.overlay_rect.y + 120
            for i, it in enumerate(self.items):
                # shop button rect - must match draw position
                btn_x = base_x + 450 + 20
                btn_y = base_y + i * 90 + 16
                btn_rect = pg.Rect(btn_x, btn_y, 48, 48)
                if btn_rect.collidepoint(input_manager.mouse_pos):
                    Logger.info(f"Shop button clicked for item: {it.get('name')}")
                    try:
                        if self.game_scene:
                            gs = self.game_scene
                            bag = getattr(gs, 'bag', None)
                            
                            # get current coins from bag or backpack
                            current_coins = 0
                            
                            # try bag first
                            if bag and hasattr(bag, '_items_data'):
                                for item in bag._items_data:
                                    if (item.get('name') or '').lower() in ('coins', 'coin'):
                                        current_coins = int(item.get('count', 0))
                                        Logger.info(f"Found coins in bag: {current_coins}")
                                        break
                            
                            # fallback to backpack_overlay
                            if current_coins == 0 and hasattr(gs, 'backpack_overlay') and gs.backpack_overlay:
                                for item in (gs.backpack_overlay.get_items() or []):
                                    if (item.get('name') or '').lower() in ('coins', 'coin'):
                                        current_coins = int(item.get('count', 0))
                                        Logger.info(f"Found coins in backpack: {current_coins}")
                                        break
                            
                            # also check game_scene.money
                            if current_coins == 0:
                                current_coins = int(getattr(gs, 'money', 0))
                                Logger.info(f"Using game_scene.money: {current_coins}")
                            
                            Logger.info(f"Item price: {it['price']}, Current coins: {current_coins}")
                            
                            # check if enough money
                            if current_coins >= it['price']:
                                new_coin_count = current_coins - it['price']
                                
                                # deduct coins from bag
                                coin_updated = False
                                if bag and hasattr(bag, '_items_data'):
                                    for item in bag._items_data:
                                        if (item.get('name') or '').lower() in ('coins', 'coin'):
                                            item['count'] = new_coin_count
                                            coin_updated = True
                                            Logger.info(f"Updated coins in bag to {new_coin_count}")
                                            break
                                
                                # also update backpack if exists
                                if hasattr(gs, 'backpack_overlay') and gs.backpack_overlay:
                                    for item in (gs.backpack_overlay.get_items() or gs.backpack_overlay.items or []):
                                        if (item.get('name') or '').lower() in ('coins', 'coin'):
                                            item['count'] = new_coin_count
                                            Logger.info(f"Updated coins in backpack to {new_coin_count}")
                                            break
                                
                                # update game_scene money
                                gs.money = new_coin_count
                                
                                # add purchased item to bag
                                if bag and hasattr(bag, '_items_data'):
                                    found = False
                                    item_key = (it.get('key') or '').lower()
                                    item_name = (it.get('name') or '').lower()
                                    for item in bag._items_data:
                                        # 同时检查 key 和 name，任一匹配即视为同一物品
                                        existing_key = (item.get('key') or '').lower()
                                        existing_name = (item.get('name') or '').lower()
                                        if (item_key and existing_key == item_key) or (item_name and existing_name == item_name):
                                            item['count'] = int(item.get('count', 0)) + 1
                                            found = True
                                            Logger.info(f"Incremented item count for {it.get('name')} (key: {it.get('key')})")
                                            break
                                    if not found:
                                        bag._items_data.append({
                                            'name': it.get('name'),
                                            'key': it.get('key'),
                                            'img': it.get('img'),
                                            'count': 1
                                        })
                                        Logger.info(f"Added new item to bag: {it.get('name')} (key: {it.get('key')})")
                                
                                # also add to backpack_overlay
                                if hasattr(gs, 'backpack_overlay') and gs.backpack_overlay:
                                    bp_items = gs.backpack_overlay.get_items() or gs.backpack_overlay.items or []
                                    found = False
                                    item_key = (it.get('key') or '').lower()
                                    item_name = (it.get('name') or '').lower()
                                    for item in bp_items:
                                        # 同时检查 key 和 name，任一匹配即视为同一物品
                                        existing_key = (item.get('key') or '').lower()
                                        existing_name = (item.get('name') or '').lower()
                                        if (item_key and existing_key == item_key) or (item_name and existing_name == item_name):
                                            item['count'] = int(item.get('count', 0)) + 1
                                            found = True
                                            break
                                    if not found:
                                        bp_items.append({
                                            'name': it.get('name'),
                                            'key': it.get('key'),
                                            'img': it.get('img'),
                                            'count': 1
                                        })
                                
                                Logger.info(f"Bought {it['key']} for {it['price']}")
                                return
                            else:
                                # not enough money
                                self.hint_text = '錢不夠'
                                self.hint_expire = pg.time.get_ticks() + self.hint_duration
                                Logger.info("Not enough money to buy")
                                return
                    except Exception as e:
                        Logger.error(f"Buy error: {e}")
                        import traceback
                        traceback.print_exc()
        
        # handle sell actions: clicking shop cart button
        if self.tab == "sell" and input_manager.mouse_pressed(1):
            base_x = self.overlay_rect.x + 60
            base_y = self.overlay_rect.y + 120
            
            # prepare price lookup from shop buy prices
            price_lookup = {}
            for si in self.items:
                if si.get('key'):
                    price_lookup[si.get('key').lower()] = si.get('price', 0)
                if si.get('name'):
                    price_lookup[si.get('name').lower()] = si.get('price', 0)
            
            # collect monsters and items (excluding coins)
            monsters = []
            items = []
            try:
                if self.game_scene and hasattr(self.game_scene, 'backpack_overlay'):
                    monsters = self.game_scene.backpack_overlay.get_monsters() or []
                    items = [it for it in (self.game_scene.backpack_overlay.get_items() or []) if (it.get('name') or '').lower() not in ('coins', 'coin')]
            except Exception:
                monsters = []
                items = []
            
            # combined list: monsters then items
            combined = []
            for m in monsters:
                combined.append(('monster', m))
            for it in items:
                combined.append(('item', it))
            
            # check each item/monster for button clicks
            row_h = 90
            col_w = 450 + 20
            for idx, entry in enumerate(combined):
                col = 0 if idx < 6 else 1
                row = idx if idx < 6 else idx - 6
                draw_x = base_x + col * col_w
                if col == 1:
                    draw_x += 65
                draw_y = base_y + row * row_h
                
                # shop button position
                btn_x = draw_x + 450 + 20
                btn_y = draw_y + 16
                btn_rect = pg.Rect(btn_x, btn_y, 48, 48)
                
                if btn_rect.collidepoint(input_manager.mouse_pos):
                    kind, data = entry
                    Logger.info(f"Sell button clicked for {kind}: {data.get('name')}")
                    
                    try:
                        if self.game_scene:
                            gs = self.game_scene
                            
                            if kind == 'monster':
                                # check if last monster
                                if len(monsters) <= 1:
                                    self.hint_text = '你只剩一個怪物了不能賣'
                                    self.hint_expire = pg.time.get_ticks() + self.hint_duration
                                    Logger.info("Cannot sell last monster")
                                    return
                                
                                # sell monster for fixed price 100
                                sell_price = 100
                                
                                # add coins to bag
                                bag = getattr(gs, 'bag', None)
                                if bag and hasattr(bag, '_items_data'):
                                    for item in bag._items_data:
                                        if (item.get('name') or '').lower() in ('coins', 'coin'):
                                            item['count'] = int(item.get('count', 0)) + sell_price
                                            Logger.info(f"Added {sell_price} coins to bag")
                                            break
                                
                                # also update backpack
                                if hasattr(gs, 'backpack_overlay') and gs.backpack_overlay:
                                    for item in (gs.backpack_overlay.get_items() or gs.backpack_overlay.items or []):
                                        if (item.get('name') or '').lower() in ('coins', 'coin'):
                                            item['count'] = int(item.get('count', 0)) + sell_price
                                            Logger.info(f"Added {sell_price} coins to backpack")
                                            break
                                
                                # update game_scene money
                                gs.money = int(getattr(gs, 'money', 0)) + sell_price
                                
                                # remove monster from backpack
                                monster_idx = combined[:idx].count(('monster', m) for m in monsters if m == data)
                                actual_idx = monsters.index(data)
                                if hasattr(gs, 'backpack_overlay') and gs.backpack_overlay:
                                    try:
                                        gs.backpack_overlay.monsters.pop(actual_idx)
                                        Logger.info(f"Removed monster {data.get('name')} from backpack")
                                    except Exception as e:
                                        Logger.error(f"Failed to remove monster: {e}")
                                
                                Logger.info(f"Sold monster {data.get('name')} for {sell_price}")
                                return
                            
                            elif kind == 'item':
                                # get sell price (half of buy price)
                                item_key = (data.get('key') or data.get('name') or '').lower()
                                buy_price = price_lookup.get(item_key, 0)
                                sell_price = int(buy_price / 2) if buy_price > 0 else 0
                                
                                # add coins to bag
                                bag = getattr(gs, 'bag', None)
                                if bag and hasattr(bag, '_items_data'):
                                    for item in bag._items_data:
                                        if (item.get('name') or '').lower() in ('coins', 'coin'):
                                            item['count'] = int(item.get('count', 0)) + sell_price
                                            Logger.info(f"Added {sell_price} coins to bag")
                                            break
                                
                                # also update backpack
                                if hasattr(gs, 'backpack_overlay') and gs.backpack_overlay:
                                    for item in (gs.backpack_overlay.get_items() or gs.backpack_overlay.items or []):
                                        if (item.get('name') or '').lower() in ('coins', 'coin'):
                                            item['count'] = int(item.get('count', 0)) + sell_price
                                            Logger.info(f"Added {sell_price} coins to backpack")
                                            break
                                
                                # update game_scene money
                                gs.money = int(getattr(gs, 'money', 0)) + sell_price
                                
                                # decrement item count in bag
                                if bag and hasattr(bag, '_items_data'):
                                    for item in bag._items_data:
                                        if (item.get('key') or '').lower() == item_key or (item.get('name') or '').lower() == item_key:
                                            current_count = int(item.get('count', 0))
                                            if current_count > 1:
                                                item['count'] = current_count - 1
                                                Logger.info(f"Decremented item count to {item['count']}")
                                            else:
                                                bag._items_data.remove(item)
                                                Logger.info(f"Removed item {item.get('name')} from bag")
                                            break
                                
                                # decrement item count in backpack
                                if hasattr(gs, 'backpack_overlay') and gs.backpack_overlay:
                                    for item in (gs.backpack_overlay.get_items() or gs.backpack_overlay.items or []):
                                        if (item.get('key') or '').lower() == item_key or (item.get('name') or '').lower() == item_key:
                                            current_count = int(item.get('count', 0))
                                            if current_count > 1:
                                                item['count'] = current_count - 1
                                            else:
                                                try:
                                                    (gs.backpack_overlay.get_items() or gs.backpack_overlay.items).remove(item)
                                                except:
                                                    pass
                                            break
                                
                                Logger.info(f"Sold item {data.get('name')} for {sell_price}")
                                return
                    
                    except Exception as e:
                        Logger.error(f"Sell error: {e}")
                        import traceback
                        traceback.print_exc()


    def draw(self, screen):
        if not self.is_active:
            return
        # fonts are selected per-string by _get_font_for_text()
        screen.blit(pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)), (0, 0))
        # darken
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(128)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        pg.draw.rect(screen, (255, 165, 48), self.overlay_rect)
        pg.draw.rect(screen, (0, 0, 0), self.overlay_rect, 4)

        # title
        try:
            font_title = self._get_font_for_text('SHOP', 48)
        except Exception:
            font_title = pg.font.SysFont(None, 48)
        text = font_title.render('SHOP', False, (0, 0, 0))
        screen.blit(text, (self.overlay_rect.x + 30, self.overlay_rect.y + 30))

        # hint text (shown when non-empty and not expired)
        try:
            if self.hint_text and pg.time.get_ticks() <= getattr(self, 'hint_expire', 0):
                try:
                    # set hint to 1.5x of base (base 28 -> 42)
                    hint_font = self._get_font_for_text(self.hint_text, 42)
                except Exception:
                    hint_font = pg.font.SysFont(None, 42)
                hint_surf = hint_font.render(self.hint_text, True, (200, 30, 30))
                hx = self.overlay_rect.x + (self.overlay_rect.w - hint_surf.get_width()) // 2
                # move hint up by additional 10 pixels from previous placement
                hy = self.overlay_rect.y + 16
                screen.blit(hint_surf, (hx, hy))
            else:
                # clear expired
                if self.hint_text:
                    self.hint_text = ""
        except Exception:
            pass

        # draw buy and sell buttons
        buy_img = self.buy_btn_img_h if self.buy_rect.collidepoint(input_manager.mouse_pos) else self.buy_btn_img
        buy_img = pg.transform.smoothscale(buy_img, (self.buy_rect.w, self.buy_rect.h))
        screen.blit(buy_img, (self.buy_rect.x, self.buy_rect.y))
        sell_img = self.sell_btn_img_h if self.sell_rect.collidepoint(input_manager.mouse_pos) else self.sell_btn_img
        sell_img = pg.transform.smoothscale(sell_img, (self.sell_rect.w, self.sell_rect.h))
        screen.blit(sell_img, (self.sell_rect.x, self.sell_rect.y))
        # labels
        try:
            lbl_font_buy = self._get_font_for_text('Buy', 32)
        except Exception:
            lbl_font_buy = pg.font.SysFont(None, 32)
        try:
            lbl_font_sell = self._get_font_for_text('Sell', 32)
        except Exception:
            lbl_font_sell = pg.font.SysFont(None, 32)
        lbl_buy = lbl_font_buy.render('Buy', True, (0,0,0))
        lbl_sell = lbl_font_sell.render('Sell', True, (0,0,0))
        screen.blit(lbl_buy, (self.buy_rect.x + (self.buy_rect.w - lbl_buy.get_width())//2, self.buy_rect.y + (self.buy_rect.h - lbl_buy.get_height())//2))
        screen.blit(lbl_sell, (self.sell_rect.x + (self.sell_rect.w - lbl_sell.get_width())//2, self.sell_rect.y + (self.sell_rect.h - lbl_sell.get_height())//2))

        # X button
        x_button_default = resource_manager.get_image("UI/button_x.png")
        x_button_hover = resource_manager.get_image("UI/button_x_hover.png")
        x_img = x_button_hover if self.x_button.collidepoint(input_manager.mouse_pos) else x_button_default
        x_img = pg.transform.smoothscale(x_img, (40, 40))
        screen.blit(x_img, (self.x_button.x, self.x_button.y))

        # coin display left of X button
        try:
            coins = 0
            if self.game_scene and hasattr(self.game_scene, 'money'):
                coins = int(getattr(self.game_scene, 'money', 0))
            else:
                # fallback: scan backpack items
                if self.game_scene and hasattr(self.game_scene, 'backpack_overlay'):
                    for it in (self.game_scene.backpack_overlay.get_items() or []):
                        if (it.get('name') or '').lower() in ('coins', 'coin'):
                            coins = int(it.get('count', 0))
                            break
        except Exception:
            coins = 0

        try:
            coin_img = resource_manager.get_image('ingame_ui/coin.png')
            if coin_img:
                icon = pg.transform.smoothscale(coin_img, (32, 32))
                # move coin icon 20px left
                coin_x = self.x_button.x - 55 - 32 - 6 - 20
                coin_y = self.x_button.y + (self.x_button.h - 32) // 2
                screen.blit(icon, (coin_x, coin_y))
                coin_font = self._get_font_for_text(f'x{coins}', 32)
                coin_txt = coin_font.render(f'x{coins}', True, (0,0,0))
                screen.blit(coin_txt, (coin_x + 36, coin_y + 4))
        except Exception:
            pass

        # content area
        if self.tab == 'buy':
            base_x = self.overlay_rect.x + 60
            base_y = self.overlay_rect.y + 120
            for i, it in enumerate(self.items):
                # bg
                if self.item_bg:
                    bg = pg.transform.smoothscale(self.item_bg, (450, 80))
                    screen.blit(bg, (base_x, base_y + i * 90))
                # icon
                img = resource_manager.get_image(it['img'])
                if img:
                    icon = pg.transform.smoothscale(img, (48, 48))
                    screen.blit(icon, (base_x + 8, base_y + i * 90 + 16))
                # name
                name_font = self._get_font_for_text(it.get('name',''), 32)
                name_txt = name_font.render(it['name'], True, (0,0,0))
                screen.blit(name_txt, (base_x + 70, base_y + i * 90 + 20))
                # quantity (previously price position)
                qty_font = self._get_font_for_text('x1', 32)
                qty_txt = qty_font.render('x1', True, (0,0,0))
                screen.blit(qty_txt, (base_x + 310, base_y + i * 90 + 20))
                # price moved to the right
                price_font = self._get_font_for_text(f"${it['price']}", 32)
                price_txt = price_font.render(f"${it['price']}", True, (0,0,0))
                screen.blit(price_txt, (base_x + 370, base_y + i * 90 + 20))
                # shop button image to the right of price
                btn_x = base_x + 450 + 20
                btn_y = base_y + i * 90 + 16
                btn_w, btn_h = 48, 48
                btn_rect = pg.Rect(btn_x, btn_y, btn_w, btn_h)
                shop_img = self.shop_btn_img_h if btn_rect.collidepoint(input_manager.mouse_pos) else self.shop_btn_img
                if shop_img:
                    shop_img = pg.transform.smoothscale(shop_img, (btn_w, btn_h))
                    screen.blit(shop_img, (btn_x, btn_y))
        # sell tab: list backpack monsters and items (exclude coins) with same layout as buy
        if self.tab == 'sell':
            base_x = self.overlay_rect.x + 60
            base_y = self.overlay_rect.y + 120

            # prepare price lookup from shop buy prices
            price_lookup = {}
            for si in self.items:
                if si.get('key'):
                    price_lookup[si.get('key').lower()] = si.get('price', 0)
                if si.get('name'):
                    price_lookup[si.get('name').lower()] = si.get('price', 0)

            # collect monsters then items (excluding coins)
            monsters = []
            items = []
            try:
                if self.game_scene and hasattr(self.game_scene, 'backpack_overlay'):
                    monsters = self.game_scene.backpack_overlay.get_monsters() or []
                    items = [it for it in (self.game_scene.backpack_overlay.get_items() or []) if (it.get('name') or '').lower() not in ('coins', 'coin')]
            except Exception:
                monsters = []
                items = []

            # render combined list in two columns: first 6 on left, continue on right
            row_h = 90
            col_w = 450 + 20  # banner width + padding
            combined = []
            for m in monsters:
                combined.append(('monster', m))
            for it in items:
                combined.append(('item', it))
            for idx, entry in enumerate(combined):
                col = 0 if idx < 6 else 1
                row = idx if idx < 6 else idx - 6
                draw_x = base_x + col * col_w
                if col == 1:
                    draw_x += 65
                draw_y = base_y + row * row_h
                # bg same as buy
                if self.item_bg:
                    bg = pg.transform.smoothscale(self.item_bg, (450, 80))
                    screen.blit(bg, (draw_x, draw_y))
                kind, data = entry
                if kind == 'monster':
                    img_path = data.get('sprite_path') or data.get('img')
                    img = resource_manager.get_image(img_path) if img_path else None
                    if img:
                        icon = pg.transform.smoothscale(img, (48, 48))
                        screen.blit(icon, (draw_x + 8, draw_y + 16))
                    # name
                    name_font = self._get_font_for_text(data.get('name','Monster'), 32)
                    name_txt = name_font.render(data.get('name', 'Monster'), True, (0,0,0))
                    screen.blit(name_txt, (draw_x + 70, draw_y + 20))
                    # qty
                    qty_font = self._get_font_for_text('x1', 32)
                    qty_txt = qty_font.render('x1', True, (0,0,0))
                    screen.blit(qty_txt, (draw_x + 310, draw_y + 20))
                    # price fixed at 100
                    price_font = self._get_font_for_text(f"$100", 32)
                    price_txt = price_font.render(f"$100", True, (0,0,0))
                    screen.blit(price_txt, (draw_x + 370, draw_y + 20))
                    # button
                    btn_x = draw_x + 450 + 20
                    btn_y = draw_y + 16
                    btn_w, btn_h = 48, 48
                    btn_rect = pg.Rect(btn_x, btn_y, btn_w, btn_h)
                    shop_img = self.shop_btn_img_h if btn_rect.collidepoint(input_manager.mouse_pos) else self.shop_btn_img
                    if shop_img:
                        shop_img = pg.transform.smoothscale(shop_img, (btn_w, btn_h))
                        screen.blit(shop_img, (btn_x, btn_y))
                else:
                    # item entry
                    img_path = data.get('img') or None
                    if not img_path:
                        it_name = (data.get('name') or '').lower()
                        for si in self.items:
                            if (si.get('key') and si.get('key').lower() == it_name) or (si.get('name') and si.get('name').lower() == it_name):
                                img_path = si.get('img')
                                break
                    img = resource_manager.get_image(img_path) if img_path else None
                    if img:
                        icon = pg.transform.smoothscale(img, (48, 48))
                        screen.blit(icon, (draw_x + 8, draw_y + 16))
                    name_font = self._get_font_for_text(data.get('name','Item'), 32)
                    name_txt = name_font.render(data.get('name', 'Item'), True, (0,0,0))
                    screen.blit(name_txt, (draw_x + 70, draw_y + 20))
                    qty_font = self._get_font_for_text(f"x{data.get('count', 0)}", 32)
                    qty_txt = qty_font.render(f"x{data.get('count', 0)}", True, (0,0,0))
                    screen.blit(qty_txt, (draw_x + 310, draw_y + 20))
                    it_name = (data.get('name') or '').lower()
                    buy_p = price_lookup.get(it_name, None)
                    sell_p = int(buy_p / 2) if buy_p is not None else 0
                    price_font = self._get_font_for_text(f"${sell_p}", 32)
                    price_txt = price_font.render(f"${sell_p}", True, (0,0,0))
                    screen.blit(price_txt, (draw_x + 370, draw_y + 20))
                    btn_x = draw_x + 450 + 20
                    btn_y = draw_y + 16
                    btn_w, btn_h = 48, 48
                    btn_rect = pg.Rect(btn_x, btn_y, btn_w, btn_h)
                    shop_img = self.shop_btn_img_h if btn_rect.collidepoint(input_manager.mouse_pos) else self.shop_btn_img
                    if shop_img:
                        shop_img = pg.transform.smoothscale(shop_img, (btn_w, btn_h))
                        screen.blit(shop_img, (btn_x, btn_y))