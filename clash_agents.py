"""AI Agents to Play Clash Royale."""
from typing import List

from board import *
#from game import *
import random
import pandas as pd
from ast import literal_eval as make_tuple
from tqdm import tqdm

class RandomLegalAgent:
    """A reinforcement learning agent who only ever plays a random, legal card
    or None every step."""

    def __init__(self, deck : List[GameCard], enemydeck : List[GameCard], board : GameBoard):
        self.board = board
        self.deck = deck
        self.is_evil = False
        self.actions = []
        # actions as for all cards (and None), possible locations (card, (x,y))
        for card in deck:
            for location in card.LegalDeployments:
                self.actions.append((card.name, location))

        all_locations = []
        for i in range(self.board.width):
            for j in range(self.board.height):
                all_locations.append((i, j))
        self.actions.extend([(None, loc) for loc in all_locations])


        states = []
        # states for all nearest possible troops (card, (location))
        for card in enemydeck:
            states.extend([(card.name, loc) for loc in all_locations])

        all_states = []
        # all states as (card, (location), elixir)
        for state in states:
            all_states.extend([(state[0], state[1], elixir) for elixir in range(11)])

        self.states = all_states

        self.qvalues = {}
        #print(self.states)
        for state in self.states:
            self.qvalues[state] = 0.0

    def getAction(self, state):
        legal_actions = self.board.get_legal_actions(self.is_evil)
        #print(legal_actions)
        action = legal_actions[np.random.choice(range(len(legal_actions)))]
        return action

    def update(self, state, action, nextState, reward: float):
        """
          The parent class calls this to observe a
          state = action => nextState and reward transition.
          You should do your Q-Value update here
          NOTE: You should never call this function,
          it will be called on your behalf
        """
        return


class NearestTroopAgent:
    """A Reinfocement Learning Agent to consider
    only the nearest troop."""

    def __init__(self, deck : List[GameCard], enemydeck : List[GameCard], board : GameBoard, epsilon = 0.2, discount = 0.9, learning_rate = 0.2):
        self.board = board
        self.deck = deck
        self.is_evil = False
        self.actions = []
        # actions as for all cards (and None), possible locations (card, (x,y))

        for card in deck:
            for location in card.LegalDeployments:
                self.actions.append((card.name, location))

        all_locations = []
        for i in range(self.board.width):
            for j in range(self.board.height):
                all_locations.append((i, j))
        self.actions.append((None, (0,0)))

        states = []
        # states for all nearest possible troops (card, (location))
        for card in enemydeck:
            states.extend([(card.name, i) for i in range(36)])

        # Initializing for extraneous states.
        states.extend([('princess tower', i) for i in range(36)])
        states.extend([('king tower', i) for i in range(36)])
        states.append((None, 0))

        all_states = []
        # all states as (card, (location), elixir)
        for state in states:
            all_states.extend([(state[0], state[1], elixir) for elixir in range(11)])

        self.states = all_states

        qstates = []
        for state in all_states:
            qstates.extend([(state, action) for action in self.actions])

        self.qvalues = {}
        for state in qstates:
            self.qvalues[state] = 0.0

        # Exploration probability
        self.epsilon = epsilon
        self.discount = discount
        self.alpha = learning_rate
        #print(list(self.qvalues.keys())[:10])

    def getQValue(self, state, action):
        """
          Returns Q(state,action)
          Should return 0.0 if we have never seen a state
          or the Q node value otherwise
        """
        s_a_pair = tuple((state, action))
        if s_a_pair in self.qvalues:
            return self.qvalues[s_a_pair]
        else:
            return 0.0

    def computeValueFromQValues(self, state):
        """
          Returns max_action Q(state,action)
          where the max is over legal actions.  Note that if
          there are no legal actions, which is the case at the
          terminal state, you should return a value of 0.0.
        """
        actions = self.board.get_legal_actions(self.is_evil)
        if not actions:
            return 0.0
        else:
            return max([self.getQValue(state, action) for action in actions])

    def computeActionFromQValues(self, state):
        """
          Compute the best action to take in a state.
        """
        actions = self.board.get_legal_actions(self.is_evil)
        if not actions:
            return None
        else:
            actions_and_vals = [(action, self.getQValue(state, action)) for action in actions]
            # Find max tuple by Qvalue and return corresponding action
            return max(actions_and_vals, key=lambda x: x[1])[0]

    def getAction(self, state):
        """
          Compute the action to take in the current state.  With
          probability self.epsilon, we should take a random action and
          take the best policy action otherwise.
        """
        # Pick Action
        legalActions = self.board.get_legal_actions(self.is_evil)
        explore = random.random() <= self.epsilon
        if explore:
            return random.choice(legalActions)
        else:
            return self.computeActionFromQValues(state)

    def update(self, state, action, nextState, reward: float):
        """
          The parent class calls this to observe a
          state = action => nextState and reward transition.
          You should do your Q-Value update here
          NOTE: You should never call this function,
          it will be called on your behalf
        """
        curr_sample = reward + self.discount * self.computeValueFromQValues(nextState)
        self.qvalues[(state, action)] = (1 - self.alpha) * self.qvalues[(state, action)] + self.alpha * curr_sample

    def export_agent(self, filename):
        new_dict = {}
        all_keys = list(self.qvalues.keys())
        for i in range(len(all_keys)):
            if self.qvalues.get(all_keys[i]) != 0.0:
                new_dict[i] = [str(all_keys[i]), self.qvalues.get(all_keys[i])]
        qvals_df = pd.DataFrame.from_dict(new_dict, orient='index', columns=['S_and_A', 'Value'])
        qvals_df.to_parquet(filename)
        print("Wrote", qvals_df.shape[0], "values to", filename)

    def load_qvals(self, filename):
        qvals_df = pd.read_parquet(filename)
        print("Reading", qvals_df.shape[0], "q values from file.")
        for ind, val in tqdm(qvals_df.iterrows()):
            self.qvalues[make_tuple(val[0])] = val[1]






