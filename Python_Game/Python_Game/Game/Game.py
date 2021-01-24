import arcade
import time
import os
import tkinter as tk
import tkinter.messagebox as msg
import pickle

# Constants used to scale our sprites from their original size
CHARACTER_SCALING = 1
TILE_SCALING = 0.5
FLAG_SCALING = 0.5

# Movement speed of player, in pixels per frame
PLAYER_MOVEMENT_SPEED = 5
GRAVITY = 1.0
PLAYER_JUMP_SPEED = 20

# Constants used to track if the player is facing left or right
RIGHT_FACING = 0
LEFT_FACING = 1

# How many pixels to keep as a minimum margin between the character
# and the edge of the screen.
LEFT_VIEWPORT_MARGIN = 250
RIGHT_VIEWPORT_MARGIN = 250
BOTTOM_VIEWPORT_MARGIN = 50
TOP_VIEWPORT_MARGIN = 100

GAME_RUNNING = 2
GAME_OVER = 3

PLAYER_START_X = 64
PLAYER_START_Y = 128

def load_texture_pair(filename):
    """
    Load a texture pair, with the second being a mirror image.
    """
    return [
        arcade.load_texture(filename),
        arcade.load_texture(filename, mirrored=True)
    ]

class PlayerUpdate(arcade.Sprite):
    """ Player Sprite"""
    def __init__(self):

        # Set up parent class
        super().__init__()

        # Default to face-right
        self.character_face_direction = RIGHT_FACING

        # Used for flipping between image sequences
        self.cur_texture = 0
        self.scale = CHARACTER_SCALING

        # Track our state
        self.jumping = False
        self.climbing = False

        # --- Load Textures ---

        main_path = ":resources:images/animated_characters/robot/robot"

        # Load textures for idle standing
        self.idle_texture_pair = load_texture_pair(f"{main_path}_idle.png")
        self.jump_texture_pair = load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = load_texture_pair(f"{main_path}_fall.png")

        # Load textures for walking
        self.walk_textures = []
        for i in range(8):
            texture = load_texture_pair(f"{main_path}_walk{i}.png")
            self.walk_textures.append(texture)

        # Set the initial texture
        self.texture = self.idle_texture_pair[0]

        # Hit box will be set based on the first image used. If you want to specify
        # a different hit box, you can do it like the code below.
        # self.set_hit_box([[-22, -64], [22, -64], [22, 28], [-22, 28]])
        #self.set_hit_box(self.texture.hit_box_points)

    def update_animation(self, delta_time: float = 1/60):

        # Figure out if we need to flip face left or right
        if self.change_x < 0 and self.character_face_direction == RIGHT_FACING:
            self.character_face_direction = LEFT_FACING
        elif self.change_x > 0 and self.character_face_direction == LEFT_FACING:
            self.character_face_direction = RIGHT_FACING

        # Jumping animation
        if self.change_y > 0:
            self.texture = self.jump_texture_pair[self.character_face_direction]
            return
        elif self.change_y < 0:
            self.texture = self.fall_texture_pair[self.character_face_direction]
            return

        # Idle animation
        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Walking animation
        self.cur_texture += 1
        if self.cur_texture > 7:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture][self.character_face_direction]

