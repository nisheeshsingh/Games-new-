# Flappy Bird Game - Execution Flow Documentation

## Overview
This is a Flappy Bird clone built with Pygame, featuring multiple game states, customizable bird skins, difficulty levels, themes, and a powerup system with coin collection.

## Program Entry Point

The game starts at the **main while loop** (line 1263):
```python
while True:
    menu_result = show_main_menu()
    current_difficulty = show_difficulty_selector()
    selected_bird_skin_idx = show_bird_selector()
    # ... game initialization
```

This creates the main game cycle that loops indefinitely, allowing players to replay after game over.

---

## Initialization Phase

### 1. **Pygame & Assets Setup** (Lines 1-65)
- Initializes Pygame mixer for audio
- Loads/checks for audio files (`wing.wav`, `hit.wav`)
- Defines constants:
  - Screen dimensions: 1200x800
  - Game physics: gravity, speed, pipe gap
  - Difficulty presets
  - Color themes (Classic, Neon, Cybercity, Hell)
  - Bird skins with power-up boost multipliers

### 2. **Graphics Generation** (Lines 67-244)
Before the main game loop:
- `create_bird_graphics(color)` - Creates animated bird sprite with 4 wing states
- `create_mario_pipe(color)` - Creates 3D Mario-style pipes with metallic effects
- `create_ground_graphics(color)` - Creates textured ground sprite
- `apply_theme(base)` - Generates all graphics based on current theme

---

## Main Menu System

### **show_main_menu()** (Line 715)
Displays navigable menu with options:
1. **PLAY** - Starts game flow
2. **SHOP** - Opens bird skin shop
3. **HOW TO PLAY** - Shows instructions
4. **THEMES** - Theme selector
5. **QUIT** - Exits game

**Navigation:** UP/DOWN arrow keys, SPACE to confirm

---

## Pre-Game Setup Screens

### **show_difficulty_selector()** (Line 835)
Lets player choose difficulty:
- **Easy**: Speed=5, Gravity=0.6, Gap=180
- **Normal**: Speed=8, Gravity=0.9, Gap=150
- **Hard**: Speed=12, Gravity=1.2, Gap=120
- **Extreme**: Speed=16, Gravity=1.6, Gap=100

Difficulty affects:
- How fast pipes scroll (`GAME_SPEED`)
- Bird falling speed (`GRAVITY`)
- Pipe gap size (`PIPE_GAP`)

### **show_bird_selector()** (Line 867)
Player selects from owned bird skins. Each skin has:
- Unique color
- Power-up boost multiplier (1.0-2.0)
- More expensive birds = more frequent powerup spawns

### **show_shop_menu()** (Line 791)
Allows purchasing bird skins with coins earned from gameplay.

### **show_theme_menu()** (Line 756)
Switches between visual themes affecting:
- Background colors and gradients
- Pipe colors
- Bird colors
- Text colors

---

## Main Game Loop

### **Game Initialization** (Lines 1268-1308)

1. **Create game sprites:**
   - `bird_group` - Contains single Bird sprite
   - `ground_group` - Contains 2 scrolling ground sprites
   - `pipe_group` - Contains 6 pipe sprites (3 pairs)

2. **Initialize game state:**
   - `score = 0`
   - `coins_earned_this_run = 0`
   - `scored_pairs = set()` - Tracks which pipes have been scored
   - `pipe_pair_id = 0` - Unique ID for each pipe pair

### **Begin/Ready State** (Lines 1310-1348)

Shows "GET READY!" screen while waiting for player input:
- Listens for SPACE, UP, or mouse click to start
- Allows theme switching with T key
- Bird bounces idly with `bird.begin()` animation

### **Playing State** (Lines 1350-1500)

#### **Input Handling:**
- **SPACE/UP**: Bird flaps (`bird.bump()` sets negative velocity)
- **Mouse Click**: Bird flaps
- **T Key**: Toggle theme (hot-swappable)

#### **Game Updates Each Frame (60 FPS):**

1. **Sprite Updates:**
   ```
   bird_group.update()        # Apply gravity, animate wings
   ground_group.update()      # Scroll ground
   pipe_group.update()        # Scroll pipes
   powerup_group.update()     # Animate powerups, check lifetime
   ```

2. **Screen Wrapping:**
   - If ground sprite exits left edge, remove it and spawn new ground at right
   - If pipe pair exits left edge, remove both pipes and spawn 3 new random pipes

3. **Powerup System:**
   ```
   - Spawns randomly every 200 frames (or less for expensive birds)
   - Two types:
     * IMMUNITY: 5 second immunity to pipe damage
     * DOUBLE_SCORE: 5 second 2x score multiplier
   - Powerups fade away after 10 seconds if not collected
   ```

