# Optimax Rogue: A Competitive Roguelike Environment

This package contains the server for a rogue-like competitive environment "Optimax Rogue".
It is inspired by the success of OpenAI in Dota 2 and other recent reinforcement learning
successes.

## Similar Packages

Before you use this package, you have to know what else is out there! Optimax Rogue is one
of many libraries intended for use with reinforcement libraries. Check out the following links
and decide if they might be better for you:

- OpenAI Retro: https://github.com/openai/retro
- OpenAI Gym: https://github.com/openai/gym
- Rogueinabox: https://github.com/rogueinabox/rogueinabox
- Arcade Learning Environment: https://github.com/mgbellemare/Arcade-Learning-Environment
- VizDoom: https://github.com/mwydmuch/ViZDoom
- BotHack and related: https://github.com/krajj7/BotHack
- Pygame Learning Environment: https://pygame-learning-environment.readthedocs.io/en/latest/
- PySC2: https://github.com/deepmind/pysc2
- AI safety gridworlds: https://github.com/deepmind/ai-safety-gridworlds
- OSIM RL: https://github.com/stanfordnmbl/osim-rl
- AIKorea curated list: https://github.com/aikorea/awesome-rl#open-source-reinforcement-learning-platforms

## What's unique about Optimax Rogue

It offeres an 2-player competitive environment with a randomly generated world and enemies,
which was built from the ground up to be readily consumable by machine learning or human input.
The competitive nature allows it to leverage the self-play dynamics that has been proven successful
by AlphaGo and OpenAI. It decouples the game engine from machine learning completely *and* human
interaction completely, ensuring you can use exactly the components you need. Far from forgetting
the importance of sharing your invention, Optimax Rogue is built in anticipation of rendering the
game both real-time and through playbacks.

In short, Optimax Rogue gives you everything you need, without requiring that you use it all.

## Launching the Server

Launching Optimax Rogue is easy. Simply download the library and execute the following command
in terminal: `python -m main`. Optimax Rogue expects Python 3.7.

## About the Game

Every game starts with 2 agents placed on a 2d grid of a fixed width and height, where every entry in the grid may have an immovable wall. There is a ladder somewhere on the map which becomes visible when an agent gets near it. Enemies may spawn on the map (see Combat), which may be killed for experience. Leveling refills health and mana, where mana is used to deal extra damage. Enemies may drop items, which provide flat attribute bonuses if picked up. There are a finite number of item spots available.

Agents may attack each other, and if the agents are on separate levels the agent further behind begins taking damage that scales linearly with time since separation. The game ends if an agent
dies, with the longer living agent winning. If both agents die during the same tick then one wins
at random.

## Connections

A lobby system is used to play the game. This is fairly painless if you intend to run the server
locally and have only two clients play at a time, or if you want to add a ranked matchmaking
system on top. A player connects and can optionally specify a lobby id. If they do not specify
a lobby id, a new lobby is created and they are told the id. The other player connects with that
lobby id, and the game starts. The game runs until either player dies. Spectators may join either
in the lobby stage or in the gameplay stage.

Every server spawns a new instance of the server python environment, ensuring that crashes don't
bring the entire thing down.

## Technical Details

Games are played in synchronous mode - all players must give their orders for the turn before the
turn is simulated.

## Combat

If players A and B attack each other during the same turn, then both take half damage and are put on a 3-turn attack cooldown (attacks are measured as stay and you cannot defend). If A attacks B and B
stays still, the damage is negated and A cannot attack or defend the next turn. If A attacks B's current location but B moves, no damage is dealt. If A attacks B's new location, full damage is dealt.

When calculating A's attack damage, if A has mana then up to 1/3 the manabar is converted into damage and spent.

A player may heal by spending up to 1/3 their manabar and converting it to health. They cannot move while healing.