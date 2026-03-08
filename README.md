# Flappy Bird Game

A feature-rich Flappy Bird clone built with Pygame, featuring multiple difficulty levels, customizable bird skins, dynamic themes, powerups, and a coin-based economy system.

## Table of Contents
- [Features](#features)
- [How to Play](#how-to-play)
- [Controls](#controls)
- [Game Mechanics](#game-mechanics)
- [Difficulty Levels](#difficulty-levels)
- [Customization](#customization)
- [Installation](#installation)
- [Running the Game](#running-the-game)

---

## Features

### 🎮 Core Gameplay
- Classic Flappy Bird mechanics with gravity-based physics
- Procedurally generated pipe obstacles
- Smooth 60 FPS gameplay
- Sound effects for flapping and collisions

### 🎯 Multiple Difficulty Levels
- **Easy**: Slower speed, gentle gravity, larger gaps
- **Normal**: Balanced difficulty
- **Hard**: Fast pipes, stronger gravity, tight gaps
- **Extreme**: Ultimate challenge for skilled players

### 🎨 Theme System
- **Classic**: Traditional sky-blue aesthetic
- **Neon**: Dark background with vibrant colors
- **Cybercity**: Green text, dark futuristic look
- **Hell**: Dark red and orange theme
- Hot-swap themes with T key during gameplay

### 🦅 Bird Customization
- 8 unique bird skins with different colors
- Each skin has a power-up boost multiplier (more expensive = stronger boosts)
- Shop system to purchase skins with earned coins

### ⚡ Powerup System
- **Immunity Shield**: 5-second protection against pipe collisions
- **2x Score Multiplier**: Double points earned for 5 seconds
- Powerups spawn randomly throughout gameplay
- More expensive bird skins spawn powerups more frequently

### 💰 Coin Economy
- Earn 1 coin per pipe successfully passed
- Accumulate coins across multiple games
- Spend coins in the shop to unlock bird skins
- Persistent save across sessions

### 🎬 Enhanced UI
- Glowing buttons and boxes with shadow effects
- Floating score animations
- Real-time powerup timers
- Coin display in HUD
- Smooth text rendering with multi-layer shadows

---

## How to Play

1. **Start Game**: Select "PLAY" from the main menu
2. **Choose Difficulty**: Select your preferred difficulty level
3. **Select Bird**: Choose from your owned bird skins
4. **Ready Screen**: Press SPACE to begin when you see "GET READY!"
5. **Navigate**: Flap to avoid pipes and collect powerups
6. **Score Points**: Pass through each pipe gap successfully (+1 point, +1 coin)
7. **Game Over**: Collision with pipes, ground, or ceiling ends the game
8. **Earn Rewards**: Coins earned this run are added to your total

### Game Over Flow
After each game, view your results:
- **Score**: Points earned this run
- **High Score**: Your best score ever
- **Coins Earned**: Coins from this game
- **Total Coins**: Total accumulated coins
- Choose to **Play Again** or return to **Main Menu**

---

## Controls

| Control | Action |
|---------|--------|
| **SPACE** | Flap / Menu Selection / Confirm |
| **UP ARROW** | Flap / Menu Navigation |
| **DOWN ARROW** | Menu Navigation |
| **MOUSE CLICK** | Flap / Start Game / Menu Selection |
| **T** | Toggle Themes (mid-game only) |
| **ESC** | Back to Menu (in shop/themes) |

### Menu Navigation
- Use **UP/DOWN arrow keys** to select options
- Press **SPACE** or **CLICK** to confirm selection

---

## Game Mechanics

### Physics System
- **Gravity**: Constant downward acceleration each frame
- **Flapping**: Instant upward velocity when jumping
- **Air Resistance**: None (arcade-style physics)
- **Bird Rotation**: Bird tilts based on falling/rising speed

### Scoring
- **+1 Point** for each pipe pair successfully passed
- **With 2x Multiplier**: +2 Points per pipe (during powerup active)
- Score displayed in top-left corner

### Collision Detection
- **Pixel-perfect**: Using pygame masks for accurate collisions
- **Pipe Collision**: End game (unless immune)
- **Ground Collision**: End game
- **Ceiling Collision**: End game
- **Powerup Collision**: Automatic pickup when touched

### Powerup Duration
- Each powerup lasts exactly **5 seconds**
- Timers displayed in top-right corner
- Multiple powerups can stack (immunity + 2x score)
- Immunity only protects against **pipes**, not ground or ceiling

---

## Difficulty Levels

| Difficulty | Speed | Gravity | Pipe Gap | Notes |
|-----------|-------|---------|----------|-------|
| Easy | 5 | 0.6 | 180px | Perfect for beginners |
| Normal | 8 | 0.9 | 150px | Balanced challenge |
| Hard | 12 | 1.2 | 120px | Expert players |
| Extreme | 16 | 1.6 | 100px | Hardcore mode |

**What Each Stat Does:**
- **Speed**: How fast pipes scroll left (pixels/frame)
- **Gravity**: Downward acceleration (pixels/frame²)
- **Pipe Gap**: Space between top/bottom pipes

---

## Customization

### Themes
Access from Main Menu → THEMES

Each theme includes:
- Unique background gradient
- Custom pipe color
- Distinct bird appearance
- Theme-appropriate text colors

**Can also toggle in-game** with T key (pipes and graphics regenerate instantly)

### Bird Skins

| Skin | Cost | Boost | Powerup Spawn Rate |
|------|------|-------|-------------------|
| Classic Gold | Free | 1.0x | Every 200 frames |
| Royal Blue | 150 | 1.3x | Every 154 frames |
| Crimson Red | 200 | 1.5x | Every 133 frames |
| Emerald Green | 250 | 1.8x | Every 111 frames |
| Electric Purple | 300 | 2.0x | Every 100 frames |
| Sunset Orange | 200 | 1.5x | Every 133 frames |
| Aqua Cyan | 250 | 1.8x | Every 111 frames |
| Rose Pink | 300 | 2.0x | Every 100 frames |

**How Skin Boost Works:**
- Higher boost = More frequent powerup spawns
- More expensive birds are stronger (more powerups)
- Boost multiplier affects score earnings with 2x powerup

---

## Installation

### Requirements
- Python 3.7+
- Pygame library

### Setup

1. **Clone or download** this repository

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Game

### Start the Game
```bash
python flappy.py
```

### Game Saves
- Coins persist during gameplay session
- High score resets on program restart (can be modified to save to file)
- Bird skin ownership saved in `owned_bird_skins` variable

---

## Audio

The game includes optional sound effects:
- `assets/audio/wing.wav` - Flap sound
- `assets/audio/hit.wav` - Collision sound

If audio files are missing, the game runs silently (no errors).

---

## Project Structure

```
flappy/
├── flappy.py              # Main game file
├── README.md              # This file
├── EXECUTION_FLOW.md      # Detailed code documentation
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata
└── assets/
    └── audio/
        ├── wing.wav
        └── hit.wav
```

---

## Tips & Tricks

### Scoring Tips
- **Use Powerups**: Activate 2x Score powerup before passing pipes
- **Stack Boosts**: Combine bird skin boost with 2x Score for maximum points
- **Passive Generation**: Expensive birds auto-spawn more powerups
- **Immunity First**: Use immunity to reach safe zones, then collect 2x Score

### Strategy
- **Easy Mode**: Get comfortable with controls and spacing
- **Normal Mode**: Master the rhythm of flapping
- **Hard Mode**: Light taps, precise timing required
- **Extreme Mode**: Pre-emptive flapping, never react (too late)

### Bird Selection
- **Beginners**: Classic Gold (free) or Royal Blue
- **Experienced**: Crimson Red or Sunset Orange
- **Experts**: Electric Purple or Rose Pink (maximum powerup spawns)

---

## Game Over Conditions

The game ends immediately when:
1. ❌ Bird collides with any pipe (unless immunity active)
2. ❌ Bird touches the ground
3. ❌ Bird touches the ceiling

**No second chances** - Game over is instant!

---

## Known Features

- ✅ Procedurally generated pipe heights
- ✅ Smooth pixel-perfect collision detection
- ✅ Floating score animations
- ✅ Rotating powerup visual effects
- ✅ Glowing UI elements with shadows
- ✅ Theme hot-swapping mid-game
- ✅ Persistent coin accumulation
- ✅ Bird skin system with power scaling

---

## Future Enhancement Ideas

- Save high scores and coins to file
- Leaderboard system
- More bird skins and themes
- Achievement system
- Background music
- Particle effects for collisions
- Combo multiplier system
- Seasonal themes

---

## Credits

Built with **Pygame** - Python game development library

Inspired by the classic **Flappy Bird** game mechanics 