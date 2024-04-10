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

stop = False

# Initialize lists to store contour data
def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        genome.fitness = 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        game_window = gw.getWindowsWithTitle("GeneRally")[0]
        if game_window.title != "GeneRally":
            time.sleep(5)
            print('Game window not found, waiting for 5 seconds...')
            genome.fitness = 0  # No game window, so no fitness
            continue

        if game_data:
            car_center, white_gray_data, min_distance = game_data
        else:
            print('No game data, waiting for 5 seconds...')
            time.sleep(5)
            genome.fitness = 0  # No game data, so no fitness
            continue

        for white_gray in white_gray_data:
            data = list(car_center) + list(white_gray.values()) + [min_distance]
            action = net.activate(data)
            initial_position = car_center
            # Interpret the outputs as actions
            if action[0] > 0.2:  # Move forward
                pyautogui.keyDown('up')
                pyautogui.keyUp('up')
            if action[1] > 1:  # Move backward
                pyautogui.keyDown('down')
                pyautogui.keyUp('down')
            if action[2] > 0.5:  # Turn left
                pyautogui.keyDown('left')
                pyautogui.keyUp('left')
            if action[3] > 0.2:  # Turn right
                pyautogui.keyDown('right')
                pyautogui.keyUp('right')

            # Update the fitness based on the result of the action
            if game_data:
                car_center, white_gray_data, min_distance = game_data
            else:
                print('No game data, waiting for 5 seconds...')
                time.sleep(5)
                genome.fitness = 0  # No game data, so no fitness
                continue

            current_position = car_center
            distance = np.sqrt((current_position[0] - initial_position[0])**2 + (current_position[1] - initial_position[1])**2)
            genome.fitness += distance

            # Check for collisions with walls
            for wall in white_gray_data:
                # Calculate the distance from the car to the wall
                wall_distance = np.sqrt((current_position[0] - wall['x'])**2 + (current_position[1] - wall['y'])**2)
                # Reward the car for being further from the wall
                if wall_distance > 20:
                    genome.fitness += wall_distance * 10  # Adjust reward as needed
                else:
                    genome.fitness -= wall_distance * 10

                # Penalize the car for hitting a wall
                if (current_position[0] < wall['x'] + wall['w'] and
                    current_position[1] < wall['y'] + wall['h']):
                    genome.fitness -= 100  # Adjust penalty as needed
                    break
                else:
                    continue
            break


def run_neat():
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, 'config-feedforward.txt')

    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    winner = p.run(eval_genomes, 50)

def run_game():
    global stop
    while not stop:
        sct = mss()
        pink_data = []
        light_gray_data = []
        white_gray_data = []
        min_distance = float('inf')

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

        blank_image = np.zeros_like(screenshot)

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
        light_gray_lower_rgb = np.array([0, 250, 0])
        light_gray_upper_rgb = np.array([0, 250, 0])
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
        min_contour_area_pink = 100  # Adjust this value based on your needs
        min_contour_area_light_gray = 10  # Adjust this value based on your needs
        min_contour_area_white_gray = 0.1  # Adjust this value based on your needs

        # Create a blank image of the same size as the screenshot
        blank_image = np.zeros_like(screenshot)
        
        # Draw bounding rectangles around the contours on the blank image
        for contour in pink_contours:
            if cv2.contourArea(contour) > min_contour_area_pink:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(blank_image, (x, y), (x + w, y + h), (255, 0, 255), 2)
                pink_data.append({'x': x, 'y': y, 'w': w, 'h': h})

        for contour in light_gray_contours:
            if cv2.contourArea(contour) > min_contour_area_light_gray:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.drawContours(blank_image, [contour], -1, (255, 255, 0), 2)
                light_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})

        for contour in white_gray_contours:
            if cv2.contourArea(contour) > min_contour_area_white_gray:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.drawContours(blank_image, [contour], -1, (0, 255, 0), 2)
                white_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})

        if pink_data:
            padding_x = 10
            padding_y = 10
            car_center_x = int(np.mean([d['x'] for d in pink_data])) + padding_x
            car_center_y = int(np.mean([d['y'] for d in pink_data])) + padding_y
            car_center = (car_center_x, car_center_y)

            closest_wall = None  # Initialize closest wall as None

            for wall in white_gray_data:
                wall_center = (wall['x'] + wall['w'] // 2, wall['y'] + wall['h'] // 2)
                distance = ((car_center[0] - wall_center[0]) ** 2 + (car_center[1] - wall_center[1]) ** 2) ** 0.5

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
        return car_center, white_gray_data, min_distance

def run_game_and_update_global_data():
    global game_data
    while True:  # Run game in a loop
            game_data = run_game()  # Update the game data

def run_neat_with_global_data():
    while True:  # Run NEAT in a loop
        run_neat()

# Create and start the threads
game_thread = Thread(target=run_game_and_update_global_data)
neat_thread = Thread(target=run_neat_with_global_data)

game_thread.start()
neat_thread.start()

# Wait for the threads to finish (they won't, because they're in infinite loops)
game_thread.join()
neat_thread.join()