import cv2
import numpy as np
from mss import mss
import neat
import pyautogui
import pygetwindow as gw
import time

main_screen_width = 2560
main_screen_height = 1440
second_screen_width = 1600
second_screen_height = 900

sct = mss()

# Initialize lists to store contour data
pink_data = []
light_gray_data = []
white_gray_data = []

def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        genome.fitness = 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)

        screenshot = sct.grab({'top': 30, 'left': -second_screen_width, 'width': second_screen_width, 'height': second_screen_height})
        time.sleep(0.1)
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGBA2RGB)
        pink_data, light_gray_data, white_gray_data = process_screenshot(screenshot)

        if pink_data:
            initial_position = pink_data[0]
        else:
            print('No pink data found')
            time.sleep(1)
            continue

        for pink, light_gray, white_gray in zip(pink_data, light_gray_data, white_gray_data):
            data = list(pink.values()) + list(light_gray.values()) + list(white_gray.values())
            action = net.activate(data)
            game_window = gw.getWindowsWithTitle("GeneRally")[0]
            game_window.activate()
            time.sleep(0.1)
            print(game_window)
            if game_window.title != "GeneRally":
                print('GeneRally window not found')
                break
            # Interpret the outputs as actions
            if action[0] > 0.5:  # Move forward
                pyautogui.keyDown('up')
                pyautogui.keyUp('up')
            if action[1] > 0.5:  # Move backward
                pyautogui.keyDown('down')
                pyautogui.keyUp('down')
            if action[2] > 0.5:  # Turn left
                pyautogui.keyDown('left')
                pyautogui.keyUp('left')
            if action[3] > 0.5:  # Turn right
                pyautogui.keyDown('right')
                pyautogui.keyUp('right')
            # Update the fitness based on the result of the action
            current_position = pink_data[0]
            distance = np.sqrt((current_position['x'] - initial_position['x'])**2 + (current_position['y'] - initial_position['y'])**2)
            genome.fitness += distance

            # Check for collisions with walls
            for wall in white_gray_data:
                if (current_position['x'] < wall['x'] + wall['w'] and
                    current_position['x'] + current_position['w'] > wall['x'] and
                    current_position['y'] < wall['y'] + wall['h'] and
                    current_position['y'] + current_position['h'] > wall['y']):
                    genome.fitness -= 100  # Adjust penalty as needed

            # Check if off track
            on_track = False
            for track in light_gray_data:
                if (current_position['x'] > track['x'] and
                    current_position['x'] + current_position['w'] < track['x'] + track['w'] and
                    current_position['y'] > track['y'] and
                    current_position['y'] + current_position['h'] < track['y'] + track['h']):
                    on_track = True
                    break
            if not on_track:
                genome.fitness -= 100  # Adjust penalty as needed
            
            
            

config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, 'config-feedforward.txt')

p = neat.Population(config)
p.add_reporter(neat.StdOutReporter(True))
stats = neat.StatisticsReporter()
p.add_reporter(stats)

def process_screenshot(screenshot):
    # Convert the image from BGR to HSV
    hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

    # Define color ranges in RGB
    pink_lower_rgb = np.array([0, 0, 0])
    pink_upper_rgb = np.array([51, 51, 51])
    light_gray_lower_rgb = np.array([109, 109, 109])
    light_gray_upper_rgb = np.array([190, 190, 190])
    white_gray_lower_rgb = np.array([191, 191, 191])
    white_gray_upper_rgb = np.array([232, 232, 211])

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
    min_contour_area = 300  # Adjust this value based on your needs

    # Draw bounding rectangles around the contours and store the data
    pink_data = []
    light_gray_data = []
    white_gray_data = []
    for contour in pink_contours:
        if cv2.contourArea(contour) > min_contour_area:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(screenshot, (x, y), (x + w, y + h), (255, 0, 255), 2)
            pink_data.append({'x': x, 'y': y, 'w': w, 'h': h})
    for contour in light_gray_contours:
        if cv2.contourArea(contour) > min_contour_area:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.drawContours(screenshot, [contour], -1, (255, 255, 0), 2)
            light_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})

    for contour in white_gray_contours:
        if cv2.contourArea(contour) > min_contour_area:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.drawContours(screenshot, [contour], -1, (0, 255, 0), 2)
            white_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})

    return pink_data, light_gray_data, white_gray_data

while True:
    screenshot = sct.grab({'top': 30, 'left': -second_screen_width, 'width': second_screen_width, 'height': second_screen_height})
    screenshot = np.array(screenshot)
    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGBA2RGB)
    
    # Convert the image from BGR to HSV
    hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

    # Convert RGB to HSV
    def convert_rgb_to_hsv(color):
        color = np.uint8([[color]])
        hsv_color = cv2.cvtColor(color, cv2.COLOR_RGB2HSV)
        return hsv_color[0][0]

    # Define color ranges in RGB
    pink_lower_rgb = np.array([0, 0, 0])
    pink_upper_rgb = np.array([51, 51, 51])
    light_gray_lower_rgb = np.array([109, 109, 109])
    light_gray_upper_rgb = np.array([190, 190, 190])
    white_gray_lower_rgb = np.array([191, 191, 191])
    white_gray_upper_rgb = np.array([232, 232, 211])

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
    min_contour_area = 100  # Adjust this value based on your needs

    # Draw bounding rectangles around the contours
    for contour in pink_contours:
        if cv2.contourArea(contour) > min_contour_area:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(screenshot, (x, y), (x + w, y + h), (0, 0, 255), 2)
            pink_data.append({'x': x, 'y': y, 'w': w, 'h': h})

    for contour in light_gray_contours:
        if cv2.contourArea(contour) > min_contour_area:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.drawContours(screenshot, [contour], -1, (255, 255, 0), 2)
            light_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})

    for contour in white_gray_contours:
        if cv2.contourArea(contour) > min_contour_area:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.drawContours(screenshot, [contour], -1, (0, 255, 0), 2)
            white_gray_data.append({'x': x, 'y': y, 'w': w, 'h': h})
    cv2.imshow('Rally', screenshot)
    winner = p.run(eval_genomes, 50)
    if cv2.waitKey(1) == ord('q'):
        break
    if cv2.getWindowProperty('Rally', cv2.WND_PROP_VISIBLE) < 1:
        break
