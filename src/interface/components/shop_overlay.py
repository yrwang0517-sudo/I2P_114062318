import os
import re
import pygame as pg
from src.utils import GameSettings, Logger
from src.core.services import input_manager, resource_manager

class ShopOverlay:
    def __init__(self, game_scene=None):
        self.is_active = False
        # Same size as BackpackOverlay (1250 x 700)
        self.overlay_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - 1250) // 2,
            (GameSettings.SCREEN_HEIGHT - 700) // 2,
            1250, 700
        )
        self.game_scene = game_scene
        # Buttons: (image_normal, image_hover) - using UI/raw paths consistent with other UI
        self.buy_btn_img = resource_manager.get_image("UI/raw/UI_Flat_Button01a_1.png")
        # swap: use _4 as default image and _1 as hover image per request
        self.buy_btn_img = resource_manager.get_image("UI/raw/UI_Flat_Button01a_4.png")
        self.buy_btn_img_h = resource_manager.get_image("UI/raw/UI_Flat_Button01a_1.png")

        # button rects (placed near top-left inside overlay)
        btn_w, btn_h = 180, 56
        padding = 20
        self.buy_rect = pg.Rect(self.overlay_rect.x + padding, self.overlay_rect.y + padding, btn_w, btn_h)
        # sell button on the right of buy (visual only)
        self.sell_btn_img = resource_manager.get_image("UI/raw/UI_Flat_Button01a_4.png")
        self.sell_btn_img_h = resource_manager.get_image("UI/raw/UI_Flat_Button01a_1.png")
        self.sell_rect = pg.Rect(self.overlay_rect.x + padding + btn_w + 10, self.overlay_rect.y + padding, btn_w, btn_h)

        # Items available to buy
        self.items = [
            {"key": "hp_potion", "name": "hp potion", "img": "ingame_ui/potion.png", "price": 2},
            {"key": "max_hp_potion", "name": "max hp potion", "img": "ingame_ui/potion.png", "price": 5},
            {"key": "pokeball", "name": "Pokeball", "img": "ingame_ui/ball.png", "price": 3},
            {"key": "attack", "name": "attack", "img": "ingame_ui/options1.png", "price": 2},
            {"key": "defense", "name": "defense", "img": "ingame_ui/options2.png", "price": 2},
            {"key": "exp_potion", "name": "exp potion", "img": "ingame_ui/exp_potion.png", "price": 5},
        ]

        # UI background for each item
        self.item_bg = resource_manager.get_image("UI/raw/UI_Flat_Banner03a.png")

        # shop button images (click to buy)
        self.shop_btn_img = resource_manager.get_image("UI/button_shop.png")
        self.shop_btn_img_h = resource_manager.get_image("UI/button_shop_hover.png")
        # state
        self.tab = "buy"  # or "sell"

        # X button
        self.x_button = pg.Rect(self.overlay_rect.right - 100, self.overlay_rect.top + 10, 40, 40)

        # hint text shown at top of overlay (empty by default)
        self.hint_text = ""
        self.hint_expire = 0
        # duration in milliseconds to show hint
        self.hint_duration = 2000

        # font cache: keys are (font_name, size)
        self._font_cache = {}
        # path to local Minecraft TTF
        self._minecraft_ttf = os.path.join('assets', 'fonts', 'Minecraft.ttf')
        # regex to detect CJK Unified Ideographs (Chinese characters)
        self._cjk_re = re.compile(r'[\u4e00-\u9fff]')

    def _get_font_for_text(self, text: str, size: int):
        """Return a pygame Font object: use Microsoft JhengHei if text contains CJK characters,
        otherwise use Minecraft TTF. Cache fonts by (type,size).
        """
        try:
            use_cjk = bool(self._cjk_re.search(text or ''))
        except Exception:
            use_cjk = False

        key = ('jhenghei' if use_cjk else 'minecraft', size)
        if key in self._font_cache:
            return self._font_cache[key]

        font_obj = None
        if use_cjk:
            try:
                font_obj = pg.font.SysFont('Microsoft JhengHei', size)
            except Exception:
                font_obj = pg.font.SysFont(None, size)
        else:
            try:
                if os.path.exists(self._minecraft_ttf):
                    font_obj = pg.font.Font(self._minecraft_ttf, size)
                else:
                    # fallback to system default
                    font_obj = pg.font.SysFont(None, size)
            except Exception:
                font_obj = pg.font.SysFont(None, size)

        self._font_cache[key] = font_obj
        return font_obj

    def _sync_coins_with_bag(self):
        """Ensure bag and backpack_overlay have a Coins item that matches game_scene.money."""
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
        # handle buy/sell tab clicks
        if input_manager.mouse_pressed(1):
            if self.buy_rect.collidepoint(input_manager.mouse_pos):
                self.toggle_tab("buy")
            if self.sell_rect.collidepoint(input_manager.mouse_pos):
                self.toggle_tab("sell")

        # handle buy actions via per-item shop button (click the button at the right)
        if self.tab == "buy" and input_manager.mouse_pressed(1):
            base_x = self.overlay_rect.x + 60
            base_y = self.overlay_rect.y + 120
            for i, it in enumerate(self.items):
                # shop button rect placed to the right of the price
                btn_x = base_x + 420 + 20
                btn_y = base_y + i * 90 + 16
                btn_rect = pg.Rect(btn_x, btn_y, 48, 48)
                if btn_rect.collidepoint(input_manager.mouse_pos):
                    try:
                        if self.game_scene:
                            gs = self.game_scene
                            player_money = getattr(gs, 'money', 0)
                            if player_money >= it['price']:
                                gs.money = player_money - it['price']
                                # sync coin count into bag/backpack
                                try:
                                    self._sync_coins_with_bag()
                                except Exception:
                                    pass
                                # try to add to Bag if available, otherwise add to BackpackOverlay
                                bag = getattr(gs, 'bag', None)
                                added = False
                                try:
                                    if bag is not None:
                                        # prefer an API if present
                                        if hasattr(bag, 'add_item'):
                                            try:
                                                bag.add_item(it['key'], 1)
                                                added = True
                                            except Exception:
                                                added = False
                                        # fallback to internal _items_data if present
                                        if not added and hasattr(bag, '_items_data'):
                                            bag._items_data.append({'name': it.get('name'), 'key': it.get('key'), 'img': it.get('img'), 'count': 1})
                                            added = True
                                except Exception:
                                    added = False

                                # if Bag wasn't available/updated, update BackpackOverlay directly
                                try:
                                    if not added and hasattr(gs, 'backpack_overlay') and gs.backpack_overlay is not None:
                                        items_list = gs.backpack_overlay.get_items() or gs.backpack_overlay.items
                                        # try to find existing item by key or name
                                        found = False
                                        for bk in items_list:
                                            if ((bk.get('key') or '').lower() == (it.get('key') or '').lower()) or ((bk.get('name') or '').lower() == (it.get('name') or '').lower()):
                                                bk['count'] = int(bk.get('count', 0)) + 1
                                                found = True
                                                break
                                        if not found:
                                            try:
                                                items_list.append({'name': it.get('name'), 'key': it.get('key'), 'img': it.get('img'), 'count': 1})
                                            except Exception:
                                                pass
                                except Exception:
                                    pass

                                Logger.info(f"Bought {it['key']} for {it['price']}")
                            else:
                                Logger.info("Not enough money to buy")
                    except Exception:
                        pass

        # handle sell actions: clicking the same-position buttons will sell
        if self.tab == "sell" and input_manager.mouse_pressed(1):
            base_x = self.overlay_rect.x + 60
            base_y = self.overlay_rect.y + 120
            # collect monsters and items (exclude coins)
            monsters = []
            items = []
            try:
                if self.game_scene and hasattr(self.game_scene, 'backpack_overlay'):
                    monsters = self.game_scene.backpack_overlay.get_monsters() or []
                    items = [it for it in (self.game_scene.backpack_overlay.get_items() or []) if (it.get('name') or '').lower() not in ('coins','coin')]
            except Exception:
                monsters = []
                items = []

            # build price lookup for buy prices
            price_lookup = {}
            for si in self.items:
                if si.get('key'):
                    price_lookup[si.get('key').lower()] = si.get('price', 0)
                if si.get('name'):
                    price_lookup[si.get('name').lower()] = si.get('price', 0)

            # sell monsters: fixed price 100
            for i, m in enumerate(monsters):
                btn_x = base_x + 420 + 20
                btn_y = base_y + i * 90 + 16
                btn_rect = pg.Rect(btn_x, btn_y, 48, 48)
                if btn_rect.collidepoint(input_manager.mouse_pos):
                    try:
                        if self.game_scene:
                            gs = self.game_scene
                            # do not allow selling if this is the player's last monster
                            try:
                                if len(monsters) <= 1:
                                    # set hint text and expiry
                                    self.hint_text = '你只剩一個怪物了不能賣'
                                    self.hint_expire = pg.time.get_ticks() + self.hint_duration
                                    # do not perform sell
                                    continue
                            except Exception:
                                pass

                            gs.money = getattr(gs, 'money', 0) + 100
                            # sync coin count into bag/backpack
                            try:
                                self._sync_coins_with_bag()
                            except Exception:
                                pass
                            # remove the monster from backpack
                            try:
                                gs.backpack_overlay.monsters.pop(i)
                            except Exception:
                                pass
                            Logger.info(f"Sold monster {m.get('name')} for 100")
                    except Exception:
                        pass

            # sell items: price = half of buy price, decrement count and remove if zero
            start_idx = len(monsters)
            for j, it in enumerate(items):
                i = start_idx + j
                btn_x = base_x + 420 + 20
                btn_y = base_y + i * 90 + 16
                btn_rect = pg.Rect(btn_x, btn_y, 48, 48)
                if btn_rect.collidepoint(input_manager.mouse_pos):
                    try:
                        it_name = (it.get('name') or '').lower()
                        buy_p = price_lookup.get(it_name, None)
                        sell_p = int(buy_p / 2) if buy_p is not None else 0
                        if self.game_scene:
                            gs = self.game_scene
                            gs.money = getattr(gs, 'money', 0) + sell_p
                            # sync coin count into bag/backpack
                            try:
                                self._sync_coins_with_bag()
                            except Exception:
                                pass
                            # find and decrement in backpack items
                            try:
                                for bk in gs.backpack_overlay.items:
                                    if (bk.get('name') or '').lower() == it_name:
                                        bk['count'] = max(0, int(bk.get('count', 0)) - 1)
                                        if bk['count'] <= 0:
                                            try:
                                                gs.backpack_overlay.items.remove(bk)
                                            except Exception:
                                                pass
                                        break
                            except Exception:
                                pass
                            Logger.info(f"Sold item {it.get('name')} for {sell_p}")
                    except Exception:
                        pass

        # sell functionality removed per request

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
