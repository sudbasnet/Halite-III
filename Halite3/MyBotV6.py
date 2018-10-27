#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.positionals import Direction, Position
import random
from math import inf, pow
# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()


# total number of turns based on the grid size (linear relationship)
def get_total_turn_count(input_game):
    return 3.125 * input_game.game_map.height + 300


# halite level for each bot at which it tries to deposit it home (linear relationship)
def return_home_halite_level(input_game):
    total_turns = get_total_turn_count(input_game)
    if input_game.turn_number <= 0.98 * total_turns:
        return constants.MAX_HALITE * 0.9
    else:
        return constants.MAX_HALITE


# to check for gridlocks at a certain position "pos", "atleast" means that many or more directions are blocked
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


# to check for open directions at a certain position "pos", "atleast" means that many or more directions are open
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


# find the position of the nearest storage point, could be the shipyard or another drop-off
def get_closest_dropoff(input_me, input_ship):
    depo = [input_me.shipyard.position]
    for d in input_me.get_dropoffs():
        depo.append(d.position)


# move randomly to the next available location, check_occupied means be safe before finding nearest random location
def random_move(input_map, input_ship, reserved_positions, check_occupied=False):
    options = input_ship.position.get_surrounding_cardinals()
    random.shuffle(options)
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
    logging.info("resource graph length %d", len(all_resources))
    return all_resources


def get_best_resource_locations(input_game, top = 5):
    return resource_graph(input_game)[:top]  # return top 5


# probability of reproduction (exponential) decreases as the turn-number increases
def get_reproduction_rate(input_game):
    if (input_game.turn_number/get_total_turn_count(input_game)) < 0.20:
        return 0.8
    elif (input_game.turn_number/get_total_turn_count(input_game)) < 0.30:
        return 0.7
    elif (input_game.turn_number/get_total_turn_count(input_game)) < 0.40:
        return 0.4
    elif (input_game.turn_number/get_total_turn_count(input_game)) < 0.50:
        return 0.2
    elif (input_game.turn_number/get_total_turn_count(input_game)) < 0.70:
        return 0.1
    elif (input_game.turn_number/get_total_turn_count(input_game)) < 0.100:
        return 0.05
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


# positions that can be potential drop off, top 10 or so from the resource graph
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
    dropoffs = mean_halite_at_all_locations[:10]
    return dropoffs


# get the current positions where I have a ship
def get_all_ship_positions(input_me):
    all_ships = []
    for shp in input_me.get_ships():
        all_ships.append(shp.position)
    return all_ships


center_of_map = Position(round(game.game_map.width/2), round(game.game_map.width/2))
maximum_distance_possible = game.game_map.calculate_distance(center_of_map, Position(0, 0))  #(from center to edge)
# logging.info("maximum distance is %s", maximum_distance_possible)
target_lock = {}
resource_dict = resource_graph(game)
# collection of positions that the ships have chosen to take next
next_positions = []
# collection of positions where the ships are collecting
still_positions = []
# collection of positions where charged ships are
charged_positions = []

# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("TheDragonSlayerV6")
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

    # get a list of all available drop-offs for myself
    all_available_dropoffs = get_all_depos(me)
    # a list of best locations
    options = get_best_resource_locations(game, 30)
    # get enemy shipyard and dock information
    # check every 100 turn number to find the best location for creating a new drop off

    """POTENTIAL DROPOFF"""
    potential_dropoff_location = None
    if game.turn_number in [100, 300]:
        best_dropoff_options = get_potential_dropoffs(game)
        enemy_shipyards = get_enemy_shipyards(game)
        closest = inf
        for dropoff in best_dropoff_options:
            min_distance_to_my_dropoff = inf
            min_distance_to_enemy_dropoff = inf
            for x in all_available_dropoffs:
                if game_map.calculate_distance(x, dropoff[0]) < min_distance_to_my_dropoff:
                    min_distance_to_my_dropoff = game_map.calculate_distance(x, dropoff[0])
                if min_distance_to_my_dropoff >=0.5 * maximum_distance_possible:
                    potential_dropoff_location = x
                    break
        logging.info("potential_dropoff_location is %s", potential_dropoff_location)
    """POTENTIAL DROPOFF"""
    # a collection of positions of all the ships in my fleet
    all_ship_positions = get_all_ship_positions(me)

    # reset the bots from last loop after spawning
    next_positions = []
    still_positions = []
    charged_positions = []

    # now, the regular loop of things
    for ship in me.get_ships():
        if (game_map[ship.position].halite_amount >= 0.01 * constants.MAX_HALITE and ship.id not in target_lock) or \
                (ship.halite_amount < 0.1 * game_map[ship.position].halite_amount):
            still_positions.append(ship.position)
        if ship.id in target_lock and ship.position not in all_available_dropoffs:
            next_pos = None
            target_lock_choices = ship.position.get_surrounding_cardinals()
            dist = inf
            for tlc in target_lock_choices:
                if tlc not in (still_positions + charged_positions):
                    if game_map.calculate_distance(tlc, target_lock[ship.id]) < dist:
                        dist = game_map.calculate_distance(tlc, target_lock[ship.id])
                        next_pos = tlc
            charged_positions.append(next_pos)

    for ship in me.get_ships():
        logging.info("captain's log %d", ship.id)
        # check if the shp is full and needs to go back to deposit it's halite
        # need to check the distance as well to see if it's worth going back - To Be Added (TBA)
        # if the ship has reached the shipyard and deposited the halite, it no longer has a locked target
        if ship.id in target_lock and (ship.position == target_lock[ship.id]):
            target_lock.pop(ship.id)

        if (ship.halite_amount >= return_home_halite_level(game) or game.turn_number > get_total_turn_count(game) * 0.99) and ship.id not in target_lock:
            closest = inf
            target = me.shipyard.position
            for depo in all_available_dropoffs:
                if game_map.calculate_distance(ship.position, depo) < closest:
                    closest = game_map.calculate_distance(ship.position, depo)
                    target = depo
                    logging.info("target %s", target)
            if potential_dropoff_location is not None and game_map.calculate_distance(ship.position, potential_dropoff_location) < closest and me.halite_amount > constants.DROPOFF_COST * 2:
                logging.info("got potential new drop off")
                target = potential_dropoff_location
            if not gridlock(game_map, target, 3):
                target_lock[ship.id] = target
                logging.info("the ship: %d has the target %s", ship.id, target_lock[ship.id])

        if potential_dropoff_location is not None and ship.position == potential_dropoff_location and me.halite_amount > constants.DROPOFF_COST * 2:
            ship.make_dropoff()
            if ship.id in target_lock:
                target_lock.pop(ship.id)
            potential_dropoff_location = None

        # initialize the next position for current ship
        next_pos = ship.position
        navigated = False
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
                        and first_choice not in still_positions \
                        and first_choice not in charged_positions \
                        and game_map[ship.position].halite_amount < 0.75 * game_map[first_choice].halite_amount:
                    # move to the option with the highest halite
                    if game_map[first_choice].halite_amount > game_map[next_pos].halite_amount:
                        next_pos = first_choice
                        navigated = True
                        logging.info("level 1")
        # now we look at conditions that have a locked target and sees no gridlock
        else:
            next_pos = ship.position
            target_lock_choices = ship.position.get_surrounding_cardinals()
            dist = inf
            for tlc in target_lock_choices:
                if tlc not in (next_positions + still_positions):  # do not check charded positins here
                    if game_map.calculate_distance(tlc, target_lock[ship.id]) < dist:
                        dist = game_map.calculate_distance(tlc, target_lock[ship.id])
                        next_pos = tlc
                        navigated = True
                        logging.info("level 2, locked")
        if navigated is False and game_map[ship.position].halite_amount < 0.025 * constants.MAX_HALITE:
            closest_to_ship = inf
            best_option = ship.position
            for opt in options:
                if game_map.calculate_distance(ship.position, opt[0]) < closest_to_ship:
                    closest_to_ship = game_map.calculate_distance(ship.position, opt[0])
                    best_option = opt[0]
            next_pos = ship.position
            target_lock_choices = ship.position.get_surrounding_cardinals()
            random.shuffle(target_lock_choices)
            dist = inf
            for tlc in target_lock_choices:
                if tlc not in (next_positions + still_positions + charged_positions):
                    if game_map.calculate_distance(tlc, best_option) < dist:
                        dist = game_map.calculate_distance(tlc, best_option)
                        next_pos = tlc
                        navigated = True
                        logging.info("level 3, nearest jewel")

        # # if at the shipyard then get out of there as soon as possible
        if next_pos == ship.position:
            if ship.position == me.shipyard.position or \
                    (gridlock(game_map, me.shipyard.position, 4) and ship.position in me.shipyard.position.get_surrounding_cardinals()):
                next_pos = random_move(game_map, ship, next_positions + still_positions + charged_positions)
                logging.info("level 4, random move")

        if next_pos == ship.position and gridopen(game_map, ship.position) and game_map[ship.position].halite_amount == 0:
            next_pos = random_move(game_map, ship, next_positions + still_positions + charged_positions)
            logging.info("level 5, random move")

        # enemy ship found, avoid it
        if game_map[next_pos].is_occupied and next_pos not in all_ship_positions and next_pos not in all_available_dropoffs:
            next_pos = random_move(game_map, ship, next_positions + still_positions + charged_positions, check_occupied=True)
            logging.info("level 5, random move")

        next_direction = game_map.naive_navigate(ship, next_pos)

        safe_direction = game_map.naive_navigate(ship, next_pos)
        unsafe_directions = game_map.get_unsafe_moves(ship.position, next_pos)

        if safe_direction in unsafe_directions:
            next_direction = safe_direction
        else:
            next_direction = (unsafe_directions + [safe_direction])[0]

        # if at a gridlock and need to break it, kill own ship
        if ship.id in target_lock and gridlock(game_map, target_lock[ship.id], 4) and next_pos == target_lock[ship.id]:
            next_direction = (game_map.get_unsafe_moves(ship.position, next_pos) + [game_map.naive_navigate(ship, next_pos)])[0]

        # update the list of positions the bots will take
        if next_direction == Direction.Still:
            logging.info("Ship is STILL")
            if ship.position in next_positions:
                logging.info("PROBLEM ENCOUNTERED")
                logging.info("ship %d wants to move to %s", ship.id, next_pos)
                logging.info(next_positions)
            next_positions.append(ship.position)
        else:
            if next_pos in next_positions:
                logging.info("PROBLEM ENCOUNTERED")
                logging.info("ship %d wants to move to %s", ship.id, next_pos)
                logging.info(next_positions)
            next_positions.append(next_pos)

        if game.turn_number > get_total_turn_count(game) * 0.97 and ship.id in target_lock and ship.position in target_lock[ship.id].get_surrounding_cardinals():
            next_direction = (game_map.get_unsafe_moves(ship.position, target_lock[ship.id]) + [game_map.naive_navigate(ship, target_lock[ship.id])])[0]
            if ship.position == target_lock[ship.id]:
                next_direction == Direction.Still

        # finally update the next direction
        if next_direction == Direction.Still:
            command_queue.append(ship.stay_still())
        else:
            command_queue.append(ship.move(next_direction))

        if game.turn_number == 2:
            logging.info("the shipyard is at %s", me.shipyard.position)
        logging.info(next_positions)
        logging.info("this is ship number %d at position %s and is going to %s", ship.id, ship.position, next_pos)
        logging.info ("this ship was navigated? %s", navigated)

    # If I have enough halite and the probability distribution gives be a true value, spawn a ship.
    # Don't spawn a ship if currently have a ship at port.
    create_new_bot = False  # First set the new bot creation indicator as False
    if me.halite_amount >= constants.SHIP_COST \
            and me.shipyard.position not in all_ship_positions \
            and me.shipyard.position not in next_positions + still_positions + charged_positions \
            and gridopen(game_map, me.shipyard.position, 2) \
            and random.random() <= get_reproduction_rate(game):
        create_new_bot = True
        command_queue.append(me.shipyard.spawn())
    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
