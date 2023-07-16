from cocos.sprite import Sprite
from cocos.euclid import Vector2
from cocos.collision_model import CollisionManagerGrid, AARectShape
from cocos.layer import Layer
from cocos.director import director
from cocos.scene import Scene
from cocos.text import Label
from pyglet.window import key
from pyglet.image import load as iload, ImageGrid, Animation
from pyglet.media import load as mload
from random import random

# 1:52:32

def load_animation(image):
    seq = ImageGrid(iload(image),2,1)
    return Animation.from_image_sequence(seq,0.5)

TYPES = {
    "1": (load_animation("img/alien1.png"),40),
    "2": (load_animation("img/alien2.png"),20),
    "3": (load_animation("img/alien3.png"),10)
         }

class Actor(Sprite):
    def __init__(self, image, x, y):
        super().__init__(image)

        pos = Vector2(x, y)
        self.position = pos

        self.cshape = AARectShape(pos, self.width * 0.5, self.height * 0.5)

    def move(self, offset):
        self.position += offset
        self.cshape.center += offset

    def update(self, delta_time):
        pass

    def collide(self, other):
        pass

class Alien(Actor):
    def __init__(self, x, y, alien_type, column=None):
        # get the tuple from the dictionary and unpack it
        animation, points = TYPES[alien_type]
        # call Actor constructor with image and coordinates
        super().__init__(animation, x, y)
        # different aliens are worth different points
        self.points = points
        # aliens know which AlienColumn they belong to
        self.column = column

    def on_exit(self):
        # call the original on_exit method in CocosNode
        super().on_exit()

        # if an alien's column is set, remove it from the column
        if self.column:
            self.column.remove(self)


# a column creates and contains its Aliens
class AlienColumn:
    def __init__(self, x, y):
        # enumerate() provides an index number for each list item
        alien_types = enumerate(["3", "3", "2", "2", "1"])

        self.aliens = [
            Alien(x, y + i * 60, alien_type, self)
            for i, alien_type in alien_types
        ]

    # method to tell a column to remove an alien from itself
    def remove(self, alien):
        self.aliens.remove(alien)

    # method to ask the column if it's too close to the edge of
    # the screen and needs to change direction
    def should_turn(self, direction):
        # if all the aliens in the column have been destroyed,
        # its location doesn't matter
        if len(self.aliens) == 0:
            return False

        # get bottom-most alien
        alien = self.aliens[0]

        # get x coordinate and width of screen
        x, width = alien.x, alien.parent.width

        # direction of 1 means travelling right, -1 is left
        return x >= width - 50 and direction == 1 or \
               x <= 50 and direction == -1


# the Swarm contains all AlienColumns
class Swarm:
    # initialized with x and y of bottom alien in first column
    def __init__(self, x, y):
        # make 10 columns, 60 pixels apart, using list comprehension
        self.columns = [
            AlienColumn(x + i * 60, y)
            for i in range(10)
        ]
        # swarm initially moves to the right (direction 1)
        self.direction = 1
        # only has horizontal speed
        self.speed = Vector2(10, 0)

        # swarm moves once per second, so accumulate the
        # delta_times until it reaches 1
        self.elapsed = 0.0
        self.period = 1.0

    # return True/False whether any column is too close to edge of screen
    def side_reached(self):
        # execute the lambda (anonymous inline function), passing it each
        # AlienColumn, then test if any of the columns report True
        return any(map(lambda col: col.should_turn(self.direction), self.columns))

    # define an iterator that returns all the aliens in the swarm, one at a time
    # (much easier than writing nested loops over and over!)
    def __iter__(self):
        for column in self.columns:
            for alien in column.aliens:
                yield alien

    # called once per frame so the swarm can move all the aliens in its columns
    def update(self, delta_time):
        # accumulate the elapsed time
        self.elapsed += delta_time

        # if the elapsed time exceeds the movement period (1 second)
        while self.elapsed >= self.period:
            # deduct the period from the elapsed time
            self.elapsed -= self.period

            # multiply speed by direction to get +10 or -10 vector
            movement = self.direction * self.speed

            # test if it's time to change direction
            if self.side_reached():
                # reverse the sign of the direction (+/-1)
                self.direction *= -1
                # don't move left/right, move down instead
                movement = Vector2(0, -10)

            # use iterator to move each Alien (the Swarm itself is an iterator)
            for alien in self:
                alien.move(movement)

class PlayerCannon(Actor):
    def __init__(self, x, y):
        super().__init__("img/cannon.png", x ,y)
        self.speed = Vector2(200, 0)

    def collide(self, other):
        other.kill()
        self.kill()

    def update(self, delta_time):

        horizontal_movement = keyboard[key.RIGHT] - keyboard[key.LEFT]

        left_edge = self.width * 0.5
        right_edge = self.parent.width - left_edge

        if left_edge <= self.x <= right_edge:
            self.move(self.speed * horizontal_movement * delta_time)

        if left_edge > self.x or right_edge < self.x: # fixes bug that makes cannon stick to either side of the screen
            self.move(self.speed * horizontal_movement * delta_time * -1)

class HUD(Layer):
    def __init__(self):
        super().__init__()

        w, h = director.get_window_size()
        self.score_text = Label("", font_size=18)
        self.score_text.position = (20, h - 40)

        self.lives_text = Label("", font_size=18)
        self.lives_text.position = (w - 100, h - 40)

        self.add(self.score_text)
        self.add(self.lives_text)

    def update_score(self, score):
        self.score_text.element.text = "Score: {}".format(score)

    def update_lives(self, lives):
        self.lives_text.element.text = "Lives: {}".format(lives)

    def show_game_over(self, message):
        w, h = director.get_window_size()
        game_over_text = Label(message, font_size=50, anchor_x="center", anchor_y="center")
        game_over_text.position = (w * 0.5, h * 0.5)
        self.add(game_over_text)


class GameLayer(Layer):
    def __init__(self, hud):
        super().__init__()
        self.hud = hud

        w, h = director.get_window_size()
        self.width = w
        self.height = h

        self.lives = 3
        self.score = 0

        cell = 1.25 * 50
        self.collman = CollisionManagerGrid(0, w, 0, h, cell, cell)

        self.update_score()
        self.create_player()

        self.create_swarm(100, 300)

        self.schedule(self.game_loop)


    def create_player(self):
        self.player = PlayerCannon(self.width * 0.5, 50)
        self.add(self.player)
        self.hud.update_lives(self.lives)

    def update_score(self, points=0):
        self.score += points
        self.hud.update_score(self.score)

    def game_loop(self,delta_time):
        for _,actor in self.children:
            actor.update(delta_time)
        self.swarm.update(delta_time)

    def create_swarm(self, x, y):
        self.swarm = Swarm(x, y)
        for alien in self.swarm:
            self.add(alien)

if __name__ == "__main__":
    director.init(caption="Space Invaders", width=800, height=650)

    keyboard = key.KeyStateHandler()

    director.window.push_handlers(keyboard)

    main_scene = Scene()
    hud_layer = HUD()

    main_scene.add(hud_layer, z=1)

    game_layer = GameLayer(hud_layer)

    main_scene.add(game_layer, z=0)

    director.run(main_scene)