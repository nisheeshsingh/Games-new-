import pygame, random, time, os, sys
from pygame.locals import *

# Try to import numpy for better audio quality, fallback if unavailable
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ---------- constants ----------
SCREEN_WIDHT = 1200
SCREEN_HEIGHT = 800
SPEED = 10
GRAVITY = 2.5
GAME_SPEED = 15

GROUND_WIDHT = 2 * SCREEN_WIDHT
GROUND_HEIGHT = 100

PIPE_WIDHT = 80
PIPE_HEIGHT = 500

PIPE_GAP = 150
PIPE_SPACING = 400  # Constant spacing between pipe pairs

# difficulty settings: (name, game_speed, gravity, pipe_gap)
DIFFICULTIES = [
    ("Easy", 5, 0.6, 180),
    ("Normal", 8, 0.9, 150),
    ("Hard", 12, 1.2, 120),
    ("Extreme", 16, 1.6, 100),
]
current_difficulty = 1

wing = 'assets/audio/wing.wav'
hit = 'assets/audio/hit.wav'
boop = 'assets/audio/boop.wav'
victory = 'assets/audio/victory.wav'

if not os.path.exists(wing):
    wing = None
if not os.path.exists(hit):
    hit = None
if not os.path.exists(boop):
    boop = None
if not os.path.exists(victory):
    victory = None

def generate_beep(frequency=1000, duration=100, volume=0.3):
    """Generate a beep sound using sine wave with better audio quality"""
    try:
        if not HAS_NUMPY:
            return None
        
        sample_rate = 44100
        frames = int(duration * sample_rate / 1000)
        t = np.linspace(0, duration/1000, frames)
        
        # Create sine wave with fade in/out to avoid clicks
        fade_frames = max(1, int(frames * 0.1))
        wave = np.sin(2.0 * np.pi * frequency * t)
        
        # Apply fade in and fade out
        fade_in = np.linspace(0, 1, fade_frames)
        fade_out = np.linspace(1, 0, fade_frames)
        wave[:fade_frames] *= fade_in
        wave[-fade_frames:] *= fade_out
        
        # Convert to audio format
        wave = (wave * 32767 * volume).astype(np.int16)
        sound = pygame.sndarray.make_sound(wave)
        return sound
    except Exception:
        return None

def play_beep(frequency=1000, duration=100):
    """Play a beep sound with proper volume"""
    try:
        if not HAS_NUMPY:
            return
        sound = generate_beep(frequency, duration, 0.5)  # Slightly louder
        if sound:
            # Create a channel to ensure it plays
            channel = pygame.mixer.find_channel()
            if channel:
                channel.play(sound)
    except Exception:
        pass

def play(sound):
    if sound:
        try:
            pygame.mixer.music.load(sound)
            pygame.mixer.music.play()
        except pygame.error:
            pass

THEMES = [
    {"name": "classic",   "bg": (135, 206, 250), "pipe": (34, 139, 34), "bird": (255, 200, 0), "ground": (139, 69, 19), "text": (255, 255, 255), "accent": (255, 255, 255), "shadow": (50, 50, 50), "dark": (50, 50, 50)},
    {"name": "neon",      "bg": (0, 0, 0),       "pipe": (255, 20, 147), "bird": (0, 255, 255), "ground": (255, 69, 0), "text": (0, 255, 255), "accent": (255, 255, 0), "shadow": (100, 100, 100), "dark": (20, 20, 30)},
    {"name": "cybercity", "bg": (10, 10, 50),    "pipe": (0, 255, 0),    "bird": (255, 0, 255), "ground": (50, 50, 50), "text": (100, 255, 100), "accent": (255, 100, 255), "shadow": (100, 100, 100), "dark": (20, 20, 50)},
    {"name": "hell",      "bg": (100, 0, 0),      "pipe": (139, 0, 0),    "bird": (255, 69, 0),   "ground": (80, 0, 0), "text": (255, 255, 100), "accent": (255, 100, 0), "shadow": (100, 100, 100), "dark": (60, 20, 0)},
    {"name": "forest",    "bg": (51, 102, 51),    "pipe": (139, 35, 35),  "bird": (255, 215, 0),  "ground": (34, 85, 34),  "text": (255, 255, 200), "accent": (144, 238, 144), "shadow": (100, 100, 100), "dark": (25, 60, 25)},
    {"name": "ocean",     "bg": (0, 105, 148),    "pipe": (70, 130, 180), "bird": (255, 255, 0),  "ground": (188, 143, 143), "text": (255, 255, 255), "accent": (64, 224, 208), "shadow": (100, 100, 100), "dark": (0, 71, 107)},
    {"name": "sunset",    "bg": (255, 140, 60),   "pipe": (180, 82, 45),  "bird": (255, 20, 147), "ground": (139, 69, 19),  "text": (255, 250, 205), "accent": (255, 215, 0),  "shadow": (100, 100, 100),  "dark": (160, 82, 45)},
    {"name": "midnight",  "bg": (20, 24, 82),     "pipe": (100, 100, 150), "bird": (0, 255, 255), "ground": (40, 40, 60),  "text": (173, 216, 230), "accent": (138, 43, 226), "shadow": (100, 100, 100), "dark": (30, 30, 80)},
]
current_theme = 0

# Bird skins - (name, color, cost, powerup_boost, is_premium, is_legendary)
BIRD_SKINS = [
    ("Classic Gold", (255, 200, 0), 0, 1.0, False, False),        # Free, available by default
    ("Royal Blue", (25, 100, 200), 150, 1.3, False, False),
    ("Crimson Red", (220, 20, 60), 200, 1.5, False, False),
    ("Emerald Green", (50, 205, 50), 250, 1.8, False, False),
    ("Electric Purple", (138, 43, 226), 300, 2.0, False, False),
    ("Sunset Orange", (255, 140, 0), 200, 1.5, False, False),
    ("Aqua Cyan", (0, 255, 255), 250, 1.8, False, False),
    ("Rose Pink", (255, 105, 180), 300, 2.0, False, False),
    # Premium Skins (themed after game themes)
    ("Forest Guardian", (144, 238, 144), 500, 2.5, True, False),
    ("Ocean Blue", (64, 224, 208), 500, 2.5, True, False),
    ("Sunset Blaze", (255, 165, 0), 600, 2.8, True, False),
    ("Midnight Mystic", (186, 85, 211), 600, 2.8, True, False),
    ("Neon Cyber", (0, 255, 255), 700, 3.0, True, False),
    ("Hellfire Dragon", (255, 69, 0), 800, 3.2, True, False),
    # Legendary Skin
    ("Rainbow Legend", None, 1500, 5.0, True, True),  # None color - will be rainbow
]

owned_bird_skins = {0}  # Player starts with Classic Gold
total_coins = 0
coins_earned_this_run = 0

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

pipe_pair_id = 0


