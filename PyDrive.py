import pygame, sys, time, math, os, random
import neat
from neat.checkpoint import Checkpointer

# Set up the window
WINDOWWIDTH = 1920
WINDOWHEIGHT = 1400
windowSurface = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT),0,32)
pygame.display.set_caption('PyDrive')
scale_factor = 0.9
generation = 0
fps = 60


# set up the colors
BLACK = (0, 0, 0)
WHITE = (255,255,255)
BGREEN = (0, 200, 0)
GREEN = (0, 160, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
LBLUE = (0, 200, 255)
LGREY = (75,75,75)
BROWN = (139,69,19)
DGREY = (25,25,25)

# set up best times
best_sector1 = 6.84
best_sector2 = 14.51
best_sector3 = 21.67
best_finish = 29.68
gen_sector1 = float('inf')
gen_sector2 = float('inf')
gen_sector3 = float('inf')
gen_finish = float('inf')
best_score = 0

total_distance = 90

# set up car
class Car:
    def __init__(self, human=False):
        self.surface = pygame.image.load('graphics/car.png').convert_alpha()
        self.surface = pygame.transform.scale(self.surface, (100, 100))
        self.rotateSurface = self.surface
        self.pos = [600, 150]
        self.angle = 0
        self.speed = 2
        self.max_speed = 5
        self.acceleration = 1
        self.deceleration = 0.5
        self.turnspeed = 1.5
        self.center = [self.pos[0] + 50, self.pos[1] + 50]
        self.radars = []
        self.radars_for_draw = []
        self.is_alive = True
        self.goal = False
        self.distance = 0
        self.time_spent = 0
        self.time_reward = 0
        self.action = ""
        self.sector1 = float('inf')
        self.sector2 = float('inf')
        self.sector3 = float('inf')
        self.finish = float('inf')
        self.finish_time = None
        self.action_reward = 0
        self.human = human

    def draw(self, windowSurface):
        self.draw_radar(windowSurface)
        windowSurface.blit(self.rotateSurface, self.pos)
        

    def draw_radar(self, windowSurface):
        for r in self.radars:
            pos, dist = r
            
    def check_collision(self, map):
        self.is_alive = True
        for p in self.four_points:
            if map.get_at((int(p[0]), int(p[1]))) == (BLACK):
                self.is_alive = False
                break
            if map.get_at((int(p[0]), int(p[1]))) == (RED) and self.sector1 == float('inf'):
                self.sector1 = self.time_spent
            if map.get_at((int(p[0]), int(p[1]))) == (BLUE) and self.sector2 == float('inf'):
                self.sector2 = self.time_spent
            if map.get_at((int(p[0]), int(p[1]))) == (GREEN) and self.sector3 == float('inf'):
                self.sector3 = self.time_spent
            if self.sector1 != float('inf') and self.sector2 != float('inf') and self.sector3 != float('inf'):
                if map.get_at((int(p[0]), int(p[1]))) == (LBLUE) and self.finish == float('inf'):
                    self.finish = self.time_spent
                    self.finish_time = time.time()
        
    def check_radar(self, degree, map):
        length = 0
        x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
        y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)
        while not map.get_at((x, y)) == (BLACK) and length < 500:
            length += 1
            x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
            y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)
        
        dist = int(math.sqrt(math.pow(x - self.center[0], 2) + math.pow(y - self.center[1], 2)))
        self.radars.append(((x, y), dist))
    
    def update(self, map, elapsed_time):
        if self.action == "left":
            self.angle -= self.turnspeed
        if self.action == "right":
            self.angle += self.turnspeed
        if self.action == "up":
            self.speed += self.acceleration
            if self.speed > self.max_speed:
                self.speed = self.max_speed
        if self.speed < 2:
            self.speed = 2
        if self.speed > 2.5:
            self.speed -= self.deceleration

        self.pos[0] += math.cos(math.radians(self.angle)) * self.speed
        self.pos[1] -= math.sin(math.radians(self.angle)) * self.speed

        self.distance += self.speed * 0.0166667
        self.time_spent = elapsed_time

        self.rotateSurface = self.rot_center(self.surface, self.angle)

        self.center = [int(self.pos[0] +50), int(self.pos[1] +50)]
        len = 40
        left_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 30))) * len, self.center[1] + math.sin(math.radians(360 - (self.angle + 30))) * len]
        right_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 150))) * len, self.center[1] + math.sin(math.radians(360 - (self.angle + 150))) * len]
        left_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 210))) * len, self.center[1] + math.sin(math.radians(360 - (self.angle + 210))) * len]
        right_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 330))) * len, self.center[1] + math.sin(math.radians(360 - (self.angle + 330))) * len]
        self.four_points = [left_top, right_top, left_bottom, right_bottom]

        self.check_collision(map)
        self.radars.clear()
        for d in range(-90, 120, 45):
            self.check_radar(d, map)

        if self.finish_time != None:
            if time.time() - self.finish_time > 0.3:
                self.is_alive = False
    
    def get_data(self):
        radars = self.radars
        ret = [0,0,0,0,0]
        for i,r in enumerate(radars):
            ret[i] = int(r[1] / 30)
        return ret
    
    def get_alive(self):
        return self.is_alive
    
    def get_reward(self):
        distance_reward = self.distance / total_distance
        if distance_reward > 1:
            distance_reward = 1

        self.action_reward += 0.01 if self.action == "up" else 0

        return (distance_reward * 100) + self.time_reward + self.action_reward
    
    def rot_center(self, image, angle):
        orig_rect = image.get_rect()
        rot_image = pygame.transform.rotate(image, angle)
        rot_rect = orig_rect.copy()
        rot_rect.center = rot_image.get_rect().center
        rot_image = rot_image.subsurface(rot_rect).copy()
        return rot_image

