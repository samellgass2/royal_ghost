"""Executable to run the game."""


import numpy as np
import pyglet as pg
import pyglet.graphics as graphics
import pyglet.gl as gl
import random
from board import *
from clash_agents import *

###### GLOBAL PARAMS ######
speedup_factor = 100
EPISODES = 50
CURR_EPISODE = 0
WINS = 0
LOSSES = 0

STATES_INIT = 0

episode_name = "weights_toward_5096.parquet"
MODEL_FILE = "weights_toward_5096.parquet"

###### GLOBAL PARAMS ######


###### LOAD OLD MODEL ######

def load_model():
    global MODEL_FILE
    global CURR_EPISODE
    global EPISODES
    global episode_name

    print("Enter how many episodes have been run so far:")
    num_eps = int(input())
    CURR_EPISODE += num_eps
    EPISODES += num_eps

    print("Enter file name to parse Q values from or RETURN if none.")
    filename = input()
    if filename:
        MODEL_FILE = filename
    print("Enter output file name to send Q values to or RETURN for same as input.")
    new_epi_name = input()
    if new_epi_name:
        episode_name = new_epi_name
    elif filename:
        episode_name = filename


load_model()

window = pg.window.Window(width=600, height=800, caption="Royal Ghost")

board_backdrop = pg.resource.image("images/clash-board.jpeg")
tile_size = (600 * 0.8) / 18

####### INITIALIZE GAME AND AGENTS #########

BOARD = GameBoard(tile_size, None)
deck = [Barbarians((0,0), BOARD), Zap((0,0), BOARD), MiniPekka((0,0), BOARD), HogRider((0,0), BOARD),
        Archers((0,0), BOARD), Bomber((0,0), BOARD), BabyDragon((0,0), BOARD), Goblins((0,0), BOARD)]
BOARD.deck = deck
[BOARD.draw_card() for i in range(4)]
[BOARD.draw_evil_card() for j in range(4)]
tile_view = False
verbose_mode = True

# AGENT = RandomLegalAgent(deck, deck, BOARD)
AGENT = NearestTroopAgent(deck, deck, BOARD)
EVIL_AGENT = NearestTroopAgent(deck, deck, BOARD)
EVIL_AGENT.is_evil = True

USE_COUNTS = {}
for card in deck:
    USE_COUNTS[card.name] = 0

####### INITIALIZE GAME AND AGENTS #########

if MODEL_FILE:
    AGENT.load_qvals(MODEL_FILE)
    EVIL_AGENT.load_qvals(MODEL_FILE)
last_action = None


def reset():
    """Resets board and game (but NOT agent), triggers next episode."""
    global CURR_EPISODE
    global BOARD
    global AGENT
    global EVIL_AGENT
    global WINS
    global LOSSES

    # Remove previous schedule
    pg.clock.unschedule(BOARD.increment_elixir)
    pg.clock.unschedule(BOARD.update_state)
    pg.clock.unschedule(dispatch_agent)
    pg.clock.unschedule(dispatch_evil_agent)

    CURR_EPISODE += 1
    if BOARD.won:
        WINS += 1
    else:
        LOSSES += 1
    if CURR_EPISODE >= EPISODES:
        print("Training has ended after", EPISODES, "episodes.")
        print("=================================")
        print("Agent's use of each card was:")
        total_use = sum(list(USE_COUNTS.values()))
        for key in USE_COUNTS:
            print("Agent used", key, round(100*USE_COUNTS[key]/total_use,2), "% of the time.")

        AGENT.export_agent(episode_name)
        print("Export completed.")
        print("=================================")
        print(" ")
        pg.app.EventLoop().exit()
        window.close()

    else:
        # Reset board and reference for agent
        del BOARD
        BOARD = GameBoard(tile_size, deck)
        count_states(AGENT)
        AGENT.board = BOARD
        EVIL_AGENT.board = BOARD

        # Create new schedule
        pg.clock.schedule_interval(BOARD.increment_elixir, (1 / speedup_factor) * 2.8)
        pg.clock.schedule_interval(BOARD.update_state, (1 / speedup_factor) * 1)

        # Dispatch game state to NN / RL net
        pg.clock.schedule_interval(dispatch_agent, (1 / speedup_factor) * 1)
        pg.clock.schedule_interval(dispatch_evil_agent, (1 / speedup_factor) * 1)




def count_states(AGENT):
    """A function to return what % of qvalues have been initialized."""
    global STATES_INIT
    total = 0

    for key in AGENT.qvalues:
        if AGENT.qvalues.get(key) != 0.0:
            total += 1
    STATES_INIT = total / len(AGENT.qvalues.keys())
    print("So far have explored", total, "out of ", len(AGENT.qvalues.keys()))

def process_action(action, is_evil=False):
    """A function to take an agent's action and turn it into troop generation."""
    card, location = action
    if is_evil:
        location = invert_location(location)
    if card is None:
        return
    if card == 'barbarians':
        return Barbarians(location, BOARD, is_evil=is_evil)
    if card == 'zap':
        return Zap(location, BOARD, is_evil=is_evil)
    if card == 'mini pekka':
        return MiniPekka(location, BOARD, is_evil=is_evil)
    if card == 'hog rider':
        return HogRider(location, BOARD, is_evil=is_evil)
    if card == 'archers':
        return Archers(location, BOARD, is_evil=is_evil)
    if card == 'bomber':
        return Bomber(location, BOARD, is_evil=is_evil)
    if card == 'baby dragon':
        return BabyDragon(location, BOARD, is_evil=is_evil)
    if card == 'goblins':
        return Goblins(location, BOARD, is_evil=is_evil)

