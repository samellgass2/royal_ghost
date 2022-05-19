# Royal Ghost In the Marchine
### A Clash Royale Reinforcement Learning trained Artificial Intelligence
## Goal
Teach a Q-Learner Agent to win at Clash Royale* using a simplified version of the game and a reward function that is biased toward units doing damage and taking out the opposing towers (win condition).

*This project was built from scratch by me, and so there are some concessions made in the accuracy of the 'royal ghost' version of the game relative to Clash Royale.

## Use
The game can be executed by running
```terminal
>>> python game.py
```
Which will prompt a user to update the episode count for the UI, choose a file to import weights from, and choose a file to export weights to.
```terminal
Enter how many episodes have been run so far:
>>>x
Enter file name to parse Q values from or RETURN if none.
>>>input_file.parquet
Enter output file name to send Q values to or RETURN for same as input.
>>>output_file.parquet
```
The input Q-values will be used for both the agent **and the adversary**, although the adversary will **not** update its weights (learn) during training, but stay static.

In this way, training can occur in batches of any size, used in a script to terminate at a certain point.

### Notes:
- Speed up factor can be controlled in real time using **+** to raise speed by 1x, **-** to lower by 1x, **RIGHT** to lower by 5x, and **LEFT** to raise by 5x.
- The main metric for how much exploration has occurred is the **% of states explored**, which simply checks how many potential Q(state, action) values have been initialized as a rough proxy for training robustness.

##Agents
- **RandomLegalAgent**: takes a random action with equal probability, action as given by the GameBoard
- **NearestTroopAgent**: an agent that defines state as **(nearest_card.name, (int) dist_to_tower)**, and prescribes an action based on its learned Q-values

##Progress
At the time of writing (5/19/22), the NearestTroopAgent has played 5,000 games and explored > 1.5% of all Q states, and is able to gather some key ideas about strategy:
- Use of spell cards as instant reward (knows to drop *zap* on towers for high reward)
- Use of cheap cards as counter (knows to use 2 and 3 cost goblins, archers, and bomber to counter cheap enemy troops)
- Use of building-targeting cards (knows that Hog Rider will target towers and yield more reward reliably compared to troops with other targeting policies)

## Structure
- game.py is the main executable, hosting a GameBoard object that allows a ClashAgent to play against another ClashAgent in the 
pseudo-Clash Royale World
- board.py is most of the game code, including the GameBoard class, GameCard class, all types of cards as subclasses of GameCard, and all unique cards as subclasses of those 
- clash_agents.py holds the Q-learner agent and random choice agent, and crucially allows for Q-values to be written to and imported from parquet files
