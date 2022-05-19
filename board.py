"""Board to simulate gameplay"""

import pyglet as pg
import numpy as np
import random


class GameTile:
    """Defunct."""
    def __init__(self, sprite = None):
        self.card = sprite

    def fill(self, sprite):
        self.card = sprite

    def empty(self):
        self.card = None



class GameCard:
    """A troop card superclass to specify default actions."""
    def __init__(self, cost, location, name, health, dps, speed, target_policy, range, board, AoE, LegalDeployments, flying, building, units, is_evil=False):
        """Initialize card."""
        self.location = location
        self.name = name
        self.health = health
        self.maxhealth = health
        self.units = units
        self.dps = dps
        self.speed = speed
        self.target_policy = target_policy
        self.target = None
        self.range = range
        self.status = False
        self.board = board
        self.AoE = AoE
        self.LegalDeployments = LegalDeployments
        self.is_flying = flying
        self.is_building = building
        self.cost = cost
        self.is_evil = is_evil
        self.epsilon = 0.15

    def target_distance(self, x = None, y = None):
        """Returns euclidean distance from (x,y) to self.target."""
        if x is None and y is None:
            x,y = self.location
        if not self.target:
            return 0
        return ((x - self.target.location[0]) ** 2 + (y - self.target.location[1])**2) ** 0.5

    def move(self):
        """Move toward target or nearest tower, or randomly w.p. self.epsilon."""
        if self.target:
            # Choose a random legal move with probability epsilon
            actions_and_dists = self.get_legal_actions_and_dists()
            best_action = min(actions_and_dists, key = lambda a_and_d : a_and_d[1])[0]

            if random.random() <= self.epsilon:
                best_action = actions_and_dists[np.random.randint(len(actions_and_dists))][0]
            if best_action == 'left':
                self.move_left()
            elif best_action == 'right':
                self.move_right()
            elif best_action == 'up':
                self.move_up()
            elif best_action == 'down':
                self.move_down()
            # If no valid action, do nothing
            else:
                return
        # If no clear direction to move, find target.
        else:
            self.find_target()

    def can_move(self, x, y):
        """Boolean if moving to (x,y) would be legal."""
        all_cards = self.board.live_troops.copy()
        all_cards.extend(self.board.live_evil_troops)
        occupied = [card.location for card in all_cards]

        # Staying still should always be legal
        if (x,y) == self.location:
            return True
        return self.board.in_bounds(x, y) and ((x,y) not in self.board.illegal_spaces) and ((x,y) not in occupied)

    def get_legal_actions_and_dists(self):
        """Returns all legal actions as (action, dist to target)."""
        actions = []
        x,y = self.location
        if self.can_move(x-1, y):
            actions.append(('left', self.target_distance(x-1, y)))
        if self.can_move(x+1, y):
            actions.append(('right', self.target_distance(x+1, y)))
        if self.can_move(x, y-1):
            actions.append(('down', self.target_distance(x, y-1)))
        if self.can_move(x, y+1):
            actions.append(('up', self.target_distance(x, y+1)))
        if len(actions) < 1:
            actions = [(None, 100)]
        return actions

    def get_all_locations(self, y=30):
        """Returns a list of all locations on the board."""
        locs = []
        for i in range(18):
            for j in range(y):
                locs.append((i,j))
        return locs


    def move_left(self):
        """Moves card left."""
        x,y = self.location
        self.location = (x - 1, y)

    def move_right(self):
        """Moves card right."""
        x, y = self.location
        self.location = (x + 1, y)

    def move_up(self):
        """Moves card up."""
        x, y = self.location
        self.location = (x, y + 1)

    def move_down(self):
        """Moves card down."""
        x, y = self.location
        self.location = (x, y - 1)

    def attack(self):
        """Attack a given target once in range, handle killing and scoring."""
        will_die = ((self.target.units - 1) * self.target.maxhealth + self.target.health) < (self.dps * self.units)
        self.target.take_damage(self.dps * self.units)
        print(self.name, " attacks", self.target.name, "for ", self.dps * self.units, "damage!")
        if will_die:
            print(self.name, "has killed", self.target.name, "!")
            self.target = None
        if self.is_evil:
            self.board.evil_troop_damage += (self.dps * self.units)
        else:
            self.board.troop_damage += (self.dps * self.units)


    def take_damage(self, damage):
        """Take damage from any source, handles dying."""
        if damage > self.health:
            overkill = damage - self.health
            self.units -= 1
            if self.units > 0:
                self.health = self.maxhealth - overkill
            else:
                self.die()
        else:
            self.health -= damage

    def die(self):
        """Die, or add self to board's garbage pile."""
        self.board.dead.append(self)


    def find_target(self):
        """Allow self.board to specify the nearest target given self's policy."""
        self.target = self.board.target(self, self.target_policy)

    def action(self):
        """Take action in {attack, move}, main loop for troop action in a given turn."""
        # TODO: implement speed as something of consequence
        # for _ in range(self.speed):
        # If affected by status (zap), take a turn off and retarget..
        if self.status:
            self.status = False
            self.find_target()
        elif self.target and self.target_distance() < self.range+1:
            self.attack()
        else:
            self.find_target()
            self.move()



