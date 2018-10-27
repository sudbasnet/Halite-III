#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants
from math import inf
from copy import deepcopy
# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

ALPHA = 0.05
GAMMA = 0.5
COST = 0.5

class QTable:
    def __init__(self, position, reward, utilities):
        self.position = position
        self.utilities = utilities
        # [up, right, down, left, same]
        self.reward = reward
        # reward is the halite amount at that postion

    def maxQ(self):
        maximumQ = -10000
        for utility in self.utilities:
            if utility[1] > maximumQ:
                maximumQ = utility[1]
        return maximumQ

    def display_data(self):
        logging.info("Position of this grid is %s", self.position)
        logging.info("Reward at this location is %s", self.reward)
        logging.info("And the utilities are: %s", self.utilities)


# total number of turns based on the grid size (linear relationship)
def get_total_turn_count(height):
    return 3.125 * height + 300


def reinforce(input_game_map, grid_table, iterations, alpha, gamma, cost):
    # it is always a square grid
    repeated = 0
    while repeated < iterations:
        for x in range(input_game_map.width):
            for y in range(input_game_map.height):
                grid = grid_table[x][y]
                positions = [input_game_map.normalize(Position(x, y + 1)),
                             input_game_map.normalize(Position(x + 1, y)),
                             input_game_map.normalize(Position(x, y - 1)),
                             input_game_map.normalize(Position(x - 1, y)),
                             Position(x, y)]
                neighbors = []
                for i in range(5):
                    neighbors.append(grid_table[positions[i].x][positions[i].y])
                    if positions[i] == grid.position:
                        updated_utility= utility_function(grid.utilities[i][1], alpha, gamma, 0, neighbors[i])
                    else:
                        updated_utility = utility_function(grid.utilities[i][1], alpha, gamma, cost, neighbors[i])
                    grid.utilities[i] = (grid.utilities[i][0], updated_utility)
                grid_table[x][y] = grid
        repeated += 1
    return grid_table


def initialize_grid(input_game_map):
    q_table = []
    # “n”, “s”, “e”, “w”
    default = [(Direction.North, 0), (Direction.South, 0), (Direction.East, 0), (Direction.West, 0)]
    for x in range(input_game_map.width):
        q_table.append([])
        for y in range(input_game_map.height):
            position = input_game_map.normalize(Position(x, y))
            q_object = QTable(position, input_game_map[position].halite_amount, default + [(Direction.Still, input_game_map[position].halite_amount)])
            q_table[x].append(q_object)
    # logging.info(q_table)
    return q_table


# for ordering by the halite amounts in the resource list
def by_halite(element):
        return element[1]


def update_grid(input_game_map, q_table):
    for x in range(input_game_map.width):
        for y in range(input_game_map.height):
            position = input_game_map.normalize(Position(x, y))
            halite_amount = input_game_map[position].halite_amount
            q_table[x][y].reward = halite_amount
            q_table[x][y].utilities[4] = (Direction.Still, halite_amount)
    # logging.info(q_table)
    return q_table


def utility_function(utility, alpha, gamma, cost, state):
    # alpha is the rate of how much I value the future
    # gamma is how certain it is that the reqward is real
    # state means the new position
    # the new state implies the action taken in itself
    utility = (utility * (1 - alpha)) + (alpha * ((state.reward * (1 - cost)) + (gamma * state.maxQ())))
    return utility


# find locations of all my storage options, returns a list of positions
def get_all_depos(input_me):
    my_depos = []
    depos = input_me.get_dropoffs()
    for d in depos:
        my_depos.append(d.position)
    return my_depos + [input_me.shipyard.position]


# find the closest storage facility
def get_closest_drop_off(input_game, pos):
    all_depos = get_all_depos(input_game.me)
    closest_depo = input_game.me.shipyard.position
    d = inf
    for depo in all_depos:
        if input_game.game_map.calculate_distance(pos, depo) < d:
            d = input_game.game_map.calculate_distance(pos, depo)
            closest_depo = depo
    return closest_depo


# bots that re designed to go to a specific place
# usually delivery bots go to drop-offs
delivery_bots = {} # {ship.id : destination.position}


# find delivery bots, ship.ids only
def activate_delivery_bots(in_game):
    for shp in in_game.me.get_ships():

        # get the closest drop-off locaition
        closest_drop_off = get_closest_drop_off(game, shp.position)

        # If towards the end, make everyone go to the deposit
        if in_game.turn_number >= 0.95 * get_total_turn_count(in_game.game_map.height):
            delivery_bots[shp.id] = closest_drop_off

        # Free up hoarding ships that just deposited halite
        if shp.position in all_available_dropoffs and shp.id in delivery_bots:
            delivery_bots.pop(shp.id)

        # Check if any ship is full, make it a hoarder
        if shp.is_full and shp.id not in delivery_bots:
            delivery_bots[shp.id] = closest_drop_off

        logging.info("There are %d ships in the delivery situation", len(delivery_bots))


# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
game_utility_grid = initialize_grid(game.game_map)
game_utility_grid = reinforce(game.game_map, game_utility_grid, 10, ALPHA, GAMMA, COST)
game_utility_grid[2][2].display_data()
game_utility_grid[2][3].display_data()
game_utility_grid[3][2].display_data()
game_utility_grid[2][1].display_data()
game_utility_grid[1][2].display_data()
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("UtilityBot")
# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    game_utility_grid = update_grid(game_map, game_utility_grid)
    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    game_utility_grid = reinforce(game_map, game_utility_grid, 10, ALPHA, GAMMA, COST)

    all_available_dropoffs = get_all_depos(me)

    activate_delivery_bots(game)

    command_queue = []

    for ship in me.get_ships():
        a, b = ship.position.x, ship.position.y
        game_utility_grid[a][b].display_data()
        if ship.id in delivery_bots:
            command_queue.append(ship.move(game_map.naive_navigate(ship, get_closest_drop_off(game, ship.position))))
        else:
            # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
            #   Else, collect halite.
            ship_x, ship_y = ship.position.x, ship.position.y
            ship_utility = deepcopy(game_utility_grid[ship_x][ship_y].utilities)
            ship_utility.sort(key=by_halite, reverse=True)
            for i in range(5):
                if game_map[ship.position.directional_offset(ship_utility[i][0])].is_occupied and ship.position.directional_offset(ship_utility[i][0]) != ship.position:
                    logging.info("continues")
                    continue
                else:
                    if Direction.convert(ship_utility[i][0]) == "o":
                        logging.info("still at %s", ship.stay_still())
                        command_queue.append(ship.stay_still())
                    else:
                        logging.info("logging %s", ship_utility[i][0])
                        command_queue.append(ship.move(ship_utility[i][0]))
                    break

        # if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
        #     command_queue.append(
        #         ship.move(
        #             random.choice([ Direction.North, Direction.South, Direction.East, Direction.West ])))
        # else:
        #     command_queue.append(ship.stay_still())

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    logging.info(command_queue)
    game.end_turn(command_queue)

