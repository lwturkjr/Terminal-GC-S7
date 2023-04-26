import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, FACTORY, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, all_turn_states
        WALL = config["unitInformation"][0]["shorthand"]
        FACTORY = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        all_turn_states = []
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        turn_number = game_state.turn_number
        projected_mp = game_state.project_future_MP(1)
        num_factories = self.get_num_factories(game_state)
        future_mp = num_factories + projected_mp
        enemy_unit_health_left = self.enemy_unit_health_left(game_state)
        enemy_unit_health_right = self.enemy_unit_health_right(game_state)

        enemy_unit_health = enemy_unit_health_left + enemy_unit_health_right
        

        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.
        
        
        if turn_number < 3:
            self.starting_defense(game_state)
            self.interceptor_atk(game_state)
        elif turn_number == 3:
            self.initial_deploy(game_state)
            self.main_atk(game_state)
        else:
            self.deploy_prime(game_state)
            if game_state.enemy_health <= 15 or future_mp > 40 or game_state.number_affordable(SCOUT) > 40:
                self.low_health_atk(game_state)
            elif turn_number > 5 and turn_number % 2 == 1 or game_state.number_affordable(SCOUT) > 60:
                self.main_atk(game_state)
            elif turn_number < 5:
                self.main_atk(game_state)
            elif enemy_unit_health < 2000:
                self.scout_atk(game_state)
            else:
                self.interceptor_stall(game_state)
    
        game_state.submit_turn()

    # Basic Starting Defense
    def starting_defense(self, game_state):
        # Turrets
        #tur_pos = [[2,12], [25,12], [10,12], [17,12]]
        tur_pos = [[6,12],[21,12]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
               
        #Factories
        fact_pos = [[13,3],[14,3],[13,4]]
        for pos in fact_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(FACTORY, pos)
        for pos in fact_pos:
            if game_state.contains_stationary_unit(pos):
                game_state.attempt_upgrade(pos)

    
    # Initial Deploy decision(Right or Left)
    def initial_deploy(self, game_state):
        rand_select = random.randint(1, 100)
        enemy_unit_health_left = self.enemy_unit_health_left(game_state)
        enemy_unit_health_right = self.enemy_unit_health_right(game_state)

        #wall_pos = [[0,13],[1,13],[27,13],[26,13]]
        #for pos in wall_pos:
        #    game_state.attempt_spawn(WALL, pos)

        # Let's check which side is stronger, and we'll setup our defenses on the opposit side to try and attack the weaker side
        if enemy_unit_health_left < enemy_unit_health_right:
            game_state.attempt_remove([21,12])
            self.deploy_left(game_state)
        elif enemy_unit_health_left > enemy_unit_health_right:
            game_state.attempt_remove([6,12])
            self.deploy_right(game_state)
        else:
            if (rand_select % 2) == 0:
                game_state.attempt_remove([21,12])
                self.deploy_left(game_state)
            else:
                game_state.attempt_remove([6,12])
                self.deploy_right(game_state)

    # Call left or right defense based on opponents attacks from last turn
    def deploy_prime(self, game_state):
        my_occupied = self.my_occupied(game_state)
        my_left_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) 
        my_right_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)

        my_left_edges.remove([0,13])
        my_left_edges.remove([1,12])
        my_right_edges.remove([27,13])
        my_right_edges.remove([26,12])

        wall_pos = [[0,13],[1,13],[2,13],[27,13],[26,13],[25,13]]
        if game_state.enemy_health <= 15 and game_state.contains_stationary_unit([18,4]) or game_state.number_affordable(SCOUT) > 40 and game_state.contains_stationary_unit([18,4]):
            wall_pos.remove([0,13])
            wall_pos.remove([1,13])
        elif game_state.enemy_health <= 15 and game_state.contains_stationary_unit([9,4]) or game_state.number_affordable(SCOUT) > 40 and game_state.contains_stationary_unit([9,4]):
            wall_pos.remove([27,13])
            wall_pos.remove([26,13])
        else:
            if game_state.contains_stationary_unit([18,4]):
                game_state.attempt_remove([5,11])
            else:
                game_state.attempt_remove([22,11])

        for pos in wall_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
            else:
                game_state.attempt_upgrade(pos)

        check_right = any(pos in my_right_edges for pos in my_occupied)
        check_left = any(pos in my_left_edges for pos in my_occupied)

        if check_right == True:
            self.deploy_left(game_state)
        elif check_left == True:
            self.deploy_right(game_state)
        elif check_left == False and check_right == False:
            self.initial_deploy(game_state)
        else:
            for pos in my_occupied:
                game_state.attempt_remove(pos)
        
    def deploy_left(self, game_state):
        my_factories = self.get_num_factories(game_state)
        my_occupied = self.my_occupied(game_state)
        projected_mp = game_state.project_future_MP(1)
        num_factories = self.get_num_factories(game_state)
        future_mp = num_factories + projected_mp

        wall_pos = [] # Right
        for num in range(4, 13):
            x = game_state.HALF_ARENA + num
            y =  num
            wall_pos.append([int(x), int(y)])
            wall_pos.append([17,4])
            wall_pos.append([16,4])
            wall_pos.append([15,3])
            wall_pos.append([14,2])
        for pos in wall_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
                
        wall_pos = [] # Left
        for num in range(1, 9):
            x = game_state.HALF_ARENA - 1 - num
            y =  num + 2
            wall_pos.append([int(x), int(y)])
        for pos in wall_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
        #[1,12],[2,12],[3,12]
        wall_pos_00 = [[8,13]]
        #if game_state.number_affordable(SCOUT) > 40 or future_mp > 40 or game_state.enemy_health <= 15:
        #    wall_pos_00.remove([1,12])
        #    wall_pos_00.remove([2,12])

        tur_pos = [[8,12]]
        for pos in wall_pos_00:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
            else:
                game_state.attempt_upgrade(pos)

        tur_pos = [[6,10]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
            else:
                game_state.attempt_upgrade(pos)

        fact_pos = []
        for num in range(12, 16):
            x = num
            y = 4
            fact_pos.append([int(x), int(y)])
        for pos in fact_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(FACTORY, pos)
            else:
                game_state.attempt_upgrade(pos)
        #[3,12],
        tur_pos = [[4,12]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
        #[4,11],,[25,12]
        tur_pos = [[7,10]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
        wall_pos_01 = [[8,10],[3,13],[4,13],[5,13],[6,13],[7,13],[7,12],[27,13],[26,13]]
        for pos in wall_pos_01:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
        
        if game_state.number_affordable(SCOUT) > 40 or future_mp > 40 or game_state.enemy_health <= 15:
            # ,[1,12],[2,12]
            remove = [[0,13],[1,13]]
            game_state.attempt_spawn(WALL, [5,11])
            game_state.attempt_remove([5,11])
            #game_state.attempt_spawn(WALL, [5,10])
            #game_state.attempt_remove([5,10])

            for pos in remove:
                game_state.attempt_remove(pos)
        
        # Upgrade all Turrets
        if game_state.number_affordable(TURRET) > 4 and my_factories > 10 and game_state.contains_stationary_unit([0,13]):
            my_turrets = []
            for pos in my_occupied:
                if game_state.contains_unit_of_type(TURRET, pos) != False:
                    my_turrets.append(pos)
            for pos in my_turrets:
                game_state.attempt_upgrade(pos)

        #wall_pos_02 = [[7,13],[6,13],[5,13]]
        #for pos in wall_pos:
        #    if not game_state.contains_stationary_unit(pos):
        #        game_state.attempt_spawn(WALL, pos)

        tur_pos = [[6,12],[5,12],[4,12]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
        
        # Upgrade as many key walls as possible.
        wall_pos = wall_pos_00 + wall_pos_01 #+ wall_pos_02
        for pos in wall_pos:
            game_state.attempt_upgrade(pos)

        # Upgrade all Turrets
        if game_state.number_affordable(TURRET) > 8 and my_factories > 10 and game_state.contains_stationary_unit([0,13]):
            my_turrets = []
            for pos in my_occupied:
                if game_state.contains_unit_of_type(TURRET, pos) != False:
                    my_turrets.append(pos)
            for pos in my_turrets:
                game_state.attempt_upgrade(pos)
        
        if game_state.number_affordable(WALL) > 200:
            for pos in my_occupied:
                game_state.attempt_upgrade(pos)

        if game_state.number_affordable(FACTORY) > 1:
            self.more_factories(game_state)
                 
    def deploy_right(self, game_state):
        my_factories = self.get_num_factories(game_state)
        my_occupied = self.my_occupied(game_state)
        projected_mp = game_state.project_future_MP(1)
        num_factories = self.get_num_factories(game_state)
        future_mp = num_factories + projected_mp

        wall_pos = [] # Left
        for num in range(4, 13):
            x = game_state.HALF_ARENA - 1 - num
            y =  num
            wall_pos.append([int(x), int(y)])
            wall_pos.append([10,4])
            wall_pos.append([11,4])
            wall_pos.append([12,3])
            wall_pos.append([13,2])
        for pos in wall_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
        
        wall_pos = [] # Right
        for num in range(1, 9):
            x = game_state.HALF_ARENA + num
            y =  num + 2
            wall_pos.append([int(x), int(y)])
        for pos in wall_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
        #[24,12],[25,12],[26,12],
        wall_pos_00 = [[19,13]]
        #if game_state.number_affordable(SCOUT) > 40 or future_mp > 40 or game_state.enemy_health <= 15:
        #    wall_pos_00.remove([26,12])
        #    wall_pos_00.remove([25,12])

        tur_pos = [[19,12]]
        for pos in wall_pos_00:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
            else:
                game_state.attempt_upgrade(pos)
        
        tur_pos = [[21,10]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
            else:
                game_state.attempt_upgrade(pos)
        
        fact_pos = []
        for num in range(12, 16):
            x = num
            y = 4
            fact_pos.append([int(x), int(y)])
        for pos in fact_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(FACTORY, pos)
            else:
                game_state.attempt_upgrade(pos)
               
        tur_pos = [[23,12]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
        
        #[23,11],,[2,12]
        tur_pos = [[20,10],[20,9]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
        wall_pos_01 = [[19,10],[24,13],[23,13],[22,13],[21,13],[20,13],[20,12],[0,13],[1,13]]
        for pos in wall_pos_01:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(WALL, pos)
        
        if game_state.number_affordable(SCOUT) > 40 or future_mp > 40 or game_state.enemy_health <= 15:
            #,[26,12],[25,12]
            remove = [[27,13],[26,13]]
            game_state.attempt_spawn(WALL, [22,11])
            game_state.attempt_remove([22,11])
            #game_state.attempt_spawn(WALL, [22,10])
            #game_state.attempt_remove([22,10])

            for pos in remove:
                game_state.attempt_remove(pos)
   
        # Upgrade all Turrets
        if game_state.number_affordable(TURRET) > 4 and my_factories > 10 and game_state.contains_stationary_unit([27,13]):
            my_turrets = []
            for pos in my_occupied:
                if game_state.contains_unit_of_type(TURRET, pos) != False:
                    my_turrets.append(pos)
            for pos in my_turrets:
                game_state.attempt_upgrade(pos)
        
        #wall_pos_02 = [[20,13],[21,13],[22,13]]
        #for pos in wall_pos_02:
        #    if not game_state.contains_stationary_unit(pos):
        #        game_state.attempt_spawn(WALL, pos)

        tur_pos = [[21,12],[22,12],[23,12]]
        for pos in tur_pos:
            if not game_state.contains_stationary_unit(pos):
                game_state.attempt_spawn(TURRET, pos)
        
        # Upgrade as many key walls as possible.
        wall_pos = wall_pos_00 + wall_pos_01 #+ wall_pos_02
        for pos in wall_pos:
            game_state.attempt_upgrade(pos)
        
        # Upgrade all Turrets
        if game_state.number_affordable(TURRET) > 8 and my_factories > 10 and game_state.contains_stationary_unit([27,13]):
            my_turrets = []
            for pos in my_occupied:
                if game_state.contains_unit_of_type(TURRET, pos) != False:
                    my_turrets.append(pos)
            for pos in my_turrets:
                game_state.attempt_upgrade(pos)
        
        if game_state.number_affordable(WALL) > 200:
            for pos in my_occupied:
                game_state.attempt_upgrade(pos)

        if game_state.number_affordable(FACTORY) > 1:
            self.more_factories(game_state)

    
    def more_factories(self, game_state):
    
        if not game_state.contains_stationary_unit([9,4]):
            fact_pos = []
            for num in range(11,19):
                x = num
                y = 5
                fact_pos.append([int(x), int(y)])
            for num in range(10,20):
                x = num
                y = 6
                fact_pos.append([int(x), int(y)])
            for num in range(9,21):
                x = num
                y = 7
                fact_pos.append([int(x), int(y)])
            for num in range(8,22):
                x = num
                y = 8
                fact_pos.append([int(x), int(y)])
            for num in range(7,23):
                x = num
                y = 9
                fact_pos.append([int(x), int(y)])
            for num in range(9,24):
                x = num
                y = 10
                fact_pos.append([int(x), int(y)])
            for num in range(14,25):
                x = num
                y = 11
                fact_pos.append([int(x), int(y)])            

        elif not game_state.contains_stationary_unit([18,4]):
            fact_pos = []
            for num in range(9,17):
                x = num
                y = 5
                fact_pos.append([int(x), int(y)])
            for num in range(8,18):
                x = num
                y = 6
                fact_pos.append([int(x), int(y)])
            for num in range(7,19):
                x = num
                y = 7
                fact_pos.append([int(x), int(y)])
            for num in range(6,20):
                x = num
                y = 8
                fact_pos.append([int(x), int(y)])
            for num in range(5,20):
                x = num
                y = 9
                fact_pos.append([int(x), int(y)])
            for num in range(4,19):
                x = num
                y = 10
                fact_pos.append([int(x), int(y)])
            for num in range(3,11):
                x = num
                y = 11
                fact_pos.append([int(x), int(y)])

        for pos in fact_pos:
            if not game_state.contains_stationary_unit(pos) and game_state.number_affordable(FACTORY) > 2:
                game_state.attempt_spawn(FACTORY, pos)
        for pos in fact_pos:
            if game_state.contains_stationary_unit(pos):
                game_state.attempt_upgrade(pos)

    def main_atk(self, game_state): 
        enemy_mp = game_state.get_resource(1, 1)
        my_mp = game_state.get_resource(1,0)
        my_hp = game_state.my_health
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        #enemy_edges = self.get_enemy_edges(game_state)
        enemy_mp = game_state.get_resource(1, 1)
        enemy_occupied = self.enemy_occupied(game_state)
        enemy_turrets = self.enemy_turrets(game_state)
        turn_number = game_state.turn_number
        projected_mp = game_state.project_future_MP(1)
        num_factories = self.get_num_factories(game_state)
        future_mp = num_factories + projected_mp

        front_enemy_rows = []
        for num in range (0,28):
            x = num
            y = 14
            front_enemy_rows.append([int(x), int(y)])
        for num in range (1,27):
            x = num
            y = 15
            front_enemy_rows.append([int(x), int(y)])
        for num in range (2,26):
            x = num
            y = 16
            front_enemy_rows.append([int(x), int(y)])

        occupied_front = []
        for pos in front_enemy_rows:
            if pos in enemy_occupied:
                occupied_front.append(pos)

        enemy_unit_health_left = self.enemy_unit_health_left(game_state)
        enemy_unit_health_right = self.enemy_unit_health_right(game_state)
                    
        if turn_number < 1:
            rand_select = random.randint(1, 100)
            if (rand_select % 2) == 0:
                spawn_pos = [9,4]
            else:
                spawn_pos = [18,4]
        elif enemy_unit_health_left > enemy_unit_health_right:
            left_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
            deploy_locations = self.filter_blocked_locations(left_edges, game_state)
            spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
        elif enemy_unit_health_left < enemy_unit_health_right:
            right_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            deploy_locations = self.filter_blocked_locations(right_edges, game_state)
            spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
        else:
            spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)

        path = game_state.find_path_to_edge(spawn_pos)

        upgraded_units = []
        non_upgraded_units = []
        for pos in enemy_turrets:
            if game_state.check_if_upgraded(pos) == True:
                upgraded_units.append(pos)
            elif game_state.check_if_upgraded(pos) == False:
                non_upgraded_units.append(pos)
        
        upgraded_turret_threat = []
        for pos in upgraded_units:
            tur_range = game_state.game_map.get_locations_in_range(pos, 3.5)
            for pos in tur_range:
                if pos in path:
                    upgraded_turret_threat.append(tur_range)
        
        non_upgraded_turret_threat = []
        for pos in upgraded_units:
            tur_range = game_state.game_map.get_locations_in_range(pos, 3.5)
            for pos in tur_range:
                if pos in path:
                    non_upgraded_turret_threat.append(tur_range)
               
        tur_upgraded_scout_damage = len(upgraded_turret_threat) * 15
        tur_non_upgraded_scout_damage = len(non_upgraded_turret_threat) * 5

        total_tur_scout_damage = tur_upgraded_scout_damage + tur_non_upgraded_scout_damage

        tur_upgraded_interceptor_damage = len(upgraded_turret_threat) * (15 * 4)
        tur_non_upgraded_interceptor_damage = len(non_upgraded_turret_threat) * (5 * 4)
        total_tur_interceptor_damage = tur_upgraded_interceptor_damage + tur_non_upgraded_interceptor_damage
        
        if turn_number > 10:
            scout_stack_health = (game_state.number_affordable(SCOUT) - 10) * 15
            int_stack_health = (game_state.number_affordable(INTERCEPTOR) - 10) * 40
        else:
            scout_stack_health = (game_state.number_affordable(SCOUT) - 5) * 15
            int_stack_health = (game_state.number_affordable(INTERCEPTOR) - 5) * 40
        
        dem_stack_damage = game_state.number_affordable(DEMOLISHER) * 6 * 2 * 4.5

        if dem_stack_damage > 300 and game_state.number_affordable(SCOUT) < 40 and future_mp < 40 and enemy_mp < 30 or len(occupied_front) > 25 and dem_stack_damage > 350 and game_state.number_affordable(SCOUT) < 45 and enemy_mp < 30:
            #gamelib.debug_write("Demolisher atk")
            self.demolisher_atk(game_state)
        elif scout_stack_health > total_tur_scout_damage and turn_number > 1 and enemy_mp < my_hp + 15 or game_state.number_affordable(SCOUT) >= 45:
            #gamelib.debug_write("Scout atk")
            self.scout_atk(game_state)
        elif int_stack_health > total_tur_interceptor_damage and enemy_mp < 15 and my_mp < 15 or game_state.turn_number < 2:
            #gamelib.debug_write("Interceptor atk")
            self.interceptor_atk(game_state)
        else:
            #gamelib.debug_write("Interceptor attack")
            #self.interceptor_stall(game_state)
            return
    
    def low_health_atk(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        turn_number = game_state.turn_number
        projected_mp = game_state.project_future_MP(1)
        num_factories = self.get_num_factories(game_state)
        future_mp = num_factories + projected_mp

        enemy_unit_health_left = self.enemy_unit_health_left(game_state)
        enemy_unit_health_right = self.enemy_unit_health_right(game_state)

        spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)

        if game_state.contains_unit_of_type(WALL, [22,10]) and game_state.contains_stationary_unit([25,12]) and game_state.contains_stationary_unit([26,12]) or game_state.contains_unit_of_type(WALL, [5,11]) and game_state.contains_stationary_unit([1,12]) and game_state.contains_stationary_unit([2,12]):
            return
       

        if game_state.number_affordable(SCOUT) > 35:
            if game_state.number_affordable(SCOUT) > 40 or future_mp > 40:
                if game_state.contains_stationary_unit([18,4]):
                    spawn_pos00 = [14,0]
                    spawn_pos01 = [16,2]

                    if not game_state.contains_stationary_unit([1,12]) and not game_state.contains_stationary_unit([2,12]) and not game_state.contains_stationary_unit([0,13]) and not game_state.contains_stationary_unit([1,13]):
                        
                        game_state.attempt_spawn(SCOUT,spawn_pos00, 15)

                        while game_state.number_affordable(SCOUT) > 0:
                            game_state.attempt_spawn(SCOUT,spawn_pos01)
                    else:
                        return

                else: 
                    spawn_pos00 = [13,0]
                    spawn_pos01 = [11,2]
                    
                    if not game_state.contains_stationary_unit([25,12]) and not game_state.contains_stationary_unit([26,12]) and not game_state.contains_stationary_unit([27,13]) and not game_state.contains_stationary_unit([26,13]):
                        
                        game_state.attempt_spawn(SCOUT,spawn_pos00, 15)

                        while game_state.number_affordable(SCOUT) > 0:
                            game_state.attempt_spawn(SCOUT,spawn_pos01)
                    else:
                        return

            elif not game_state.contains_stationary_unit([9,4]):
                spawn_pos00 = [11,2]
                spawn_pos01 = [13,0]
                
                game_state.attempt_spawn(SCOUT,spawn_pos00, 15)

                while game_state.number_affordable(SCOUT) > 0:
                    game_state.attempt_spawn(SCOUT,spawn_pos01)

            elif not game_state.contains_stationary_unit([18,4]):
                spawn_pos00 = [16,2]
                spawn_pos01 = [14,0]
            
                game_state.attempt_spawn(SCOUT,spawn_pos00, 15)

                while game_state.number_affordable(SCOUT) > 0:
                    game_state.attempt_spawn(SCOUT,spawn_pos01)
        else:
            if game_state.enemy_health <= 15 and game_state.number_affordable(SCOUT) > 15:
                half_stack = game_state.number_affordable(SCOUT) / 2
                if not game_state.contains_stationary_unit([1,12]) and not game_state.contains_stationary_unit([2,12]) and not game_state.contains_stationary_unit([0,13]) and not game_state.contains_stationary_unit([1,13]):
                    if game_state.contains_stationary_unit([18,4]):
                        spawn_pos00 = [14,0]
                        spawn_pos01 = [16,2]

                        game_state.attempt_spawn(SCOUT, spawn_pos00, int(half_stack))

                        while game_state.number_affordable(SCOUT) > 0:
                            game_state.attempt_spawn(SCOUT, spawn_pos01)
                    else:
                        return
                
                elif game_state.contains_stationary_unit([9,4]) and game_state.number_affordable(SCOUT) > 15:
                    if not game_state.contains_stationary_unit([25,12]) and not game_state.contains_stationary_unit([26,12]) and not game_state.contains_stationary_unit([27,13]) and not game_state.contains_stationary_unit([26,13]):
                        spawn_pos00 = [13,0]
                        spawn_pos01 = [11,2]

                        game_state.attempt_spawn(SCOUT, spawn_pos00, int(half_stack))

                        while game_state.number_affordable(SCOUT) > 0:
                            game_state.attempt_spawn(SCOUT, spawn_pos01)
                    else:
                        return
                else:
                    return


    def interceptor_stall(self, game_state):
        #enemy_spawns_last_turn = self.enemy_spawns_one_turn(game_state)
        breaches_on_me = self.detect_breaches_on_self(game_state)
        #turn_number = game_state.turn_number
        enemy_mp = game_state.get_resource(1, 1)
        my_turrets = self.my_turrets(game_state)
        #friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        enemy_spawn_guess = self.hypothetical_enemy_spawn(game_state)

        path = game_state.find_path_to_edge(enemy_spawn_guess[0])

        upgraded_units = []
        non_upgraded_units = []
        for pos in my_turrets:
            if game_state.check_if_upgraded(pos) == True:
                upgraded_units.append(pos)
            elif game_state.check_if_upgraded(pos) == False:
                non_upgraded_units.append(pos)
        
        upgraded_turret_threat = []
        for pos in upgraded_units:
            tur_range = game_state.game_map.get_locations_in_range(pos, 3.5)
            for pos in tur_range:
                if pos in path:
                    upgraded_turret_threat.append(tur_range)
        
        non_upgraded_turret_threat = []
        for pos in upgraded_units:
            tur_range = game_state.game_map.get_locations_in_range(pos, 3.5)
            for pos in tur_range:
                if pos in path:
                    non_upgraded_turret_threat.append(tur_range)
               
        tur_upgraded_scout_damage = len(upgraded_turret_threat) * 15
        tur_non_upgraded_scout_damage = len(non_upgraded_turret_threat) * 5

        my_turret_dmg = tur_upgraded_scout_damage + tur_non_upgraded_scout_damage

       #if game_state.contains_stationary_unit([18,4]) and len(breaches_on_me) > 0 or enemy_mp * 15 > my_turret_dmg and game_state.contains_stationary_unit([18,4]):
       #    game_state.attempt_spawn(INTERCEPTOR, [5,8], 1)
       #elif game_state.contains_stationary_unit([9,4]) and len(breaches_on_me) > 0 or enemy_mp * 15 > my_turret_dmg and game_state.contains_stationary_unit([9,4]):
       #    game_state.attempt_spawn(INTERCEPTOR, [22,8], 1)
       #else:
       #    return

        if enemy_mp > 10 and enemy_mp <= 20 and my_turret_dmg < enemy_mp * 15:
            if game_state.contains_stationary_unit([18,4]) and len(breaches_on_me) > 0 and game_state.contains_stationary_unit([18,4]):
                game_state.attempt_spawn(INTERCEPTOR, [5,8], 1)
            elif game_state.contains_stationary_unit([9,4]) and len(breaches_on_me) > 0 and game_state.contains_stationary_unit([9,4]):
                game_state.attempt_spawn(INTERCEPTOR, [22,8], 1)
            else:
                return
        elif enemy_mp > 20 and enemy_mp <= 30 and my_turret_dmg < enemy_mp * 15:    
            if game_state.contains_stationary_unit([18,4]) and len(breaches_on_me) > 0 and game_state.contains_stationary_unit([18,4]):
                game_state.attempt_spawn(INTERCEPTOR, [5,8], 3)
            elif game_state.contains_stationary_unit([9,4]) and len(breaches_on_me) > 0 and game_state.contains_stationary_unit([9,4]):
                game_state.attempt_spawn(INTERCEPTOR, [22,8], 3)
            else:
                return
        elif enemy_mp > 40 and my_turret_dmg < enemy_mp * 15:
            if game_state.contains_stationary_unit([18,4]) and len(breaches_on_me) > 0 and game_state.contains_stationary_unit([18,4]):
                game_state.attempt_spawn(INTERCEPTOR, [5,8], 5)
            elif game_state.contains_stationary_unit([9,4]) and len(breaches_on_me) > 0 and game_state.contains_stationary_unit([9,4]):
                game_state.attempt_spawn(INTERCEPTOR, [22,8], 5)
            else: 
                return
        else:
            return

    def scout_atk(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        turn_number = game_state.turn_number

        enemy_unit_health_left = self.enemy_unit_health_left(game_state)
        enemy_unit_health_right = self.enemy_unit_health_right(game_state)

        #spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)

        if game_state.number_affordable(SCOUT) > 30:
            if game_state.contains_stationary_unit([9,4]):
                spawn_pos00 = [13,0]
                spawn_pos01 = [11,2]
                
                game_state.attempt_spawn(SCOUT,spawn_pos00, 15)

                while game_state.number_affordable(SCOUT) > 0:
                    game_state.attempt_spawn(SCOUT,spawn_pos01)

            elif game_state.contains_stationary_unit([18,4]):
                spawn_pos00 = [14,0]
                spawn_pos01 = [16,2]
            
                game_state.attempt_spawn(SCOUT,spawn_pos00, 15)

                while game_state.number_affordable(SCOUT) > 0:
                    game_state.attempt_spawn(SCOUT,spawn_pos01)
                
        else:
            if turn_number == 0:
                rand_select = random.randint(1, 100)
                if (rand_select % 2) == 0:
                    spawn_pos = [9,4]
                else:
                    spawn_pos = [18,4]
            elif enemy_unit_health_left > enemy_unit_health_right:
                left_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
                deploy_locations = self.filter_blocked_locations(left_edges, game_state)
                spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
            elif enemy_unit_health_left < enemy_unit_health_right:
                right_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
                deploy_locations = self.filter_blocked_locations(right_edges, game_state)
                spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
            else:
                if game_state.contains_stationary_unit([9,4]):
                    spawn_pos = [13,0]
                elif game_state.contains_stationary_unit([18,4]):
                    spawn_pos = [14,0]
                else:
                    spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)

        while game_state.number_affordable(SCOUT) > 0:
            game_state.attempt_spawn(SCOUT,spawn_pos)

    def interceptor_atk(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
        enemy_mp = game_state.get_resource(1, 1)

        if game_state.turn_number < 3:
            #spawn_pos = random.choice(deploy_locations)
            locations = [[9,4],[18,4],[22,8],[5,8]]
            spawn_pos = spawn_pos = random.choice(locations)
            while game_state.number_affordable(INTERCEPTOR) > 0:
               game_state.attempt_spawn(INTERCEPTOR, spawn_pos)
        elif game_state.turn_number < 1:
            spawn_pos = random.choice(deploy_locations)
            while game_state.number_affordable(INTERCEPTOR) > 0:
               game_state.attempt_spawn(INTERCEPTOR, spawn_pos)
        else:
            if game_state.contains_stationary_unit([18,4]):
                spawn_pos = [8,5]
            elif game_state.contains_stationary_unit([9,4]):
                spawn_pos = [19,5]
            elif game_state.number_affordable(INTERCEPTOR) >= 10:
                self.interceptor_stall(game_state)                
            else:
                spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
            
            while game_state.number_affordable(INTERCEPTOR) > 3:
                game_state.attempt_spawn(INTERCEPTOR,spawn_pos)

    def demolisher_atk(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        turn_number = game_state.turn_number
        enemy_unit_health_left = self.enemy_unit_health_left(game_state)
        enemy_unit_health_right = self.enemy_unit_health_right(game_state)
            
        if enemy_unit_health_left < enemy_unit_health_right and game_state.contains_stationary_unit([9,4]):
            spawn_pos = [13,0]
            while(game_state.number_affordable(DEMOLISHER) > 0):
                game_state.attempt_spawn(DEMOLISHER,spawn_pos)
        elif enemy_unit_health_left > enemy_unit_health_right and game_state.contains_stationary_unit([9,4]):
            spawn_pos = [22,8]
            while(game_state.number_affordable(DEMOLISHER) > 0):
                game_state.attempt_spawn(DEMOLISHER,spawn_pos)
        elif enemy_unit_health_left < enemy_unit_health_right and game_state.contains_stationary_unit([18,4]):
            spawn_pos = [5,8]
            while(game_state.number_affordable(DEMOLISHER) > 0):
                game_state.attempt_spawn(DEMOLISHER,spawn_pos)
        elif enemy_unit_health_left > enemy_unit_health_right and game_state.contains_stationary_unit([18,4]):
            spawn_pos = [14,0]
            while(game_state.number_affordable(DEMOLISHER) > 0):
                game_state.attempt_spawn(DEMOLISHER,spawn_pos)
        else:
            spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
            while(game_state.number_affordable(DEMOLISHER) > 0):
                game_state.attempt_spawn(DEMOLISHER,spawn_pos)

    def target_rear_factories(self, game_state):
        deploy_locations = [[3,10],[24,10]]
        enemy_factories = self.get_enemy_factories(game_state)
        enemy_left_edges = self.get_enemy_edge_left(game_state)
        
        if game_state.turn_number > 0:
            enemy_spawns_last_turn = self.enemy_spawns_one_turn(game_state)
        else: 
            enemy_spawns_last_turn = []
        
        left_attacks = []
        right_attacks = []
        for pos in enemy_spawns_last_turn:
            if pos in enemy_left_edges:
                left_attacks.append(pos)
            else:
                right_attacks.append(pos)

        enemy_unit_health_left = self.enemy_unit_health_left(game_state)
        enemy_unit_health_right = self.enemy_unit_health_right(game_state)

        num_enemy_factories = len(enemy_factories)

        factories_left = []
        factories_right = []
        for pos in enemy_factories:
            if pos[0] < 14:
                factories_left.append(pos)
            else:
                factories_right.append(pos)

        if enemy_unit_health_left < enemy_unit_health_right and len(factories_right) > len(factories_left) and len(right_attacks) > len(left_attacks):
            left_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
            deploy_locations = self.filter_blocked_locations(left_edges, game_state)
            spawn_pos = [1,12]
        elif enemy_unit_health_left > enemy_unit_health_right and len(factories_right) < len(factories_left) and len(right_attacks) < len(left_attacks):
            right_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
            deploy_locations = self.filter_blocked_locations(right_edges, game_state)
            spawn_pos = [26,12]
        else:
            spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)
        
        path = game_state.find_path_to_edge(spawn_pos)

        range_from_path = []
        for pos in path:
            locations_in_range = game_state.game_map.get_locations_in_range(pos, 3.5)
            range_from_path.append(locations_in_range)
        combined_list = sum(range_from_path, [])
        
        turrets_in_range_of_path = []
        for pos in combined_list:
            if game_state.contains_unit_of_type(TURRET, pos) != False and pos not in turrets_in_range_of_path and pos[1] > 13:
                turrets_in_range_of_path.append(pos)

        upgraded_units = []
        non_upgraded_units = []
        for pos in turrets_in_range_of_path:
            if game_state.check_if_upgraded(pos) == True:
                upgraded_units.append(pos)
            elif game_state.check_if_upgraded(pos) == False:
                non_upgraded_units.append(pos)

        locations_in_range_of_upgraded = []
        for pos in upgraded_units:
            if pos in game_state.game_map.get_locations_in_range(pos, 3.5):
                locations_in_range_of_upgraded.append(pos)

        locations_in_range_of_non_upgraded = []
        for pos in non_upgraded_units:
            if pos in game_state.game_map.get_locations_in_range(pos, 2.5):
                locations_in_range_of_non_upgraded.append(pos)

        upgraded_damage_spaces = []
        non_upgraded_damage_spaces = []
        for pos in path:
            if pos in locations_in_range_of_upgraded:
                upgraded_damage_spaces.append(pos)
            elif pos in locations_in_range_of_non_upgraded:
                non_upgraded_damage_spaces.append(pos)
            
        
        tur_upgraded_demolisher_damage = len(upgraded_damage_spaces) * (15 * 2)
        tur_non_upgraded_demolisher_damage = len(non_upgraded_damage_spaces) * (5 * 2)

        tur_damage_demolisher = tur_upgraded_demolisher_damage + tur_non_upgraded_demolisher_damage

        dem_stack_health = game_state.number_affordable(DEMOLISHER) * 5

        if num_enemy_factories >= 2 and dem_stack_health > tur_damage_demolisher:
            while game_state.number_affordable(DEMOLISHER) > 0:
                game_state.attempt_spawn(DEMOLISHER, spawn_pos)
        elif num_enemy_factories >= 2 and dem_stack_health > tur_damage_demolisher:
            while game_state.number_affordable(DEMOLISHER) > 0:
                game_state.attempt_spawn(DEMOLISHER, spawn_pos)
        else:
            self.main_atk(game_state)

                
#===============================================================================================================# 
#================================================= FUNCTIONS ===================================================#
#===============================================================================================================#
    # On action, need this for detecting breaches, and getting enemy info
    # Need to add self.on_action(game_state_string) under def start(self): in algocore.py
    def on_action_frame(self, turn_string):
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        #events = state["events"]
        #breaches = events["breach"]
        #selfDestructs = events["selfDestruct"]
        try:
            all_turn_states[state["turnInfo"][1]][state["turnInfo"][2]] = state
        except Exception:
            all_turn_states.append([])
            all_turn_states[state["turnInfo"][1]].append(state)
    def detect_breaches_on_opponent(self, game_state):
        list_breaches = []
        if game_state.turn_number != 0:
            for frame in all_turn_states[game_state.turn_number -1]:
                for breach in frame["events"]["breach"]:
                    if breach[4] == 1:
                        list_breaches.append(breach[0])
            return list_breaches
    #Detect breaches made on us
    def detect_breaches_on_self(self, game_state):
        list_breaches = []
        if game_state.turn_number != 0:
            for frame in all_turn_states[game_state.turn_number -1]:
                for breach in frame["events"]["breach"]:
                    if breach[4] == 2:
                        list_breaches.append(breach[0])
            return list_breaches
    # Check if we self destructed last round
    def detect_our_selfDestructs(self, game_state):
        list_selfDestructs = []
        if game_state.turn_number != 0:
            for frame in all_turn_states[game_state.turn_number -1]:
                for selfDestruct in frame["events"]["selfDestruct"]:
                    if selfDestruct[4] == 1:
                        list_selfDestructs.append(selfDestruct[0])
            return list_selfDestructs

    def enemy_unit_health_right(self, game_state):
        enemy_occupied = self.enemy_occupied(game_state)
        for pos in enemy_occupied:
            if pos[0] < 13:
               enemy_occupied.remove(pos)
        total_health = 0
        for pos in enemy_occupied:
            unit = game_state.game_map[pos][0] 
            total_health = unit.health + total_health
        return total_health
    
    def enemy_unit_health_left(self, game_state):
        enemy_occupied = self.enemy_occupied(game_state)
        for pos in enemy_occupied:
            if pos[0] > 14:
               enemy_occupied.remove(pos)
        total_health = 0
        for pos in enemy_occupied:
            unit = game_state.game_map[pos][0] 
            total_health = unit.health + total_health

        return total_health

    # Breaches on right side
    def right_breached_on_self(self, game_state):
        list_breaches = self.detect_breaches_on_self(game_state)
        right_edge = self.bottom_right(game_state)
        
        check = any(i in list_breaches for i in right_edge)
        if check is True:
            return True 
        else:
            return False
        
    # Breaches on the right side, at top
    def right_top_breached(self, game_state):
        list_breaches = self.detect_breaches_on_self(game_state)
        my_right_top = []
        for num in range(10, 14):
            x = game_state.HALF_ARENA + num
            y = num
            my_right_top.append([int(x), int(y)])
        
        #gamelib.debug_write("Right Top: ",my_right_top)
        check = any(i in list_breaches for i in my_right_top)

        if check is True:
            return True 
        else:
            return False

    # Breaches on left side
    def left_breached_on_self(self, game_state):
        list_breaches = self.detect_breaches_on_self(game_state)
        left_edge = self.bottom_left(game_state)
        
        check = any(i in list_breaches for i in left_edge)

        if check is True:
            return True 
        else:
            return False
    # Breaches on the right side, at top
    def left_top_breached(self, game_state):
        list_breaches = self.detect_breaches_on_self(game_state)
        my_left_top = []
        for num in range(10, 14):
            x = game_state.HALF_ARENA - 1 - num
            y = num
            my_left_top.append([int(x), int(y)])
        #gamelib.debug_write("My top left ", my_left_top)
        check = any(i in list_breaches for i in my_left_top)

        if check is True:
            return True 
        else:
            return False
    # Bottom left edges
    def bottom_left(self, game_state):
        bottom_left = []
        for num in range(0, game_state.game_map.HALF_ARENA):
            x = game_state.game_map.HALF_ARENA - 1 - num
            y = num
            bottom_left.append([int(x), int(y)])
        return bottom_left
    # Bottom right edges
    def bottom_right(self, game_state):
        bottom_right = []
        for num in range(0, game_state.game_map.HALF_ARENA):
            x = game_state.game_map.HALF_ARENA + num
            y = num
            bottom_right.append([int(x), int(y)])
        return bottom_right
    # Filter blocked locations (From starter python-algo)
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered
    # Get my occupied locations
    def my_occupied(self, game_state):
        bottom_half = []
        for i in range(game_state.ARENA_SIZE):
            for j in range(math.floor(game_state.ARENA_SIZE / 2)):
                if (game_state.game_map.in_arena_bounds([i, j])):
                    bottom_half.append([i, j])
        bottom_occupied = []
        for pos in bottom_half:
            if game_state.contains_stationary_unit(pos):
                bottom_occupied.append(pos)
        return bottom_occupied
    # Get enemy occupied positions
    def enemy_occupied(self, game_state): 
        top_half = []
        for i in range(game_state.ARENA_SIZE):
            for j in range(math.floor(game_state.ARENA_SIZE * 2)):
                if (game_state.game_map.in_arena_bounds([i, j]) and j > 13):
                    top_half.append([i, j])
        top_occupied = []
        for pos in top_half:
            if game_state.contains_stationary_unit(pos):
                top_occupied.append(pos) 
        return top_occupied     
    # Get how many factories I have
    def get_num_factories(self, game_state):
        bottom_occupied = self.my_occupied(game_state)

        my_fact_pos = []
        for pos in bottom_occupied:
            if game_state.contains_unit_of_type(FACTORY, pos) != False: 
                my_fact_pos.append(pos)

        return len(my_fact_pos)

    # Try and get enemy factory numbers, for now I guess I'll assume they're in the back.
    def get_enemy_factories(self, game_state):
        top_occupied = self.enemy_occupied(game_state)
        enemy_fact_pos = []
        for pos in top_occupied:
            if game_state.contains_unit_of_type(FACTORY, pos) != False:
                enemy_fact_pos.append(pos)
        
        return enemy_fact_pos

    # Find least damage spawn (From starter python-algo)
    def least_damage_spawn_location(self, location_options, game_state):
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]
    
    # Get enemy paths for right side attacks
    def get_enemy_paths_right(self, game_state):
        occupied = self.enemy_occupied(game_state)
        unique_spawn_pos = self.enemy_spawns_one_turn(game_state)
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.enemy_spawns_two_turn(game_state)
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.enemy_spawns_three_turn(game_state)
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.hypothetical_enemy_spawn(game_state)

        enemy_left_edge = self.get_enemy_edge_left(game_state) 
        paths_right = []
        for pos in unique_spawn_pos:
            if pos in occupied and pos in enemy_left_edge:
                game_state.game_map.remove_unit(pos)
                paths_right.append(game_state.find_path_to_edge(pos, game_state.game_map.BOTTOM_RIGHT))
            elif pos in enemy_left_edge:
                paths_right.append(game_state.find_path_to_edge(pos, game_state.game_map.BOTTOM_RIGHT))
        return paths_right
    # Get enemy paths for left side attacks 
    def get_enemy_paths_left(self, game_state):
        occupied = self.enemy_occupied(game_state)
        unique_spawn_pos = self.enemy_spawns_one_turn(game_state)
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.enemy_spawns_two_turn(game_state)
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.enemy_spawns_three_turn(game_state) 
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.hypothetical_enemy_spawn(game_state)
        enemy_right_edge = self.get_enemy_edge_right(game_state) 
        paths_left = []
        for pos in unique_spawn_pos:
            if pos in occupied and pos in enemy_right_edge:
                game_state.game_map.remove_unit(pos)
                paths_left.append(game_state.find_path_to_edge(pos, game_state.game_map.BOTTOM_LEFT))
            elif pos in enemy_right_edge:
                paths_left.append(game_state.find_path_to_edge(pos, game_state.game_map.BOTTOM_LEFT))
        return paths_left
    # Get enemy paths for right side attacks
    def get_enemy_spawn_right(self, game_state):
        unique_spawn_pos = self.enemy_spawns_one_turn(game_state)
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.hypothetical_enemy_spawn(game_state)

        enemy_right_edge = self.get_enemy_edge_right(game_state) 
        right_spawns = []
        for pos in unique_spawn_pos:
            if pos in enemy_right_edge:
                right_spawns.append(pos)
        return right_spawns
    # Get enemy paths for right side attacks
    def get_enemy_spawn_left(self, game_state):
        unique_spawn_pos = self.enemy_spawns_one_turn(game_state)
        if len(unique_spawn_pos) < 1:
            unique_spawn_pos = self.hypothetical_enemy_spawn(game_state)

        enemy_left_edge = self.get_enemy_edge_left(game_state) 
        left_spawns = []
        for pos in unique_spawn_pos:
            if pos in enemy_left_edge:
                left_spawns.append(pos)
        return left_spawns


    # Get attack paths going left
    def get_left_attacks (self, game_state):
        enemy_path_right = self.get_enemy_paths_right(game_state)
        enemy_path_left = self.get_enemy_paths_left(game_state)
        left_base = []
        for num in range(3, 14):
            x = num 
            y = 10
            left_base.append([int(x), int(y)])
        for num in range(2, 14):
            x = num 
            y = 11
            left_base.append([int(x), int(y)])
        for num in range(1, 14):
            x = num 
            y = 12
            left_base.append([int(x), int(y)])
        for num in range(0, 14):
            x = num 
            y = 13
            left_base.append([int(x), int(y)])
        for num in range(0, 14):
            x = num 
            y = 14
            left_base.append([int(x), int(y)])
        for num in range(1, 14):
            x = num 
            y = 15
            left_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left
        for num in range(2, 14):
            x = num 
            y = 16
            left_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left  
        for num in range(3, 14):
            x = num 
            y = 17
            left_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left  
        for num in range(3, 14):
            x = num 
            y = 18
            left_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left  
        left = []
        for path in combined_paths:
            for pos in path:
                if pos in left_base:
                    left.append(pos)
        return left
    # Get attack paths going right
    def get_right_attacks (self, game_state):
        enemy_path_right = self.get_enemy_paths_right(game_state)
        enemy_path_left = self.get_enemy_paths_left(game_state)
        right_base = []
        for num in range(14, 25):
            x = num 
            y = 10
            right_base.append([int(x), int(y)])
        for num in range(14, 26):
            x = num 
            y = 11
            right_base.append([int(x), int(y)])
        for num in range(14, 27):
            x = num 
            y = 12
            right_base.append([int(x), int(y)])
        for num in range(14, 28):
            x = num 
            y = 13
            right_base.append([int(x), int(y)])
        for num in range(14, 28):
            x = num 
            y = 14
            right_base.append([int(x), int(y)])
        for num in range(14, 27):
            x = num 
            y = 15
            right_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left
        for num in range(14, 26):
            x = num 
            y = 16
            right_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left
        for num in range(14, 25):
            x = num 
            y = 17
            right_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left
        for num in range(14, 24):
            x = num 
            y = 18
            right_base.append([int(x), int(y)])
        combined_paths = enemy_path_right + enemy_path_left
        right = []
        for path in combined_paths:
            for pos in path:
                if pos in right_base:
                    right.append(pos)
        return right
    
    # Get Enemy information spawn positions
    def enemy_spawns_one_turn(self, game_state):
        #enemy_edges = self.get_enemy_edges(game_state)
        if game_state.turn_number < 1:
            unique_spawn_pos = self.hypothetical_enemy_spawn(game_state)
            return unique_spawn_pos
        all_spawn_pos = []
        # 3 = SCOUT, 4 = EMP, 5 = INTERCEPTOR
        #gamelib.debug_write("p2units [3]: ", all_turn_states[game_state.turn_number -1][0]["p2Units"][3])
        # For SCOUTS/PINGS
        for i in all_turn_states[game_state.turn_number -1][0]["p2Units"][3]:
            # Pings/Scouts move fast and the first recorded location is always 1 away from the edge. 
            # Mobile units move vertically, then horizontally (From what I've witnessed), so we'll increase the y by one
            # This should give the actual spawn location
            all_spawn_pos.append([i[0],i[1]+1]) 
            #all_info_spawn_pos.append([i[0],i[1]])
        # For DESCTRUCTORS/EMPS
        for i in all_turn_states[game_state.turn_number -1][0]["p2Units"][4]:
            #gamelib.debug_write("[i[0],i[1]] [4]", [i[0],i[1]])
            all_spawn_pos.append([i[0],i[1]])
        # For INTERCEPTORS/SCRAMBLERS
        for i in all_turn_states[game_state.turn_number -1][0]["p2Units"][5]:
            all_spawn_pos.append([i[0],i[1]])
        unique_spawn_pos = []
        for pos in all_spawn_pos:
            if pos not in unique_spawn_pos:
                unique_spawn_pos.append(pos)
        return unique_spawn_pos
    def enemy_spawns_two_turn(self, game_state):
        if game_state.turn_number < 2:
            unique_spawn_pos = self.hypothetical_enemy_spawn(game_state)
            return unique_spawn_pos
        all_spawn_pos = []
        for i in all_turn_states[game_state.turn_number -2][0]["p2Units"][3]:    
            # Pings/Scouts move fast and the first recorded location is always 1 away from the edge. 
            # Mobile units move vertically, then horizontally (From what I've witnessed), so we'll increase the y by one
            # This should give the actual spawn location
            all_spawn_pos.append([i[0],i[1]+1]) 
        for i in all_turn_states[game_state.turn_number -2][0]["p2Units"][4]:
            all_spawn_pos.append([i[0],i[1]])
        for i in all_turn_states[game_state.turn_number -2][0]["p2Units"][5]:
            all_spawn_pos.append([i[0],i[1]])     
        unique_spawn_pos = []
        for pos in all_spawn_pos:
            if pos not in unique_spawn_pos:
                unique_spawn_pos.append(pos)
        return unique_spawn_pos
    def enemy_spawns_three_turn(self, game_state): 
        if game_state.turn_number < 3:
            unique_spawn_pos = self.hypothetical_enemy_spawn(game_state)
            return unique_spawn_pos
        all_spawn_pos = []
        for i in all_turn_states[game_state.turn_number -3][0]["p2Units"][3]:    
            # Pings/Scouts move fast and the first recorded location is always 1 away from the edge. 
            # Mobile units move vertically, then horizontally (From what I've witnessed), so we'll increase the y by one
            # This should give the actual spawn location
            all_spawn_pos.append([i[0],i[1]+1]) 
        for i in all_turn_states[game_state.turn_number -3][0]["p2Units"][4]:
            all_spawn_pos.append([i[0],i[1]])
        for i in all_turn_states[game_state.turn_number -3][0]["p2Units"][5]:
            all_spawn_pos.append([i[0],i[1]])     
        unique_spawn_pos = []
        for pos in all_spawn_pos:
            if pos not in unique_spawn_pos:
                unique_spawn_pos.append(pos)
        return unique_spawn_pos
    
    # Enemy right edges
    def get_enemy_edge_right(self, game_state):
        enemy_right_edge = game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
        return enemy_right_edge

    # Enemy left edges
    def get_enemy_edge_left(self, game_state):
        enemy_left_edge = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT)
        return enemy_left_edge

    def get_enemy_edges(self, game_state):
        enemy_edges = self.get_enemy_edge_left(game_state) + self.get_enemy_edge_right(game_state)
        
        return enemy_edges

    # We attempt to check all paths for opponent destructor and return the safest path
    def hypothetical_enemy_spawn(self, game_state):
        enemy_edges = self.get_enemy_edges(game_state)
        deploy_locations = self.filter_blocked_locations(enemy_edges, game_state)

        spawns = []
        spawn_pos = self.least_damage_spawn_location(deploy_locations, game_state)

        spawns.append(spawn_pos)
        
        return spawns
    
    # Enemy turret threat range
    def enemy_turrets(self, game_state):
        top_occupied = self.enemy_occupied(game_state)

        enemy_tur = []
        for pos in top_occupied:
            if game_state.contains_unit_of_type(TURRET, pos) != False:
                enemy_tur.append(pos)

        return enemy_tur

    # Enemy turret threat range
    def enemy_tur_threat(self, game_state):
        top_occupied = self.enemy_occupied(game_state)

        enemy_tur = []
        for pos in top_occupied:
            if game_state.contains_unit_of_type(TURRET, pos) != False:
                enemy_tur.append(pos)
        
        upgraded_units = []
        non_upgraded_units = []
        for pos in enemy_tur:
            if game_state.check_if_upgraded(pos) == True:
                upgraded_units.append(pos)
            else:
                non_upgraded_units.append(pos)

        enemy_tur_range = []
        for pos in enemy_tur:
            if pos in upgraded_units:
                tur_range = ((game_state.game_map.get_locations_in_range(pos, 3.5)))
            elif pos in non_upgraded_units:
                tur_range = ((game_state.game_map.get_locations_in_range(pos, 2.5)))
            for pos in tur_range:
                if game_state.game_map.in_arena_bounds(pos):
                    enemy_tur_range.append(pos)
        return enemy_tur_range
    
    # My Turrets
    def my_turrets(self, game_state):
        my_occupied = self.my_occupied(game_state)

        my_tur = []
        for pos in my_occupied:
            if game_state.contains_unit_of_type(TURRET, pos) != False:
                my_tur.append(pos)

        return my_tur

    # My turret threat range
    def my_tur_threat(self, game_state):
        my_turrets = self.my_turrets(game_state)

        my_tur = []
        for pos in my_turrets:
            if game_state.contains_unit_of_type(TURRET, pos) != False:
                my_tur.append(pos)
        
        upgraded_units = []
        non_upgraded_units = []
        for pos in my_tur:
            if game_state.check_if_upgraded(pos) == True:
                upgraded_units.append(pos)
            else:
                non_upgraded_units.append(pos)

        my_tur_range = []
        for pos in my_tur:
            if pos in upgraded_units:
                tur_range = ((game_state.game_map.get_locations_in_range(pos, 3.5)))
            elif pos in non_upgraded_units:
                tur_range = ((game_state.game_map.get_locations_in_range(pos, 2.5)))
            for pos in tur_range:
                if game_state.game_map.in_arena_bounds(pos):
                    my_tur_range.append(pos)

        return my_tur_range
    
    # Enemy turret locations
    def enemy_tur_locations(self, game_state):
        top_occupied = self.enemy_occupied(game_state)

        enemy_tur = []
        for pos in top_occupied:
            if game_state.contains_unit_of_type(TURRET, pos) != False:
                enemy_tur.append(pos)

        return enemy_tur

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()