def create_bird_graphics(color):
    """Create a realistic bird sprite with wings and details"""
    images = []
    
    for wing_state in range(4):
        bird_surf = pygame.Surface((80, 70), pygame.SRCALPHA)
        bird_surf.fill((0, 0, 0, 0))
        
        # For rainbow skin, use different colors for body parts
        if color is None:  # Rainbow skin
            colors = [
                (255, 0, 0),      # Red
                (255, 127, 0),    # Orange
                (255, 255, 0),    # Yellow
                (0, 255, 0),      # Green
                (0, 0, 255),      # Blue
                (75, 0, 130),     # Indigo
                (148, 0, 211),    # Violet
            ]
            body_color = colors[wing_state % len(colors)]
            head_color = colors[(wing_state + 1) % len(colors)]
        else:
            body_color = color
            head_color = color
        
        # Deep shadow
        pygame.draw.ellipse(bird_surf, (0, 0, 0, 80), (12, 36, 36, 10))
        
        # Body - main colored circle with gradient effect
        pygame.draw.ellipse(bird_surf, body_color, (10, 12, 28, 22))
        pygame.draw.ellipse(bird_surf, tuple(min(255, c + 40) for c in body_color), (12, 14, 24, 18))
        
        # Head - larger and better proportioned
        pygame.draw.circle(bird_surf, head_color, (36, 16), 11)
        pygame.draw.circle(bird_surf, tuple(min(255, c + 40) for c in head_color), (36, 16), 9)
        
        # Eyes - more expressive
        pygame.draw.circle(bird_surf, (255, 255, 255), (39, 13), 5)
        pygame.draw.circle(bird_surf, (240, 240, 255), (39, 13), 3)
        pygame.draw.circle(bird_surf, (0, 0, 0), (40, 12), 3)
        pygame.draw.circle(bird_surf, (100, 100, 100), (40, 12), 1)
        
        # Beak - more prominent
        beak_color = (255, 170, 0)
        pygame.draw.polygon(bird_surf, beak_color, [(46, 16), (56, 14), (46, 20)])
        pygame.draw.polygon(bird_surf, (200, 100, 0), [(46, 16), (56, 14), (46, 20)], 2)
        
        # Wing animation - smooth flapping
        wing_offset = int(6 * (wing_state - 1.5))
        wing_color = colors[(wing_state + 2) % len(colors)] if color is None else (240, 160, 0)
        wing_points = [
            (18, 16 + wing_offset),
            (32, 8 + wing_offset),
            (34, 14 + wing_offset),
            (19, 20 + wing_offset)
        ]
        
        pygame.draw.polygon(bird_surf, wing_color, wing_points)
        pygame.draw.polygon(bird_surf, (160, 90, 0), wing_points, 2)
        
        # Tail feathers - two layers for depth
        tail_color = colors[(wing_state + 3) % len(colors)] if color is None else (220, 140, 0)
        pygame.draw.polygon(bird_surf, tail_color, [(10, 14), (-2, 6), (2, 12)])
        pygame.draw.polygon(bird_surf, (200, 120, 0), [(10, 18), (-2, 22), (2, 20)])
        
        # Body shading for 3D effect
        pygame.draw.circle(bird_surf, (0, 0, 0, 50), (22, 28), 10)
        
        images.append(bird_surf)
    
    return images


def create_mario_pipe(color):
    """Create a Mario-style pipe with metallic 3D effect"""
    pipe_surf = pygame.Surface((PIPE_WIDHT, PIPE_HEIGHT), pygame.SRCALPHA)
    
    # Main pipe body
    pipe_body_color = tuple(max(0, c - 60) for c in color)
    pygame.draw.rect(pipe_surf, pipe_body_color, (0, 0, PIPE_WIDHT, PIPE_HEIGHT))
    
    # Strong highlight edge (left/top) - 3D beveled effect
    light_color = tuple(min(255, c + 120) for c in color)
    pygame.draw.line(pipe_surf, light_color, (1, 4), (1, PIPE_HEIGHT - 4), 5)
    pygame.draw.line(pipe_surf, light_color, (4, 0), (PIPE_WIDHT - 4, 0), 4)
    
    # Strong shadow edge (right/bottom) - 3D beveled effect
    shadow_color = (0, 0, 0)
    pygame.draw.line(pipe_surf, shadow_color, (PIPE_WIDHT - 1, 4), (PIPE_WIDHT - 1, PIPE_HEIGHT - 4), 5)
    pygame.draw.line(pipe_surf, shadow_color, (4, PIPE_HEIGHT - 1), (PIPE_WIDHT - 4, PIPE_HEIGHT - 1), 4)
    
    # Metal bands/rings with enhanced 3D metallic look
    band_color = (110, 110, 110)
    for y in range(12, PIPE_HEIGHT, 38):
        # Main band shadow
        pygame.draw.line(pipe_surf, (60, 60, 60), (1, y), (PIPE_WIDHT - 1, y), 8)
        # Main band highlight
        pygame.draw.line(pipe_surf, (180, 180, 180), (1, y - 1), (PIPE_WIDHT - 1, y - 1), 5)
        # Mid-tone band
        pygame.draw.line(pipe_surf, band_color, (1, y + 2), (PIPE_WIDHT - 1, y + 2), 3)
    
    # Bolts - with metallic shading
    for y in range(12, PIPE_HEIGHT, 38):
        # Left bolt
        pygame.draw.circle(pipe_surf, (80, 80, 80), (7, y), 4)
        pygame.draw.circle(pipe_surf, (160, 160, 160), (5, y - 1), 2)
        pygame.draw.line(pipe_surf, (50, 50, 50), (6, y), (8, y), 1)
        # Right bolt
        pygame.draw.circle(pipe_surf, (80, 80, 80), (PIPE_WIDHT - 7, y), 4)
        pygame.draw.circle(pipe_surf, (160, 160, 160), (PIPE_WIDHT - 5, y - 1), 2)
        pygame.draw.line(pipe_surf, (50, 50, 50), (PIPE_WIDHT - 8, y), (PIPE_WIDHT - 6, y), 1)
    
    return pipe_surf


