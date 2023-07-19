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

# reset rate of fire for aleins
# reset laser rate to 400

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
        self.rate_of_fire = 0.0001

        # enumerate() provides an index number for each list item
        alien_types = enumerate(["3", "3", "2", "2", "1"])

        self.aliens = [
            Alien(x, y + i * 60, alien_type, self)
            for i, alien_type in alien_types
        ]

        print(self.rate_of_fire)

    def increase_rate_of_fire(self):
        self.rate_of_fire *= 1.5

    def shoot(self):
        if random() < self.rate_of_fire and len(self.aliens) > 0:
            # get position of bottom-most alien
            x,y = self.aliens[0].position
            return AlienShoot(x, y - 50)
        else:
            return None

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
        self.speed = Vector2(10, 0) # how big the step is

        # swarm moves once per second, so accumulate the
        # delta_times until it reaches 1
        self.elapsed = 0.0
        self.period = 1.0 # how often the step is made

        self.aliens_left = 50

    def increase_difficulty(self):
        self.period -= 0.3 # question for HW - Where do you call this function

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

        # Every frame, the number of aliens in the game are counted and put in self.aliens_left
        count = 0
        for alien in self:
            count += 1
        self.aliens_left = count

        #print(self.period) # prints period for increase swarm movement difficulty




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

        is_firing = keyboard[key.SPACE]
        if PlayerShoot.ACTIVE_SHOOT is None and is_firing:
            self.parent.add(PlayerShoot(self.x,self.y + 50))
            shoot_sfx.play() # plays sound effect

class PlayerShoot(Actor):
    ACTIVE_SHOOT = None

    def __init__(self, x, y):
        super().__init__("img/laser.png", x, y)

        self.speed = Vector2(0, 2000)
        PlayerShoot.ACTIVE_SHOOT = self

    def collide(self,other):
        if isinstance(other,Alien):
            self.parent.update_score(other.points)
            other.kill()
            self.kill()

    def on_exit(self):
        super().on_exit()
        PlayerShoot.ACTIVE_SHOOT = None

    def update(self, delta_time):
        self.move(self.speed * delta_time)

class AlienShoot(Actor):
    def __init__(self, x, y):
        super().__init__("img/shoot.png", x, y)
        self.speed = Vector2(0, -400)

    def update(self, delta_time):
        self.move(self.speed * delta_time)

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

    def winning(self): # winning condition: if no aliens left in Swarm, then stop the game and say "You Win!)
        if self.swarm.aliens_left == 0:
            self.unschedule(self.game_loop)
            self.hud.show_game_over("You Win!")

    def respawn_player(self):
        self.lives -= 1
        if self.lives <0:
            self.unschedule(self.game_loop)
            self.hud.show_game_over("Game Over")
        else:
            self.create_player()

    def collide(self, actor):
        if actor is not None:
            for other in self.collman.iter_colliding(actor):
                actor.collide(other)
                return True
        return False


    def create_player(self):
        self.player = PlayerCannon(self.width * 0.5, 50)
        self.add(self.player)
        self.hud.update_lives(self.lives)

    def update_score(self, points=0):

        # if score before kill is less than 150 and score + points acquired is greater than 150, then increase difficulty
        if self.score < 150 and self.score + points >= 150:
            self.score += points
            self.swarm.increase_difficulty()
        elif self.score < 300 and self.score + points >= 300:
            self.score += points
            self.swarm.increase_difficulty()
        elif self.score < 450 and self.score + points >= 450:
            self.score += points
            self.swarm.increase_difficulty()
        else:
            self.score += points


        self.hud.update_score(self.score)

    def create_swarm(self, x, y):
        self.swarm = Swarm(x, y)
        for alien in self.swarm:
            self.add(alien)

    def game_loop(self,delta_time):

        self.winning() # call winning

        self.collman.clear()
        for _,actor in self.children:
            self.collman.add(actor)
            if not self.collman.knows(actor):
                self.remove(actor)

        if self.collide(PlayerShoot.ACTIVE_SHOOT): # if we hit something
            kill_sfx.play()

        if self.collide(self.player):
            self.respawn_player()
            die_sfx.play()

        for column in self.swarm.columns:
            shoot = column.shoot()
            if shoot is not None:
                self.add(shoot)

        for _,actor in self.children:
            actor.update(delta_time)

        self.swarm.update(delta_time)

        #print(self.swarm.aliens_left) # prints number of aliens left

if __name__ == "__main__":
    # song = mload("sfx/level1.ogg")
    # player = song.play()
    # player.loop = True

    shoot_sfx = mload("sfx/shoot.wav",streaming=False)
    kill_sfx = mload("sfx/invaderkilled.wav",streaming=False)
    die_sfx = mload("sfx/explosion.wav",streaming=False)


    director.init(caption="Space Invaders", width=800, height=650)

    keyboard = key.KeyStateHandler()

    director.window.push_handlers(keyboard)

    main_scene = Scene()
    hud_layer = HUD()

    main_scene.add(hud_layer, z=1)

    game_layer = GameLayer(hud_layer)

    main_scene.add(game_layer, z=0)

    director.run(main_scene)
