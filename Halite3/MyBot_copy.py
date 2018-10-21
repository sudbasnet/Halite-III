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
from math import inf

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()


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


def random_move(input_ship, reserved_positions):
    options = input_ship.position.get_surrounding_cardinals()
    random.shuffle(options)
    found = False
    for o in options:
        if o not in reserved_positions:
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


reproduction_rate = 1.0
target_lock = {}
resource_dict = resource_graph(game)
# for pos, halite in resource_graph.items():

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
    still_bots = []

    for ship in me.get_ships():
        # check if the shp is full and needs to go back to deposit it's halite
        # need to check the distance as well to see if it's worth going back - To Be Added (TBA)
        if ship.is_full and ship.id not in target_lock and not gridlock(game_map, me.shipyard.position):
            target_lock[ship.id] = me.shipyard.position

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
                        dist = game_map.calculate_distance(c, me.shipyard.position)
                        next_pos = c

        # in this step, we'll check which one of the
        if next_pos == ship.position:
            if ship.position == me.shipyard.position or (gridlock(game_map, me.shipyard.position, 3) and ship.position in me.shipyard.position.get_surrounding_cardinals()):
                next_pos = random_move(ship, next_positions)

        if next_pos == ship.position and gridopen(game_map, ship.position) and game_map[ship.position].halite_amount <= 0.05:
            next_pos = random_move(ship, next_positions)

        if next_pos == ship.position:
            next_positions.append(next_pos)
            still_bots.append(ship.id)

    for ship in me.get_ships():
        # check if the shp is full and needs to go back to deposit it's halite
        # need to check the distance as well to see if it's worth going back - To Be Added (TBA)
        if ship.is_full and ship.id not in target_lock and not gridlock(game_map, me.shipyard.position):
            target_lock[ship.id] = me.shipyard.position

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
                        dist = game_map.calculate_distance(c, me.shipyard.position)
                        next_pos = c

        # in this step, we'll check which one of the
        if next_pos == ship.position:
            if ship.position == me.shipyard.position or (gridlock(game_map, me.shipyard.position,
                                                                  3) and ship.position in me.shipyard.position.get_surrounding_cardinals()):
                next_pos = random_move(ship, next_positions)

        if next_pos == ship.position and gridopen(game_map, ship.position) and game_map[
            ship.position].halite_amount <= 0.05:
            next_pos = random_move(ship, next_positions)

        next_direction = \
        (game_map.get_unsafe_moves(ship.position, next_pos) + [game_map.naive_navigate(ship, next_pos)])[0]
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

    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and gridopen(game_map, me.shipyard.position, 2):
        command_queue.append(me.shipyard.spawn())
    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