def create_ground_graphics(color):
    """Create a textured ground/platform"""
    ground_surf = pygame.Surface((GROUND_WIDHT, GROUND_HEIGHT), pygame.SRCALPHA)
    
    # Main ground color
    pygame.draw.rect(ground_surf, color, (0, 0, GROUND_WIDHT, GROUND_HEIGHT))
    
    # Add dirt texture blocks
    dirt_dark = tuple(max(0, c - 40) for c in color)
    for x in range(0, GROUND_WIDHT, 40):
        for y in range(0, GROUND_HEIGHT, 40):
            if (x // 40 + y // 40) % 2 == 0:
                pygame.draw.rect(ground_surf, dirt_dark, (x, y, 40, 40))
    
    # Top edge highlight
    light_color = tuple(min(255, c + 60) for c in color)
    pygame.draw.line(ground_surf, light_color, (0, 2), (GROUND_WIDHT, 2), 3)
    
    # Add grass tufts on top
    grass_color = tuple(min(255, c + 80) for c in color)
    for x in range(0, GROUND_WIDHT, 15):
        pygame.draw.line(ground_surf, grass_color, (x, 0), (x + 5, -5), 2)
    
    return ground_surf


class Powerup(pygame.sprite.Sprite):
    """Represents a powerup item in the game"""
    
    IMMUNITY = 0
    DOUBLE_SCORE = 1
    
    def __init__(self, x, y, powerup_type, color):
        pygame.sprite.Sprite.__init__(self)
        self.powerup_type = powerup_type
        self.color = color
        self.x = x
        self.y = y
        self.lifetime = 10.0  # seconds before disappearing
        self.elapsed = 0.0
        self.pulse_time = 0.0
        
        # Create powerup sprite
        self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.mask = pygame.mask.from_surface(self.image)
        
        self.draw_powerup()
    
    def draw_powerup(self):
        """Draw powerup icon"""
        if self.powerup_type == self.IMMUNITY:
            # Draw a heart for immunity
            self._draw_heart()
        else:  # DOUBLE_SCORE
            # Draw a star for double score
            self._draw_star()
    
    def _draw_heart(self):
        """Draw a heart shape with glow"""
        self.image.fill((0, 0, 0, 0))  # Clear with transparency
        # Heart shape
        pygame.draw.circle(self.image, (255, 50, 50), (15, 12), 8)
        pygame.draw.circle(self.image, (255, 50, 50), (35, 12), 8)
        pygame.draw.polygon(self.image, (255, 50, 50), [(5, 15), (45, 15), (25, 40)])
        
        # Inner highlight
        pygame.draw.circle(self.image, (255, 150, 150), (15, 12), 5)
        pygame.draw.circle(self.image, (255, 150, 150), (35, 12), 5)
        
        # Glow effect
        pygame.draw.circle(self.image, (255, 100, 100), (15, 12), 10, 2)
        pygame.draw.circle(self.image, (255, 100, 100), (35, 12), 10, 2)
    
    def _draw_star(self):
        """Draw a star shape with glow"""
        self.image.fill((0, 0, 0, 0))  # Clear with transparency
        points = []
        for i in range(10):
            angle = i * 3.14159 / 5
            if i % 2 == 0:
                r = 18
            else:
                r = 9
            x = 25 + r * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).x
            y = 25 + r * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).y
            points.append((x, y))
        
        pygame.draw.polygon(self.image, (255, 240, 0), points)
        pygame.draw.polygon(self.image, (255, 255, 100), points, 2)
        
        # Add inner star for more depth
        inner_points = []
        for i in range(10):
            angle = i * 3.14159 / 5
            if i % 2 == 0:
                r = 12
            else:
                r = 6
            x = 25 + r * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).x
            y = 25 + r * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).y
            inner_points.append((x, y))
        pygame.draw.polygon(self.image, (255, 255, 150), inner_points)
    
    def update(self, delta_time):
        """Update powerup, return True if still alive"""
        self.elapsed += delta_time
        self.pulse_time += delta_time
        # Scroll powerup with game world
        self.rect[0] -= GAME_SPEED
        # More dramatic floating animation
        float_offset = 8 * pygame.math.Vector2(1, 0).rotate(self.pulse_time * 180).y
        self.rect.y = self.y + float_offset
        return self.elapsed < self.lifetime
    
    def draw(self, screen):
        """Draw powerup with rotating effect and pulsing glow - no artifacts"""
        angle = (self.elapsed * 120) % 360
        scale = 1.0 + 0.15 * pygame.math.Vector2(1, 0).rotate(self.pulse_time * 180).y
        
        # Create fresh large surface for this frame to avoid rotation artifacts
        temp_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        temp_surf.fill((0, 0, 0, 0))
        
        # Draw the shape fresh on temporary surface
        if self.powerup_type == self.IMMUNITY:
            # Draw heart
            pygame.draw.circle(temp_surf, (255, 50, 50), (25, 25), 10)
            pygame.draw.circle(temp_surf, (255, 50, 50), (55, 25), 10)
            pygame.draw.polygon(temp_surf, (255, 50, 50), [(15, 30), (65, 30), (40, 60)])
            pygame.draw.circle(temp_surf, (255, 150, 150), (25, 25), 6)
            pygame.draw.circle(temp_surf, (255, 150, 150), (55, 25), 6)
        else:
            # Draw star - fresh calculation each frame
            points = []
            for i in range(10):
                angle_rad = i * 3.14159 / 5
                if i % 2 == 0:
                    r = 20
                else:
                    r = 10
                x = 40 + r * pygame.math.Vector2(1, 0).rotate(angle_rad * 180 / 3.14159).x
                y = 40 + r * pygame.math.Vector2(1, 0).rotate(angle_rad * 180 / 3.14159).y
                points.append((x, y))
            pygame.draw.polygon(temp_surf, (255, 240, 0), points)
            pygame.draw.polygon(temp_surf, (255, 255, 100), points, 2)
        
        # Rotate and scale the fresh surface
        rotated = pygame.transform.rotate(temp_surf, angle)
        if scale != 1.0:
            rotated = pygame.transform.scale(rotated, (int(rotated.get_width() * scale), int(rotated.get_height() * scale)))
        
        rotated_rect = rotated.get_rect(center=self.rect.center)
        screen.blit(rotated, rotated_rect)


class FloatingScore:
    """Represents a floating score animation that appears when player scores"""
    def __init__(self, x, y, score, color, accent_color):
        self.x = x
        self.y = y
        self.score = score
        self.color = color
        self.accent_color = accent_color
        self.lifetime = 1.0  # seconds
        self.elapsed = 0.0
        self.font = pygame.font.Font(None, 48)
    
    def update(self, delta_time):
        """Update floating score position and lifetime"""
        self.elapsed += delta_time
        self.y -= 50 * delta_time  # Float upward
        return self.elapsed < self.lifetime
    
    def draw(self, screen):
        """Draw the floating score with fade effect"""
        progress = min(1.0, self.elapsed / self.lifetime)
        alpha = int(255 * (1 - progress))
        
        text = f"+{int(self.score)}"
        text_surf = self.font.render(text, True, self.accent_color)
        
        # Add glow effect with alpha
        glow_surf = pygame.Surface((text_surf.get_width() + 20, text_surf.get_height() + 20), pygame.SRCALPHA)
        for i in range(3, 0, -1):
            glow_alpha = int(alpha * (1 - i/3.0) * 0.3)
            temp_surf = self.font.render(text, True, (*self.color, glow_alpha))
            glow_surf.blit(temp_surf, (10 + i//2 - (i%2)*i//2, 10 + i//2))
        
        glow_surf.blit(text_surf, (10, 10))
        glow_surf.set_alpha(alpha)
        screen.blit(glow_surf, (int(self.x - glow_surf.get_width()//2), int(self.y - glow_surf.get_height()//2)))


class Bird(pygame.sprite.Sprite):

    def __init__(self, images):
        pygame.sprite.Sprite.__init__(self)
        self.images = images
        self.speed = SPEED
        self.current_image = 0
        self.image = self.images[0]
        self.rotated_image = self.image  # Initialize rotated image
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2
        self.center_pos = (self.rect.centerx, self.rect.centery)
        
        # Powerup tracking
        self.immunity_time = 0.0
        self.double_score_time = 0.0
        self.score_multiplier = 1.0

    def update(self):
        self.current_image = (self.current_image + 1) % 4
        base_image = self.images[self.current_image]
        self.speed += GRAVITY
        self.center_pos = (self.center_pos[0], self.center_pos[1] + self.speed)
        
        angle = min(max(-self.speed * 2, -25), 90)
        self.rotated_image = pygame.transform.rotate(base_image, angle)
        # Update rect for collision detection
        self.rect = self.rotated_image.get_rect(center=self.center_pos)
        self.mask = pygame.mask.from_surface(self.rotated_image)
        # Keep a copy of unrotated image for sprite group
        self.image = base_image

    def bump(self):
        self.speed = -SPEED
        # Also update center position to current rect center
        self.center_pos = (self.rect.centerx, self.rect.centery)

    def begin(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]


class Pipe(pygame.sprite.Sprite):

    def __init__(self, inverted, xpos, ysize, image, pair_id):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.pair_id = pair_id
        self.scored = False
        self.rect = self.image.get_rect()
        self.rect[0] = xpos

        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = - (self.rect[3] - ysize)
        else:
            self.rect[1] = SCREEN_HEIGHT - ysize

        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect[0] -= GAME_SPEED


class Ground(pygame.sprite.Sprite):
    
    def __init__(self, xpos, image):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT
    
    def update(self):
        self.rect[0] -= GAME_SPEED


def is_off_screen(sprite):
    return sprite.rect[0] < -(sprite.rect[2])


def get_random_pipes(xpos, pair_id):
    size = random.randint(100, 280)
    pipe = Pipe(False, xpos, size, pipe_img, pair_id)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP, pipe_img, pair_id)
    return pipe, pipe_inverted


pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))
pygame.display.set_caption('Flappy Bird')


def tint(surface, color):
    surf = surface.copy()
    surf.fill(color, special_flags=pygame.BLEND_MULT)
    return surf


def load_base_images():
    base = {}
    # Use generated graphics
    base['bird_color'] = (255, 200, 0)
    base['pipe_color'] = (34, 139, 34)
    base['ground_color'] = (139, 69, 19)
    return base


def apply_theme(base):
    global BACKGROUND, BEGIN_IMAGE, pipe_img, ground_img
    theme = THEMES[current_theme]
    
    # Create gradient background with smoother transitions
    BACKGROUND = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        # Create a smoother gradient
        progress = y / SCREEN_HEIGHT
        color = tuple(int(theme['bg'][i] * (1 - progress * 0.4)) for i in range(3))
        pygame.draw.line(BACKGROUND, color, (0, y), (SCREEN_WIDHT, y))
    
    # Add subtle cloud-like patterns for depth
    cloud_surf = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT), pygame.SRCALPHA)
    for i in range(3):
        cloud_y = SCREEN_HEIGHT * (0.2 + i * 0.2)
        cloud_x = SCREEN_WIDHT * 0.1
        cloud_color = tuple(int(c * 0.1) for c in theme['accent'])
        pygame.draw.circle(cloud_surf, (*cloud_color, 30), (int(cloud_x), int(cloud_y)), 60)
        pygame.draw.circle(cloud_surf, (*cloud_color, 30), (int(cloud_x + 80), int(cloud_y)), 50)
        pygame.draw.circle(cloud_surf, (*cloud_color, 20), (int(cloud_x + 160), int(cloud_y)), 40)
    
    BACKGROUND.blit(cloud_surf, (0, 0))
    
    # Create start screen
    BEGIN_IMAGE = pygame.Surface((200, 100), pygame.SRCALPHA)
    
    # Generate bird and pipe graphics
    bird_imgs = create_bird_graphics(theme['bird'])
    pipe_img = create_mario_pipe(theme['pipe'])
    ground_img = create_ground_graphics(theme['ground'])
    
    return bird_imgs, pipe_img, ground_img, theme['text'], theme['accent'], theme['shadow'], theme['dark']