class SpellCard(GameCard):
    """A gamecard with no health to be deployed anywhere."""
    def __init__(self, cost, location, name, health, dps, speed, board, AoE, is_evil=False):
        all_locations = self.get_all_locations()
        super().__init__(cost, location, name, health, dps, speed, 'all', 5, board, AoE, all_locations, flying=False, building=False, units=1, is_evil=is_evil)

    def action(self):
        """Spell action: damage all targets within range when deployed, then die."""
        if self.is_evil:
            targets = self.board.live_troops
        else:
            targets = self.board.live_evil_troops
        for target in targets:
            if self.target_distance(target.location[0], target.location[1]) < self.range:
                self.attack_target(target)
                # Allow for zap / fireball knockback effect: -1 turn
                target.status = True
        self.die()

    def attack_target(self, target):
        """Attack all targets within spell range, handle killing and scoring."""
        will_die = ((target.units - 1) * target.maxhealth + target.health) < (self.dps * self.units)
        target.take_damage(self.dps * self.units)
        print(self.name, " attacks", target.name, "for ", self.dps * self.units, "damage!")
        if will_die:
            print(self.name, "has killed", target.name, "!")
            self.target = None
        if self.is_evil:
            self.board.evil_troop_damage += (self.dps * self.units)
        else:
            self.board.troop_damage += (self.dps * self.units)

    def target_distance(self, x = None, y = None):
        """euclidean distance from self to (x,y) to see if troops are in range."""
        if not x and not y:
            return 0
        return ((self.location[0] - x) ** 2 + (self.location[1] - y)**2) ** 0.5




class TroopCard(GameCard):
    """A generic GameCard for ground troops."""
    def __init__(self, cost, location, name, health, dps, speed, target_policy, range, board, AoE, units, is_evil=False):
        all_locations = self.get_all_locations(15)
        for loc in board.illegal_spaces:
            if loc in all_locations:
                all_locations.remove(loc)

        super().__init__(cost, location, name, health, dps, speed, target_policy, range, board, AoE, all_locations, flying=False, building=False, units=units, is_evil=is_evil)


class AirCard(GameCard):
    """A generic GameCard for flying troops."""
    def __init__(self, cost, location, name, health, dps, speed, target_policy, range, board, AoE, units, is_evil=False):
        all_locations = self.get_all_locations(15)
        for loc in board.illegal_spaces:
            if loc in all_locations:
                all_locations.remove(loc)
        super().__init__(cost, location, name, health, dps, speed, target_policy, range, board, AoE, all_locations, flying=True, units=units, building=False, is_evil=is_evil)