4. **Collision Detection:**
   - **Pipe Collision**: `pygame.sprite.groupcollide(bird_group, pipe_group)`
     - Ignored if bird has active immunity
   - **Ground Collision**: Bird touches ground/ceiling
   - **Ceiling Collision**: `bird.rect.top <= 0`
   - Any collision triggers game over

5. **Scoring:**
   - When bird passes pipe pair (pipe.rect.right < bird.rect.left):
     - Add pair ID to `scored_pairs` to prevent double-scoring
     - Award `score += bird.score_multiplier` (1 or 2 points)
     - Create floating score animation
     - Play wing sound effect

#### **Rendering Each Frame:**
```
1. Draw background
2. Draw all sprites (bird, pipes, ground)
3. Draw powerups with rotation animation
4. Draw floating score animations
5. Draw HUD (score, coins, powerup timers)
6. Update display
```

---

## Game Over & Menu Resolution

### **show_game_over_menu()** (Line 945)

Displays:
- Final score
- High score
- Coins earned this run
- Total coins accumulated

**Options:**
1. **PLAY AGAIN** - Continue game loop (back to difficulty selector)
2. **MAIN MENU** - Exit game loop, return to main menu

---

## Game State Diagram

```
Main Menu
    ↓
[PLAY selected]
    ↓
Difficulty Selector
    ↓
Bird Selector
    ↓
Game Ready Screen (press SPACE)
    ↓
PLAYING
    ├─ Input: SPACE/Click to flap
    ├─ Updates: Physics, spawns, collisions
    ├─ Scoring: PassPipes = +1 point
    ├─ Powerups: Immunity or 2x Score
    └─ Collision: Game Over → Show Game Over Menu
         ├─ Play Again → Back to Difficulty Selector
         └─ Main Menu → Back to Main Menu
```

---

## Key Game Mechanics

### **Physics (Bird)**
- Gravity accelerates downward each frame: `self.speed += GRAVITY`
- Bird position: `self.rect[1] += self.speed`
- When flapping: `self.speed = -SPEED` (instant upward velocity)
- Bird rotates based on velocity for animation

### **Pipe Generation**
- Random height between 100-300 pixels
- Creates pipe pair with gap (`PIPE_GAP`) between top/bottom
- Spawns new pair every 500 pixels scrolled
- Uses `pair_id` to prevent double-scoring

### **Coin System**
- Coins earned = final score (1 coin per pipe passed)
- Accumulate in `total_coins` persistent variable
- Used to buy bird skins in shop

### **Powerup Mechanics**
- **Immunity**: Duration 5s, passes through pipes without damage
- **Double Score**: Duration 5s, multiply score earnings by 2
- Spawn frequency based on bird skin:
  - Formula: `powerup_spawn_rate = int(200 / powerup_boost)`
  - Expensive birds (2.0 boost) spawn powerups every ~100 frames
  - Cheap birds (1.0 boost) spawn every ~200 frames

### **Theme System**
- 8 colors per theme: bg, pipe, bird, ground, text, accent, shadow, dark
- Affects all visual elements
- Can toggle with T key mid-game
- Automatically regenerates all graphics

---

## Frame-by-Frame Execution Example

**Frame at 60 FPS = ~16.67ms per frame:**

1. **Input Phase** (← 0ms)
   - Check for SPACE, clicks, T key
   
2. **Update Phase** (← ~5ms)
   - Apply gravity to bird
   - Update bird position
   - Scroll pipes/ground
   - Check collisions
   - Update powerup timers
   
3. **Spawn Phase** (← ~8ms)
   - Check if pipe pair off-screen → spawn new
   - Check if ground off-screen → spawn new
   - Check if powerup should spawn
   
4. **Render Phase** (← ~15ms)
   - Clear screen, draw background
   - Draw all sprites
   - Draw HUD, text, animations
   - Update display
   
5. **Frame Cap** (← ~16.67ms)
   - `clock.tick(60)` - Wait remainder of frame

---

## Asset Usage

### **Audio Files** (Optional)
- `assets/audio/wing.wav` - Flap sound
- `assets/audio/hit.wav` - Collision sound
- Game continues if files missing (no exceptions)

### **Generated Assets** (Procedural)
- Bird sprites: 4 animation frames, customizable color
- Pipes: Metallic 3D effect with bands and bolts
- Ground: Textured with grass tufts
- Powerups: Heart (immunity) and Star (2x score)
- Background: Gradient effect based on theme

---

## Exit Conditions

Game exits when:
1. Player closes window (QUIT event)
2. Player selects QUIT from main menu
3. Pygame.quit() is called

All collected coins persist until program restart.