def draw_text_with_shadow(text, size, color, shadow_color, x, y, offset=3):
    """Draw text with multi-layer shadow and glow with contrasting background"""
    font = pygame.font.Font(None, size)
    text_width, text_height = font.size(text)
    
    # Draw semi-transparent background for text readability
    bg_surf = pygame.Surface((text_width + 10, text_height + 6), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 180))  # Dark background for contrast
    screen.blit(bg_surf, (x - 5, y - 3))
    
    # Multiple shadow layers for depth
    for i in range(offset, 0, -1):
        alpha_shadow = int(120 * (i / offset))
        shadow_surf = pygame.Surface((text_width + offset * 2, text_height + offset * 2), pygame.SRCALPHA)
        temp_text = font.render(text, True, shadow_color)
        shadow_surf.blit(temp_text, (offset, offset))
        shadow_surf.set_alpha(alpha_shadow)
        screen.blit(shadow_surf, (x - offset + i, y - offset + i))
    text_surf = font.render(text, True, color)
    screen.blit(text_surf, (x, y))


def draw_glowing_box(x, y, width, height, color, glow_color, border_width=3):
    """Draw a box with glowing border, shadow, and gradient effect"""
    # Drop shadow with better depth
    shadow_surface = pygame.Surface((width + 14, height + 14), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (0, 0, 0, 180), (3, 3, width + 8, height + 8), border_width)
    screen.blit(shadow_surface, (x - 7, y + 8))
    
    # Strong glow layers for more prominent effect
    for i in range(border_width + 3, 0, -1):
        alpha = int(255 * (1 - i / (border_width + 3)) * 0.5)
        glow_surf = pygame.Surface((width + i*2 + 4, height + i*2 + 4), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*glow_color, alpha), (0, 0, width + i*2 + 4, height + i*2 + 4), max(1, i))
        screen.blit(glow_surf, (x - i - 2, y - i - 2))
    
    # Main box with gradient-like effect
    pygame.draw.rect(screen, color, (x, y, width, height))
    
    # Highlight edge (top-left) for 3D effect
    light_color = tuple(min(255, c + 100) for c in color)
    pygame.draw.line(screen, light_color, (x + 2, y + 2), (x + width - 2, y + 2), 3)
    pygame.draw.line(screen, light_color, (x + 2, y + 2), (x + 2, y + height - 2), 3)
    
    # Shadow edge (bottom-right) for 3D effect
    shadow_edge = tuple(max(0, c - 50) for c in color)
    pygame.draw.line(screen, shadow_edge, (x + width - 2, y + 2), (x + width - 2, y + height - 2), 2)
    pygame.draw.line(screen, shadow_edge, (x + 2, y + height - 2), (x + width - 2, y + height - 2), 2)
    
    # Border
    pygame.draw.rect(screen, glow_color, (x, y, width, height), border_width)