def dispatch_agent(dt=None):
    """A function to update the agent."""
    state = nearest_troop_agent_state(False)
    action = AGENT.getAction(state)
    new_card = process_action(action)
    if verbose_mode:
        if new_card:
            print("Agent plays", new_card.name, "!")
            USE_COUNTS[new_card.name] += 1
            BOARD.place_troop(new_card)
        else:
            print("Agent plays None.")

    # Update the Q-values of the agent based on the results of its last action, now that the following state is known
    if BOARD.last_state and BOARD.last_action:
        AGENT.update(BOARD.last_state, BOARD.last_action, state, BOARD.last_payout)
    BOARD.last_state = state
    BOARD.last_action = action
    BOARD.last_payout = BOARD.action_payout()

def dispatch_evil_agent(dt=None):
    """Call the evil agent to make a move. DO NOT update agent."""
    state = nearest_troop_agent_state(True)
    action = EVIL_AGENT.getAction(state)
    new_card = process_action(action, is_evil=True)
    if verbose_mode:
        if new_card:
            print("ADVERSARY plays", new_card.name, "!")
            BOARD.place_troop(new_card)
        else:
            print("ADVERSARY plays None.")


def invert_location(location):
    x,y = location
    new_y = 30 - y
    return (x, new_y)

def nearest_troop_agent_state(is_evil):
    """Get state for a nearest troop agent as (nearest_card.name, nearest_card.location, elixir_count)"""
    if not is_evil:
        troops = [troop for troop in BOARD.live_evil_troops if troop.target]
        elixir = BOARD.elixir_count
    else:
        troops = [troop for troop in BOARD.live_troops if troop.target]
        elixir = BOARD.evil_elixir_count
    # If there exists a troop on the board targeting agent:
    if troops:
        closest_troop = min(troops, key=lambda troop: troop.target_distance())
        return (closest_troop.name, int(closest_troop.target_distance()), elixir)
    # Else, consider no troops.
    else:
        return (None, 0, elixir)




def ML_GUI(dt = None):
    """Renders ML progress."""
    EPI_NUM = pg.text.Label("EPISODE "+str(CURR_EPISODE), font_name='Times New Roman', font_size=24,
                                         x= 100, y=770, anchor_x='center',
                                         anchor_y='center')
    EPI_NUM.draw()

    state_count = pg.text.Label("Explored "+str(round(STATES_INIT*100,2))+" % of states", font_size=12,
                                         x= 100, y=740, anchor_x='center',
                                         anchor_y='center')
    state_count.draw()

    win_rate = pg.text.Label("Win Rate="+str(round(100*WINS/(WINS+LOSSES+0.001),2))+"%", font_size=10, x = 80, y=720,
                             anchor_x='center',
                             anchor_y='center'
                             )
    win_rate.draw()

def SPEED_GUI(dt = None):
    """Renders current simulation speed"""
    SPEED = pg.text.Label(str(speedup_factor)+"x speed", font_size=10,
                                         x= 500, y=770, anchor_x='center',
                                         anchor_y='center')
    SPEED.draw()


@window.event
def on_draw():
    """Main render loop for all frames."""
    if not BOARD.game_over:
        window.clear()
        board_backdrop.blit(0.1 * window.width,0.1 * window.height, width=window.width * 0.8, height=window.height * 0.8)
        BOARD.render_tiles()
        BOARD.render_elixir()
        BOARD.render_clock()
        BOARD.draw_troops()
        BOARD.render_score()
        BOARD.win_condition()
        BOARD.render_hand()
        ML_GUI()
        SPEED_GUI()
    else:
        reset()


@window.event
def on_key_press(symbol, modifiers):
    """Event handler; processes tile view and speed modifiers."""
    global speedup_factor
    global verbose_mode
    if symbol == pg.window.key.D:
        BOARD.tile_view = not BOARD.tile_view
    elif symbol == pg.window.key.MINUS:
        if speedup_factor > 1:
            speedup_factor -= 1
            reschedule_events()
    elif symbol == pg.window.key.RIGHT:
        speedup_factor += 5
        reschedule_events()
    elif symbol == pg.window.key.LEFT:
        if speedup_factor > 5:
            speedup_factor -= 5
            reschedule_events()
    elif symbol == pg.window.key.PLUS:
        speedup_factor += 1
        reschedule_events()
    elif symbol == pg.window.key.V:
        verbose_mode = not verbose_mode
        BOARD.verbose_mode = not verbose_mode

def reschedule_events():
    pg.clock.unschedule(BOARD.increment_elixir)
    pg.clock.unschedule(BOARD.update_state)

    pg.clock.unschedule(dispatch_agent)
    pg.clock.unschedule(dispatch_evil_agent)

    pg.clock.schedule_interval(BOARD.increment_elixir, (1 / speedup_factor) * 2.8)
    pg.clock.schedule_interval(BOARD.update_state, (1 / speedup_factor) * 1)

    pg.clock.schedule_interval(dispatch_agent, (1 / speedup_factor) * 1)
    pg.clock.schedule_interval(dispatch_evil_agent, (1 / speedup_factor) * 1)

count_states(AGENT)
pg.clock.schedule_interval(BOARD.increment_elixir, (1/speedup_factor)*2.8)
pg.clock.schedule_interval(BOARD.update_state, (1/speedup_factor)*1)

# Dispatch game state to NN / RL net
pg.clock.schedule_interval(dispatch_agent, (1/speedup_factor)*1)
pg.clock.schedule_interval(dispatch_evil_agent, (1/speedup_factor)*1)


pg.app.run()