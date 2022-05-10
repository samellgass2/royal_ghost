"""Board to simulate gameplay"""

import pyglet as pg


class GameTile:
    def __init__(self, sprite = None):
        self.card = sprite

    def fill(self, sprite):
        self.card = sprite

    def empty(self):
        self.card = None



class GameCard:
    def __init__(self, location, name, health, dps, speed, target_policy, range, board, AoE):
        """Initialize card."""
        self.location = location
        self.name = name
        self.health = health
        self.dps = dps
        self.speed = speed
        self.target_policy = target_policy
        self.target = None
        self.range = range
        self.status = None
        self.board = board
        self.AoE = AoE

    def target_distance(self):
        return ((self.location[0] - self.target.location[0]) ** 2 + (self.location[1] - self.target.location[1])) ** 0.5

    def move(self):
        """Move toward target ot nearest tower."""
        if self.target:
            # move toward target
            return
        else:
            # move toward closest crown tower
            return

    def attack(self, target):
        """Attack a given target once in range."""
        self.target.take_damage(self.dps)

    def take_damage(self, damage):
        """Take damage from any source."""
        if damage > self.health:
            self.health = 0
            self.die()
        else:
            self.health -= damage

    def die(self):
        self.board.kill(self)


    def find_target(self):
        self.board.target(self, self.target_policy)

    def action(self):
        """Take action in {attack, move}"""
        # TODO: look at implementations of status like zap, etc.
        if self.status:
            return
        if self.target and self.target_distance() < self.range:
            self.attack(self.target)
        else:
            self.find_target()
            self.move()

class SpellCard(GameCard):
    def __init__(self, location, name, health, dps, speed, board, AoE):
        super().__init__(location, name, health, dps, speed, None, None, board, AoE)




class GameBoard:
    def __init__(self, tile_size):
        green_img = pg.image.load("images/greensquare.png")
        green_square = pg.sprite.Sprite(green_img)
        green_square.scale_x = tile_size / green_img.width
        green_square.scale_y = (105 * tile_size) / (128 * green_img.height)
        green_square.opacity = 128
        self.green_square = green_square
        self.elixir_count = 0

        red_img = pg.image.load("images/redsquare.jpeg")
        red_square = pg.sprite.Sprite(red_img)
        red_square.scale_x = tile_size / red_img.width
        red_square.scale_y = (105 * tile_size) / (128 * red_img.height)
        red_square.opacity = 128
        self.red_square = red_square

        elixir_img = pg.image.load("images/elixir_bar.jpeg")
        elixir_bar = pg.sprite.Sprite(elixir_img)
        elixir_bar.scale_x = 1.5 * tile_size / elixir_img.width
        elixir_bar.scale_y = tile_size / elixir_img.height
        self.elixir_bar = elixir_bar


        self.height = 30
        self.width = 18
        self.board = []
        self.tile_size = tile_size
        self.xoffset = 0.1 * 600
        self.yoffset = 0.1 * 800
        self.tile_view = False
        for i in range(self.height):
            self.board.append([0 for i in range(self.width)])

        illegal_spaces = [(0,0), (1,0), (2,0), (3,0), (4,0), (5,0),
                          (12,0), (13,0), (14,0), (15,0), (16,0), (17,0),
                          (0, 29), (1, 29), (2, 29), (3, 29), (4, 29), (5, 29),
                          (12, 29), (13, 29), (14, 29), (15, 29), (16, 29), (17, 29)]

        friendly_towers = [(2,4), (3,4), (4,4), (2,5), (3,5), (4,5), (2,6), (3,6), (4,6),
                           (7,1), (8,1), (9, 1), (10, 1), (7, 2), (8, 2), (9, 2), (10,2), (7, 3), (8,3), (9, 3), (10, 3), (7,4), (8,4), (9,4), (10, 4),
                           (13, 4), (14, 4), (15, 4), (13, 5), (14, 5), (15, 5), (13, 6), (14, 6), (15,6)]

        river = [(x, 15) for x in range(self.width)]
        river.extend([(x, 14) for x in range(self.width)])
        river.remove((3, 14))
        river.remove((3, 15))
        river.remove((14, 14))
        river.remove((14, 15))

        enemy_towers = [(2, 23), (3, 23), (4, 23), (2, 24), (3, 24), (4, 24), (2, 25), (3, 25), (4, 25),
                        (7, 25), (8, 25), (9, 25), (10, 25), (7, 26), (8, 26), (9, 26), (10, 26), (7, 27), (8, 27), (9, 27), (10, 27), (7, 28), (8, 28), (9, 28), (10, 28),
                        (13, 23), (14, 23), (15, 23), (13, 24), (14, 24), (15, 24), (13, 25), (14, 25), (15, 25)]

        illegal_spaces.extend(friendly_towers)
        illegal_spaces.extend(river)
        illegal_spaces.extend(enemy_towers)
        self.enemy_towers = enemy_towers

        for space in illegal_spaces:
            self.board[space[1]][space[0]] = -1

    def in_bounds(self, x, y):
        return (x >= 0) and (x < self.width) and (y >= 0) and (y < self.height)

    def render_tiles(self):
        if self.tile_view:
            for y in range(self.height):
                for x in range(self.width):
                    screen_x, screen_y = self.xy_to_screen(x, y)
                    if self.board[y][x] >= 0:
                        self.green_square.x = screen_x
                        self.green_square.y = screen_y
                        self.green_square.draw()
                    else:
                        self.red_square.x = screen_x
                        self.red_square.y = screen_y
                        self.red_square.draw()




    def xy_to_screen(self, x, y):
        new_x = x * self.tile_size + self.xoffset
        new_y = (105 * y * self.tile_size) / 128 + self.yoffset
        return new_x, new_y

    def increment_elixir(self, dt=None):
        if self.elixir_count < 10:
            self.elixir_count += 1

    def render_elixir(self):
        start_x = self.xoffset
        self.elixir_bar.x = start_x
        start_y = self.yoffset/3
        self.elixir_bar.y = start_y
        for i in range(self.elixir_count):
            self.elixir_bar.draw()
            self.elixir_bar.x += self.elixir_bar.width

        count = pg.text.Label(str(self.elixir_count), font_name='Times New Roman', font_size=16,
                      x=start_x + 10 * self.elixir_bar.width, y=start_y, anchor_x='center', anchor_y='center')
        count.draw()

        if self.elixir_count == 10:
            full = pg.text.Label("FULL!", font_name='Times New Roman', font_size=16,
                                  x=start_x + 10 * self.elixir_bar.width, y=start_y/2, anchor_x='center',
                                  anchor_y='center')
            full.draw()