def draw_button(x, y, width, height, text, color, text_color, glow_color, is_hovered=False):
    """Draw an interactive button with enhanced hover and shadow effects"""
    # Scale button on hover for interactive feedback
    scale_offset = 5 if is_hovered else 0
    scaled_x = x - scale_offset
    scaled_y = y - scale_offset
    scaled_width = width + (scale_offset * 2)
    scaled_height = height + (scale_offset * 2)
    
    if is_hovered:
        draw_glowing_box(scaled_x, scaled_y, scaled_width, scaled_height, color, glow_color, 8)
    else:
        draw_glowing_box(x, y, width, height, color, glow_color, 4)
    
    font = pygame.font.Font(None, 48 if is_hovered else 44)
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=(x + width//2, y + height//2))
    
    # Multi-layer shadow for depth with improved quality
    shadow_surf = font.render(text, True, (0, 0, 0))
    shadow_surf.set_alpha(200)
    for offset in [5, 3]:
        shadow_rect = shadow_surf.get_rect(center=(x + width//2 + offset, y + height//2 + offset))
        screen.blit(shadow_surf, shadow_rect)
    
    # Add inner highlight for 3D button effect - better gradient
    highlight_height = max(2, height // 4)
    highlight_surf = pygame.Surface((width - 10, highlight_height), pygame.SRCALPHA)
    highlight_alpha = 120 if is_hovered else 80
    highlight_surf.fill((*text_color, highlight_alpha))
    screen.blit(highlight_surf, (x + 5, y + 5))
    
    # Add subtle bottom border for more depth
    bottom_alpha = 100 if is_hovered else 60
    bottom_border = pygame.Surface((width - 10, 2), pygame.SRCALPHA)
    bottom_border.fill((*glow_color, bottom_alpha))
    screen.blit(bottom_border, (x + 5, y + height - 7))
    
    screen.blit(text_surf, text_rect)


def draw_title_box(title, subtitle, theme_data):
    """Draw the main title area with enhanced styling"""
    title_y = 20
    
    # Draw decorative top bar with gradient-like effect
    for i in range(4):
        alpha = int(255 * (1 - i/4.0))
        pygame.draw.line(screen, (*theme_data['accent'], alpha), (50, 10 + i), (SCREEN_WIDHT - 50, 10 + i), max(1, 4 - i))
    
    # Draw main title with enhanced shadow and glow
    title_x = SCREEN_WIDHT//2 - 150
    
    # Create animated glow effect
    glow_surf = pygame.Surface((400, 120), pygame.SRCALPHA)
    for i in range(20, 0, -1):
        glow_alpha = int(25 * (1 - i/20.0))
        pygame.draw.circle(glow_surf, (*theme_data['accent'], glow_alpha), (200, 60), 80 + i)
    screen.blit(glow_surf, (title_x - 100, title_y - 20))
    
    draw_text_with_shadow(title, 72, theme_data['accent'], theme_data['shadow'], 
                         title_x, title_y, offset=5)
    
    # Draw decorative bottom bar under title with more detail
    for i in range(3):
        pygame.draw.line(screen, theme_data['accent'], (100, 98 + i), (SCREEN_WIDHT - 100, 98 + i), 
                        max(1, 3 - i), )
    
    # Add ornamental corner accents
    accent_bright = tuple(min(255, c + 60) for c in theme_data['accent'])
    pygame.draw.circle(screen, accent_bright, (100, 98), 4)
    pygame.draw.circle(screen, accent_bright, (SCREEN_WIDHT - 100, 98), 4)
    
    if subtitle:
        draw_text_with_shadow(subtitle, 28, theme_data['text'], theme_data['shadow'],
                             SCREEN_WIDHT//2 - 100, title_y + 75, offset=2)


base_images = load_base_images()
bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)

score = 0
high_score = 0
scored_pairs = set()

clock = pygame.time.Clock()


def show_how_to_play():
    global current_theme, text_color, accent_color, shadow_color, dark_color
    
    showing_help = True
    
    while showing_help:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        
        # Add semi-transparent background for better text readability
        help_bg = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT - 100), pygame.SRCALPHA)
        help_bg.fill((0, 0, 0, 80))
        screen.blit(help_bg, (0, 100))
        
        draw_title_box('HOW TO PLAY', '', THEMES[current_theme])
        
        # Simple list format for better readability
        lines = [
            ("CONTROLS:", accent_color, 28),
            ("  SPACE or UP - Flap", text_color, 24),
            ("  MOUSE CLICK - Flap", text_color, 24),
            ("  T - Toggle Themes", text_color, 24),
            ("", text_color, 24),
            ("GAMEPLAY:", accent_color, 28),
            ("  Pass pipes for 1 point each", text_color, 24),
            ("  Earn coins = score", text_color, 24),
            ("  Avoid ground and ceiling", text_color, 24),
            ("", text_color, 24),
            ("POWERUPS:", accent_color, 28),
            ("  HEART - Immunity 5s (vs pipes)", (255, 0, 0), 24),
            ("  STAR - 2x Score 5s", (255, 215, 0), 24),
            ("", text_color, 24),
            ("BIRD SKINS:", accent_color, 28),
            ("  Buy with coins", text_color, 24),
            ("  Premium/Legendary = more boost", text_color, 24),
        ]
        
        start_y = 130
        current_y = start_y
        
        for line_text, line_color, line_size in lines:
            if line_text:
                draw_text_with_shadow(line_text, line_size, line_color, shadow_color, 60, current_y, offset=2)
            current_y += 32
        
        draw_text_with_shadow('SPACE or ESC: Back to Menu', 18, text_color, shadow_color,
                             20, SCREEN_HEIGHT - 40, offset=1)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_SPACE or event.key == K_ESCAPE:
                    play_beep(400, 100)
                    showing_help = False
        
        pygame.display.update()


def show_main_menu():
    global current_theme, bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color, total_coins
    
    menu_running = True
    selected_option = 0
    
    while menu_running:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        
        # Display coins in top-right corner
        draw_glowing_box(SCREEN_WIDHT - 260, 10, 250, 80, dark_color, accent_color, 4)
        draw_text_with_shadow(f'Total Coins: {total_coins}', 36, (255, 215, 0), shadow_color, 
                             SCREEN_WIDHT - 245, 25, offset=2)
        
        draw_title_box('FLAPPY BIRD', 'Press SPACE to Play', THEMES[current_theme])
        
        button_width = 240
        button_height = 70
        button_x = SCREEN_WIDHT//2 - button_width//2
        
        buttons = [
            (button_x, 180, "PLAY"),
            (button_x, 280, "SHOP"),
            (button_x, 380, "HOW TO PLAY"),
            (button_x, 480, "THEMES"),
            (button_x, 580, "QUIT")
        ]
        
        for idx, (x, y, label) in enumerate(buttons):
            is_hovered = idx == selected_option
            draw_button(x, y, button_width, button_height, label, dark_color,
                       accent_color if is_hovered else text_color,
                       accent_color, is_hovered)
        
        draw_text_with_shadow('UP/DOWN: Select | SPACE/CLICK: Confirm', 18, text_color, 
                             shadow_color, 10, SCREEN_HEIGHT - 40, offset=1)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected_option = (selected_option - 1) % len(buttons)
                    play_beep(600, 100)
                elif event.key == K_DOWN:
                    selected_option = (selected_option + 1) % len(buttons)
                    play_beep(500, 100)
                elif event.key == K_SPACE:
                    if selected_option == 0:
                        play_beep(800, 150)
                        return "play"
                    elif selected_option == 1:
                        play_beep(800, 150)
                        show_shop_menu()
                    elif selected_option == 2:
                        play_beep(800, 150)
                        show_how_to_play()
                    elif selected_option == 3:
                        play_beep(800, 150)
                        show_theme_menu()
                    elif selected_option == 4:
                        play_beep(400, 200)
                        pygame.quit()
                        sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                play_beep(800, 150)
                return "play"
        
        pygame.display.update()


def show_theme_menu():
    global current_theme, bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color
    
    theme_menu_running = True
    selected_theme = current_theme
    
    while theme_menu_running:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        
        draw_title_box('SELECT THEME', '', THEMES[current_theme])
        
        for i, theme in enumerate(THEMES):
            y_pos = 180 + i*70
            is_selected = i == selected_theme
            
            if is_selected:
                draw_glowing_box(SCREEN_WIDHT//2 - 100, y_pos - 10, 200, 60, 
                                theme['dark'], theme['accent'], 3)
                color = theme['accent']
            else:
                pygame.draw.rect(screen, theme['dark'], (SCREEN_WIDHT//2 - 100, y_pos - 10, 200, 60))
                pygame.draw.rect(screen, theme['accent'], (SCREEN_WIDHT//2 - 100, y_pos - 10, 200, 60), 2)
                color = theme['text']
            
            draw_text_with_shadow(theme['name'], 32, color, theme['shadow'],
                                 SCREEN_WIDHT//2 - 60, y_pos + 5, offset=2)
        
        draw_text_with_shadow('UP/DOWN: Select | SPACE: Confirm | ESC: Back', 16, text_color,
                             shadow_color, 10, SCREEN_HEIGHT - 40, offset=1)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected_theme = (selected_theme - 1) % len(THEMES)
                    play_beep(600, 100)
                elif event.key == K_DOWN:
                    selected_theme = (selected_theme + 1) % len(THEMES)
                    play_beep(500, 100)
                elif event.key == K_SPACE:
                    current_theme = selected_theme
                    bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)
                    play_beep(800, 150)
                    theme_menu_running = False
                elif event.key == K_ESCAPE:
                    play_beep(400, 100)
                    theme_menu_running = False
        
        pygame.display.update()


def show_shop_menu():
    global total_coins, owned_bird_skins, text_color, accent_color, shadow_color, dark_color
    
    shop_running = True
    selected_skin = 0
    
    while shop_running:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        
        draw_title_box('BIRD SHOP', f'Coins: {total_coins}', THEMES[current_theme])
        
        # Calculate how many skins to show per screen
        skins_per_screen = 3
        start_idx = (selected_skin // skins_per_screen) * skins_per_screen
        visible_skins = BIRD_SKINS[start_idx:start_idx + skins_per_screen]
        
        for i, skin_data in enumerate(visible_skins):
            actual_idx = start_idx + i
            skin_name = skin_data[0]
            color = skin_data[1]
            cost = skin_data[2]
            powerup_boost = skin_data[3]
            is_premium = skin_data[4]
            is_legendary = skin_data[5]
            
            y_pos = 200 + i * 120
            is_selected = actual_idx == selected_skin
            is_owned = actual_idx in owned_bird_skins
            
            # Draw skin preview box
            box_color = accent_color if is_selected else dark_color
            border_color = accent_color if (is_selected or is_owned) else shadow_color
            
            draw_glowing_box(80, y_pos, 1050, 120, box_color, border_color, 4 if is_selected else 2)
            
            # Draw bird preview
            if color is None:  # Rainbow skin
                bird_preview = create_bird_graphics(None)
                preview_img = pygame.transform.scale(bird_preview[2], (70, 60))  # Use different frame for animation
            else:
                bird_preview = create_bird_graphics(color)
                preview_img = pygame.transform.scale(bird_preview[0], (70, 60))
            screen.blit(preview_img, (110, y_pos + 30))
            
            # Draw skin info with premium/legendary tag
            tag = ""
            tag_color = accent_color
            if is_legendary:
                tag = " [LEGENDARY]"
                tag_color = (255, 215, 0)  # Gold
            elif is_premium:
                tag = " [PREMIUM]"
                tag_color = (218, 165, 32)  # Goldenrod
            
            info_text = f"{skin_name}{tag}"
            draw_text_with_shadow(info_text, 30, tag_color if tag else accent_color, shadow_color, 210, y_pos + 20, offset=2)
            draw_text_with_shadow(f"Boost: +{int((powerup_boost - 1) * 100)}%", 22, text_color, shadow_color, 210, y_pos + 55, offset=1)
            
            # Draw cost or "OWNED" status
            if is_owned:
                draw_text_with_shadow("OWNED", 36, (0, 255, 0), shadow_color, 950, y_pos + 42, offset=2)
            else:
                cost_text = f"Cost: {cost}"
                cost_color = (255, 215, 0) if not is_legendary else (255, 0, 0)
                draw_text_with_shadow(cost_text, 30, cost_color, shadow_color, 950, y_pos + 45, offset=2)
        
        draw_text_with_shadow('UP/DOWN: Select | SPACE: Buy | ESC: Back', 18, text_color, shadow_color, 
                             20, SCREEN_HEIGHT - 40, offset=1)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected_skin = (selected_skin - 1) % len(BIRD_SKINS)
                    play_beep(600, 100)  # Boop sound on navigation
                elif event.key == K_DOWN:
                    selected_skin = (selected_skin + 1) % len(BIRD_SKINS)
                    play_beep(500, 100)  # Boop sound on navigation
                elif event.key == K_SPACE:
                    # Try to buy the skin
                    skin_data = BIRD_SKINS[selected_skin]
                    skin_name = skin_data[0]
                    cost = skin_data[2]
                    is_legendary = skin_data[5]
                    
                    if selected_skin not in owned_bird_skins:
                        if total_coins >= cost:
                            total_coins -= cost
                            owned_bird_skins.add(selected_skin)
                            # Play victory sound if legendary skin
                            if is_legendary:
                                playVictorySound()
                            else:
                                play_beep(800, 200)
                    else:
                        play_beep(400, 100)  # Beep if already owned
                elif event.key == K_ESCAPE:
                    shop_running = False
        
        pygame.display.update()


def playVictorySound():
    """Play victory sound for legendary skin purchase"""
    if victory:
        play(victory)
    else:
        # Play a victory-like beep sequence
        for freq in [523, 659, 784, 1047]:
            play_beep(freq, 150)


def show_difficulty_selector():
    global current_theme, bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color
    
    selecting_difficulty = True
    selected_diff_idx = 1
    
    while selecting_difficulty:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        
        draw_title_box('SELECT DIFFICULTY', '', THEMES[current_theme])
        
        for i, (diff_name, speed, grav, gap) in enumerate(DIFFICULTIES):
            y_pos = 180 + i*70
            is_selected = i == selected_diff_idx
            
            if is_selected:
                draw_glowing_box(SCREEN_WIDHT//2 - 100, y_pos - 10, 200, 60,
                                dark_color, accent_color, 3)
                color = accent_color
            else:
                pygame.draw.rect(screen, dark_color, (SCREEN_WIDHT//2 - 100, y_pos - 10, 200, 60))
                pygame.draw.rect(screen, accent_color, (SCREEN_WIDHT//2 - 100, y_pos - 10, 200, 60), 1)
                color = text_color
            
            draw_text_with_shadow(diff_name, 32, color, shadow_color,
                                 SCREEN_WIDHT//2 - 60, y_pos + 5, offset=2)
        
        draw_text_with_shadow('UP/DOWN: Select | SPACE/CLICK: Start', 16, text_color,
                             shadow_color, 20, SCREEN_HEIGHT - 40, offset=1)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected_diff_idx = (selected_diff_idx - 1) % len(DIFFICULTIES)
                    play_beep(600, 100)
                elif event.key == K_DOWN:
                    selected_diff_idx = (selected_diff_idx + 1) % len(DIFFICULTIES)
                    play_beep(500, 100)
                elif event.key == K_SPACE:
                    play_beep(800, 150)
                    selecting_difficulty = False
            if event.type == MOUSEBUTTONDOWN:
                play_beep(800, 150)
                selecting_difficulty = False
        
        pygame.display.update()
    
    return selected_diff_idx


def show_bird_selector():
    global current_theme, text_color, accent_color, shadow_color, dark_color
    
    selecting_bird = True
    selected_bird_idx = 0
    
    while selecting_bird:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        
        draw_title_box('SELECT YOUR BIRD', '', THEMES[current_theme])
        
        # Show only owned birds
        owned_birds = sorted(list(owned_bird_skins))
        
        for display_idx, bird_idx in enumerate(owned_birds):
            skin_data = BIRD_SKINS[bird_idx]
            skin_name = skin_data[0]
            color = skin_data[1]
            cost = skin_data[2]
            powerup_boost = skin_data[3]
            is_premium = skin_data[4]
            is_legendary = skin_data[5]
            
            y_pos = 180 + display_idx * 120
            is_selected = display_idx == selected_bird_idx
            
            if is_selected:
                draw_glowing_box(150, y_pos, 900, 100, dark_color, accent_color, 4)
                color_text = accent_color
            else:
                pygame.draw.rect(screen, dark_color, (150, y_pos, 900, 100))
                pygame.draw.rect(screen, accent_color, (150, y_pos, 900, 100), 2)
                color_text = text_color
            
            # Draw bird preview
            if color is None:  # Rainbow skin
                bird_preview = create_bird_graphics(None)
                preview_img = pygame.transform.scale(bird_preview[1], (60, 50))
            else:
                bird_preview = create_bird_graphics(color)
                preview_img = pygame.transform.scale(bird_preview[0], (60, 50))
            screen.blit(preview_img, (180, y_pos + 25))
            
            # Add tag to name
            tag = ""
            tag_color = color_text
            if is_legendary:
                tag = " [LEGENDARY]"
                tag_color = (255, 215, 0)
            elif is_premium:
                tag = " [PREMIUM]"
                tag_color = (218, 165, 32)
            
            draw_text_with_shadow(skin_name + tag, 36, tag_color, shadow_color, 280, y_pos + 10, offset=2)
            draw_text_with_shadow(f'Boost: +{int((powerup_boost - 1) * 100)}%', 24, (255, 215, 0), shadow_color, 280, y_pos + 55, offset=1)
        
        draw_text_with_shadow('UP/DOWN: Select | SPACE/CLICK: Confirm', 18, text_color, shadow_color, 
                             20, SCREEN_HEIGHT - 40, offset=1)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected_bird_idx = (selected_bird_idx - 1) % len(owned_birds)
                    play_beep(600, 100)
                elif event.key == K_DOWN:
                    selected_bird_idx = (selected_bird_idx + 1) % len(owned_birds)
                    play_beep(500, 100)
                elif event.key == K_SPACE:
                    selecting_bird = False
            if event.type == MOUSEBUTTONDOWN:
                selecting_bird = False
        
        pygame.display.update()
    
    return owned_birds[selected_bird_idx]


def show_game_over_menu(final_score, final_high_score, coins_earned=0, total_coins=0):
    global current_theme, bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color
    
    game_over_running = True
    selected_option = 0
    
    while game_over_running:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        
        overlay = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT))
        overlay.set_alpha(120)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        draw_glowing_box(SCREEN_WIDHT//2 - 220, 30, 440, 540, dark_color, accent_color, 5)
        
        draw_text_with_shadow('GAME OVER', 64, accent_color, shadow_color,
                             SCREEN_WIDHT//2 - 150, 60, offset=4)
        draw_text_with_shadow(f'Score: {final_score}', 40, text_color, shadow_color,
                             SCREEN_WIDHT//2 - 80, 160, offset=3)
        draw_text_with_shadow(f'High Score: {final_high_score}', 40, accent_color, shadow_color,
                             SCREEN_WIDHT//2 - 160, 230, offset=3)
        draw_text_with_shadow(f'Coins Earned: +{coins_earned}', 36, (255, 215, 0), shadow_color,
                             SCREEN_WIDHT//2 - 150, 310, offset=3)
        draw_text_with_shadow(f'Total Coins: {total_coins}', 36, (255, 215, 0), shadow_color,
                             SCREEN_WIDHT//2 - 140, 380, offset=3)
        
        button_width = 240
        button_height = 70
        button_x = SCREEN_WIDHT//2 - button_width//2
        
        buttons = [
            (button_x, 470, "PLAY AGAIN"),
            (button_x, 560, "MAIN MENU")
        ]
        
        for idx, (x, y, label) in enumerate(buttons):
            is_hovered = idx == selected_option
            draw_button(x, y, button_width, button_height, label, dark_color,
                       accent_color if is_hovered else text_color,
                       accent_color, is_hovered)
        
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected_option = (selected_option - 1) % len(buttons)
                    play_beep(600, 100)
                elif event.key == K_DOWN:
                    selected_option = (selected_option + 1) % len(buttons)
                    play_beep(500, 100)
                elif event.key == K_SPACE:
                    play_beep(800, 150)
                    return selected_option
            if event.type == MOUSEBUTTONDOWN:
                play_beep(800, 150)
                return 0
        
        pygame.display.update()


if __name__ == "__main__":
    while True:
        menu_result = show_main_menu()
        current_difficulty = show_difficulty_selector()
        selected_bird_skin_idx = show_bird_selector()
        
        _, GAME_SPEED, GRAVITY, PIPE_GAP = DIFFICULTIES[current_difficulty]
        
        # Create bird images based on selected skin
        skin_data = BIRD_SKINS[selected_bird_skin_idx]
        skin_name = skin_data[0]
        bird_color = skin_data[1]
        cost = skin_data[2]
        powerup_boost = skin_data[3]
        bird_imgs = create_bird_graphics(bird_color)
        
        play_again = True
        while play_again:
            score = 0
            scored_pairs = set()
            pipe_pair_id = 0
            coins_earned_this_run = 0
        
            bird_group = pygame.sprite.Group()
            bird = Bird(bird_imgs)
            bird_group.add(bird)
        
            ground_group = pygame.sprite.Group()
        
            for i in range(2):
                ground = Ground(GROUND_WIDHT * i, ground_img)
                ground_group.add(ground)
        
            pipe_group = pygame.sprite.Group()
            for i in range(3):
                pipes = get_random_pipes(SCREEN_WIDHT + (PIPE_SPACING * i), pipe_pair_id)
                pipe_pair_id += 1
                pipe_group.add(pipes[0])
                pipe_group.add(pipes[1])
        
            begin = True
        
            while begin:
                clock.tick(60)
            
                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == KEYDOWN:
                        if event.key == K_SPACE or event.key == K_UP:
                            bird.bump()
                            play(wing)
                            begin = False
                        elif event.key == K_t:
                            current_theme = (current_theme + 1) % len(THEMES)
                            bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)
                            bird = Bird(bird_imgs)
                            bird_group.empty(); bird_group.add(bird)
                            ground_group.empty()
                            for i in range(2):
                                ground = Ground(GROUND_WIDHT * i, ground_img)
                                ground_group.add(ground)
            
                    if event.type == MOUSEBUTTONDOWN and event.button == 1:
                        bird.bump()
                        play(wing)
                        begin = False
            
                screen.blit(BACKGROUND, (0, 0))
            
                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])
                    new_ground = Ground(GROUND_WIDHT - 20, ground_img)
                    ground_group.add(new_ground)
            
                bird.begin()
                ground_group.update()
            
                # Draw bird manually with full transparency during GET READY
                # Use base image (unrotated) for static display
                bird_display = pygame.Surface((80, 70), pygame.SRCALPHA)
                bird_display.fill((0, 0, 0, 0))
                bird_display.blit(bird.image, (0, 0))
                screen.blit(bird_display, bird.rect)
                ground_group.draw(screen)
            
                # Draw "GET READY" text
                draw_text_with_shadow('GET READY!', 48, accent_color, shadow_color,
                                     SCREEN_WIDHT//2 - 110, 150, offset=3)
            
                pygame.display.update()
        
            playing = True
            floating_scores = []  # List to track floating score animations
            delta_time = 1/60.0  # Time per frame at 60 FPS
            powerup_group = pygame.sprite.Group()
            powerup_spawn_counter = 0
        
            # Calculate powerup spawn rate based on selected bird skin's powerup boost
            powerup_spawn_rate = int(200 / powerup_boost)  # More expensive birds spawn powerups more frequently
        
            while playing:
                clock.tick(60)
            
                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == KEYDOWN:
                        if event.key == K_SPACE or event.key == K_UP:
                            bird.bump()
                            play(wing)
                        elif event.key == K_t:
                            current_theme = (current_theme + 1) % len(THEMES)
                            bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)
                    if event.type == MOUSEBUTTONDOWN and event.button == 1:
                        bird.bump()
                        play(wing)
            
                screen.blit(BACKGROUND, (0, 0))
            
                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])
                    new_ground = Ground(GROUND_WIDHT - 20, ground_img)
                    ground_group.add(new_ground)
            
                if is_off_screen(pipe_group.sprites()[0]):
                    pipe_group.remove(pipe_group.sprites()[0])
                    pipe_group.remove(pipe_group.sprites()[0])
                    # Get the rightmost pipe position and spawn new ones after it
                    rightmost_x = max(pipe.rect.x for pipe in pipe_group)
                    pipes = get_random_pipes(rightmost_x + PIPE_SPACING, pipe_pair_id)
                    pipe_pair_id += 1
                    pipe_group.add(pipes[0])
                    pipe_group.add(pipes[1])
            
                bird_group.update()
                ground_group.update()
                pipe_group.update()
            
                # Update bird powerup timers
                bird.immunity_time = max(0, bird.immunity_time - delta_time)
                bird.double_score_time = max(0, bird.double_score_time - delta_time)
                # Calculate multiplier based on active powerups
                bird.score_multiplier = 2.0 if bird.double_score_time > 0 else 1.0
            
                # Spawn powerups randomly in safe areas (middle of screen, away from edges)
                powerup_spawn_counter += 1
                if powerup_spawn_counter > powerup_spawn_rate:
                    powerup_spawn_counter = 0
                    powerup_type = random.choice([Powerup.IMMUNITY, Powerup.DOUBLE_SCORE])
                    # Safe spawn zone: right side of screen, middle vertical area
                    x = SCREEN_WIDHT + 150  # Spawn far right so it scrolls into view
                    # Spawn in the middle section, avoiding ground (bottom 150px) and top 100px
                    y = random.randint(150, SCREEN_HEIGHT - 150)
                    powerup_group.add(Powerup(x, y, powerup_type, accent_color))
            
                # Update and draw powerups
                powerups_to_remove = []
                for powerup in powerup_group:
                    if not powerup.update(delta_time):
                        powerups_to_remove.append(powerup)
            
                for powerup in powerups_to_remove:
                    powerup_group.remove(powerup)
            
                # Check powerup collision with bird
                powerup_collisions = pygame.sprite.groupcollide(bird_group, powerup_group, False, True, pygame.sprite.collide_rect)
                for bird_sprite in powerup_collisions:
                    for powerup in powerup_collisions[bird_sprite]:
                        if powerup.powerup_type == Powerup.IMMUNITY:
                            bird.immunity_time = 5.0  # 5 seconds of immunity - pipes pass through!
                        else:  # DOUBLE_SCORE
                            bird.double_score_time = 5.0  # 5 seconds of 2x score
                            score = int(score * 2)  # Multiply current score by 2
            
                # Draw bird manually with proper rotation (no artifact rendering)
                screen.blit(bird.rotated_image, bird.rect)
                
                pipe_group.draw(screen)
                ground_group.draw(screen)
            
                # Draw powerups with custom rotation
                for powerup in powerup_group:
                    powerup.draw(screen)
            
                # Draw score with enhanced styling
                draw_glowing_box(10, 10, 280, 110, dark_color, accent_color, 4)
                draw_text_with_shadow(f'Score: {score}', 44, accent_color, shadow_color, 25, 18, offset=2)
                draw_text_with_shadow(f'Coins: {total_coins}', 36, (255, 215, 0), shadow_color, 25, 70, offset=2)
            
                # Draw powerup status with better styling
                powerup_y_offset = 130
                if bird.immunity_time > 0:
                    immunity_percent = min(100, int((bird.immunity_time / 5.0) * 100))
                    draw_glowing_box(10, powerup_y_offset, 280, 70, (220, 20, 60), (255, 100, 100), 3)
                    draw_text_with_shadow('IMMUNITY ACTIVE', 26, (255, 255, 255), (0, 0, 0), 20, powerup_y_offset + 8, offset=2)
                    draw_text_with_shadow(f'{bird.immunity_time:.1f}s', 32, (255, 200, 200), (0, 0, 0), 180, powerup_y_offset + 32, offset=1)
                    # Progress bar
                    bar_width = int(260 * immunity_percent / 100)
                    pygame.draw.rect(screen, (150, 10, 30), (20, powerup_y_offset + 55, 260, 8))
                    pygame.draw.rect(screen, (255, 100, 100), (20, powerup_y_offset + 55, bar_width, 8))
                    powerup_y_offset += 80
            
                if bird.double_score_time > 0:
                    score_percent = min(100, int((bird.double_score_time / 5.0) * 100))
                    draw_glowing_box(10, powerup_y_offset, 280, 70, (220, 170, 0), (255, 255, 0), 3)
                    draw_text_with_shadow('2x SCORE ACTIVE', 26, (0, 0, 0), (100, 100, 0), 20, powerup_y_offset + 8, offset=2)
                    draw_text_with_shadow(f'{bird.double_score_time:.1f}s', 32, (255, 255, 0), (0, 0, 0), 180, powerup_y_offset + 32, offset=1)
                    # Progress bar
                    bar_width = int(260 * score_percent / 100)
                    pygame.draw.rect(screen, (200, 150, 0), (20, powerup_y_offset + 55, 260, 8))
                    pygame.draw.rect(screen, (255, 255, 0), (20, powerup_y_offset + 55, bar_width, 8))
            
                # Update and draw floating scores
                active_scores = []
                for float_score in floating_scores:
                    if float_score.update(delta_time):
                        active_scores.append(float_score)
                        float_score.draw(screen)
                floating_scores = active_scores
            
                pygame.display.update()
            
                # Check collisions
                ground_collision = pygame.sprite.groupcollide(bird_group, ground_group, False, False, pygame.sprite.collide_mask)
                pipe_collision = pygame.sprite.groupcollide(bird_group, pipe_group, False, False, pygame.sprite.collide_mask) and bird.immunity_time <= 0
                ceiling_collision = bird.rect.top <= 0
            
                if ground_collision or pipe_collision or ceiling_collision:
                    play(hit)
                    coins_earned_this_run = int(score)
                    total_coins += coins_earned_this_run
                    high_score = max(high_score, score)
                    time.sleep(0.5)
                    playing = False
            
                for pipe in pipe_group:
                    if pipe.pair_id not in scored_pairs and pipe.rect.right < bird.rect.left:
                        scored_pairs.add(pipe.pair_id)
                        score_increment = int(bird.score_multiplier)
                        score += score_increment
                        # Create floating score animation at pipe position 
                        floating_scores.append(FloatingScore(pipe.rect.centerx, pipe.rect.centery, score_increment, accent_color, accent_color))
                        play(wing)
        
            menu_choice = show_game_over_menu(score, high_score, coins_earned_this_run, total_coins)
        
            # Handle menu choice
            if menu_choice == 1:  # MAIN MENU selected
                play_again = False
            # else menu_choice == 0, which means PLAY AGAIN - continue the while play_again loop