class Barbarians(TroopCard):
    """The barbarian unit card (troopcard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(5, location, 'barbarians', health=670, dps=137, speed=1, target_policy='ground', range=1, board=board, AoE=1, units=5, is_evil=is_evil)


class Zap(SpellCard):
    """The zap unit card (spellcard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(2, location, 'zap', 0, 192, 0, board, 2.5, is_evil=is_evil)


class MiniPekka(TroopCard):
    """The mini pekka unit card (troopcard)"""
    def __init__(self, location, board, is_evil=False):
        super().__init__(4, location, 'mini pekka', 1361, 450, 2, 'ground', 1, board, 1, 1, is_evil=is_evil)


class HogRider(TroopCard):
    """The hog rider unit card (troopcard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(4, location, "hog rider", 1696, 198, 3, 'buildings', 1, board, 1, 1, is_evil=is_evil)


class Goblins(TroopCard):
    """The goblins unit card (troopcard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(2, location, "goblins", 202, 109, 2, "ground", 1, board, 1, 3, is_evil=is_evil)


class Bomber(TroopCard):
    """The bomber unit card (troopcard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(2, location, 'bomber', 332, 123, 1, 'ground', 4.5, board, 1.5, 1, is_evil=is_evil)


class Archers(TroopCard):
    """The archers unit card (troopcard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(3, location, "archers", 304, 97, 1, 'all', 5, board, 1, 2, is_evil=is_evil)


class BabyDragon(AirCard):
    """The baby dragon unit card (aircard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(4, location, "baby dragon", 1152, 106, 1, 'all', 3.5, board, 2, 1, is_evil=is_evil)


class PrincessTower(GameCard):
    """The princess tower building card (gamecard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(0, location, 'princess tower', 3052, 136, 0, 'all', 7.5, board, 1, None,
                         False, units=1, building=True, is_evil=is_evil)

    def move(self):
        return

class KingTower(GameCard):
    """The king tower building card (gamecard)."""
    def __init__(self, location, board, is_evil=False):
        super().__init__(0, location, 'king tower', 4824, 109, 0, 'all', 7.5, board, 1, None,
                         False, units=1, building=True, is_evil=is_evil)

    def move(self):
        return

class GameBoard:
    """The abstraction to handle all units, updates, scoring, and dispatching troop actions."""
    def __init__(self, tile_size, deck):
        ########## GRAPHICS ##########
        green_img = pg.image.load("images/greensquare.png")
        green_square = pg.sprite.Sprite(green_img)
        green_square.scale_x = tile_size / green_img.width
        green_square.scale_y = (105 * tile_size) / (128 * green_img.height)
        green_square.opacity = 128
        self.green_square = green_square
        self.elixir_count = 0
        self.evil_elixir_count = 0
        self.verbose_mode = True

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

        barbs_img = pg.image.load("images/barbarians.png")
        barbarians = pg.sprite.Sprite(barbs_img)
        barbarians.scale_x = 1.5 * tile_size / barbs_img.width
        barbarians.scale_y = 1.5 * (105 * tile_size) / (128 * barbs_img.height)
        self.barbarians = barbarians

        zap_img = pg.image.load("images/zap.png")
        zap = pg.sprite.Sprite(zap_img)
        zap.scale_x = 1.5 * tile_size / zap_img.width
        zap.scale_y = 1.5 * (105 * tile_size) / (128 * zap_img.height)
        self.zap = zap

        mp_img = pg.image.load("images/mini_pekka.png")
        mini_pekka = pg.sprite.Sprite(mp_img)
        mini_pekka.scale_x = 1.5 * tile_size / mp_img.width
        mini_pekka.scale_y = 1.5 * (105 * tile_size) / (128 * mp_img.height)
        self.mini_pekka = mini_pekka

        hog_img = pg.image.load("images/hog_rider.png")
        hog_rider = pg.sprite.Sprite(hog_img)
        hog_rider.scale_x = 1.5 * tile_size / hog_img.width
        hog_rider.scale_y = 1.5 * (105 * tile_size) / (128 * hog_img.height)
        self.hog_rider = hog_rider

        gob_img = pg.image.load("images/goblins.png")
        goblins = pg.sprite.Sprite(gob_img)
        goblins.scale_x = 1.5 * tile_size / gob_img.width
        goblins.scale_y = 1.5 * (105 * tile_size) / (128 * gob_img.height)
        self.goblins = goblins

        bomb_img = pg.image.load("images/bomber.png")
        bomber = pg.sprite.Sprite(bomb_img)
        bomber.scale_x = 1.5 * tile_size / bomb_img.width
        bomber.scale_y = 1.5 * (105 * tile_size) / (128 * bomb_img.height)
        self.bomber = bomber

        arch_img = pg.image.load("images/archers.png")
        archers = pg.sprite.Sprite(arch_img)
        archers.scale_x = 1.5 * tile_size / arch_img.width
        archers.scale_y = 1.5 * (105 * tile_size) / (128 * arch_img.height)
        self.archers = archers

        bd_img = pg.image.load("images/baby dragon.png")
        baby_dragon = pg.sprite.Sprite(bd_img)
        baby_dragon.scale_x = 1.5 * tile_size / bd_img.width
        baby_dragon.scale_y = 1.5 * (105 * tile_size) / (128 * bd_img.height)
        self.baby_dragon = baby_dragon

        ############ BOARD ############

        # Board initialization
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
        self.illegal_spaces = illegal_spaces
        self.enemy_towers = enemy_towers

        for space in illegal_spaces:
            self.board[space[1]][space[0]] = -1

        ########## DECK AND STATE ###########

        # Deck initalization
        self.deck = deck
        self.enemydeck = deck
        self.hand = []
        self.evil_hand = []

        # Timer and Bookkeeping initialization
        self.time = 3 * 60
        self.live_troops = []
        self.live_evil_troops = []
        self.dead = []

        self.troop_damage = 0
        self.evil_troop_damage = 0

        # Crown towers
        self.live_troops.append(PrincessTower((3,6), self))
        self.live_troops.append(PrincessTower((14, 6), self))
        self.live_troops.append(KingTower((9,3), self))

        # Evil Crown towers
        self.live_evil_troops.append(PrincessTower((3,23), self, is_evil=True))
        self.live_evil_troops.append(PrincessTower((14, 23), self, is_evil=True))
        self.live_evil_troops.append(KingTower((9,25), self, is_evil=True))

        self.score = 0
        self.evil_score = 0
        self.game_over = False
        self.won = False

        # Agent helpers
        self.last_action = None
        self.last_state = None
        self.last_payout = 0

        # Initialize Hand
        if self.deck:
            for i in range(4):
                self.draw_card()
                self.draw_evil_card()

    def in_bounds(self, x, y):
        """Boolean if (x,y) is in bounds of the board."""
        #
        # all_cards = self.board.live_troops.copy()
        # all_cards.extend(self.board.live_evil_troops)
        # occupied = [card.location for card in all_cards]

        return (x >= 0) and (x < self.width) and (y >= 0) and (y < self.height)

    def render_tiles(self):
        """Render the board as legal/illegal tiles."""
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


    def draw_troops(self):
        """Render all living troops and their health."""
        all_cards = self.live_troops.copy()
        all_cards.extend(self.live_evil_troops)
        for card in all_cards:
            # Convert location to screen space
            screen_x, screen_y = self.xy_to_screen(card.location[0], card.location[1])
            sprite = self.grab_sprite(card.name)
            if sprite:
                sprite.x = screen_x
                sprite.y = screen_y
                sprite.draw()
                # Draw health label
                health_label = pg.text.Label(str(card.health), font_name='Times New Roman', font_size=9,
                                      x=screen_x, y=screen_y + 10, anchor_x='center',
                                      anchor_y='center', color=(card.is_evil*255,0,(1-card.is_evil)*255,255))
                health_label.draw()
                # If multiple living units, draw all health bars
                if card.units > 1:
                    for i in range(card.units - 1):
                        more_health_label = pg.text.Label(str(card.maxhealth), font_name='Times New Roman', font_size=9,
                                      x=screen_x, y=screen_y + 20 + 10*i, anchor_x='center',
                                      anchor_y='center', color=(card.is_evil*255,0,(1-card.is_evil)*255,255))
                        more_health_label.draw()
            # Case towers
            else:
                health_label = pg.text.Label(str(card.health), font_name='Times New Roman', font_size=24,
                                             x=screen_x, y=screen_y + 10, anchor_x='center',
                                             anchor_y='center', color=(card.is_evil*255,0,(1-card.is_evil)*255, 255))
                health_label.draw()


    def grab_sprite(self, name):
        """Convert card.name into card objects."""
        if name == 'barbarians':
            return self.barbarians
        if name == 'zap':
            return self.zap
        if name == 'mini pekka':
            return self.mini_pekka
        if name == 'hog rider':
            return self.hog_rider
        if name == 'archers':
            return self.archers
        if name == 'bomber':
            return self.bomber
        if name == 'baby dragon':
            return self.baby_dragon
        if name == 'goblins':
            return self.goblins

    def xy_to_screen(self, x, y):
        """Convert board spaces into screen coordinates."""
        new_x = x * self.tile_size + self.xoffset
        new_y = (105 * y * self.tile_size) / 128 + self.yoffset
        return new_x, new_y

    def increment_elixir(self, dt=None):
        """Handle elixir update and dispatch elixir graphics."""
        if self.elixir_count < 10:
            self.elixir_count += 1

        if self.evil_elixir_count < 10:
            self.evil_elixir_count += 1

        self.render_elixir()

    def render_elixir(self):
        """Elixir bar graphics."""
        start_x = self.xoffset
        self.elixir_bar.x = start_x
        start_y = self.yoffset / 1.5
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

        enemy_count = pg.text.Label(str(self.evil_elixir_count), font_name='Times New Roman', font_size=16,
                      x=start_x + 10 * self.elixir_bar.width, y=800 - start_y, anchor_x='center', anchor_y='center')

        enemy_count.draw()

    def render_score(self):
        """Display crown tower score graphics."""
        friendly = pg.text.Label(str(self.score), font_name='Times New Roman', font_size=24, x = 520, y = 350, anchor_x='center',
                                  anchor_y='center', color=(0,0,255,255))
        evil = pg.text.Label(str(self.evil_score), font_name='Times New Roman', font_size=24, x = 520, y = 450, anchor_x='center',
                                  anchor_y='center', color=(255,0,0,255))
        friendly.draw()
        evil.draw()

    def tower_tiebreaker_won(self):
        """Calculate which team won in the event of a score tie at times up."""
        all_cards = self.live_troops.copy()
        all_cards.extend(self.live_evil_troops)
        min_friendly = float('inf')
        min_evil = float('inf')
        for card in all_cards:
            if card.name == 'princess tower' or card.name == 'king tower':
                if card.is_evil:
                    if card.health < min_evil:
                        min_evil = card.health
                else:
                    if card.health < min_friendly:
                        min_friendly = card.health
        return min_friendly >= min_evil


    def update_state(self, dt = None):
        """Update loop for entire game: dispatch all troops, clear trash, assess game condition."""
        print(" ")
        print("=========== TURN:", 180 - self.time, " =============")
        if self.score == 3 or self.evil_score == 3 or (self.time <= 0 and self.score != self.evil_score):
            self.game_over = True
            self.won = (self.score > self.evil_score)
        # Case equal towers, tie break by health
        elif self.time <= 0:
            self.game_over = True
            self.won = self.tower_tiebreaker_won()

        if self.game_over:
            self.win_condition()
            return
        # Take out the trash
        for dead_card in self.dead:
            if dead_card in self.live_evil_troops:
                self.live_evil_troops.remove(dead_card)
                if dead_card.name == 'princess tower':
                    self.score += 1
                    self.troop_damage += 100
                elif dead_card.name == 'king tower':
                    self.score = 3
                    self.troop_damage += 1000
            elif dead_card in self.live_troops:
                self.live_troops.remove(dead_card)
                if dead_card.name == 'princess tower':
                    self.evil_score += 1
                    self.evil_troop_damage += 100
                elif dead_card.name == 'king tower':
                    self.evil_score = 3
                    self.evil_troop_damage += 1000
            del dead_card

        self.dead = []

        # Update global time
        self.time -= 1

        # Let all cards act + bookkeeping
        self.troop_damage = 0
        self.evil_troop_damage = 0
        all_cards = self.live_troops.copy()
        all_cards.extend(self.live_evil_troops)
        for card in all_cards:
            # If the return value is something - it exited because the card died
            card.action()

        # print([card.name for card in self.hand])
        # print([card.name for card in self.evil_hand])



    def render_clock(self, dt = None):
        """Clock timer graphics."""
        minute = self.time // 60
        second = str(self.time % 60)
        if len(second) < 2:
            second = "0"+second
        timer_label = pg.text.Label(str(minute)+":"+second, font_name='Times New Roman', font_size=24, x = 520, y = 750, anchor_x='center',
                                  anchor_y='center')
        timer_label.draw()

    def draw_card(self):
        """Draw a card not in hand from the deck into the player's hand."""
        # If hand initialized and unfull, don't duplicate
        if self.hand and len(self.hand) < 4:
            curr = set([card.name for card in self.hand])
            all = [card for card in self.deck if card.name not in curr]
            self.hand.append(np.random.choice(all))
        # If hand uninitialized and unfull, draw at random from deck
        elif len(self.hand) < 4:
            self.hand.append(np.random.choice(self.deck))

    def draw_evil_card(self):
        """Draw a card not in hand from the deck into the player's hand."""
        # If hand initialized and unfull, don't duplicate
        if self.evil_hand and len(self.evil_hand) < 4:
            curr = set([card.name for card in self.evil_hand])
            all = [card for card in self.deck if card.name not in curr]
            self.evil_hand.append(np.random.choice(all))
        # If hand uninitialized and unfull, draw at random from deck
        elif len(self.evil_hand) < 4:
            self.evil_hand.append(np.random.choice(self.deck))


    def get_legal_actions(self, is_evil):
        """For a game agent: gives all legal actions given current elixir cost and hand."""
        actions = []
        actions.append((None, (0,0)))
        if not is_evil:
            for card in self.hand:
                if card.cost <= self.elixir_count:
                    actions.extend([(card.name, loc) for loc in card.LegalDeployments])
        else:
            for card in self.evil_hand:
                if card.cost <= self.evil_elixir_count:
                    actions.extend([(card.name, loc) for loc in card.LegalDeployments])

        return actions

    def action_payout(self):
        """Calculates the reward at the end of the turn."""
        # Where troop_damage = sum(all damage) + 100 * (princess tower kills) + 1000 * (game wins)
        return self.troop_damage - self.evil_troop_damage


    def place_troop(self, card):
        """Places a troop card onto the board and updates hand."""
        if not card.is_evil:
            if card.cost <= self.elixir_count and card.name in [cand.name for cand in self.hand]:
                self.elixir_count -= card.cost
            self.live_troops.append(card)
            self.hand = [cand for cand in self.hand if cand.name != card.name]
            self.draw_card()
        else:
            if card.cost <= self.evil_elixir_count and card.name in [cand.name for cand in self.evil_hand]:
                self.evil_elixir_count -= card.cost
            self.live_evil_troops.append(card)
            self.evil_hand = [cand for cand in self.evil_hand if cand.name != card.name]
            self.draw_evil_card()

    def target(self, card, target_policy):
        """Allows a card to target the nearest enemy card given its policy."""
        targets = []
        if card.is_evil:
            candidates = self.live_troops
        else:
            candidates = self.live_evil_troops

        for cand in candidates:
            if target_policy == 'buildings':
                if cand.is_building:
                    targets.append(cand)
            elif target_policy == 'ground':
                if not cand.is_flying:
                    targets.append(cand)
            else:
                targets.append(cand)

        cards_and_dists = []
        for candidate in targets:
            dist = ((card.location[0] - candidate.location[0]) ** 2 + (card.location[1] - candidate.location[1]) ** 2) ** 0.5
            cards_and_dists.append((candidate, dist))

        #print("card", card.name, "may target best of", [(candidate.name, candidate.location) for candidate in targets])

        if cards_and_dists:
            return min(cards_and_dists, key = lambda pair : pair[1])[0]
        else:
            return

    def win_condition(self):
        """If game has ended, trigger game ending graphics."""
        if not self.game_over:
            return
        if self.won:
            text = "GAME OVER: YOU WIN!"
        else:
            text = "GAME OVER: YOU LOSE!"

        timer_label = pg.text.Label(text, font_name='Times New Roman', font_size=36,
                                        x=300, y=400, anchor_x='center',
                                        anchor_y='center')
        timer_label.draw()

    def render_hand(self):
        """Hand of cards graphics to show current hand and cost."""
        x_ind = 0
        for card in self.hand:
            sprite = self.grab_sprite(card.name)
            sprite.x = self.xoffset + (x_ind * (sprite.width + self.tile_size))
            sprite.y = self.yoffset / 4
            sprite.scale_x *= 1
            sprite.scale_y *= 1
            sprite.draw()
            sprite.scale_x /= 1
            sprite.scale_y /= 1
            # Draw health label
            health_label = pg.text.Label(str(card.cost), font_name='Times New Roman', font_size=16,
                                         x=self.xoffset + (x_ind * (sprite.width + self.tile_size)), y=10, anchor_x='center',
                                         anchor_y='center',
                                         color=(200, 0, 200, 255))
            health_label.draw()
            x_ind += 1



