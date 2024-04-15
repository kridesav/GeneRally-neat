import cv2
import numpy as np
from mss import mss
import neat
import pyautogui
import pygetwindow as gw
from threading import Thread, Lock
import keyboard
from queue import Queue
import time

main_screen_width = 2560
main_screen_height = 1440
second_screen_width = 1600
second_screen_height = 900

game_data = {}
game_lock = Lock()
stop = False

config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, 'config-feedforward.txt')
p = neat.Population(config)
p.add_reporter(neat.StdOutReporter(True))
stats = neat.StatisticsReporter()
p.add_reporter(stats)

def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        pyautogui.keyUp('up')
        reset_game()
        crossed_checkpoints = set()
        not_crashed = True
        genome.fitness = 0
        last_checkpoint_time = 0
        initial_position = None
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        while True:
            game_window = gw.getWindowsWithTitle("GeneRally")[0]
            if game_window.title == "GeneRally":
                break
            time.sleep(5)
            print('Game window not found, waiting for 5 seconds...')
            genome.fitness = 0  # No game window, so no fitness
        if not game_data:
            print('No game data, waiting for 5 seconds...')
            time.sleep(5)
            genome.fitness = 0
            continue
        else:
            while not_crashed:
                car_center, directions_data, light_gray_data = game_data
                # Flatten directions_data and next_checkpoint_data into lists
                directions_data_list = [item for sublist in directions_data.values() for item in sublist]
                # next_checkpoint_data_list = [item for sublist in next_checkpoint_data.values() for item in sublist]
                # Create the data list
                data = list(car_center) + directions_data_list  #next_checkpoint_data_list
                print(data)
                # Feed the data into the neural network
                action = net.activate(data)
                if initial_position is None:
                    initial_position = car_center
                start_time = time.time()
                # Interpret the outputs as actions
                pyautogui.keyDown('up')  # Press the up key

                if action[0] > 0.5:  # Release the up key
                    pyautogui.keyUp('up')
                elif action[1] > 0.5:  # Turn right
                    pyautogui.keyUp('up')
                    pyautogui.keyDown('right')
                    pyautogui.keyUp('right')
                # Update the fitness based on the result of the action
                end_time = time.time()
                time_taken = end_time - start_time
                current_position = car_center
                distance_squared = (current_position[0] - initial_position[0])**2 + (current_position[1] - initial_position[1])**2
                genome.fitness += (distance_squared * 0.0001) / (time_taken + 1e-6) # Adjust reward as needed
                initial_position = current_position

                min_distance = min(directions_data.values())
                if min_distance[0] <= 15:
                    if genome.fitness > 10:
                        genome.fitness -= 10
                    else:
                        genome.fitness = 0
                    print('Crashed')
                    not_crashed = False
                    break
                if keyboard.is_pressed('q'):
                    stop = True
                    break
            print(f'Genome ID: {genome_id}, Fitness: {genome.fitness}, Crossed Checkpoints: {crossed_checkpoints}')

def run_neat():
            global stop
            while not stop:
                game_window = gw.getWindowsWithTitle("GeneRally")[0]
                if game_window.title == "GeneRally":
                    break
                time.sleep(5)
                print('Game window not found, waiting for 5 seconds...')

            winner = p.run(eval_genomes, 50)

def reset_game():
    pyautogui.keyDown('esc')
    pyautogui.keyUp('esc')
    time.sleep(0.3)
    pyautogui.keyDown('up')
    pyautogui.keyUp('up')
    time.sleep(0.3)
    pyautogui.keyDown('enter')
    pyautogui.keyUp('enter')
    time.sleep(0.3)
    pyautogui.keyDown('enter')
    pyautogui.keyUp('enter')
    time.sleep(0.3)
    pyautogui.keyDown('enter')
    pyautogui.keyUp('enter')
    time.sleep(0.3)
    pyautogui.keyDown('enter')
    pyautogui.keyUp('enter')
    time.sleep(3)

def rectangles_intersect(r1, r2):
    return not (r1['x'] > r2['x'] + r2['w'] or
                r1['x'] + r1['w'] < r2['x'] or
                r1['y'] > r2['y'] + r2['h'] or
                r1['y'] + r1['h'] < r2['y'])

