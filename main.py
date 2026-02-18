import random

import arcade
from pyglet.graphics import Batch

SCREEN_WIDTH = 700
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Castle Camera"
TILE_SCALING = 1.0
TILE_SIZE = 70
SPEED = 4
CAMERA_LERP = 0.12
# Размеры мёртвой зоны камеры
DEAD_ZONE_W = int(SCREEN_WIDTH * 0.35)
DEAD_ZONE_H = int(SCREEN_HEIGHT * 0.45)


class StartView(arcade.View):
    def on_show(self):
        """Настройка начального экрана"""
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        """Отрисовка начального экрана"""
        self.clear()

        # Батч для текста
        self.batch = Batch()
        start_text = arcade.Text(
            "Заколдованный замок",
            self.window.width / 2, self.window.height / 2,
            arcade.color.WHITE,
            font_size=50,
            anchor_x="center",
            batch=self.batch
        )
        any_key_text = arcade.Text(
            "Any key to start",
            self.window.width / 2, self.window.height / 2 - 75,
            arcade.color.GRAY,
            font_size=20,
            anchor_x="center",
            batch=self.batch
        )

        self.batch.draw()

    def on_key_press(self, key, modifiers):
        """Начало игры при нажатии клавиши"""
        game_view = LevelFirst()
        game_view.setup()
        self.window.show_view(game_view)


class LevelFirst(arcade.View):
    def __init__(self):
        super().__init__()

        arcade.set_background_color(arcade.color.SKY_BLUE)
        # Камеры: мир и GUI
        self.world_camera = arcade.camera.Camera2D()
        self.gui_camera = arcade.camera.Camera2D()

        # Причина тряски — специальный объект ScreenShake2D
        self.camera_shake = arcade.camera.grips.ScreenShake2D(
            self.world_camera.view_data,
            max_amplitude=15.0,
            acceleration_duration=0.1,
            falloff_time=0.5,
            shake_frequency=10.0,
        )

        self.batch = Batch()

        self.on_key_press_set = set()
        self.explosion_sound = arcade.load_sound(":resources:sounds/explosion1.wav")
        self.gems_eaten = 0

        self.score_text = arcade.Text(
            'Score: 0',
            30,
            SCREEN_HEIGHT - 40,
            arcade.color.RED,
            font_size=32,
            batch=self.batch
        )

    def setup(self):
        """Настраиваем игру здесь. Вызывается при старте и при рестарте"""
        # ===== ВОЛШЕБСТВО ЗАГРУЗКИ КАРТЫ! (Почти без магии) =====
        # Грузим тайловую карту
        tile_map = arcade.load_tilemap('assets/tiled.tmx', scaling=TILE_SCALING)

        self.world_width = int(tile_map.width * tile_map.tile_width * TILE_SCALING)
        self.world_height = int(tile_map.height * tile_map.tile_height * TILE_SCALING)

        self.player_list = arcade.SpriteList()
        self.gemes_list = arcade.SpriteList()

        self.castle_list = tile_map.sprite_lists["castle"]
        self.windows_list = tile_map.sprite_lists["windows"]
        self.fence_list = tile_map.sprite_lists["fence"]
        self.stones_list = tile_map.sprite_lists["stones"]
        self.yard_list = tile_map.sprite_lists["yard"]
        self.collision_list = tile_map.sprite_lists['collision']

        self.player_sprite = arcade.Sprite(':resources:images/animated_characters/robot/robot_idle.png')
        self.player_sprite.center_x = SCREEN_WIDTH // 2
        self.player_sprite.center_y = SCREEN_HEIGHT // 4
        self.player_list.append(self.player_sprite)

        self.gem_num = random.randint(4, 7)

        for _ in range(self.gem_num):
            gem = arcade.Sprite(':resources:images/items/gemBlue.png', 0.5)
            gem.center_x = random.randint(1, 13) * TILE_SIZE
            gem.center_y = random.randint(1, 4) * TILE_SIZE
            self.gemes_list.append(gem)

        self.physics_engine = arcade.PhysicsEngineSimple(
            self.player_sprite, self.collision_list
        )

    def on_draw(self):
        """Отрисовка экрана"""
        self.clear()

        self.camera_shake.update_camera()
        self.world_camera.use()

        self.castle_list.draw()
        self.windows_list.draw()
        self.yard_list.draw()
        self.fence_list.draw()
        self.stones_list.draw()
        self.gemes_list.draw()
        self.player_list.draw()

        self.camera_shake.readjust_camera()

        self.gui_camera.use()
        self.batch.draw()

    def on_update(self, delta_time: float):
        self.camera_shake.update(delta_time)

        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0

        if arcade.key.LEFT in self.on_key_press_set:
            self.player_sprite.change_x = -SPEED
        if arcade.key.RIGHT in self.on_key_press_set:
            self.player_sprite.change_x = SPEED
        if arcade.key.DOWN in self.on_key_press_set:
            self.player_sprite.change_y = -SPEED
        if arcade.key.UP in self.on_key_press_set:
            self.player_sprite.change_y = SPEED

        self.player_sprite.center_x += self.player_sprite.change_x
        self.player_sprite.center_y += self.player_sprite.change_y

        self.physics_engine.update()

        player_and_gem_collision = arcade.check_for_collision_with_list(self.player_sprite, self.gemes_list)
        for gem in player_and_gem_collision:
            self.explosion_sound.play()
            self.camera_shake.start()
            self.gems_eaten += 1
            gem.remove_from_sprite_lists()

        # Камера: мёртвая зона + плавное следование
        cam_x, cam_y = self.world_camera.position

        dz_left = cam_x - DEAD_ZONE_W // 2
        dz_right = cam_x + DEAD_ZONE_W // 2

        dz_bottom = cam_y - DEAD_ZONE_H // 2
        dz_top = cam_y + DEAD_ZONE_H // 2

        px, py = self.player_sprite.center_x, self.player_sprite.center_y
        target_x, target_y = cam_x, cam_y

        if px < dz_left:
            target_x = px + DEAD_ZONE_W // 2
        elif px > dz_right:
            target_x = px - DEAD_ZONE_W // 2
        if py < dz_bottom:
            target_y = py + DEAD_ZONE_H // 2
        elif py > dz_top:
            target_y = py - DEAD_ZONE_H // 2

        # Не показываем «пустоту» за краями карты
        half_w = self.world_camera.viewport_width / 2
        half_h = self.world_camera.viewport_height / 2

        target_x = max(half_w, min(self.world_width - half_w, target_x))
        target_y = max(half_h, min(self.world_height - half_h, target_y))

        # Плавно к цели, аналог arcade.math.lerp_2d, но руками
        smooth_x = (1 - CAMERA_LERP) * cam_x + CAMERA_LERP * target_x
        smooth_y = (1 - CAMERA_LERP) * cam_y + CAMERA_LERP * target_y

        self.cam_target = (smooth_x, smooth_y)

        self.world_camera.position = (self.cam_target[0], self.cam_target[1])

        if self.gem_num == self.gems_eaten:
            game_view = LevelSecond()
            game_view.setup()
            self.window.show_view(game_view)

        self.score_text = arcade.Text(
            f'Score: {self.gems_eaten}',
            30,
            SCREEN_HEIGHT - 40,
            arcade.color.RED,
            font_size=32,
            batch=self.batch
        )

    def on_key_press(self, key, modifiers):
        self.on_key_press_set.add(key)

    def on_key_release(self, key, modifiers):
        if key in self.on_key_press_set:
            self.on_key_press_set.remove(key)


