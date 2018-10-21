#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt
# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

from hlt.game_map import GameMap
# This library allows you to generate random numbers.
import random
from math import inf, pow

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()


def get_total_turn_count(input_game):
    return 3.125 * input_game.game_map.height + 300


def return_home_halite_level(input_game):
    total_turns = get_total_turn_count(input_game)
    if input_game.turn_number >= 0.8 * total_turns:
        return (-2 * ((input_game.turn_number/total_turns)+0.05) + 0.4) * constants.MAX_HALITE  # y = mx + c, linear scale
    else:
        return constants.MAX_HALITE


# As soon as you call "ready" function below, the 2 second per turn timer will start.
def gridlock(input_game_map, pos, atleast=4):
    neighbor_count = 0
    neighborhood = pos.get_surrounding_cardinals()
    for n in neighborhood:
        if input_game_map[n].is_occupied:
            neighbor_count += 1
    if neighbor_count >= atleast:
        return True
    else: 
        return False


def gridopen(input_game_map, pos, atleast=2):
    neighbor_count = 0
    neighborhood = pos.get_surrounding_cardinals()
    for n in neighborhood:
        if input_game_map[n].is_occupied:
            neighbor_count += 1
    if neighbor_count <= atleast:
        return True
    else: 
        return False


def get_closest_dropoff(input_me, input_ship):
    depo = [input_me.shipyard.position]
    for d in input_me.get_dropoffs():
        depo.append(d.position)


def random_move(input_map, input_ship, reserved_positions, check_occupied=False):
    options = input_ship.position.get_surrounding_cardinals()
    # random.shuffle(options)
    found = False
    for o in options:
        if check_occupied and not input_map[o].is_occupied and o not in reserved_positions:
            found = True
            return o
        elif o not in reserved_positions:
            found = True
            return o
    if not found:
        return input_ship.position


def resource_graph(input_game):
    all_resources = []
    for x in range(input_game.game_map.width):
        for y in range(input_game.game_map.height):
            position = Position(x, y)
            all_resources.append((position, input_game.game_map[position].halite_amount))
            # all_resources[(x, y)] = input_game.game_map[position].halite_amount
    return all_resources


def get_reproduction_rate(input_game):
    x = (input_game.turn_number/get_total_turn_count(input_game))*10
    prob = 256 * pow(0.5, x)
    return (prob/10.0) - 0.1


def get_enemy_shipyards(input_game):
    all_enemy_shipyards = []
    for x in range(input_game.game_map.width):
        for y in range(input_game.game_map.height):
            position = Position(x, y)
            if input_game.game_map[position].has_structure and position not in get_all_depos(input_game.me):
                all_enemy_shipyards.append(position)
    return all_enemy_shipyards


def by_halite(element):
        return element[1]


def get_all_depos(input_me):
    my_depos = []
    depos = input_me.get_dropoffs()
    for d in depos:
        my_depos.append(d.position)
    return my_depos + [input_me.shipyard.position]


def get_potential_dropoffs(input_game):
    mean_halite_at_all_locations = []
    for x in range(input_game.game_map.width):
        for y in range(input_game.game_map.height):
            position = Position(x, y)
            halite = input_game.game_map[position].halite_amount
            cardinals = position.get_surrounding_cardinals()
            for cardinal in cardinals:
                halite += input_game.game_map[cardinal].halite_amount
            mean = halite/5.0
            mean_halite_at_all_locations.append((position, mean))
    mean_halite_at_all_locations.sort(key=by_halite, reverse=True)
    dropoffs = mean_halite_at_all_locations[:4]
    return dropoffs


def get_all_ship_positions(input_me):
    all_ships = []
    for shp in input_me.get_ships():
        all_ships.append(shp.position)
    return all_ships


best_dropoff_options = get_potential_dropoffs(game)
target_lock = {}
resource_dict = resource_graph(game)
# for pos, halite in resource_graph.items():

# dictionary to track if the bot was still the last n number of times
still_bot_dict = {}
# lists to track the bots that were still in the last turn
still_bots = []
# lists to track the bots that were moving in the last turn
scout_bots = []