def run_game(sct):
    global stop
    while game_lock:
        while not stop:
            time.sleep(0.3)
            
            pink_data = []
            light_gray_data = []
            white_gray_data = []
            min_distance = float('inf')
            directions_data = {}
            next_checkpoint_data = {}
            min_distance_checkpoint = float('inf')
            line_id = 0

            # Retry the screen capture if it fails
            for _ in range(10):  # Retry up to 5 times
                try:
                    screenshot = sct.grab({'top': 30, 'left': -second_screen_width, 'width': second_screen_width, 'height': second_screen_height})
                    break  # If the capture was successful, break out of the loop
                except Exception as e:
                    print(f"Screen capture failed with error: {e}")
                    time.sleep(1)  # Wait a bit before retrying

            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGBA2RGB)

            # Define the area to exclude
            exclude_area = np.zeros_like(screenshot)
            height, width, _ = screenshot.shape
            start_x = 0
            start_y = int(height * 0.92)
            end_x = width
            end_y = height  
            cv2.rectangle(exclude_area, (start_x, start_y), (end_x, end_y), (0, 0, 255), -1)
            # Apply the exclusion mask to the image
            screenshot = cv2.addWeighted(screenshot, 1, exclude_area, 1, 0)
            
            # Convert the image from BGR to HSV
            hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

            # Convert RGB to HSV
            def convert_rgb_to_hsv(color):
                color = np.uint8([[color]])
                hsv_color = cv2.cvtColor(color, cv2.COLOR_RGB2HSV)
                return hsv_color[0][0]

            pink_lower_rgb = np.array([0, 0, 0])
            pink_upper_rgb = np.array([51, 51, 51])
            light_gray_lower_rgb = np.array([241, 237, 45])
            light_gray_upper_rgb = np.array([242, 238, 46])
            white_gray_lower_rgb = np.array([224, 221, 218])
            white_gray_upper_rgb = np.array([241, 237, 233])

            # Convert color ranges to HSV
            pink_lower = convert_rgb_to_hsv(pink_lower_rgb)
            pink_upper = convert_rgb_to_hsv(pink_upper_rgb)
            light_gray_lower = convert_rgb_to_hsv(light_gray_lower_rgb)
            light_gray_upper = convert_rgb_to_hsv(light_gray_upper_rgb)
            white_gray_lower = convert_rgb_to_hsv(white_gray_lower_rgb)
            white_gray_upper = convert_rgb_to_hsv(white_gray_upper_rgb)

            # Create masks
            pink_mask = cv2.inRange(hsv, pink_lower, pink_upper)
            light_gray_mask = cv2.inRange(hsv, light_gray_lower, light_gray_upper)
            white_gray_mask = cv2.inRange(hsv, white_gray_lower, white_gray_upper)

            # Find contours in the masks
            pink_contours, _ = cv2.findContours(pink_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            light_gray_contours, _ = cv2.findContours(light_gray_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            white_gray_contours, _ = cv2.findContours(white_gray_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            # Define a minimum contour area
            min_contour_area_pink = 50  # Adjust this value based on your needs
            min_contour_area_light_gray = 500  # Adjust this value based on your needs
            min_contour_area_white_gray = 1  # Adjust this value based on your needs

            # Create a blank image of the same size as the screenshot
            blank_image = np.zeros_like(screenshot)
            
            # Draw bounding rectangles around the contours on the blank image

            for contour in light_gray_contours:
                if cv2.contourArea(contour) > min_contour_area_light_gray:
                    x, y, w, h = cv2.boundingRect(contour)
                    light_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})

            for contour in white_gray_contours:
                if cv2.contourArea(contour) > min_contour_area_white_gray:
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.drawContours(blank_image, [contour], -1, (0, 255, 0), 2)
                    white_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})
            
            for contour in pink_contours:
                if cv2.contourArea(contour) > min_contour_area_pink:
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.drawContours(blank_image, [contour], -1, (255, 0, 255), -1)
                    pink_data.append({'x': x, 'y': y, 'w': w, 'h': h})

            if light_gray_data:
                for line in light_gray_data:
                    line['id'] = line_id
                    line_id += 1

            if pink_data:
                padding_x = 10
                padding_y = 10
                car_center_x = int(np.mean([d['x'] for d in pink_data])) + padding_x
                car_center_y = int(np.mean([d['y'] for d in pink_data])) + padding_y
                car_center = (car_center_x, car_center_y)

                directions = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]

                # For each direction
                for dx, dy in directions:
                    closest_wall = None
                    min_distance = float('inf')

                    # For each wall
                    for wall in white_gray_data:
                        wall_center = (wall['x'] + wall['w'] // 2, wall['y'] + wall['h'] // 2)

                        # Calculate the distance in the direction of interest
                        distance = ((car_center[0] + dx - wall_center[0]) ** 2 + (car_center[1] + dy - wall_center[1]) ** 2) ** 0.5

                        # If this wall is closer than the current closest wall, update minimum distance and closest wall
                        if distance < min_distance:
                            min_distance = distance
                            closest_wall = wall

                    # Draw a line to the closest wall and display the distance
                    if closest_wall is not None:
                        closest_wall_center = (closest_wall['x'] + closest_wall['w'] // 2, closest_wall['y'] + closest_wall['h'] // 2)
                        cv2.line(blank_image, car_center, closest_wall_center, (255, 255, 255), 2)
                        text_position = (int((car_center[0] + closest_wall_center[0]) / 2), int((car_center[1] + closest_wall_center[1]) / 2))
                        cv2.putText(blank_image, str(round(min_distance, 2)), text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    
                    # Store the direction and the minimum distance in the dictionary
                    directions_data[(dx, dy)] = [min_distance]

                # closest_checkpoint = None
                # # For each checkpoint
                # for checkpoint in light_gray_data:
                #     checkpoint_center = (checkpoint['x'] + checkpoint['w'] // 2, checkpoint['y'] + checkpoint['h'] // 2)

                #     # Calculate the distance to the checkpoint
                #     distance = ((car_center[0] - checkpoint_center[0]) ** 2 + (car_center[1] - checkpoint_center[1]) ** 2) ** 0.5

                #     # If this checkpoint is closer than the current closest checkpoint, update minimum distance and closest checkpoint
                #     if distance < min_distance_checkpoint:
                #         min_distance_checkpoint = distance
                #         closest_checkpoint = checkpoint_center

                #     if closest_checkpoint is not None:
                #         # Calculate the direction to the next checkpoint
                #         dx_checkpoint = closest_checkpoint[0] - car_center[0]
                #         dy_checkpoint = closest_checkpoint[1] - car_center[1]

                #         # Store the direction and the minimum distance to the next checkpoint in a dictionary
                #         next_checkpoint_data = {'direction': (dx_checkpoint, dy_checkpoint), 'distance': [min_distance_checkpoint]}

                #         # Draw a line to the next checkpoint and display the distance
                #         cv2.line(blank_image, car_center, closest_checkpoint, (255, 0, 0), 2)
                #         text_position = (int((car_center[0] + closest_checkpoint[0]) / 2), int((car_center[1] + closest_checkpoint[1]) / 2))
                #         cv2.putText(blank_image, str(round(next_checkpoint_data['distance'][0], 2)), text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            else:
                print('No car detected')
                break

            # Display the blank image with the rectangles
            if blank_image is not None:
                cv2.imshow('Rally', blank_image)
            else:
                print('No image to display')
                break
            if cv2.waitKey(1) == ord('q') or keyboard.is_pressed('q'):
                stop = True
                cv2.destroyAllWindows()
                break
            return car_center, directions_data, light_gray_data  #next_checkpoint_data

def run_game_and_update_global_data():
    global game_data
    while True:
        with game_lock:
            sct = mss()
            game_data = run_game(sct)  # Update the game data

# Create and start the threads
game_thread = Thread(target=run_game_and_update_global_data)
neat_thread = Thread(target=run_neat)

game_thread.start()
neat_thread.start()

# Wait for the threads to finish (they won't, because they're in infinite loops)
game_thread.join()
neat_thread.join()