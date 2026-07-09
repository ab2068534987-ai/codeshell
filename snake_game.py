import pygame
import random
import sys

CELL_SIZE = 25
GRID_W = 24
GRID_H = 18
WIDTH = CELL_SIZE * GRID_W
HEIGHT = CELL_SIZE * GRID_H + 40
FPS = 10

BG_COLOR = (30, 30, 46)
GRID_COLOR = (40, 40, 56)
SNAKE_COLOR = (137, 180, 250)
SNAKE_HEAD_COLOR = (116, 199, 236)
FOOD_COLOR = (243, 139, 168)
SCORE_BAR_COLOR = (24, 24, 37)
TEXT_COLOR = (205, 214, 244)
WALL_COLOR = (88, 91, 112)

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRS = {pygame.K_UP: UP, pygame.K_DOWN: DOWN, pygame.K_LEFT: LEFT, pygame.K_RIGHT: RIGHT}
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Snake Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 56)
        self.reset()

    def reset(self):
        mid = GRID_W // 2, GRID_H // 2
        self.snake = [mid, (mid[0] - 1, mid[1]), (mid[0] - 2, mid[1])]
        self.direction = RIGHT
        self.food = self._place_food()
        self.score = 0
        self.game_over = False
        self.paused = False

    def _place_food(self):
        while True:
            pos = (random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1))
            if pos not in self.snake:
                return pos

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    self.reset()
                    continue
                if self.game_over:
                    continue
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    return
                if event.key in DIRS:
                    new_dir = DIRS[event.key]
                    if new_dir != OPPOSITE.get(self.direction):
                        self.direction = new_dir

    def update(self):
        if self.game_over or self.paused:
            return
        head = self.snake[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])

        if new_head[0] < 0 or new_head[0] >= GRID_W or new_head[1] < 0 or new_head[1] >= GRID_H:
            self.game_over = True
            return
        if new_head in self.snake:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 10
            self.food = self._place_food()
        else:
            self.snake.pop()

    def draw(self):
        self.screen.fill(BG_COLOR)

        # grid lines
        play_area_top = 40
        for x in range(GRID_W + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (x * CELL_SIZE, play_area_top), (x * CELL_SIZE, HEIGHT))
        for y in range(GRID_H + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (0, play_area_top + y * CELL_SIZE), (WIDTH, play_area_top + y * CELL_SIZE))

        # score bar
        pygame.draw.rect(self.screen, SCORE_BAR_COLOR, (0, 0, WIDTH, 40))
        pygame.draw.line(self.screen, WALL_COLOR, (0, 40), (WIDTH, 40), 2)
        score_text = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_text, (10, 10))

        # food
        fx, fy = self.food
        food_rect = pygame.Rect(fx * CELL_SIZE + 3, fy * CELL_SIZE + play_area_top + 3, CELL_SIZE - 6, CELL_SIZE - 6)
        pygame.draw.rect(self.screen, FOOD_COLOR, food_rect, border_radius=5)

        # snake
        for i, (sx, sy) in enumerate(self.snake):
            color = SNAKE_HEAD_COLOR if i == 0 else SNAKE_COLOR
            rect = pygame.Rect(sx * CELL_SIZE + 2, sy * CELL_SIZE + play_area_top + 2, CELL_SIZE - 4, CELL_SIZE - 4)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)

        # overlays
        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            go_text = self.big_font.render("GAME OVER", True, FOOD_COLOR)
            self.screen.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 40))
            hint = self.font.render("Press R to restart", True, TEXT_COLOR)
            self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 30))
        elif self.paused:
            pause_text = self.big_font.render("PAUSED", True, SNAKE_HEAD_COLOR)
            self.screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - 40))
            hint = self.font.render("Press SPACE to resume", True, TEXT_COLOR)
            self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 30))

        pygame.display.flip()

    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    SnakeGame().run()