class Game(arcade.Window):
    """This Class Creates a Game"""
    
    def __init__(self, SCREEN_WIDTH, SCREEN_HEIGHT, title, leaderboard):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, title)

        self.SCREEN_WIDTH = SCREEN_WIDTH
        self.SCREEN_HEIGHT = SCREEN_HEIGHT
        self.leaderboard = leaderboard

        self.game_over = False
        self.new_game = False

        self.set_mouse_visible(False)

        # Set the path to start with this program
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)

        # Track the current state of what key is pressed
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.jump_needs_reset = False

        self.current_state = GAME_RUNNING

        # These are 'lists' that keep track of our sprites. Each sprite should
        # go into a list.
        self.flag_list = None
        self.wall_list = None
        self.player_list = None

        # Separate variable that holds the player sprite
        self.player_sprite = None

        arcade.set_background_color(arcade.csscolor.BLUE)

        # Our physics engine
        self.physics_engine = None

        # Used to keep track of our scrolling
        self.view_bottom = 0
        self.view_left = 0

        self.changed = True

        self.end_of_map = 0

        # Keep track of the time
        self.text_angle = 0
        self.time_elapsed = 0.0
        
        # Add Sounds - Resource from Arcade
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.win_sound = arcade.load_sound(":resources:sounds/coin1.wav")

    def setup(self):

        # Used to keep track of our scrolling
        self.view_bottom = 0
        self.view_left = 0

        self.current_state = GAME_RUNNING
        self.player_moved = False

        """ Set up the game here. Call this function to restart the game. """
        # Create the Sprite lists
        self.player_list = arcade.SpriteList()
        self.wall_list = arcade.SpriteList()
        self.flag_list = arcade.SpriteList()

        # Set up the player, specifically placing it at these coordinates.
        self.player_sprite = PlayerUpdate()

        # Set up the player, specifically placing it at these coordinates.
        self.player_sprite.center_x = PLAYER_START_X
        self.player_sprite.center_y = PLAYER_START_Y
        self.player_list.append(self.player_sprite)

        # Create the 'physics engine'
        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite, self.wall_list, GRAVITY)

        flag = arcade.Sprite(":resources:images/items/flagRed1.png", FLAG_SCALING)
        flag.center_x = 2332
        flag.center_y = 364

        self.flag_list.append(flag)

        self.buildMap()

    def on_draw(self):
        arcade.start_render()

        # Draw our sprites
        self.wall_list.draw()
        self.flag_list.draw()
        self.player_list.draw()

        arcade.draw_text(f"{self.time_elapsed:7.2f}",(self.view_left + (self.SCREEN_WIDTH/2)),(self.SCREEN_HEIGHT-100),arcade.color.BLACK, 20)

        if self.game_over:
            """
            Draw "Game over" across the screen.
            """
            output = "Game Over"
            arcade.draw_text(output,(self.view_left + (self.SCREEN_WIDTH/2)),(self.SCREEN_HEIGHT-50),arcade.color.BLACK, 20)

            output = "Click to restart"
            arcade.draw_text(output,(self.view_left + (self.SCREEN_WIDTH/2)),(self.SCREEN_HEIGHT-150),arcade.color.BLACK, 20)

    def process_keychange(self):
        """
        Called when we change a key up/down or we move on/off a ladder.
        """

        if self.current_state == GAME_RUNNING:
            # Process up/down
            if self.up_pressed:
                if self.physics_engine.can_jump() and not self.jump_needs_reset:
                    self.player_sprite.change_y = PLAYER_JUMP_SPEED
                    self.jump_needs_reset = True
                    arcade.play_sound(self.jump_sound)

            # Process left/right
            if self.right_pressed and not self.left_pressed:
                self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
            elif self.left_pressed and not self.right_pressed:
                self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
            else:
                self.player_sprite.change_x = 0

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        if self.current_state == GAME_RUNNING:
            if key == arcade.key.UP or key == arcade.key.W:
                self.up_pressed = True
                arcade.play_sound(self.jump_sound)
            #elif key == arcade.key.DOWN or key == arcade.key.S:
                #self.down_pressed = True
            elif (key == arcade.key.LEFT or key == arcade.key.A) and self.player_sprite._get_left() > 50:
                self.left_pressed = True
            elif key == arcade.key.RIGHT or key == arcade.key.D:
                self.right_pressed = True

            if self.player_moved == False:
                self.player_moved = True

            self.process_keychange()

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """
        if self.current_state == GAME_RUNNING:
            if key == arcade.key.UP or key == arcade.key.W:
                self.up_pressed = False
                self.jump_needs_reset = False
            elif key == arcade.key.DOWN or key == arcade.key.S:
                self.down_pressed = False
            elif key == arcade.key.LEFT or key == arcade.key.A or self.player_sprite._get_left() < 50:
                self.left_pressed = False
            elif key == arcade.key.RIGHT or key == arcade.key.D:
                self.right_pressed = False

            self.process_keychange()

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Called when the user presses a mouse button.
        """
        if self.current_state == GAME_OVER or self.current_state == None:
            # Restart the game.
            self.addScore()
            self.setup()
            self.changed = True
            self.time_elapsed = 0.0
            self.new_game = True
            self.game_over = False


    def on_update(self, delta_time):
        """ Movement and game logic """

        # Move the player with the physics engine
        self.physics_engine.update()

        # See if we hit any coins
        flag_hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.flag_list)

        # Loop through each coin we hit (if any) and remove it
        for flag in flag_hit_list:
            # Remove the coin
            flag.remove_from_sprite_lists()
            # Play a sound
            arcade.play_sound(self.win_sound)

        if len(self.flag_list) == 0:
            self.current_state = GAME_OVER
            self.set_mouse_visible(True)
            self.game_over = True



        # --- Manage Scrolling ---

        # Track if we need to change the viewport
        if self.current_state != GAME_OVER:
            self.player_list.update_animation(delta_time)
        else:  
            self.score = delta_time

        if self.current_state == GAME_RUNNING:
            self.changed = False

        if self.player_sprite.center_y < -100:
            self.player_sprite.center_x = PLAYER_START_X
            self.player_sprite.center_y = PLAYER_START_Y

            # Set the camera to the start
            self.view_left = 0
            self.view_bottom = 0
            self.changed = True

        # Left Boundary prevents the Player from going off the screen on the left
        left_boundary = self.view_left + 10

        if (self.player_sprite.left < left_boundary) or self.current_state == GAME_OVER:
            self.player_sprite.change_x = 0
        if self.current_state != GAME_OVER and self.player_moved == True:
            self.time_elapsed += delta_time

        # Scroll left
        #left_boundary = self.view_left + LEFT_VIEWPORT_MARGIN
        #if self.player_sprite.left < left_boundary:
        #    self.view_left -= left_boundary - self.player_sprite.left
        #    self.changed = True

        # Scroll right
        right_boundary = self.view_left + self.SCREEN_WIDTH - RIGHT_VIEWPORT_MARGIN
        if self.player_sprite.right > right_boundary:
            self.view_left += self.player_sprite.right - right_boundary
            self.changed = True

        # Scroll up
        top_boundary = self.view_bottom + self.SCREEN_HEIGHT - TOP_VIEWPORT_MARGIN
        if self.player_sprite.top > top_boundary:
            self.view_bottom += self.player_sprite.top - top_boundary
            self.changed = True

        # Scroll down
        bottom_boundary = self.view_bottom + BOTTOM_VIEWPORT_MARGIN
        if self.player_sprite.bottom < bottom_boundary:
            self.view_bottom -= bottom_boundary - self.player_sprite.bottom
            self.changed = True


        if self.changed or self.new_game:
            # Only scroll to integers. Otherwise we end up with pixels that
            # don't line up on the screen
            self.view_bottom = int(self.view_bottom)
            self.view_left = int(self.view_left)

            # Do the scrolling
            arcade.set_viewport(self.view_left, self.SCREEN_WIDTH + self.view_left, self.view_bottom, self.SCREEN_HEIGHT + self.view_bottom)
            if self.new_game:
                self.new_game = False

            

    def buildMap(self):

        # Create the ground
        # This shows using a loop to place multiple sprites horizontally
        for x in range(-64, 448, 64):
            wall = arcade.Sprite(":resources:images/tiles/stoneMid.png", TILE_SCALING)
            wall.center_x = x
            wall.center_y = 32
            self.wall_list.append(wall)

        wall = arcade.Sprite(":resources:images/tiles/stoneMid.png", TILE_SCALING)
        wall.center_x = 420
        wall.center_y = 32
        self.wall_list.append(wall)

        wall = arcade.Sprite(":resources:images/tiles/stoneRIGHT.png", TILE_SCALING)
        wall.center_x = 448
        wall.center_y = 32
        self.wall_list.append(wall)

        # Create the Platforms Top Layer
        self.platform_3(700, 300)
        self.platform_2(1080, 400)
        cx = 1400
        cy = 360
        for i in range(5):
            self.platform_1((cx + (i * 64)), (cy + (i * 64)))

        self.platform_3(1950, 500)

        # Create the platforms Bottom Layer
        self.platform_1(1000, 32)
        self.platform_2(1250, 132)
        self.platform_2(1378, 68)
        self.platform_1(1650, 200)
        self.platform_3(1950, 130)

        # Final Platform
        self.platform_1(2300, 300)

        # Put some crates on the ground
        # This shows using a coordinate list to place sprites
        coordinate_list = [[256, 96],
                           [450, 96],
                           [450, 160],
                           [450, 224]]

        for coordinate in coordinate_list:
            # Add a crate on the ground
            wall = arcade.Sprite(":resources:images/tiles/boxCrate_double.png", TILE_SCALING)
            wall.position = coordinate
            self.wall_list.append(wall)


    def platform_1(self, coord_x, coord_y):
        wall = arcade.Sprite(":resources:images/tiles/stone.png", TILE_SCALING)
        wall.center_x = coord_x
        wall.center_y = coord_y
        self.wall_list.append(wall)

    def platform_2(self, coord_x, coord_y):
        wall = arcade.Sprite(":resources:images/tiles/stoneLEFT.png", TILE_SCALING)
        wall.center_x = coord_x
        wall.center_y = coord_y
        self.wall_list.append(wall)

        wall = arcade.Sprite(":resources:images/tiles/stoneRIGHT.png", TILE_SCALING)
        wall.center_x = coord_x + 64
        wall.center_y = coord_y
        self.wall_list.append(wall)

    def platform_3(self, coord_x, coord_y):
        wall = arcade.Sprite(":resources:images/tiles/stoneLEFT.png", TILE_SCALING)
        wall.center_x = coord_x
        wall.center_y = coord_y
        self.wall_list.append(wall)

        wall = arcade.Sprite(":resources:images/tiles/stoneMID.png", TILE_SCALING)
        wall.center_x = coord_x + 64
        wall.center_y = coord_y
        self.wall_list.append(wall)

        wall = arcade.Sprite(":resources:images/tiles/stoneRIGHT.png", TILE_SCALING)
        wall.center_x = coord_x + 128
        wall.center_y = coord_y
        self.wall_list.append(wall)

    def addScore(self):
        self.main_window = tk.Tk()
        self.main_window.title('Leaderboard')

        # Frames
        self.label_frame = tk.Frame(self.main_window)
        self.apply_frame = tk.Frame(self.main_window)

        # Label
        self.label = tk.Label(self.label_frame, text='Add your name to the leaderboard (3 Character MAX) : ')

        # Entry
        self.entry = tk.Entry(self.label_frame, width=10)

        # Button
        self.apply = tk.Button(self.apply_frame, text='Apply', command=self.addtoLeaderboard)

        # Pack
        self.label.pack(side='left')
        self.entry.pack(side='left')
        self.apply.pack(side='right')

        self.label_frame.pack(side='left')
        self.apply_frame.pack(side='left')

        tk.mainloop()

    def addtoLeaderboard(self):
        name = '   '
        if len(self.entry.get()) == 1:
            name = self.entry.get() + '  '
        elif len(self.entry.get()) == 2:
            name = self.entry.get() + ' '
        elif len(self.entry.get()) == 3:
            name = self.entry.get()
        elif len(self.entry.get()) > 3:
            name = self.entry.get()
            name = name[0:3]

        if name not in self.leaderboard:
            self.leaderboard[name] = float(format(self.time_elapsed, ',.2f'))
            
        else:
            if float(self.leaderboard[name]) > self.time_elapsed:
                self.leaderboard[name] = float(format(self.time_elapsed, ',.2f'))
                
            else:
                msg.showinfo('Failure to Add', 'That name already exists with a higher score.')

        self.pickleScores(self.leaderboard)
        self.main_window.quit()
        self.main_window.destroy()

    def pickleScores(self, leaderboard):
        file = open('leaderboard.txt', 'wb')
        
        pickle.dump(leaderboard, file)

        file.close()
