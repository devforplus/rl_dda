from enum import Enum, auto

import pyxel as px

from config.stage.stage_num import FINAL_STAGE
from config.music import special_music_files, stage_music_mapping
from components.player import Player
from components.sprite import (
    sprites_update,
    sprites_draw,
    sprite_lists_collide,
    sprite_collide_list,
)
from hud import Hud
from explosion import Explosion
from powerup import Powerup
from stage_background import StageBackground
import input as input
from audio import AudioManager

# 오디오 매니저 인스턴스 생성
audio_manager = AudioManager()

class State(Enum):
    """스테이지 상태 열거형."""

    PLAYER_SPAWNED = 0
    PLAY = auto()
    PLAYER_DEAD = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    STAGE_CLEAR = auto()


# 플레이어 스폰 시간 (프레임 단위)
PLAYER_SPAWN_IN_FRAMES = 30
# 스테이지 클리어 후 대기 시간 (프레임 단위)
STAGE_CLEAR_FRAMES = 180


class GameStateStage:
    def __init__(self, game) -> None:
        """
        스테이지 상태 초기화.

        플레이어, 적, 배경 등을 초기화합니다.
        """
        self.game = game
        self.state = State.PLAYER_SPAWNED
        self.input = game.app.input
        self.font = game.app.main_font

        # 상태 관련 타이머 초기화
        self.state_time = 0

        # 플레이어 및 관련 객체 초기화
        self.player = Player(self)
        self.player_shots = []

        # 적 및 관련 객체 초기화
        self.enemies = []
        self.enemy_shots = []
        self.bosses = []

        # 폭발 효과 리스트 초기화
        self.explosions = []

        # 파워업 리스트 초기화 및 사이클 리셋
        self.powerups = []
        Powerup.reset_cycle()

        # 배경 초기화
        self.background = StageBackground(
            self,
            f"stage_{game.game_vars.stage_num}.tmx",
            self.game.game_vars.is_vortex_stage(),
        )

        # HUD 초기화
        self.hud = Hud(game.game_vars, self.font)

        # 스테이지 클리어 체크 플래그 초기화
        self.check_stage_clear = False

        # 음악 로드 및 재생
        self.music = audio_manager.load_music(stage_music_mapping[self.game.game_vars.stage_num])
        audio_manager.play_music(self.music, num_channels=3)

    def on_exit(self):
        """스테이지 상태 종료 시 처리."""
        audio_manager.stop_music()

    def end_of_vortex_stage(self):
        if self.state == State.PLAY:
            self.check_stage_clear = True

    def stage_clear_init(self):
        self.enemy_shots.clear()
        for e in self.enemies:
            e.destroy()
        self.switch_state(State.STAGE_CLEAR)
        if self.game.game_vars.stage_num < FINAL_STAGE:
            self.music = audio_manager.load_music(special_music_files["stage_clear"])
            audio_manager.play_music(self.music, False, num_channels=3, theTick=620)
        else:
            audio_manager.stop_music()

    def respawn_player(self):
        self.player = Player(self)

    def get_scroll_x_speed(self):
        return self.background.scroll_x_speed

    def add_enemy(self, e):
        self.enemies.append(e)
        # print(f"Added enemy type {e.type} at {e.x//8},{e.y//8}")

    def add_boss(self, b):
        self.bosses.append(b)

    def add_powerup(self, p):
        self.powerups.append(p)

    def add_explosion(self, x, y, delay):
        self.explosions.append(Explosion(self, x, y, delay))

    def trigger_bomb(self):
        self.enemy_shots.clear()
        for e in self.enemies:
            e.hit_with_bomb()
        for b in self.bosses:
            b.hit_with_bomb()

    def add_score(self, amount):
        self.game.game_vars.add_score(amount)

    # Doesnt include bosses.
    def get_num_enemies(self):
        return len(self.enemies)

    def add_player_shot(self, s):
        self.player_shots.append(s)

    def add_enemy_shot(self, s):
        self.enemy_shots.append(s)

    def update_play(self):
        """게임 플레이 상태를 업데이트합니다."""
        self.player.update()

        # I 키를 눌렀을 때 무적모드 토글
        if self.input.has_tapped(input.INVINCIBLE):
            self.player.toggle_invincibility()
            
        # C 키를 눌렀을 때 데이터 수집 토글 -> App.update()에서 이미 처리하므로 여기서는 제거
        # if self.input.has_tapped(input.COLLECT_DATA):
        #     if hasattr(self.game, 'app') and hasattr(self.game.app, 'toggle_data_collection'):
        #         self.game.app.toggle_data_collection()
        #     else:
        #         print("[GAME_STATE_STAGE_ERROR] Cannot find app.toggle_data_collection")

    def switch_state(self, new):
        self.state = new
        self.state_time = 0
        # print(f"Switched stage state to {self.state}")

    def update_player_dead(self):
        if len(self.explosions) == 0:
            if self.game.game_vars.lives > 0:
                self.respawn_player()
                self.switch_state(State.PLAYER_SPAWNED)
            else:
                self.switch_state(State.GAME_OVER)
                self.music = audio_manager.load_music(special_music_files["game_over"])
                audio_manager.play_music(self.music, False, num_channels=3)

    def play_boss_music(self):
        self.music = audio_manager.load_music(special_music_files["boss"])
        audio_manager.play_music(self.music, True, num_channels=3)

    def update_game_over(self):
        print("[GAME_PY_DEBUG] Game over, restarting game automatically.")
        self.game.restart_game()

    def update_player_spawned(self):
        self.player.update_spawned()
        if self.state_time == PLAYER_SPAWN_IN_FRAMES:
            self.switch_state(State.PLAY)

    def update_stage_clear(self):
        if self.state_time >= STAGE_CLEAR_FRAMES and not audio_manager.is_music_playing():
            self.game.go_to_next_stage()

    def update(self):
        """스테이지 상태 업데이트."""
        self.state_time += 1

        if self.state == State.PLAYER_SPAWNED:
            self.update_player_spawned()
        elif self.state == State.PLAY:
            if self.input.has_tapped(input.BUTTON_2):
                self.switch_state(State.PAUSED)
                return
            self.update_play()
        elif self.state == State.PLAYER_DEAD:
            self.update_player_dead()
        elif self.state == State.PAUSED:
            if self.input.has_tapped(input.BUTTON_2):
                self.switch_state(State.PLAY)
            else:
                return
        elif self.state == State.GAME_OVER:
            self.update_game_over()
            return
        elif self.state == State.STAGE_CLEAR:
            self.update_stage_clear()

        self.background.update()

        sprites_update(self.powerups)
        sprites_update(self.player_shots)
        sprites_update(self.enemies)
        sprites_update(self.bosses)
        sprites_update(self.enemy_shots)

        if self.check_stage_clear:
            self.check_stage_clear = False
            if len(self.bosses) == 0:
                self.stage_clear_init()

        sprite_lists_collide(self.player_shots, self.enemies)
        sprite_lists_collide(self.player_shots, self.bosses)
        sprite_collide_list(self.player, self.powerups)
        sprite_collide_list(self.player, self.enemy_shots)
        sprite_collide_list(self.player, self.enemies)
        sprite_collide_list(self.player, self.bosses)

        sprites_update(self.explosions)

        if self.state == State.PLAY and self.player.remove:
            self.switch_state(State.PLAYER_DEAD)
            self.player_shots.clear()

    def draw(self):
        """스테이지 상태 그리기."""
        self.background.draw()

        if self.state != State.PLAYER_DEAD and self.state != State.GAME_OVER:
            self.player.draw()

        sprites_draw(self.powerups)
        sprites_draw(self.player_shots)
        sprites_draw(self.enemies)
        sprites_draw(self.bosses)
        sprites_draw(self.explosions)
        sprites_draw(self.enemy_shots)

        self.hud.draw()

        if self.state == State.PAUSED:
            self.font.draw_text(104, 88, "PAUSED")
        elif self.state == State.GAME_OVER:
            self.font.draw_text(96, 88, "GAME OVER")
        elif self.state == State.STAGE_CLEAR:
            if self.game.game_vars.stage_num != FINAL_STAGE:
                if self.state_time > 60:
                    if self.game.game_vars.is_vortex_stage():
                        self.font.draw_text(80, 88, "LEAVING VORTEX")
                    else:
                        self.font.draw_text(80, 88, "ENTERING VORTEX")
