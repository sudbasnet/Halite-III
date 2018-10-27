#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

import random
from math import inf

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Established>>> """
# This game object contains the initial game state.
game = hlt.Game()

occupied_position = []
""" <<<Initialize all functions>>> """
# total number of turns based on the grid size (linear relationship)
def get_total_turn_count(height):
    return 3.125 * height + 300


# to check for gridlocks at a certain position "in_position"
#   "least" means that many or more directions are blocked
def gridlock(in_game_map, in_position, least=4):
    neighbor_count = 0
    neighborhood = in_position.get_surrounding_cardinals()
    for n in neighborhood:
        if in_game_map[n].is_occupied:
            neighbor_count += 1
    if neighbor_count >= least:
        return True
    else:
        return False


# to check for open directions at a certain position "in_position"
#   "least" means that many or more directions are open
def gridopen(in_game_map, in_position, least=4):
    open_count = 0
    neighborhood = in_position.get_surrounding_cardinals()
    for n in neighborhood:
        if not in_game_map[n].is_occupied:
            open_count += 1
    if open_count >= least:
        return True
    else:
        return False


# give next position randomly
# "reserved_positions" is a list of positions that the ship is not allowed to go to
def random_move(input_ship, reserved_positions):
    move_options = input_ship.position.get_surrounding_cardinals()
    random.shuffle(move_options)
    for option in move_options:
        if option not in reserved_positions:
            return option
    return input_ship.position


# give the best option for getting to the destination (Position)
def directed_move(input_map, input_ship, destination, reserved_positions, include_self=False):
    best_opt = input_ship.position
    move_options = input_ship.position.get_surrounding_cardinals()
    if include_self:
        move_options = move_options + [input_ship.position]
    d = inf
    for option in move_options:
        if option not in reserved_positions:
            if input_map.calculate_distance(option, destination) < d:
                d = input_map.calculate_distance(option, destination)
                best_opt = option
    return best_opt


# collects the data on halite_amount at each location in the map
# returns a list with tuples of (position, halite_amount)
def resource_graph(input_game):
    all_resources = []
    for x in range(input_game.game_map.width):
        for y in range(input_game.game_map.height):
            position = Position(x, y)
            all_resources.append((position, input_game.game_map[position].halite_amount))
            # all_resources[(x, y)] = input_game.game_map[position].halite_amount
    all_resources.sort(key=by_halite, reverse=True)
    return all_resources


def mean_halite(in_game_map, pos):
    halite_at_pos = in_game_map[pos].halite_amount
    for p in  pos.get_surrounding_cardinals():
        halite_at_pos += in_game_map[p].halite_amount
    return halite_at_pos/5


def get_best_resource_locations(input_game, top = 5):
    rg = resource_graph(input_game)[:top]  # return top 5
    final_rg = []
    for x in rg:
        mean_at = mean_halite(input_game.game_map, x[0])
        final_rg.append((x[0], mean_at))
    final_rg.sort(key=by_halite, reverse=True)
    return final_rg


def find_best_resource_location(pos, resource_collection):
    best_opts = []
    for opt in resource_collection:
        d = game.game_map.calculate_distance(pos, opt[0])
        best_opts.append((opt[0], d))
    best_opts.sort(key=by_halite, reverse=False)
    return best_opts


# probability of reproduction (exponential) decreases as the turn-number increases
def get_reproduction_rate(turn_number, height):
    if (turn_number/get_total_turn_count(height)) < 0.20:
        return 0.8
    elif (turn_number/get_total_turn_count(height)) < 0.30:
        return 0.7
    elif (turn_number/get_total_turn_count(height)) < 0.40:
        return 0.5
    elif (turn_number/get_total_turn_count(height)) < 0.50:
        return 0.3
    elif (turn_number/get_total_turn_count(height)) < 0.70:
        return 0.2
    elif (turn_number/get_total_turn_count(height)) < 0.100:
        return 0.1
    else:
        return 0.0
    # x = (input_game.turn_number/get_total_turn_count(input_game))*10
    # prob = 256 * pow(0.5, x)
    # return (prob/10.0) - 0.2


# find the location of enemy-shipyards and drop-offs
def get_enemy_shipyards(input_game):
    all_enemy_shipyards = []
    for x in range(input_game.game_map.width):
        for y in range(input_game.game_map.height):
            position = Position(x, y)
            if input_game.game_map[position].has_structure and position not in get_all_depos(input_game.me):
                all_enemy_shipyards.append(position)
    return all_enemy_shipyards


# for ordering by the halite amounts in the resource list
def by_halite(element):
        return element[1]


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


# get the current positions where I have a ships
def get_all_ship_positions(input_me):
    all_ships = []
    for sp in input_me.get_ships():
        all_ships.append(sp.position)
    return all_ships


def get_neighborhood_halite_details(input_game_map, position, radius):
    halite_map = []
    x = position.x
    y = position.y
    min_x = x - radius
    min_y = y - radius
    max_x = x + radius + 1
    max_y = y + radius + 1
    for i in range(min_x, max_x):
        for j in range(min_y, max_y):
            pos = Position(i, j)
            halite_map.append((pos, input_game_map[pos].halite_amount))
    halite_map.sort(key=by_halite, reverse=True)
    return halite_map


def get_neighborhood_enemy_details(input_game_map, position, radius, own_positions):
    enemy_map = []
    x = position.x
    y = position.y
    min_x = x - radius
    min_y = y - radius
    max_x = x + radius + 1
    max_y = y + radius + 1
    for i in range(min_x, max_x):
        for j in range(min_y, max_y):
            pos = Position(i, j)
            if input_game_map[pos].is_occupied and pos not in own_positions:
                enemy_map.append((pos, True))
    return enemy_map


def get_enemy_ship_locations(input_game_map, my_ships_and_depos, height, dont_check_positions = []):
    enemy_ships = []
    for x in range(height):
        for y in range(height):
            position = Position(x, y)
            if position not in dont_check_positions:
                if input_game_map[position].is_occupied and position not in my_ships_and_depos:
                    enemy_ships.append(position)
    return enemy_ships


""" <<< Map Variables and Functions >>> """
# maximum distance between two points in the map
maximum_distance_possible = game.game_map.calculate_distance(Position(round(game.game_map.width/2), round(game.game_map.width/2)), Position(0, 0))

# check the total resources available in the map
total_available_resources = 0
for r in resource_graph(game):
    total_available_resources += r[1]

# bots that re designed to go to a specific place
# usually delivery bots go to drop-offs
delivery_bots = {} # {ship.id : destination.position}

# next positions that ships will take
ship_navigation = {} # {ship.id : ship.position}

# all bot-type lists initialization
paralyzed_bots = [] # bots that have less than 10% of the halite in their position
scout_bots = [] # for experimental reasons
hunter_bots = [] # these bots look for better grid positions
gatherer_bots = [] # these are stationary bots that either don't have enough cargo to move or are collecting
confused_bots = [] # don't have a clear option (need to make them go to the best resource)
shark_bots =[] # these bots go out and collide with enemy
pilot_fish_bots = [] # these bots follow a shark bot and collect halite from the explosion

# find delivery bots, ship.ids only
def activate_delivery_bots(in_game):
    for ship in in_game.me.get_ships():

        # get the closest drop-off locaition
        closest_drop_off = get_closest_drop_off(game, ship.position)

        # If towards the end, make everyone go to the deposit
        if in_game.turn_number >= 0.95 * get_total_turn_count(in_game.game_map.height):
            delivery_bots[ship.id] = closest_drop_off

        # Free up hoarding ships that just deposited halite
        if ship.position in all_available_dropoffs and ship.id in delivery_bots:
            delivery_bots.pop(ship.id)

        # Check if any ship is full, make it a hoarder
        if ship.is_full and ship.id not in delivery_bots and not gridlock(in_game.game_map, closest_drop_off, 3):
            delivery_bots[ship.id] = closest_drop_off


# find Gatherers, they retain their positions
def find_gatherer_bots(in_game, reserved_ships):
    positions = []
    for ship in in_game.me.get_ships():
        if ((in_game.game_map[ship.position].halite_amount >= 0.04 * constants.MAX_HALITE )\
                or (in_game.game_map[ship.position].halite_amount * 0.1 > ship.halite_amount)) and ship.id not in reserved_ships:
            logging.info("ship %d is a gatherer, at position %s", ship.id, ship.position)
            positions.append(ship.position)
            ship_navigation[ship.id] = ship.position
            if in_game.game_map[ship.position].halite_amount * 0.1 > ship.halite_amount:
                paralyzed_bots.append(ship.id)
            else:
                gatherer_bots.append(ship.id)
    return positions


# find Gatherers, they retain their positions
def find_paralyzed_bots(in_game):
    positions = []
    for ship in in_game.me.get_ships():
        if in_game.game_map[ship.position].halite_amount * 0.1 > ship.halite_amount:
            logging.info("ship %d is paralyzed, at position %s", ship.id, ship.position)
            ship_navigation[ship.id] = ship.position
            positions.append(ship.position)
            paralyzed_bots.append(ship.id)
    return positions

# avoid the restricted positions (gatherers)
def get_moves_delivery_bots(in_game, reserved_positions):
    positions = []
    for ship in in_game.me.get_ships():
        if ship.id in delivery_bots and ship.position not in all_available_dropoffs:
            next_position = directed_move(in_game.game_map, ship, delivery_bots[ship.id], reserved_positions + positions + enemy_bots, include_self=False)
            ship_navigation[ship.id] = next_position
            positions.append(next_position)
            logging.info("ship %d is a delivery bot, from position %s, going to %s", ship.id, ship.position, next_position)
    return positions

# If Hunter, get directions
def get_moves_hunter_bots(in_game, reserved_positions):
    positions = []
    all_occupied_positions = []
    for ship in in_game.me.get_ships():
        halite_at_position = in_game.game_map[ship.position].halite_amount
        if ship.id not in delivery_bots and ship.id not in paralyzed_bots:
            next_position = None
            best_halite = halite_at_position
            move_options = ship.position.get_surrounding_cardinals()
            if in_game.game_map[ship.position].halite_amount >= 0.04 * constants.MAX_HALITE:
                next_position = directed_move(in_game.game_map, ship, ship.position, reserved_positions + positions + enemy_bots,
                                         include_self=True)
            for op in move_options:
                neighbor_halite = game_map[op].halite_amount
                if halite_at_position < neighbor_halite * 0.5 and op not in (reserved_positions + positions):
                    if neighbor_halite > best_halite:
                        best_halite = neighbor_halite
                        next_position = op
            if next_position is not None:
                ship_navigation[ship.id] = next_position
                positions.append(next_position)
                if next_position == ship.position:
                    gatherer_bots.append(ship.id)
                    logging.info("ship %d is a gatherer bot, from position %s, going to %s", ship.id, ship.position,
                                 next_position)
                else:
                    hunter_bots.append(ship.id)
                    logging.info("ship %d is a hunter bot, from position %s, going to %s", ship.id, ship.position,
                                 next_position)
        if ship.id in ship_navigation:
            all_occupied_positions.append(ship_navigation[ship.id])
    return all_occupied_positions

""" <<<The game will now start playing>>> """

game.ready("MyPythonBot")
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    """<<<Main Navigation Dictionary Refresh>>>"""
    ship_navigation.clear()

    """<<<All Bot Types Refresh >>>"""
    # scout ships, that will make the kessel run in 12 parsecs
    paralyzed_bots.clear()
    scout_bots.clear()
    shark_bots.clear()
    pilot_fish_bots.clear()
    hunter_bots.clear()
    gatherer_bots.clear()
    confused_bots.clear()

    """ <<<Important Map Variables that need to refresh>>> """
    # top something richest locations on the map
    rich_locations = get_best_resource_locations(game, 30)

    # collection of positions of all the ships in my fleet
    all_ship_positions = get_all_ship_positions(me)

    # get a list of all available drop-offs in my fleet
    all_available_dropoffs = get_all_depos(me)

    # get the location of all enemy ships
    enemy_bots = get_enemy_ship_locations(game_map, all_ship_positions + all_available_dropoffs, game_map.height, all_available_dropoffs)

    # get the list of best resource location (game, "top")
    best_resources = get_best_resource_locations(game, 30)

    # A command queue holds all the commands, submit it at the end of the turn.
    command_queue = []

    """ <<<Find the Next positions to occupy>>> """

    # activate any bot that might want to go home or free the bot that wants to start gathering
    activate_delivery_bots(game)

    # get all bot positions that will remain still because of paralysis
    paralyzed_bots_next_positions = find_paralyzed_bots(game)

    # get next position for bots that are trying to deliver payload
    # we give them the next priority because we dont want them still
    # its a waste of time to make them wait
    # these bots must not collide with the paralyzed bots
    delivery_bots_next_positions = get_moves_delivery_bots(game, paralyzed_bots_next_positions + enemy_bots)

    # now activate the hunter bots
    # return positions of every bot so fat, not just hunter bots
    next_positions = get_moves_hunter_bots(game, delivery_bots_next_positions + paralyzed_bots_next_positions + enemy_bots)

    # all bots not covered by the above are called confused bots
    # find next position for confused bots
    # set up directions for every bot, and add to the command_queue
    for shp in me.get_ships():
        closest_drop_off_position = get_closest_drop_off(game, shp.position)
        if shp.id not in ship_navigation:
            # next_pos = None
            # get_neighborhood_halite_details(game_map, shp.position, 2)
            # if game_map[shp.position].halite_amount < 0.025 * constants.MAX_HALITE and random.random() <= 0.7 :
            best_option = find_best_resource_location(shp.position, rich_locations)
            best_options = best_option[:1]
            random.shuffle(best_options)
            next_pos = directed_move(game_map, shp, best_options[0][0], next_positions + enemy_bots, include_self=True)
            logging.info("ship %d is a nothing bot, from position %s, doing directed move, going to %s", shp.id, shp.position, next_pos)
            if next_pos in next_positions:
                logging.info("PROBLEM")
            next_positions.append(next_pos)
            ship_navigation[shp.id] = next_pos
            confused_bots.append(shp.id)

        next_direction = (game_map.get_unsafe_moves(shp.position, ship_navigation[shp.id]) + [game_map.naive_navigate(shp, ship_navigation[shp.id])])[0]

        if game.turn_number >= 0.95 * get_total_turn_count(game_map.height) and shp.position in closest_drop_off_position.get_surrounding_cardinals():
            next_direction = game_map.get_unsafe_moves(shp.position, closest_drop_off_position)[0]

        if next_direction == Direction.Still:
            command_queue.append(shp.stay_still())
        else:
            command_queue.append(shp.move(next_direction))

    """ <<<Spawn New Ship>>> """
    # If I have enough halite and the probability distribution gives be a true value, spawn a ship.
    # Don't spawn a ship if currently have a ship at port.
    if me.halite_amount >= constants.SHIP_COST \
            and me.shipyard.position not in all_ship_positions \
            and me.shipyard.position not in next_positions \
            and gridopen(game_map, me.shipyard.position, 2) \
            and random.random() <= get_reproduction_rate(game.turn_number, game_map.height):
        command_queue.append(me.shipyard.spawn())

    # Send moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

