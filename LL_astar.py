import heapq as hq
import time
import math
from enum import Enum
import numpy as np
# graphics:
import arcade

# screen sizes:
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1050
TILE_SIZE: int


class Astar(arcade.Window):  # 36 366 98 989 LL
    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        arcade.set_background_color(arcade.color.DUTCH_WHITE)
        # scaling:
        self.scale = 0
        self.scale_names = {0: 5, 1: 10, 2: 15, 3: 22, 4: 33, 5: 45, 6: 66, 7: 90, 8: 110, 9: 165, 10: 198}
        # initial data and info:
        self.line_width = None
        self.tiles_q = None
        self.Y, self.X = SCREEN_HEIGHT - 26, SCREEN_WIDTH - 250
        self.tile_size, self.hor_tiles_q = self.get_pars()
        self.time_elapsed_ms = 0
        # grid of nodes:
        self.grid = [[Node(j, i, 1, NodeType.EMPTY) for i in range(self.hor_tiles_q)] for j in range(self.tiles_q)]
        # modes, flags and pars needed for visualization:
        self.building_walls_flag = False
        self.mode = 0  # 0 for building the walls when 1 for erasing them afterwards, 2 for a start node choosing and 3 for an end one...
        self.mode_names = {0: 'BUILDING/ERASING', 1: 'START&END_NODES_CHOOSING', 2: 'INFO_GETTING'}
        self.build_or_erase = True  # True for building and False for erasing
        self.heuristic = 0
        self.heuristic_names = {0: 'MANHATTAN', 1: 'EUCLIDIAN', 2: 'MAX_DELTA', 3: 'DIJKSTRA'}
        self.tiebreaker = None
        self.tiebreaker_names = {0: 'VECTOR_CROSS', 1: 'COORDINATES'}
        self.node_chosen = None
        self.path = None
        self.path_index = 0
        # a_star important pars:
        self.start_node = None
        self.end_node = None
        self.greedy_flag = False  # is algorithm greedy?
        self.nodes_to_be_visited = []
        self.curr_node_dict = {}
        self.max_times_visited_dict = {0: 0}
        self.neighs_added_to_heap_dict = {}
        self.iterations = 0
        self.nodes_visited = {}
        # lee_wave_spreading important pars:
        # Levi Gin area!
        # interactive pars:
        self.is_interactive = False
        self.in_interaction = False
        self.cycle_breaker_right = False
        self.cycle_breaker_left = False
        self.ticks_q = 0
        self.ticks_before = 0
        self.f_flag = False
        # walls building/erasing dicts:
        self.walls_built_erased = [([], True)]
        self.walls_index = 0

    def a_star_preparation(self):
        self.nodes_to_be_visited = [self.start_node]
        hq.heapify(self.nodes_to_be_visited)
        self.start_node.g = 0
        Node.IS_GREEDY = self.greedy_flag
        self.iterations = 0
        self.neighs_added_to_heap_dict = {0: [self.start_node]}
        self.curr_node_dict = {0: None}
        self.max_times_visited_dict = {0: 0}
        self.path = None

    def recover_path(self):
        # start point of path restoration (here we begin from the end node of the shortest path found):
        node = self.end_node
        shortest_path = []
        # path restoring (here we get the reversed path):
        while node.previously_visited_node:
            shortest_path.append(node)
            node = node.previously_visited_node
        shortest_path.append(self.start_node)
        # returns the result:
        return shortest_path

    def path_up(self):
        if self.path[self.path_index].type not in [NodeType.START_NODE, NodeType.END_NODE]:
            self.path[self.path_index].type = NodeType.PATH_NODE

    def path_down(self):
        if self.path[self.path_index].type not in [NodeType.START_NODE, NodeType.END_NODE]:
            self.path[self.path_index].type = NodeType.VISITED_NODE

    def a_star_step_up(self):
        self.neighs_added_to_heap_dict[self.iterations + 1] = []
        self.curr_node_dict[self.iterations + 1] = hq.heappop(self.nodes_to_be_visited)
        curr_node = self.curr_node_dict[self.iterations + 1]
        if self.iterations > 0 and curr_node != self.end_node:
            curr_node.type = NodeType.CURRENT_NODE
        curr_node.times_visited += 1
        if self.iterations > 1:
            if self.curr_node_dict[self.iterations].type != NodeType.END_NODE:
                self.curr_node_dict[self.iterations].type = NodeType.VISITED_NODE
        self.max_times_visited_dict[self.iterations + 1] = max(self.max_times_visited_dict[self.iterations],
                                                               curr_node.times_visited)
        if curr_node in self.nodes_visited.keys():
            self.nodes_visited[curr_node] += 1
        else:
            self.nodes_visited[curr_node] = 1
        # base case of finding the shortest path:
        if curr_node == self.end_node:
            self.path = self.recover_path()
            # curr_node.type = NodeType.VISITED_NODE
        # next step:
        # we can search for neighs on the fly or use precalculated sets:
        for neigh in curr_node.get_neighs(self):
            if neigh.g > curr_node.g + neigh.val:
                # memoization for further 'undoing':
                self.neighs_added_to_heap_dict[self.iterations + 1].append(neigh.aux_copy())
                neigh.g = curr_node.g + neigh.val
                neigh.h = neigh.heuristics[self.heuristic](neigh, self.end_node)
                if self.tiebreaker is not None:
                    neigh.tiebreaker = self.start_node.tiebreakers[self.tiebreaker](
                        self.start_node, self.end_node, neigh)
                neigh.previously_visited_node = curr_node
                if neigh not in self.nodes_visited and neigh not in [self.start_node, self.end_node]:
                    neigh.type = NodeType.NEIGH
                hq.heappush(self.nodes_to_be_visited, neigh)
        # incrementation:
        self.iterations += 1

    def a_star_step_down(self):
        curr_node = self.curr_node_dict[self.iterations]
        if self.iterations > 1:
            # times visited counter and colour 'backtracking':
            curr_node.times_visited -= 1
            if curr_node.times_visited == 0:
                if curr_node.type != NodeType.END_NODE:
                    curr_node.type = NodeType.NEIGH
            else:
                curr_node.type = NodeType.VISITED_NODE
            if self.iterations > 2:
                self.curr_node_dict[self.iterations - 1].type = NodeType.CURRENT_NODE
        if self.iterations > 0:
            # removing the current node from nodes visited:
            if self.nodes_visited[curr_node] > 1:
                self.nodes_visited[curr_node] -= 1
            else:
                self.nodes_visited.pop(curr_node)
            # removing the neighs added from the heap:
            for neigh in self.neighs_added_to_heap_dict[self.iterations]:
                y, x = neigh.y, neigh.x
                node = self.grid[y][x]
                # if node in self.nodes_to_be_visited:
                # self.nodes_to_be_visited.remove(node)
                self.remove_from_heapq(self.nodes_to_be_visited, self.nodes_to_be_visited.index(node))
                node.restore(neigh)
            # adding current node (popped out at the current iteration) to the heap:
            hq.heappush(self.nodes_to_be_visited, curr_node)
            # iteration steps back:
            self.iterations -= 1

    # from stackoverflow, removing the element from the heap, keeping the heap invariant:
    @staticmethod
    def remove_from_heapq(heap, ind: int):
        heap[ind] = heap[-1]
        heap.pop()
        if ind < len(heap):
            # as far as it is known, possible to copy the source code from the heapq module... but how to do that?..
            Astar.siftup(heap, ind)
            Astar.siftdown(heap, 0, ind)

    # source code from: https://github.com/python/cpython/blob/main/Lib/heapq.py
    @staticmethod
    def siftdown(heap, start_pos, pos):
        new_item = heap[pos]
        # Follow the path to the root, moving parents down until finding a place
        # new item fits.
        while pos > start_pos:
            parent_pos = (pos - 1) >> 1
            parent = heap[parent_pos]
            if new_item < parent:
                heap[pos] = parent
                pos = parent_pos
                continue
            break
        heap[pos] = new_item

    # source code from: https://github.com/python/cpython/blob/main/Lib/heapq.py
    @staticmethod
    def siftup(heap, pos):
        end_pos = len(heap)
        start_pos = pos
        new_item = heap[pos]
        # Bubble up the smaller child until hitting a leaf.
        child_pos = 2 * pos + 1  # leftmost child position
        while child_pos < end_pos:
            # Set child pos to index of smaller child.
            right_pos = child_pos + 1
            if right_pos < end_pos and not heap[child_pos] < heap[right_pos]:
                child_pos = right_pos
            # Move the smaller child up.
            heap[pos] = heap[child_pos]
            pos = child_pos
            child_pos = 2 * pos + 1
        # The leaf at pos is empty now. Put new item there, and bubble it up
        # to its final resting place (by sifting its parents down).
        heap[pos] = new_item
        Astar.siftdown(heap, start_pos, pos)

    def a_star_choose_node(self, node: 'Node'):
        self.node_chosen = node
        # draw a frame

    def get_pars(self):
        self.Y, self.X = SCREEN_HEIGHT - 60, SCREEN_WIDTH - 250
        self.tiles_q = self.scale_names[self.scale]
        self.line_width = int(math.sqrt(max(self.scale_names.values()) / self.tiles_q))
        tile_size = self.Y // self.tiles_q
        hor_tiles_q = self.X // tile_size
        self.Y, self.X = self.tiles_q * tile_size, hor_tiles_q * tile_size
        return tile_size, hor_tiles_q

    def get_hor_tiles(self, i):
        return (SCREEN_WIDTH - 250) // ((SCREEN_HEIGHT - 30) // self.scale_names[i])

    @staticmethod
    def get_ms(start, finish):
        return (finish - start) // 10 ** 6

    def setup(self):
        # game set up is located below:
        # sprites and etc...
        ...

    def get_all_neighs(self):  # pre-calculations (kind of optimization)
        for row in self.grid:
            for node in row:
                node.get_neighs(self)

    def draw_grid_lines(self):
        for j in range(self.tiles_q + 1):
            arcade.draw_line(5, 5 + self.tile_size * j, 5 + self.X, 5 + self.tile_size * j, arcade.color.BLACK,
                             self.line_width)

        for i in range(self.hor_tiles_q + 1):
            arcade.draw_line(5 + self.tile_size * i, 5, 5 + self.tile_size * i, 5 + self.Y, arcade.color.BLACK,
                             self.line_width)

    def on_draw(self):
        # renders this screen:
        arcade.start_render()
        # image's code:
        # grid:
        self.draw_grid_lines()
        # blocks:
        for y in range(self.tiles_q):
            for x in range(self.hor_tiles_q):
                if (n := self.grid[y][x]).type is not NodeType.EMPTY:
                    arcade.draw_rectangle_filled(5 + self.tile_size * x + self.tile_size / 2,
                                                 5 + self.tile_size * y + self.tile_size / 2,
                                                 self.tile_size - 2 * self.line_width - (
                                                     1 if self.line_width % 2 != 0 else 0),
                                                 self.tile_size - 2 * self.line_width - (
                                                     1 if self.line_width % 2 != 0 else 0), n.type.value)
                    if self.f_flag:
                        arcade.draw_text(f'{n.g + n.h}', 5 + self.tile_size * x + self.tile_size / 3,
                                         5 + self.tile_size * y + self.tile_size / 3, arcade.color.BLACK,
                                         self.tile_size // 3, bold=True)
        # HINTS:
        arcade.draw_text(f'Mode: {self.mode_names[self.mode]}', 25, SCREEN_HEIGHT - 35, arcade.color.BLACK, bold=True)
        arcade.draw_text(
            f'A* iters: {self.iterations}, path length: {len(self.path) if self.path else "No path found"}, nodes visited: {len(self.nodes_visited)}, '
            f'max times visited: {self.max_times_visited_dict[self.iterations] if self.is_interactive else "LALA"}, time elapsed: {self.time_elapsed_ms}',
            365, SCREEN_HEIGHT - 35, arcade.color.BROWN, bold=True)
        if self.mode == 2:
            if self.node_chosen:
                arcade.draw_text(
                    f"NODE'S INFO -->> pos: {self.node_chosen.y, self.node_chosen.x}, g: {self.node_chosen.g}, "
                    f"h: {self.node_chosen.h}, f=g+h: {self.node_chosen.g + self.node_chosen.h} t: {self.node_chosen.tiebreaker}, times visited: {self.node_chosen.times_visited}, type: {self.node_chosen.type}",
                    1050, SCREEN_HEIGHT - 35, arcade.color.PURPLE, bold=True)
        # SET-UPS:
        arcade.draw_text(f'Heuristics: ', SCREEN_WIDTH - 235, SCREEN_HEIGHT - 70, arcade.color.BLACK, bold=True)
        for i in range(len(self.heuristic_names)):
            arcade.draw_rectangle_outline(SCREEN_WIDTH - 225, SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * i, 18, 18,
                                          arcade.color.BLACK, 2)
            arcade.draw_text(f'{self.heuristic_names[i]}', SCREEN_WIDTH - 225 + (18 + 2 * 2),
                             SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * i - 6, arcade.color.BLACK, bold=True)

        arcade.draw_rectangle_filled(SCREEN_WIDTH - 225, SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * self.heuristic, 14,
                                     14,
                                     arcade.color.BLACK)

        arcade.draw_text(f'Tiebreakers: ', SCREEN_WIDTH - 235, SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * 3 - 18 * 3,
                         arcade.color.BLACK, bold=True)
        for i in range(len(self.tiebreaker_names)):
            arcade.draw_rectangle_outline(SCREEN_WIDTH - 225,
                                          SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * (3 + i) - 18 * 3 - 30, 18,
                                          18, arcade.color.BLACK, 2)
            arcade.draw_text(self.tiebreaker_names[i], SCREEN_WIDTH - 225 + (18 + 2 * 2),
                             SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * (3 + i) - 18 * 3 - 30 - 6, arcade.color.BLACK,
                             bold=True)

        if self.tiebreaker is not None:
            arcade.draw_rectangle_filled(SCREEN_WIDTH - 225,
                                         SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * (3 + self.tiebreaker) - 18 * 3 - 30,
                                         14,
                                         14, arcade.color.BLACK)

        arcade.draw_text('Is greedy: ', SCREEN_WIDTH - 235,
                         SCREEN_HEIGHT - 130 - (18 + 2 * 2 + 18) * 4 - 2 * 18 * 3,
                         arcade.color.BLACK, bold=True)
        arcade.draw_rectangle_outline(SCREEN_WIDTH - 225,
                                      SCREEN_HEIGHT - 130 - (18 + 2 * 2 + 18) * 4 - 2 * 18 * 3 - 30, 18, 18,
                                      arcade.color.BLACK, 2)
        arcade.draw_text(f'GREEDY_FLAG', SCREEN_WIDTH - 225 + (18 + 2 * 2),
                         SCREEN_HEIGHT - 130 - (18 + 2 * 2 + 18) * 4 - 2 * 18 * 3 - 30 - 6,
                         arcade.color.BLACK, bold=True)

        if self.greedy_flag:
            arcade.draw_rectangle_filled(SCREEN_WIDTH - 225,
                                         SCREEN_HEIGHT - 130 - (18 + 2 * 2 + 18) * 4 - 2 * 18 * 3 - 30, 14,
                                         14,
                                         arcade.color.BLACK)

        arcade.draw_text('Sizes in tiles: ', SCREEN_WIDTH - 235,
                         SCREEN_HEIGHT - 160 - (18 + 2 * 2 + 18) * 4 - 3 * 18 * 3,
                         arcade.color.BLACK, bold=True)

        for i in range(len(self.scale_names)):
            arcade.draw_rectangle_outline(SCREEN_WIDTH - 225,
                                          SCREEN_HEIGHT - 160 - (18 + 2 * 2 + 18) * (4 + i) - 3 * 18 * 3 - 30, 18, 18,
                                          arcade.color.BLACK, 2)
            arcade.draw_text(f'{self.scale_names[i]}x{self.get_hor_tiles(i)}', SCREEN_WIDTH - 225 + (18 + 2 * 2),
                             SCREEN_HEIGHT - 160 - (18 + 2 * 2 + 18) * (4 + i) - 3 * 18 * 3 - 30 - 6,
                             arcade.color.BLACK, bold=True)

        arcade.draw_rectangle_filled(SCREEN_WIDTH - 225,
                                     SCREEN_HEIGHT - 160 - (18 + 2 * 2 + 18) * (4 + self.scale) - 3 * 18 * 3 - 30, 14,
                                     14,
                                     arcade.color.BLACK)

        arcade.draw_text('Show mode: ', SCREEN_WIDTH - 235,
                         SCREEN_HEIGHT - 190 - (18 + 2 * 2 + 18) * 14 - 4 * 18 * 3, arcade.color.BLACK, bold=True)

        arcade.draw_rectangle_outline(SCREEN_WIDTH - 225,
                                      SCREEN_HEIGHT - 190 - (18 + 2 * 2 + 18) * 14 - 4 * 18 * 3 - 30, 18, 18,
                                      arcade.color.BLACK, 2)

        arcade.draw_text('IS_A_STAR_INTERACTIVE', SCREEN_WIDTH - 225 + (18 + 2 * 2),
                         SCREEN_HEIGHT - 190 - (18 + 2 * 2 + 18) * 14 - 4 * 18 * 3 - 30 - 6, arcade.color.BLACK,
                         bold=True)

        if self.is_interactive:
            arcade.draw_rectangle_filled(SCREEN_WIDTH - 225,
                                         SCREEN_HEIGHT - 190 - (18 + 2 * 2 + 18) * 14 - 4 * 18 * 3 - 30, 14, 14,
                                         arcade.color.BLACK)

        # NODE CHOSEN:
        if self.node_chosen:
            arcade.draw_circle_filled(5 + self.node_chosen.x * self.tile_size + self.tile_size / 2,
                                      5 + self.node_chosen.y * self.tile_size + self.tile_size / 2, self.tile_size / 4,
                                      arcade.color.YELLOW)

        # CURRENT PATH NODE ON START OR END NODE:
        if self.in_interaction:
            if self.start_node and self.end_node:
                if self.path is not None and self.path_index > 0:
                    p = -self.path[self.path_index].x + self.path[self.path_index - 1].x, -self.path[
                        self.path_index].y + \
                        self.path[self.path_index - 1].y
                    points = self.get_triangle(self.path[self.path_index], p)
                    arcade.draw_triangle_filled(points[0], points[1], points[2], points[3], points[4], points[5],
                                                arcade.color.RED)

            if self.path:
                arcade.draw_circle_filled(5 + self.end_node.x * self.tile_size + self.tile_size / 2,
                                          5 + self.end_node.y * self.tile_size + self.tile_size / 2,
                                          self.tile_size / 4,
                                          arcade.color.RED)

    def get_triangle(self, node: 'Node', point: tuple[int, int]):
        scaled_point = point[0] * (self.tile_size // 2 - 2), point[1] * (self.tile_size // 2 - 2)
        deltas = (scaled_point[0] - scaled_point[1], scaled_point[0] + scaled_point[1]), (
            scaled_point[0] + scaled_point[1], -scaled_point[0] + scaled_point[1])
        cx, cy = 5 + node.x * self.tile_size + self.tile_size / 2, 5 + node.y * self.tile_size + self.tile_size / 2
        return cx, cy, cx + deltas[0][0], cy + deltas[0][1], cx + deltas[1][0], cy + deltas[1][1]

    def rebuild_map(self):
        self.tile_size, self.hor_tiles_q = self.get_pars()
        # grid's renewing:
        self.grid = [[Node(j, i, 1, NodeType.EMPTY) for i in range(self.hor_tiles_q)] for j in range(self.tiles_q)]
        # pars resetting:
        self.aux_clear()
        self.start_node = None
        self.end_node = None
        self.node_chosen = None

    def update(self, delta_time: float):
        # consecutive calls during key pressing:
        k, ticks_threshold = 1, 12
        if self.cycle_breaker_right:
            self.ticks_before += 1
            if self.ticks_before >= ticks_threshold:
                self.ticks_q += 1
                if self.ticks_q == k:
                    if self.path is None:
                        self.a_star_step_up()
                    else:
                        if self.path_index < len(self.path) - 1:
                            self.path_up()
                            self.path_index += 1
                    self.ticks_q = 0
        if self.cycle_breaker_left:
            self.ticks_before += 1
            if self.ticks_before >= ticks_threshold:
                self.ticks_q += 1
                if self.ticks_q == k:
                    if self.path is None:
                        self.a_star_step_down()
                    else:
                        if self.path_index > 0:
                            self.path_down()
                            self.path_index -= 1
                        else:
                            self.path = None
                            self.a_star_step_down()
                    self.ticks_q = 0

    @staticmethod
    def linear_gradi(c: tuple[int, int, int], i):
        return c[0] + 3 * i, c[1] - 5 * i, c[2] + i * 5

    def erase_all_linked_nodes(self, node: 'Node'):
        node.type = NodeType.EMPTY
        self.walls_built_erased[self.walls_index][0].append(node)
        for neigh in node.get_extended_neighs(self):
            if neigh.type == NodeType.WALL:
                self.erase_all_linked_nodes(neigh)

    def clear_empty_nodes(self):
        # clearing the every empty node:
        for row in self.grid:
            for node in row:
                if node.type == NodeType.EMPTY and node not in [self.start_node, self.end_node]:
                    node.clear()
                else:
                    node.heur_clear()
        # clearing the nodes-relating pars of the game:
        self.aux_clear()

    def clear_grid(self):
        # clearing the every node:
        for row in self.grid:
            for node in row:
                node.clear()
        # clearing the nodes-relating pars of the game:
        self.start_node, self.end_node = None, None
        self.aux_clear()

    def aux_clear(self):
        self.nodes_visited = {}
        self.time_elapsed_ms = 0
        self.iterations = 0
        self.path = None
        self.path_index = 0
        self.curr_node_dict = {0: None}
        self.max_times_visited_dict = {0: 0}
        self.neighs_added_to_heap_dict = {}
        self.walls_built_erased = [([], True)]
        self.walls_index = 0

    def on_key_press(self, symbol: int, modifiers: int):
        # is called when user press the symbol key:
        match symbol:
            # a_star_call:
            case arcade.key.SPACE:
                if self.start_node and self.end_node:
                    if self.is_interactive:
                        self.in_interaction = True
                        self.a_star_preparation()
                    else:
                        start = time.time_ns()
                        the_shortest_path = self.start_node.a_star(self.end_node, self)
                        self.path = the_shortest_path
                        finish = time.time_ns()
                        self.time_elapsed_ms = self.get_ms(start, finish)
                        for node in the_shortest_path:
                            if node.type not in [NodeType.START_NODE, NodeType.END_NODE]:
                                node.type = NodeType.PATH_NODE
            # grid clearing:
            case arcade.key.ENTER:
                self.clear_grid()
            # recall a_star :
            case arcade.key.BACKSPACE:
                self.clear_empty_nodes()
            # a_star interactive:
            case arcade.key.RIGHT:
                if self.is_interactive:
                    self.cycle_breaker_right = True
                    if self.path is None:
                        self.a_star_step_up()
                    else:
                        if self.path_index < len(self.path) - 1:
                            self.path_up()
                            self.path_index += 1
            case arcade.key.LEFT:
                if self.is_interactive:
                    self.cycle_breaker_left = True
                    if self.path is None:
                        self.a_star_step_down()
                    else:
                        if self.path_index > 0:
                            self.path_down()
                            self.path_index -= 1
                        else:
                            self.path = None
                            self.a_star_step_down()
            case arcade.key.F:
                self.f_flag = not self.f_flag
            # undoing and cancelling:
            case arcade.key.Z:  # undo
                if self.walls_index > 0:
                    for node in (l := self.walls_built_erased[self.walls_index])[0]:
                        node.type = NodeType.EMPTY if l[1] else NodeType.WALL
                    self.walls_index -= 1
            case arcade.key.Y:  # cancel undo
                if self.walls_index < len(self.walls_built_erased) - 1:
                    for node in (l := self.walls_built_erased[self.walls_index])[0]:
                        node.type = NodeType.WALL if l[1] else NodeType.EMPTY
                    self.walls_index += 1

    def on_key_release(self, symbol: int, modifiers: int):
        match symbol:
            case arcade.key.RIGHT:
                self.cycle_breaker_right = False
                self.ticks_q = 0
                self.ticks_before = 0
            case arcade.key.LEFT:
                self.cycle_breaker_left = False
                self.ticks_q = 0
                self.ticks_before = 0

    def get_node(self, mouse_x, mouse_y):
        x_, y_ = mouse_x - 5, mouse_y - 5
        x, y = x_ // self.tile_size, y_ // self.tile_size
        return self.grid[y][x] if 0 <= x < self.hor_tiles_q and 0 <= y < self.tiles_q else None

    def on_mouse_motion(self, x, y, dx, dy):
        if self.building_walls_flag:
            if self.mode == 0:
                if self.build_or_erase is not None:
                    if self.build_or_erase:
                        n = self.get_node(x, y)
                        if n and n.type != NodeType.WALL:
                            n.type = NodeType.WALL
                            if self.walls_index < len(self.walls_built_erased) - 1:
                                self.walls_built_erased = self.walls_built_erased[:self.walls_index + 1]
                            self.walls_built_erased.append(([n], self.build_or_erase))
                            self.walls_index += 1
                    else:
                        n = self.get_node(x, y)
                        if n and n.type == NodeType.WALL:
                            n.type = NodeType.EMPTY
                            if self.walls_index < len(self.walls_built_erased) - 1:
                                self.walls_built_erased = self.walls_built_erased[:self.walls_index + 1]
                            self.walls_built_erased.append(([n], self.build_or_erase))
                            self.walls_index += 1

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        # setting_up heuristic and tiebreaker:
        for i in range(len(self.heuristic_names)):
            if SCREEN_WIDTH - 225 - 9 <= x <= SCREEN_WIDTH - 225 + 9 and SCREEN_HEIGHT - 100 - (
                    18 + 2 * 2 + 18) * i - 9 <= y <= SCREEN_HEIGHT - 100 - (18 + 2 * 2 + 18) * i + 9:
                self.heuristic = i
                break
        for i in range(len(self.tiebreaker_names)):
            if SCREEN_WIDTH - 225 - 9 <= x <= SCREEN_WIDTH - 225 + 9 and SCREEN_HEIGHT - 100 - (
                    18 + 2 * 2 + 18) * (3 + i) - 18 * 3 - 30 - 9 <= y <= SCREEN_HEIGHT - 100 - (
                    18 + 2 * 2 + 18) * (3 + i) - 18 * 3 - 30 + 9:
                self.tiebreaker = None if self.tiebreaker == i else i
                break
        for i in range(len(self.scale_names)):
            if SCREEN_WIDTH - 225 - 9 <= x <= SCREEN_WIDTH - 225 + 9 and SCREEN_HEIGHT - 160 - (
                    18 + 2 * 2 + 18) * (4 + i) - 3 * 18 * 3 - 30 - 9 <= y <= SCREEN_HEIGHT - 160 - (
                    18 + 2 * 2 + 18) * (4 + i) - 3 * 18 * 3 - 30 + 9:
                self.scale = i
                self.rebuild_map()
        if SCREEN_WIDTH - 225 - 9 <= x <= SCREEN_WIDTH - 225 + 9 and SCREEN_HEIGHT - 130 - (
                18 + 2 * 2 + 18) * 4 - 2 * 18 * 3 - 30 - 9 <= y <= SCREEN_HEIGHT - 130 - (
                18 + 2 * 2 + 18) * 4 - 2 * 18 * 3 - 30 + 9:
            self.greedy_flag = not self.greedy_flag
        if SCREEN_WIDTH - 225 - 9 <= x <= SCREEN_WIDTH - 225 + 9 and SCREEN_HEIGHT - 190 - (
                18 + 2 * 2 + 18) * 14 - 4 * 18 * 3 - 30 - 9 <= y <= SCREEN_HEIGHT - 190 - (
                18 + 2 * 2 + 18) * 14 - 4 * 18 * 3 - 30 + 9:
            self.is_interactive = not self.is_interactive
        if self.mode == 0:
            self.building_walls_flag = True
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.build_or_erase = True
            elif button == arcade.MOUSE_BUTTON_RIGHT:
                self.build_or_erase = False
            elif button == arcade.MOUSE_BUTTON_MIDDLE:
                self.build_or_erase = None
                n = self.get_node(x, y)
                if n:
                    if self.walls_index < len(self.walls_built_erased) - 1:
                        self.walls_built_erased = self.walls_built_erased[: self.walls_index + 1]
                    self.walls_built_erased.append(([], False))
                    self.walls_index += 1
                    self.erase_all_linked_nodes(n)
        elif self.mode == 1:
            if button == arcade.MOUSE_BUTTON_LEFT:
                sn = self.get_node(x, y)
                if sn:
                    if self.start_node:
                        self.start_node.type = NodeType.EMPTY
                    sn.type = NodeType.START_NODE
                    self.start_node = sn
            elif button == arcade.MOUSE_BUTTON_RIGHT:
                en = self.get_node(x, y)
                if en:
                    if self.end_node:
                        self.end_node.type = NodeType.EMPTY
                    en.type = NodeType.END_NODE
                    self.end_node = en
        elif self.mode == 2:  # a_star interactive -->> info getting:
            n = self.get_node(x, y)
            if n:
                if self.node_chosen == n:
                    self.node_chosen = None
                else:
                    self.a_star_choose_node(n)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int):
        self.mode = (self.mode + 1) % len(self.mode_names)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        self.building_walls_flag = False


class Node:
    # horizontal and vertical up and down moves:
    walk = [(dy, dx) for dx in range(-1, 2) for dy in range(-1, 2) if dy * dx == 0 and (dy, dx) != (0, 0)]
    extended_walk = [(dy, dx) for dx in range(-1, 2) for dy in range(-1, 2) if (dy, dx) != (0, 0)]
    IS_GREEDY = False

    def __init__(self, y, x, val, node_type: 'NodeType'):
        # type:
        self.type = node_type
        # important pars:
        self.y, self.x = y, x
        self.val = val
        self.neighs = set()  # the nearest neighbouring nodes
        self.previously_visited_node = None  # for building the shortest path of Nodes from the starting point to the ending one
        self.times_visited = 0
        # cost and heuristic vars:
        self.g = np.Infinity  # aggregated cost of moving from start to the current Node, Infinity chosen for convenience and algorithm's logic
        self.h = 0  # approximated cost evaluated by heuristic for path starting from the current node and ending at the exit Node
        self.tiebreaker = None
        # f = h + g or total cost of the current Node is not needed here
        # heur dict, TODO: (it should be implemented in Astar class instead of node one) (medium, easy):
        self.heuristics = {0: self.manhattan_distance, 1: self.euclidian_distance, 2: self.max_delta,
                           3: self.no_heuristic}
        self.tiebreakers = {0: self.vector_cross_product_deviation, 1: self.coordinates_pair}

    def aux_copy(self):
        copied_node = Node(self.y, self.x, self.type, self.val)
        copied_node.g = self.g
        copied_node.h = self.h
        copied_node.tiebreaker = self.tiebreaker
        return copied_node

    def restore(self, copied_node: 'Node'):
        self.g = copied_node.g
        self.h = copied_node.h
        self.tiebreaker = copied_node.tiebreaker
        if self.type != NodeType.END_NODE:
            self.type = NodeType.EMPTY

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return (self.y, self.x) == (other.y, other.x)

    # this is needed for using Node objects in priority queue like heapq and so on
    def __lt__(self, other: 'Node'):
        if self.IS_GREEDY:
            return (self.h, self.tiebreaker) < (other.h, other.tiebreaker)
        else:
            return (self.g + self.h, self.tiebreaker) < (other.g + other.h, other.tiebreaker)

    def __hash__(self):
        return hash((self.y, self.x))

    def clear(self):
        self.heur_clear()
        self.type = NodeType.EMPTY

    def heur_clear(self):
        self.g = np.Infinity
        self.h = 0
        self.tiebreaker = None
        self.previously_visited_node = None
        self.times_visited = 0
        self.neighs = set()

    @staticmethod
    def manhattan_distance(node1, node2: 'Node'):
        return abs(node1.y - node2.y) + abs(node1.x - node2.x)

    @staticmethod
    def euclidian_distance(node1, node2: 'Node'):
        return math.sqrt((node1.y - node2.y) ** 2 + (node1.x - node2.x) ** 2)

    @staticmethod
    def max_delta(node1, node2: 'Node'):
        return max(abs(node1.y - node2.y), abs(node1.x - node2.x))

    @staticmethod
    def no_heuristic(node1, node2: 'Node'):
        return 0

    # self * other, tiebreaker:
    @staticmethod
    def vector_cross_product_deviation(start, end, neigh):
        v1 = neigh.y - start.y, neigh.x - start.x
        v2 = end.y - neigh.y, end.x - neigh.x
        return abs(v1[0] * v2[1] - v1[1] * v2[0])

    @staticmethod
    def coordinates_pair(start, end, neigh):
        return neigh.y, neigh.x

    def get_neighs(self, game: 'Astar'):
        for dy, dx in self.walk:
            ny, nx = self.y + dy, self.x + dx
            if 0 <= ny < game.tiles_q and 0 <= nx < game.hor_tiles_q:
                if game.grid[ny][nx].type in [NodeType.EMPTY, NodeType.END_NODE]:
                    self.neighs.add(game.grid[ny][nx])
        return self.neighs

    def get_extended_neighs(self, game: 'Astar') -> list['Node']:
        for dy, dx in self.extended_walk:
            ny, nx = self.y + dy, self.x + dx
            if 0 <= ny < game.tiles_q and 0 <= nx < game.hor_tiles_q:
                yield game.grid[ny][nx]

    # finished, tested and approved by Levi Gin:
    def wave_lee(self, other: 'Node', game: 'Astar'):
        other.get_neighs(game)
        flag = True
        front_wave = [self]
        other.val, iteration = 0, 0
        # wave-spreading:
        while front_wave:
            iteration += 1
            new_front_wave = []
            for front_node in front_wave:
                front_node.val = iteration
                if front_node == other:
                    flag = False
                    break
                for front_neigh in front_node.get_neighs(game):
                    if front_neigh.val == 0:
                        new_front_wave.append(front_neigh)
            if not flag:
                break
            front_wave = new_front_wave[:]
        # path restoration:
        if other.val == 0:
            return []
        curr_node = other
        the_shortest_path = []
        while curr_node != self:
            the_shortest_path.append(curr_node)
            for neigh in curr_node.neighs:
                if neigh.val < curr_node.val:
                    curr_node = neigh
                    break
        return the_shortest_path

    def a_star(self, other: 'Node', game: 'Astar'):
        Node.IS_GREEDY = game.greedy_flag
        # game.get_all_neighs()
        nodes_to_be_visited = [self]
        self.g = 0
        hq.heapify(nodes_to_be_visited)
        max_times_visited = 0
        # the main cycle:
        while nodes_to_be_visited:
            game.iterations += 1
            curr_node = hq.heappop(nodes_to_be_visited)
            if curr_node not in [self, other]:
                curr_node.type = NodeType.VISITED_NODE
            curr_node.times_visited += 1
            max_times_visited = max(max_times_visited, curr_node.times_visited)
            game.nodes_visited[curr_node] = 1
            # base case of finding the shortest path:
            if curr_node == other:
                break
            # next step:
            for neigh in curr_node.get_neighs(game):
                if neigh.g > curr_node.g + neigh.val:
                    neigh.g = curr_node.g + neigh.val
                    neigh.h = neigh.heuristics[game.heuristic](neigh, other)
                    if game.tiebreaker is not None:
                        neigh.tiebreaker = self.tiebreakers[game.tiebreaker](self, other,
                                                                             neigh)
                    neigh.previously_visited_node = curr_node
                    hq.heappush(nodes_to_be_visited, neigh)
        game.max_times_visited = max_times_visited
        # start point of path restoration (here we begin from the end node of the shortest path found):
        node = other
        shortest_path = []
        # path restoring (here we get the reversed path):
        while node.previously_visited_node:
            shortest_path.append(node)
            node = node.previously_visited_node
        shortest_path.append(self)
        # returns the result:
        return shortest_path


class NodeType(Enum):
    EMPTY = None
    WALL = arcade.color.BLACK
    VISITED_NODE = arcade.color.ROSE_QUARTZ
    NEIGH = arcade.color.BLUEBERRY
    CURRENT_NODE = arcade.color.ROSE
    START_NODE = arcade.color.GREEN
    END_NODE = (75, 150, 0)
    PATH_NODE = arcade.color.RED


def main():
    # line_width par should be even number for correct grid&nodes representation:
    game = Astar(SCREEN_WIDTH, SCREEN_HEIGHT)
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()

# v0.1 base Node class created
# v0.2 base Astar(arcade.Window) class created
# v0.3 grid lines drawing added
# v0.4 grid of nodes (self.grid) for Astar class, consisting of Nodes objects created, some fields added for both classes,
# drawing of walls (not passable nodes), start and end nodes added
# v0.5 on_mouse_press() and on_mouse_release methods() overwritten
# v0.6 on_mouse_motion() method overwritten
# v0.7 on_mouse_scroll() method overwritten, now it is possible to draw walls while mouse button pressed,
# switch drawing modes and erase walls, choose start and end node (4 modes are available for now)
# v0.8 on_key_press() method overwritten, clear() method for Node class implemented for resetting the temporal fields to its defaults,
# clear() method for Astar class added to clear all the game field (every Node), now by pressing the 'ENTER' key user can clear all the map
# v0.9 info displaying added (current mode, a_star related information)
# v1.0 a_star now is called by pressing the 'SPACE' key, the shortest way is shown on the grid
# v1.1 visited_nodes are now displayed after a_star call, info extended, hash() dunder method added for class Node
# v1.2 tiebreaker (vector cross product absolute deviation) added
# v1.3 erase separate drawing mode merged with build mode, now there is one build/erase draw mode for building walls by pressing the left mouse button
# and erasing them by pressing the right one
# v1.4 fixed a bug, when some heuristic related temporal pars have not been cleared after a_star had been called
# v1.5 now it is possible to reset all heuristic related pars for the every node on the grid but leave all the walls
# and start and end nodes at their positions by pressing the 'BACKSPACE' key, clear method for Astar class divided into two methods:
# clear_empty_nodes() for partial clearing and clear_grid() for entire clearing
# v1.6 3 auxiliary heuristics added
# v1.7 user interface for heuristic  and tiebreaker choosing added
# v1.8 fixed a bug when start and end nodes have been removed after heuristic had been chosen
# v1.9 start node choosing and end node choosing drawing modes merged into one start & end nodes choosing drawing mode,
# start node is chosen by pressing the left mouse button when end node is chosen by pressing the right one
# v1.10 coordinate pairs tiebreaker added
# v1.11 fixed bug when cross vector product deviation heuristic causes no impact on a_star
# v1.12 interface for scale choosing added
# v1.13 fixed bug when node's filled rectangle has been located not in the center of related grid cell, scaling improved
# v1.14 erase_all_linked_nodes() method added to erase all coherent wall-regions by pressing the middle mouse button on the any cell of them
# v1.15 greedy interaction added, greedy_case's of a_star logic implemented, now it is possible to find some non-shortest ways fast
# v1.16 fixed bug when the time elapsed ms have not been reset after pressing keys such as 'BACKSPACE' and 'ENTER'
# v1.17 fixed bug when greedy flag has had no impact on a_star, fixed closely related to this clearing bug when if there has been at least one
# important node (start or end) unselected clearing process has been finished with error
# --- trying to visualize more visited node by numbers at first and then by colour gradient, bad idea...
# v1.171 max times visited var is now shown in the info, hotfix: bad location bug resolved, GREEDY FLAG -->> GREEDY_FLAG
# v1.18 Wave-spreading lee pathfinding algorithm been implemented, further tests needed...
# v2.0 A-star is now fully interactive (there are two methods: a_star_step_up() -->> RIGHT arrow key and a_star_step_down() -->> LEFT arrow key)
# for moving forward and back through s_star iterations if the flag is_interactive is on. Switcher related added to the window.
# v2.1 Info-getting drawing mode added. Now it is possible to get the information about every node during the a_star call by pressing
# left/right mouse button while in interactive drawing mode
# v2.2 Fixed problem when the heap invariant has been violated during a_star_step_down() calls. Implementations of sift_up() and sift_down()
# methods are borrowed from CPython.heapq github
# v2.3 fixed bug when a rare exception raised during the consecutive calls of a_star_step_down() method
# Current node to be removed from nodes_visited set have been absent. Nodes_visited now is dict instead of set as it was before
# v2.4 Added the correct path restoring to the a_star_interactive mode
# v2.5 Added two methods: path_up() and path_down() to visualize the path restoring phase step by step up and down respectively
# --- trying to represent the leading node of restoring path by a purple circle, bad idea
# v2.6 Now the leading node of the path found is represented by a directed triangle turning the way consistent with the shortest path's direction
# v2.7 fixed bug when the exception raised if user try undoing the path restoring and continue pressing the left arrow key (a_star_down calls)
# v2.8 added fast path_up() and path_down() consecutive calls during the right and the left mouse keys respectively (after a short delay)
# v2.9 fixed bug when ENTER clearing have not been working correctly, some walls have become passable, neighs is now renewed after both types of clearing
# v2.10 wave-spreading lee pathfinding algorithm has been tested and then fully corrected
#
# v2.11 fixed bug when the right arrow key is being pressed after the fully undoing of the path recovering by pressing the left arrow key and an error is raised
# removed an additional interactive step between the null-index of path found and the first call of a_star_step_down() method, the end node (
# the first node of the reversed path) now is marked by a red inner circle
# v2.12 now it is possible to get the full steps of algo by one long pressing the right mouse key and reverse this process by pressing the left moue key
# v2.13 added number representation of f = g + h par for the every visited/heap node than can be turned on/off by pressing the key 'F'
# v2.14 two excess pars have been deleted from Lastar init signature
# v3.0 undo and redo commands for wall-structures have been implemented, they can be called by pressing the 'Z' and 'Y' keys respectively
# v3.1 fixed bug when consecutive erasing linked regions by pressing the middle mouse key could not be undone correctly,passability par has been removed from class Node
# v3.2 fixed bug when walls_built_erased dict is widening enormously quick
# v3.3 common pieces of code from 2 clearing and one rebuilding methods has been merged into new method aux_clear()
# v3.4 fixed bug when END_NODE could not be visited
#
#
#
#
# TODO: add some other tiebreakers (medium, easy) +-
# TODO: upgrade the visual part (medium, medium) -+
# TODO: add a core-algo switcher that can change the right interactive panel (Lee, Astar and so on) (high, medium)
# TODO: create an info/help pages (high, hard)
# TODO: extend the algo base with Lee wave pathfinding algorithm (medium, medium) Levi Gin +-
# TODO: add a visualization for the most priority nodes in the heap (medium, medium)
# TODO: add heuristic tiebreaker and combined tiebreakers (medium, high)
# TODO: add a scroller on the right side of the window (high, medium)
# TODO: add an interaction-prohibition for a large grids (high, easy)
# TODO: find and implement other core algorithms (like Lee and Astar/Dijkstra) (low, high)
# TODO:
# TODO: add a command of wall-pattern saving and further loading (low, high)
# TODO:
# TODO:
# TODO:
# TODO:
# TODO:
# TODO:
# TODO:
