import pygame as pg
from src.utils import load_sound, GameSettings

class SoundManager:
    def __init__(self):
        pg.mixer.init()
        pg.mixer.set_num_channels(GameSettings.MAX_CHANNELS)
        self.current_bgm = None
        self.volume = GameSettings.AUDIO_VOLUME#額外加的
        
    def play_bgm(self, filepath: str):
        if self.current_bgm:
            self.current_bgm.stop()
        audio = load_sound(filepath)
        audio.set_volume(GameSettings.AUDIO_VOLUME)
        audio.play(-1)
        self.current_bgm = audio
        
    def pause_all(self):
        pg.mixer.pause()

    def resume_all(self):
        pg.mixer.unpause()
        
    def play_sound(self, filepath, volume=0.7):
        sound = load_sound(filepath)
        sound.set_volume(volume)
        sound.play()

    def stop_all_sounds(self):
        pg.mixer.stop()
        self.current_bgm = None
    #額外加的 調整音量
    def set_volume(self, v: float):
        """Set global audio volume (0.0-1.0) and apply to current BGM."""
        v = max(0.0, min(1.0, v))
        self.volume = v
        GameSettings.AUDIO_VOLUME = v
        if self.current_bgm:
            try:
                self.current_bgm.set_volume(v)
            except Exception:
                pass
    #額外加的 調整音量