def run_car(genomes, config):

    nets = []
    cars = []

    for id, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0
        cars.append(Car())

    human_car = Car(human=True)
    cars.append(human_car)    
    pygame.init()
    clock = pygame.time.Clock()
    generation_font = pygame.font.SysFont("Arial", 46)
    font = pygame.font.SysFont("Arial", 24)
    sectorfont = pygame.font.SysFont("Arial", 18)
    map = pygame.image.load('graphics/track.png').convert_alpha()
    map = pygame.transform.scale(map, (int(map.get_width() * scale_factor), int(map.get_height() * scale_factor)))
    start_time = time.time()
    for car in cars:
        car.sector1_reached = False
        car.sector2_reached = False
        car.sector3_reached = False
        car.finish_reached = False
    
    global generation, best_sector1, best_sector2, best_sector3, best_finish, best_score, fps, gen_sector1, gen_sector2, gen_sector3, gen_finish
    generation += 1
    while True:
        windowSurface.fill(BLACK)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            human_car.angle += human_car.turnspeed
        if keys[pygame.K_RIGHT]:
            human_car.angle -= human_car.turnspeed
        if keys[pygame.K_UP]:
            human_car.action = "up"

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                sys.exit(0)

        for index, car in enumerate(cars):
            if not car.human:
                output = nets[index].activate(car.get_data())
                if output[0] > 0.5:
                    car.action = "left"
                if output[1] > 0.5:
                    car.action = "right"
                if output[2] > 0.5:
                    car.action = "up"
            
        remain_cars = 0
        elapsed_time = (time.time() - start_time) * (fps / 60)
        minutes, seconds = divmod(elapsed_time, 60)
        timer = "{:02}:{:02}".format(int(minutes), int(seconds))
        current_best = 0
        farthest_car = None
        farthest_distance = 0

        for index, car in enumerate(cars):
            if car.get_alive():
                remain_cars += 1
                car.update(map, elapsed_time)
                car.action = ""
                if not car.human:
                    genomes[index][1].fitness = car.get_reward()
                    if genomes[index][1].fitness > best_score:
                        best_score = genomes[index][1].fitness
                
                # Reward for each sector
                if car.sector1 != float('inf') and not car.sector1_reached:
                    car.sector1_reached = True
                    if car.sector1 < best_sector1:
                        best_sector1 = car.sector1
                    if car.sector1 < gen_sector1:
                        gen_sector1 = car.sector1
                    car.time_reward += (best_sector1 / car.sector1) * 5

                if car.sector2 != float('inf') and not car.sector2_reached:
                    car.sector2_reached = True
                    if car.sector2 < best_sector2:
                        best_sector2 = car.sector2
                    if car.sector2 < gen_sector2:
                        gen_sector2 = car.sector2
                    car.time_reward += (best_sector2 / car.sector2) * 10
                
                if car.sector3 != float('inf') and not car.sector3_reached:
                    car.sector3_reached = True
                    if car.sector3 < best_sector3:
                        best_sector3 = car.sector3
                    if car.sector3 < gen_sector3:
                        gen_sector3 = car.sector3
                    car.time_reward += (best_sector3 / car.sector3) * 15
                
                if car.finish != float('inf') and not car.finish_reached:
                    car.finish_reached = True
                    if car.finish < best_finish:
                        best_finish = car.finish
                    if car.finish < gen_finish:
                        gen_finish = car.finish
                    car.time_reward += (best_finish / car.finish) * 20

                # Check for best score this run
                if not car.human:
                    if genomes[index][1].fitness > current_best:
                            current_best = genomes[index][1].fitness

                if car.distance > farthest_distance:
                    farthest_distance = car.distance
                    farthest_car = car                
                
        if remain_cars == 0:
            break

        windowSurface.blit(map, (0, 0))
        for car in cars:
            if car.get_alive():
                car.draw(windowSurface)

        if farthest_car is not None:
            status_bar_size = (0, 0)

            if farthest_car.sector1 != float('inf'):
                status_bar_size = (status_bar_size[0] + 40, 20)
            if farthest_car.sector2 != float('inf'):
                status_bar_size = (status_bar_size[0] + 40, 20)
            if farthest_car.sector3 != float('inf'):
                status_bar_size = (status_bar_size[0] + 40, 20)

            status_bar_pos = (farthest_car.center[0] - status_bar_size[0] // 2, farthest_car.center[1] - 100 - status_bar_size[1] // 2)

            # Draw a black rectangle slightly larger than the status bar
            border_size = (status_bar_size[0] + 2, status_bar_size[1] + 2)
            border_pos = (status_bar_pos[0] - 1, status_bar_pos[1] - 1)
            if status_bar_size[0] > 0:
                pygame.draw.rect(windowSurface, (0, 0, 0), pygame.Rect(border_pos, border_size))
                pygame.draw.rect(windowSurface, (255, 255, 255), pygame.Rect(status_bar_pos, status_bar_size))

             # Display the sector times
            sector_times = []
            if farthest_car.sector1 != float('inf'):
                sector_times.append(f"{farthest_car.sector1:.1f}")
            if farthest_car.sector2 != float('inf'):
                sector_times.append(f"{farthest_car.sector2:.1f}")
            if farthest_car.sector3 != float('inf'):
                sector_times.append(f"{farthest_car.sector3:.1f}")

            sector_times_text = sectorfont.render(" | ".join(sector_times), True, (0, 255, 0))
            windowSurface.blit(sector_times_text, (status_bar_pos[0] + 5, status_bar_pos[1] - 1))
        
        text = generation_font.render("PyDrive", True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1600, 50)
        windowSurface.blit(text, text_rect)

        text = generation_font.render("Generation: " + str(generation), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1600, 100)
        windowSurface.blit(text, text_rect)

        text = font.render("Cars Alive: " + str(remain_cars), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1600, 150)
        windowSurface.blit(text, text_rect)

        # text = font.render("Alltime top Score: " + "{:.2f}".format(best_score), True, (WHITE))
        # text_rect = text.get_rect()
        # text_rect.center = (1600, 200)
        # windowSurface.blit(text, text_rect)

        # text = font.render("Current top Score: " + "{:.2f}".format(current_best), True, (WHITE))
        # text_rect = text.get_rect()
        # text_rect.center = (1600, 225)
        # windowSurface.blit(text, text_rect)

        text = font.render("Time elapsed: " + timer, True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1600, 200)
        windowSurface.blit(text, text_rect)

        text = font.render("BEST        RUN", True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1625, 265)
        windowSurface.blit(text, text_rect)    

        text = font.render("Fastest sector 1:   " + "{:.2f}".format(best_sector1), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1500, 300)
        windowSurface.blit(text, text_rect)

        text = font.render("{:.2f}".format(gen_sector1), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1660, 300)
        windowSurface.blit(text, text_rect)

        text = font.render("Fastest sector 2:   " + "{:.2f}".format(best_sector2), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1500, 350)
        windowSurface.blit(text, text_rect)

        text = font.render("{:.2f}".format(gen_sector2), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1660, 350)
        windowSurface.blit(text, text_rect)

        text = font.render("Fastest sector 3:   " + "{:.2f}".format(best_sector3), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1500, 400)
        windowSurface.blit(text, text_rect)

        text = font.render("{:.2f}".format(gen_sector3), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1660, 400)
        windowSurface.blit(text, text_rect)

        text = font.render("Fastest Lap:         " + "{:.2f}".format(best_finish) , True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1500, 500)
        windowSurface.blit(text, text_rect)

        text = font.render("{:.2f}".format(gen_finish), True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1660, 500)
        windowSurface.blit(text, text_rect)

        text = font.render("FPS: " + "{:.2f}".format(clock.get_fps()), True, (GREEN))
        text_rect = text.get_rect()
        text_rect.center = (1600, 600)
        windowSurface.blit(text, text_rect)

        text = font.render("Press 'q' to quit", True, (WHITE))
        text_rect = text.get_rect()
        text_rect.center = (1600, 650)
        windowSurface.blit(text, text_rect)
        
        pygame.display.update()
        clock.tick(fps)

if __name__ == "__main__":
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, 'config-feedforward.txt')
    p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)
    p.add_reporter(Checkpointer(generation_interval=10, filename_prefix='neat-checkpoint-' + str(best_finish)))
    # p = Checkpointer.restore_checkpoint('neat-checkpoint-inf44') # Uncomment this line to restore from checkpoint

    p.run(run_car, 50)