game.ready("TheDragonSlayer")
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
    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    # collection of positions that the ships have chosen to take next
    next_positions = []
    # get enemy shipyard and dock information
    # check every 100 turn number to find the best location for creating a new drop off
    potential_dropoff_location = None
    if game.turn_number in [1, 100, 200, 300]:
        enemy_shipyards = get_enemy_shipyards(game)
        closest = inf
        for enemy in enemy_shipyards:
            for dropoff in best_dropoff_options:
                if game_map.calculate_distance(enemy, dropoff[0]) < closest:
                    closest = game_map.calculate_distance(enemy, dropoff[0])
                    potential_dropoff_location = dropoff[0]

    # a collection of positions of all the ships in my fleet
    all_ship_positions = get_all_ship_positions(me)

    for ship in me.get_ships():
        if game.turn_number < 10:
            logging.info(ship.id)
            logging.info(next_positions)
        # check if the shp is full and needs to go back to deposit it's halite 
        # need to check the distance as well to see if it's worth going back - To Be Added (TBA)
        if ship.halite_amount >= return_home_halite_level(game) and ship.id not in target_lock:
            closest = inf
            target = me.shipyard.position
            for depo in get_all_depos(me):
                logging.info("depo %s", depo)
                if game_map.calculate_distance(ship.position, depo) < closest:
                    closest = game_map.calculate_distance(ship.position, depo)
                    target = depo
                    logging.info("target %s", target)
            if potential_dropoff_location is not None and game_map.calculate_distance(ship.position, potential_dropoff_location) < closest and me.halite_amount > constants.DROPOFF_COST * 3:
                logging.info("got potential new drop off")
                target = potential_dropoff_location
            if not gridlock(game_map, target, 3):
                target_lock[ship.id] = target
                logging.info("the ship: %d has the target %s", ship.id, target_lock[ship.id])

        if potential_dropoff_location is not None and ship.position == potential_dropoff_location and me.halite_amount > constants.DROPOFF_COST * 3:
            ship.make_dropoff()
            if ship.id in target_lock:
                target_lock.pop(ship.id)
            potential_dropoff_location = None

        # if the ship has reached the shipyard and deposited the halite, it no longer has a locked target
        if ship.id in target_lock and (ship.position == target_lock[ship.id]):
            target_lock.pop(ship.id)

        # initialize the next position for current ship
        next_pos = ship.position

        # first, lets look at the ships that are not locked to any specific grid
        # these are the majority of the ships that are just going around
        if ship.id not in target_lock:
            for first_choice in ship.position.get_surrounding_cardinals():
                # First check conditions:
                    # the halite at my current position is 10% of the maximum halite any grid could have
                    # my current position has 50% or less halite than my neighbor
                    # the position bot is trying to go to is not occupied
                    # and hasn't been chosen as the next position by any other ship
                if game_map[ship.position].halite_amount < 0.1 * constants.MAX_HALITE \
                        and first_choice not in next_positions \
                        and game_map[ship.position].halite_amount < 0.75 * game_map[first_choice].halite_amount:
                    # move to the option with the highest halite
                    if game_map[first_choice].halite_amount > game_map[next_pos].halite_amount:
                        next_pos = first_choice
        # now we look at conditions that have a locked target and sees no gridlock
        else:
            next_pos = ship.position
            choices = ship.position.get_surrounding_cardinals()
            dist = inf
            for c in choices:
                if c not in next_positions:
                    if game_map.calculate_distance(c, target_lock[ship.id]) < dist:
                        dist = game_map.calculate_distance(c, target_lock[ship.id])
                        next_pos = c

        # if at the shipyard then get out of there as soon as possible
        if next_pos == ship.position:
            if ship.position == me.shipyard.position or (gridlock(game_map, me.shipyard.position, 4) and ship.position in me.shipyard.position.get_surrounding_cardinals()):
                next_pos = random_move(game_map, ship, next_positions)

        if next_pos == ship.position and gridopen(game_map, ship.position) and game_map[ship.position].halite_amount <= 0.05:
            next_pos = random_move(game_map, ship, next_positions)

        # enemy ship found, avoid it
        if game_map[next_pos].is_occupied and next_pos not in all_ship_positions:
            next_pos = random_move(game_map, ship, next_positions, check_occupied=True)

        next_direction = game_map.naive_navigate(ship, next_pos)

        # get the direction from the navigate function
        if ship.id in target_lock and gridlock(game_map, target_lock[ship.id], 3) and next_pos == target_lock[ship.id]:
            next_direction = (game_map.get_unsafe_moves(ship.position, next_pos) + [game_map.naive_navigate(ship, next_pos)])[0]

        # update the list of positions the bots will take
        next_positions.append(next_pos)

        # logging.info("the next pos for ship %d is %s", ship.id, next_pos)

        # finally update the next direction
        if next_direction == Direction.Still:
            command_queue.append(ship.stay_still())
        else:
            command_queue.append(ship.move(next_direction))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.

    if me.halite_amount >= constants.SHIP_COST \
            and not game_map[me.shipyard].is_occupied \
            and gridopen(game_map, me.shipyard.position, 2)\
            and random.random() <= get_reproduction_rate(game):
        command_queue.append(me.shipyard.spawn())
    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