class LevelSecond(arcade.View):
    def __init__(self):
        super().__init__()

        arcade.set_background_color(arcade.color.SKY_BLUE)
        # Камеры: мир и GUI
        self.world_camera = arcade.camera.Camera2D()
        self.gui_camera = arcade.camera.Camera2D()

        # Причина тряски — специальный объект ScreenShake2D
        self.camera_shake = arcade.camera.grips.ScreenShake2D(
            self.world_camera.view_data,
            max_amplitude=15.0,
            acceleration_duration=0.1,
            falloff_time=0.5,
            shake_frequency=10.0,
        )

        self.batch = Batch()

        self.on_key_press_set = set()
        self.explosion_sound = arcade.load_sound(":resources:sounds/explosion1.wav")
        self.money_eaten = 0

        self.game_over = False

        self.score_text = arcade.Text(
            f'Score: 0',
            30,
            SCREEN_HEIGHT - 40,
            arcade.color.RED,
            font_size=32,
            batch=self.batch
        )

    def setup(self):
        """Настраиваем игру здесь. Вызывается при старте и при рестарте"""
        # ===== ВОЛШЕБСТВО ЗАГРУЗКИ КАРТЫ! (Почти без магии) =====
        # Грузим тайловую карту
        tile_map = arcade.load_tilemap('assets/tiled.tmx', scaling=TILE_SCALING)

        self.world_width = int(tile_map.width * tile_map.tile_width * TILE_SCALING)
        self.world_height = int(tile_map.height * tile_map.tile_height * TILE_SCALING)

        self.player_list = arcade.SpriteList()
        self.money_list = arcade.SpriteList()

        self.castle_list = tile_map.sprite_lists["castle"]
        self.windows_list = tile_map.sprite_lists["windows"]
        self.fence_list = tile_map.sprite_lists["fence"]
        self.stones_list = tile_map.sprite_lists["stones"]
        self.yard_list = tile_map.sprite_lists["yard"]
        self.collision_list = tile_map.sprite_lists['collision']

        self.player_sprite = arcade.Sprite(':resources:images/animated_characters/robot/robot_idle.png')
        self.player_sprite.center_x = SCREEN_WIDTH // 2
        self.player_sprite.center_y = SCREEN_HEIGHT // 4
        self.player_list.append(self.player_sprite)

        self.money_num = random.randint(4, 7)

        for _ in range(self.money_num):
            money = arcade.Sprite(':resources:images/items/gold_1.png', 0.5)
            money.center_x = random.randint(1, 13) * TILE_SIZE
            money.center_y = random.randint(1, 4) * TILE_SIZE
            self.money_list.append(money)

        self.physics_engine = arcade.PhysicsEngineSimple(
            self.player_sprite, self.collision_list
        )

    def on_draw(self):
        """Отрисовка экрана"""
        self.clear()

        self.camera_shake.update_camera()
        self.world_camera.use()

        self.castle_list.draw()
        self.windows_list.draw()
        self.yard_list.draw()
        self.fence_list.draw()
        self.stones_list.draw()
        self.money_list.draw()
        self.player_list.draw()

        self.camera_shake.readjust_camera()

        self.gui_camera.use()
        self.batch.draw()

    def on_update(self, delta_time: float):
        self.camera_shake.update(delta_time)

        if self.game_over:
            return

        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0

        if arcade.key.LEFT in self.on_key_press_set:
            self.player_sprite.change_x = -SPEED
        if arcade.key.RIGHT in self.on_key_press_set:
            self.player_sprite.change_x = SPEED
        if arcade.key.DOWN in self.on_key_press_set:
            self.player_sprite.change_y = -SPEED
        if arcade.key.UP in self.on_key_press_set:
            self.player_sprite.change_y = SPEED

        self.player_sprite.center_x += self.player_sprite.change_x
        self.player_sprite.center_y += self.player_sprite.change_y

        self.physics_engine.update()

        player_and_money_collision = arcade.check_for_collision_with_list(self.player_sprite, self.money_list)
        for money in player_and_money_collision:
            self.explosion_sound.play()
            self.camera_shake.start()
            self.money_eaten += 1
            money.remove_from_sprite_lists()

        # Камера: мёртвая зона + плавное следование
        cam_x, cam_y = self.world_camera.position

        dz_left = cam_x - DEAD_ZONE_W // 2
        dz_right = cam_x + DEAD_ZONE_W // 2

        dz_bottom = cam_y - DEAD_ZONE_H // 2
        dz_top = cam_y + DEAD_ZONE_H // 2

        px, py = self.player_sprite.center_x, self.player_sprite.center_y
        target_x, target_y = cam_x, cam_y

        if px < dz_left:
            target_x = px + DEAD_ZONE_W // 2
        elif px > dz_right:
            target_x = px - DEAD_ZONE_W // 2
        if py < dz_bottom:
            target_y = py + DEAD_ZONE_H // 2
        elif py > dz_top:
            target_y = py - DEAD_ZONE_H // 2

        # Не показываем «пустоту» за краями карты
        half_w = self.world_camera.viewport_width / 2
        half_h = self.world_camera.viewport_height / 2

        target_x = max(half_w, min(self.world_width - half_w, target_x))
        target_y = max(half_h, min(self.world_height - half_h, target_y))

        # Плавно к цели, аналог arcade.math.lerp_2d, но руками
        smooth_x = (1 - CAMERA_LERP) * cam_x + CAMERA_LERP * target_x
        smooth_y = (1 - CAMERA_LERP) * cam_y + CAMERA_LERP * target_y

        self.cam_target = (smooth_x, smooth_y)

        self.world_camera.position = (self.cam_target[0], self.cam_target[1])

        if self.money_num == self.money_eaten:
            self.game_over = True

            self.text_win = arcade.Text(
                text='WIN!!!',
                x=SCREEN_WIDTH / 2,
                y=SCREEN_HEIGHT / 2,
                color=arcade.color.RED,
                font_size=64,
                anchor_x="center",
                anchor_y="center",
                batch=self.batch
            )

        self.score_text = arcade.Text(
            f'Score: {self.money_eaten}',
            30,
            SCREEN_HEIGHT - 40,
            arcade.color.RED,
            font_size=32,
            batch=self.batch
        )

    def on_key_press(self, key, modifiers):
        self.on_key_press_set.add(key)

    def on_key_release(self, key, modifiers):
        if key in self.on_key_press_set:
            self.on_key_press_set.remove(key)


def main():
    """Главная функция."""
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    start_screen = StartView()
    window.show_view(start_screen)

    arcade.run()


if __name__ == "__main__":
    main()