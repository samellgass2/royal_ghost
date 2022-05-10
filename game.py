"""Executable to run the game."""


import numpy as np
import pyglet as pg
import pyglet.graphics as graphics
import pyglet.gl as gl
import random
from board import *
from clash_agents import *

window = pg.window.Window(width=600, height=800, caption="Royal Ghost")

board_backdrop = pg.resource.image("images/clash-board.jpeg")
tile_size = (600 * 0.8) / 18

BOARD = GameBoard(tile_size)
tile_view = False

@window.event
def on_draw():
    window.clear()
    board_backdrop.blit(0.1 * window.width,0.1 * window.height, width=window.width * 0.8, height=window.height * 0.8)
    BOARD.render_tiles()
    BOARD.render_elixir()

@window.event
def on_key_press(symbol, modifiers):
    if symbol == pg.window.key.D:
        BOARD.tile_view = not BOARD.tile_view
    elif symbol == pg.window.key.D or symbol == pg.window.key.RIGHT:
        print('D')
    elif symbol == pg.window.key.R or symbol == pg.window.key.SPACE:
        print('R')

# Dispatch game state to NN / RL net
pg.clock.schedule_interval(BOARD.increment_elixir, 2)
pg.app.run()