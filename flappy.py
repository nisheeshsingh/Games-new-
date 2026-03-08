import pygame, random, time, os, sys, math
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
PIPE_SPACING = 400

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

if not os.path.exists(wing): wing = None
if not os.path.exists(hit): hit = None
if not os.path.exists(boop): boop = None
if not os.path.exists(victory): victory = None


def generate_beep(frequency=1000, duration=100, volume=0.3):
    try:
        if not HAS_NUMPY:
            return None
        sample_rate = 44100
        frames = int(duration * sample_rate / 1000)
        t = np.linspace(0, duration/1000, frames)
        fade_frames = max(1, int(frames * 0.1))
        wave = np.sin(2.0 * np.pi * frequency * t)
        fade_in = np.linspace(0, 1, fade_frames)
        fade_out = np.linspace(1, 0, fade_frames)
        wave[:fade_frames] *= fade_in
        wave[-fade_frames:] *= fade_out
        wave = (wave * 32767 * volume).astype(np.int16)
        sound = pygame.sndarray.make_sound(wave)
        return sound
    except Exception:
        return None


def play_beep(frequency=1000, duration=100):
    try:
        if not HAS_NUMPY:
            return
        sound = generate_beep(frequency, duration, 0.5)
        if sound:
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
    {"name": "classic",   "bg": (135, 206, 250), "pipe": (34, 139, 34), "bird": (255, 200, 0), "ground": (139, 69, 19), "text": (255, 255, 255), "accent": (30, 80, 180), "shadow": (10, 30, 80), "dark": (20, 50, 120)},
    {"name": "neon",      "bg": (0, 0, 0),       "pipe": (255, 20, 147), "bird": (0, 255, 255), "ground": (255, 69, 0), "text": (0, 255, 255), "accent": (255, 255, 0), "shadow": (100, 100, 100), "dark": (20, 20, 30)},
    {"name": "cybercity", "bg": (10, 10, 50),    "pipe": (0, 255, 0),    "bird": (255, 0, 255), "ground": (50, 50, 50), "text": (100, 255, 100), "accent": (255, 100, 255), "shadow": (100, 100, 100), "dark": (20, 20, 50)},
    {"name": "hell",      "bg": (100, 0, 0),      "pipe": (139, 0, 0),    "bird": (255, 69, 0),   "ground": (80, 0, 0), "text": (255, 255, 100), "accent": (255, 100, 0), "shadow": (100, 100, 100), "dark": (60, 20, 0)},
    {"name": "forest",    "bg": (51, 102, 51),    "pipe": (139, 35, 35),  "bird": (255, 215, 0),  "ground": (34, 85, 34),  "text": (255, 255, 200), "accent": (144, 238, 144), "shadow": (100, 100, 100), "dark": (25, 60, 25)},
    {"name": "ocean",     "bg": (0, 105, 148),    "pipe": (70, 130, 180), "bird": (255, 255, 0),  "ground": (188, 143, 143), "text": (255, 255, 255), "accent": (64, 224, 208), "shadow": (100, 100, 100), "dark": (0, 71, 107)},
    {"name": "sunset",    "bg": (255, 140, 60),   "pipe": (180, 82, 45),  "bird": (255, 20, 147), "ground": (139, 69, 19),  "text": (255, 250, 205), "accent": (255, 215, 0),  "shadow": (100, 100, 100),  "dark": (160, 82, 45)},
    {"name": "midnight",  "bg": (10, 10, 30),     "pipe": (80, 80, 120), "bird": (0, 255, 255), "ground": (30, 30, 50),  "text": (173, 216, 230), "accent": (100, 200, 255), "shadow": (50, 50, 100), "dark": (10, 10, 40)},
]
current_theme = 0

# Bird skins - (name, color, cost, powerup_boost, is_premium, is_legendary)
BIRD_SKINS = [
    ("Classic Gold",    (255, 200, 0),    0,     1.0, False, False),
    ("Royal Blue",      (25, 100, 200),   500,   1.3, False, False),
    ("Crimson Red",     (220, 20, 60),    750,   1.5, False, False),
    ("Emerald Green",   (50, 205, 50),    1000,  1.8, False, False),
    ("Electric Purple", (138, 43, 226),   1250,  2.0, False, False),
    ("Sunset Orange",   (255, 140, 0),    750,   1.5, False, False),
    ("Aqua Cyan",       (0, 255, 255),    1000,  1.8, False, False),
    ("Rose Pink",       (255, 105, 180),  1250,  2.0, False, False),
    ("Forest Guardian", (144, 238, 144),  2500,  2.5, True,  False),
    ("Ocean Blue",      (64, 224, 208),   2500,  2.5, True,  False),
    ("Sunset Blaze",    (255, 165, 0),    3500,  2.8, True,  False),
    ("Midnight Mystic", (186, 85, 211),   3500,  2.8, True,  False),
    ("Neon Cyber",      (0, 255, 255),    5000,  3.0, True,  False),
    ("Hellfire Dragon", (255, 69, 0),     7500,  3.2, True,  False),
    ("Rainbow Legend",  None,             15000, 5.0, True,  True),
]

owned_bird_skins = {0}
total_coins = 0
coins_earned_this_run = 0

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

pipe_pair_id = 0

# ─────────────────────────────────────────────────────────────────────────────
# BIRD RENDERING  (shared between shop previews AND in-game drawing)
# ─────────────────────────────────────────────────────────────────────────────

RAINBOW_COLORS = [
    (255, 60, 60),    # Red
    (255, 165, 0),    # Orange
    (255, 240, 0),    # Yellow
    (60, 220, 60),    # Green
    (60, 140, 255),   # Blue
    (140, 60, 240),   # Indigo/Violet
]


def get_rainbow_color(t_offset=0):
    """Get a smooth cycling rainbow color using frame counter"""
    t = (pygame.time.get_ticks() / 600.0 + t_offset) % 1.0
    idx = int(t * len(RAINBOW_COLORS))
    frac = (t * len(RAINBOW_COLORS)) - idx
    c1 = RAINBOW_COLORS[idx % len(RAINBOW_COLORS)]
    c2 = RAINBOW_COLORS[(idx + 1) % len(RAINBOW_COLORS)]
    return tuple(int(c1[i] + (c2[i] - c1[i]) * frac) for i in range(3))


def draw_bird_shape(surface, cx, cy, body_color, wing_frame=0, angle_deg=0, scale=1.0):
    """
    Draw a rich bird directly onto `surface` centred at (cx, cy).
    wing_frame: 0-3  (flap cycle)
    angle_deg: rotation (positive = nose-down)
    scale: size multiplier (1.0 = normal game size)
    Works for BOTH in-game rendering and shop previews.
    """
    cos_a = math.cos(math.radians(-angle_deg))
    sin_a = math.sin(math.radians(-angle_deg))

    def rot(x, y):
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        return int(cx + rx * scale), int(cy + ry * scale)

    is_rainbow = (body_color is None)

    if is_rainbow:
        bc = get_rainbow_color(0.0)
        hc = get_rainbow_color(0.15)
        wc = get_rainbow_color(0.30)
        tc = get_rainbow_color(0.45)
    else:
        bc = body_color
        hc = body_color
        wc = tuple(max(0, c - 40) for c in body_color)
        tc = tuple(min(255, c + 30) for c in body_color)

    # ── Tail feathers ──
    tail_pts = [rot(-14, -2), rot(-20, -7), rot(-18, 1), rot(-14, 4)]
    pygame.draw.polygon(surface, tc, tail_pts)
    tail_pts2 = [rot(-12, 2), rot(-20, 6), rot(-16, 6)]
    pygame.draw.polygon(surface, tuple(max(0, c - 20) for c in tc), tail_pts2)

    # ── Body ──
    body_pts = [rot(-12, -5), rot(10, -7), rot(14, 0), rot(10, 7), rot(-10, 6)]
    body_hi = tuple(min(255, c + 50) for c in bc)
    pygame.draw.polygon(surface, bc, body_pts)
    pygame.draw.polygon(surface, body_hi, body_pts, 2)

    # ── Wing (animated flap) ──
    wing_offsets = [-6, -10, -6, 0]
    wy = wing_offsets[wing_frame % 4]
    wing_pts = [rot(-2, -4), rot(8, -8 + wy), rot(9, -2 + wy // 2), rot(0, 0)]
    wing_dark = tuple(max(0, c - 30) for c in wc)
    pygame.draw.polygon(surface, wc, wing_pts)
    pygame.draw.polygon(surface, wing_dark, wing_pts, 2)

    # ── Head ──
    hx, hy = rot(13, -1)
    head_r = int(9 * scale)
    head_hi = tuple(min(255, c + 60) for c in hc)
    pygame.draw.circle(surface, hc, (hx, hy), head_r)
    pygame.draw.circle(surface, head_hi, (hx, hy), head_r, 2)

    # ── Eye white + pupil ──
    ex, ey = rot(17, -4)
    pygame.draw.circle(surface, (255, 255, 255), (ex, ey), int(4 * scale))
    px, py = rot(18, -5)
    pygame.draw.circle(surface, (20, 20, 20), (px, py), int(2 * scale))
    # Eye shine
    sx, sy = rot(19, -6)
    pygame.draw.circle(surface, (255, 255, 255), (sx, sy), max(1, int(1.2 * scale)))

    # ── Beak ──
    beak_col = (255, 160, 0)
    beak_pts = [rot(19, -2), rot(26, -1), rot(19, 3)]
    pygame.draw.polygon(surface, beak_col, beak_pts)
    pygame.draw.polygon(surface, (200, 110, 0), beak_pts, 1)

    # ── Cheek blush ──
    blush_col = (255, 180, 180, 80)
    bx, by = rot(16, 2)
    blush_surf = pygame.Surface((int(8 * scale), int(5 * scale)), pygame.SRCALPHA)
    pygame.draw.ellipse(blush_surf, (255, 150, 150, 70), blush_surf.get_rect())
    surface.blit(blush_surf, (bx - int(4 * scale), by - int(2 * scale)))


def create_bird_surface_for_shop(color, size=70):
    """Return a pygame.Surface with a bird drawn on it – used in menus / shop."""
    surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    draw_bird_shape(surf, size, size, color, wing_frame=1, angle_deg=0, scale=size / 28.0)
    return surf


def create_bird_graphics(color):
    """Keep backward-compat: returns list of 4 surfaces (one per wing frame)."""
    images = []
    for frame in range(4):
        surf = pygame.Surface((100, 90), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        draw_bird_shape(surf, 50, 45, color, wing_frame=frame, angle_deg=0, scale=1.0)
        surf = surf.convert_alpha()
        images.append(surf)
    return images


# ─────────────────────────────────────────────────────────────────────────────
# HEART drawing helper  (used both for powerup icon and in-game HUD)
# ─────────────────────────────────────────────────────────────────────────────

def draw_heart(surface, cx, cy, size, color=(255, 50, 80), outline_color=(255, 120, 140)):
    """
    Draw a proper heart shape centred at (cx, cy) with given half-size.
    Uses two circles + a triangle.
    """
    r = max(2, int(size * 0.55))
    # Left lobe
    lx = int(cx - size * 0.28)
    ly = int(cy - size * 0.15)
    pygame.draw.circle(surface, color, (lx, ly), r)
    # Right lobe
    rx = int(cx + size * 0.28)
    ry = int(cy - size * 0.15)
    pygame.draw.circle(surface, color, (rx, ry), r)
    # Bottom triangle
    pts = [
        (int(cx - size * 0.85), int(cy - size * 0.05)),
        (int(cx + size * 0.85), int(cy - size * 0.05)),
        (int(cx), int(cy + size * 0.90)),
    ]
    pygame.draw.polygon(surface, color, pts)
    # Inner highlight
    hi_color = tuple(min(255, c + 80) for c in color)
    hi_r = max(1, int(r * 0.45))
    pygame.draw.circle(surface, hi_color, (lx - int(r * 0.2), ly - int(r * 0.25)), hi_r)
    # Outline
    pygame.draw.circle(surface, outline_color, (lx, ly), r, 2)
    pygame.draw.circle(surface, outline_color, (rx, ry), r, 2)
    pygame.draw.polygon(surface, outline_color, pts, 2)


# ─────────────────────────────────────────────────────────────────────────────
# PIPE / GROUND graphics
# ─────────────────────────────────────────────────────────────────────────────

def create_mario_pipe(color):
    pipe_surf = pygame.Surface((PIPE_WIDHT, PIPE_HEIGHT), pygame.SRCALPHA)
    pipe_body_color = tuple(max(0, c - 60) for c in color)
    pygame.draw.rect(pipe_surf, pipe_body_color, (0, 0, PIPE_WIDHT, PIPE_HEIGHT))
    light_color = tuple(min(255, c + 120) for c in color)
    pygame.draw.line(pipe_surf, light_color, (1, 4), (1, PIPE_HEIGHT - 4), 5)
    pygame.draw.line(pipe_surf, light_color, (4, 0), (PIPE_WIDHT - 4, 0), 4)
    shadow_color = (0, 0, 0)
    pygame.draw.line(pipe_surf, shadow_color, (PIPE_WIDHT - 1, 4), (PIPE_WIDHT - 1, PIPE_HEIGHT - 4), 5)
    pygame.draw.line(pipe_surf, shadow_color, (4, PIPE_HEIGHT - 1), (PIPE_WIDHT - 4, PIPE_HEIGHT - 1), 4)
    band_color = (110, 110, 110)
    for y in range(12, PIPE_HEIGHT, 38):
        pygame.draw.line(pipe_surf, (60, 60, 60), (1, y), (PIPE_WIDHT - 1, y), 8)
        pygame.draw.line(pipe_surf, (180, 180, 180), (1, y - 1), (PIPE_WIDHT - 1, y - 1), 5)
        pygame.draw.line(pipe_surf, band_color, (1, y + 2), (PIPE_WIDHT - 1, y + 2), 3)
    for y in range(12, PIPE_HEIGHT, 38):
        pygame.draw.circle(pipe_surf, (80, 80, 80), (7, y), 4)
        pygame.draw.circle(pipe_surf, (160, 160, 160), (5, y - 1), 2)
        pygame.draw.circle(pipe_surf, (80, 80, 80), (PIPE_WIDHT - 7, y), 4)
        pygame.draw.circle(pipe_surf, (160, 160, 160), (PIPE_WIDHT - 5, y - 1), 2)
    return pipe_surf


def create_ground_graphics(color):
    ground_surf = pygame.Surface((GROUND_WIDHT, GROUND_HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(ground_surf, color, (0, 0, GROUND_WIDHT, GROUND_HEIGHT))
    dirt_dark = tuple(max(0, c - 40) for c in color)
    for x in range(0, GROUND_WIDHT, 40):
        for y in range(0, GROUND_HEIGHT, 40):
            if (x // 40 + y // 40) % 2 == 0:
                pygame.draw.rect(ground_surf, dirt_dark, (x, y, 40, 40))
    light_color = tuple(min(255, c + 60) for c in color)
    pygame.draw.line(ground_surf, light_color, (0, 2), (GROUND_WIDHT, 2), 3)
    grass_color = tuple(min(255, c + 80) for c in color)
    for x in range(0, GROUND_WIDHT, 15):
        pygame.draw.line(ground_surf, grass_color, (x, 0), (x + 5, -5), 2)
    return ground_surf


# ─────────────────────────────────────────────────────────────────────────────
# POWERUP
# ─────────────────────────────────────────────────────────────────────────────

class Powerup(pygame.sprite.Sprite):
    IMMUNITY = 0
    DOUBLE_SCORE = 1

    def __init__(self, x, y, powerup_type, color):
        pygame.sprite.Sprite.__init__(self)
        self.powerup_type = powerup_type
        self.color = color
        self.x = x
        self.y = y
        self.lifetime = 10.0
        self.elapsed = 0.0
        self.pulse_time = 0.0
        self.image = pygame.Surface((60, 60), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        self.elapsed += delta_time
        self.pulse_time += delta_time
        self.rect[0] -= GAME_SPEED
        float_offset = int(8 * math.sin(self.pulse_time * 2.5))
        self.rect.y = self.y + float_offset
        return self.elapsed < self.lifetime

    def draw(self, screen):
        scale = 1.0 + 0.18 * math.sin(self.pulse_time * 3.5)
        cx, cy = self.rect.center
        size = int(22 * scale)

        if self.powerup_type == self.IMMUNITY:
            # ── Beautiful glowing heart ──
            # Outer glow layers
            for glow_r in range(6, 0, -1):
                glow_alpha = int(40 * (1 - glow_r / 6.0))
                glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                draw_heart(glow_surf, size * 2, size * 2, size + glow_r * 3,
                           color=(255, 80, 80, glow_alpha),
                           outline_color=(255, 80, 80, glow_alpha))
                glow_surf.set_alpha(glow_alpha * 4)
                screen.blit(glow_surf, (cx - size * 2, cy - size * 2))
            # Solid heart
            draw_heart(screen, cx, cy, size,
                       color=(255, 50, 80),
                       outline_color=(255, 180, 190))
            # Shine sparkle
            shine_x = cx - int(size * 0.3)
            shine_y = cy - int(size * 0.4)
            shine_r = max(2, int(size * 0.18))
            pygame.draw.circle(screen, (255, 255, 255), (shine_x, shine_y), shine_r)

        else:
            # ── Golden star ──
            points = []
            for i in range(10):
                angle_pt = math.radians(-90 + i * 36) + self.pulse_time * 0.8
                r = size if i % 2 == 0 else size * 0.42
                points.append((int(cx + r * math.cos(angle_pt)), int(cy + r * math.sin(angle_pt))))
            # Glow
            for glow_r in range(5, 0, -1):
                g_alpha = int(50 * (1 - glow_r / 5.0))
                glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                g_pts = []
                for i in range(10):
                    angle_pt = math.radians(-90 + i * 36) + self.pulse_time * 0.8
                    r = (size + glow_r * 3) if i % 2 == 0 else (size + glow_r) * 0.42
                    g_pts.append((int(size * 2 + r * math.cos(angle_pt)), int(size * 2 + r * math.sin(angle_pt))))
                pygame.draw.polygon(glow_surf, (255, 230, 0, g_alpha), g_pts)
                glow_surf.set_alpha(g_alpha * 4)
                screen.blit(glow_surf, (cx - size * 2, cy - size * 2))
            pygame.draw.polygon(screen, (255, 220, 0), points)
            inner_pts = []
            for i in range(10):
                angle_pt = math.radians(-90 + i * 36) + self.pulse_time * 0.8
                r = size * 0.55 if i % 2 == 0 else size * 0.22
                inner_pts.append((int(cx + r * math.cos(angle_pt)), int(cy + r * math.sin(angle_pt))))
            pygame.draw.polygon(screen, (255, 255, 160), inner_pts)
            pygame.draw.polygon(screen, (255, 180, 0), points, 2)


# ─────────────────────────────────────────────────────────────────────────────
# FLOATING SCORE
# ─────────────────────────────────────────────────────────────────────────────

class FloatingScore:
    def __init__(self, x, y, score, color, accent_color):
        self.x = x
        self.y = y
        self.score = score
        self.color = color
        self.accent_color = accent_color
        self.lifetime = 1.0
        self.elapsed = 0.0
        self.font = pygame.font.Font(None, 48)

    def update(self, delta_time):
        self.elapsed += delta_time
        self.y -= 55 * delta_time
        return self.elapsed < self.lifetime

    def draw(self, screen):
        progress = min(1.0, self.elapsed / self.lifetime)
        alpha = int(255 * (1 - progress))
        text = f"+{int(self.score)}"
        font = get_font(52)
        # Shadow
        sh = font.render(text, True, (0, 0, 0))
        sh.set_alpha(alpha // 2)
        screen.blit(sh, (int(self.x - sh.get_width() // 2) + 2, int(self.y) + 2))
        # Main text
        text_surf = font.render(text, True, self.accent_color)
        text_surf.set_alpha(alpha)
        screen.blit(text_surf, (int(self.x - text_surf.get_width() // 2), int(self.y)))


# ─────────────────────────────────────────────────────────────────────────────
# IN-GAME BIRD DRAWING (using the unified draw_bird_shape)
# ─────────────────────────────────────────────────────────────────────────────

def draw_bird_direct(screen, bird, bird_color):
    """Draw the bird using the same renderer as the shop – consistent look."""
    cx = bird.rect.centerx
    cy = bird.rect.centery
    angle = min(max(-bird.speed * 2, -25), 80)
    wing_frame = bird.current_image % 4
    draw_bird_shape(screen, cx, cy, bird_color, wing_frame=wing_frame, angle_deg=angle, scale=1.2)


# ─────────────────────────────────────────────────────────────────────────────
# SPRITE CLASSES
# ─────────────────────────────────────────────────────────────────────────────

class Bird(pygame.sprite.Sprite):
    def __init__(self, images):
        pygame.sprite.Sprite.__init__(self)
        self.images = images
        self.speed = SPEED
        self.current_image = 0
        self.image = self.images[0]
        self.rotated_image = self.image
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2
        self.center_pos = (self.rect.centerx, self.rect.centery)
        self.immunity_time = 0.0
        self.double_score_time = 0.0
        self.score_multiplier = 1.0

    def update(self):
        self.current_image = (self.current_image + 1) % 4
        base_image = self.images[self.current_image]
        self.speed += GRAVITY
        self.center_pos = (self.center_pos[0], self.center_pos[1] + self.speed)
        angle = min(max(-self.speed * 2, -25), 80)
        self.rotated_image = pygame.transform.rotate(base_image, -angle)
        self.rect = self.rotated_image.get_rect(center=self.center_pos)
        self.mask = pygame.mask.from_surface(self.rotated_image)
        self.image = base_image

    def bump(self):
        self.speed = -SPEED
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
            self.rect[1] = -(self.rect[3] - ysize)
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


# ─────────────────────────────────────────────────────────────────────────────
# INIT & THEME
# ─────────────────────────────────────────────────────────────────────────────

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))
pygame.display.set_caption('Flappy Bird')


def tint(surface, color):
    surf = surface.copy()
    surf.fill(color, special_flags=pygame.BLEND_MULT)
    return surf


def draw_midnight_background(screen):
    screen.fill((10, 10, 30))
    random.seed(42)
    for _ in range(120):
        star_x = random.randint(0, SCREEN_WIDHT)
        star_y = random.randint(0, int(SCREEN_HEIGHT * 0.72))
        star_size = random.randint(1, 3)
        brightness = random.randint(150, 255)
        pygame.draw.circle(screen, (brightness, brightness, brightness), (star_x, star_y), star_size)
    moon_x = int(SCREEN_WIDHT * 0.85)
    moon_y = int(SCREEN_HEIGHT * 0.20)
    moon_radius = 40
    pygame.draw.circle(screen, (240, 240, 200), (moon_x, moon_y), moon_radius)
    pygame.draw.circle(screen, (180, 180, 140), (moon_x + 15, moon_y - 10), 12)
    pygame.draw.circle(screen, (180, 180, 140), (moon_x - 20, moon_y + 15), 8)
    pygame.draw.circle(screen, (180, 180, 140), (moon_x + 5, moon_y + 20), 6)


def draw_background(screen, theme_name=None):
    if theme_name == "midnight":
        draw_midnight_background(screen)
    else:
        screen.blit(BACKGROUND, (0, 0))


def load_base_images():
    return {'bird_color': (255, 200, 0), 'pipe_color': (34, 139, 34), 'ground_color': (139, 69, 19)}


def apply_theme(base):
    global BACKGROUND, BEGIN_IMAGE, pipe_img, ground_img
    theme = THEMES[current_theme]
    BACKGROUND = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        progress = y / SCREEN_HEIGHT
        color = tuple(int(theme['bg'][i] * (1 - progress * 0.4)) for i in range(3))
        pygame.draw.line(BACKGROUND, color, (0, y), (SCREEN_WIDHT, y))
    cloud_surf = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT), pygame.SRCALPHA)
    for i in range(3):
        cloud_y = SCREEN_HEIGHT * (0.2 + i * 0.2)
        cloud_x = SCREEN_WIDHT * 0.1
        cloud_color = tuple(int(c * 0.1) for c in theme['accent'])
        pygame.draw.circle(cloud_surf, (*cloud_color, 30), (int(cloud_x), int(cloud_y)), 60)
        pygame.draw.circle(cloud_surf, (*cloud_color, 30), (int(cloud_x + 80), int(cloud_y)), 50)
        pygame.draw.circle(cloud_surf, (*cloud_color, 20), (int(cloud_x + 160), int(cloud_y)), 40)
    BACKGROUND.blit(cloud_surf, (0, 0))
    BEGIN_IMAGE = pygame.Surface((200, 100), pygame.SRCALPHA)
    bird_imgs = create_bird_graphics(theme['bird'])
    pipe_img = create_mario_pipe(theme['pipe'])
    ground_img = create_ground_graphics(theme['ground'])
    return bird_imgs, pipe_img, ground_img, theme['text'], theme['accent'], theme['shadow'], theme['dark']


# ─────────────────────────────────────────────────────────────────────────────
# GUI HELPERS  (improved)
# ─────────────────────────────────────────────────────────────────────────────

_font_cache = {}

def get_font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]


def draw_text_with_shadow(text, size, color, shadow_color, x, y, offset=3):
    font = get_font(size)
    # Crisp multi-layer drop shadow - no background box
    for i in range(offset, 0, -1):
        alpha_shadow = int(200 * (i / offset))
        shadow_surf = font.render(text, True, shadow_color)
        shadow_surf.set_alpha(alpha_shadow)
        screen.blit(shadow_surf, (x + i, y + i))
    text_surf = font.render(text, True, color)
    screen.blit(text_surf, (x, y))


def draw_glowing_box(x, y, width, height, color, glow_color, border_width=3):
    # Deep drop shadow
    shadow_surface = pygame.Surface((width + 20, height + 20), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (0, 0, 0, 100), (5, 7, width + 10, height + 10), border_radius=14)
    screen.blit(shadow_surface, (x - 8, y + 5))
    # Soft outer glow rings
    for i in range(border_width + 6, 0, -1):
        alpha = int(140 * (1 - i / (border_width + 6)) * 0.4)
        glow_surf = pygame.Surface((width + i*2 + 6, height + i*2 + 6), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*glow_color, alpha),
                         (0, 0, width + i*2 + 6, height + i*2 + 6), border_radius=16)
        screen.blit(glow_surf, (x - i - 3, y - i - 3))
    # Glass body — use draw.rect so corners are transparent (not fill which ignores border_radius)
    glass_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    r, g, b = color[0], color[1], color[2]
    pygame.draw.rect(glass_surf, (r, g, b, 210), (0, 0, width, height), border_radius=12)
    # Top glass-sheen highlight
    hi_h = max(3, height // 4)
    hi_surf = pygame.Surface((width - 6, hi_h), pygame.SRCALPHA)
    pygame.draw.rect(hi_surf, (min(255,r+80), min(255,g+80), min(255,b+80), 65),
                     (0, 0, width - 6, hi_h), border_radius=6)
    glass_surf.blit(hi_surf, (3, 3))
    # Bottom shadow band
    sh_h = max(2, height // 10)
    sh_surf = pygame.Surface((width - 6, sh_h), pygame.SRCALPHA)
    pygame.draw.rect(sh_surf, (0, 0, 0, 45), (0, 0, width - 6, sh_h), border_radius=4)
    glass_surf.blit(sh_surf, (3, height - sh_h - 2))
    screen.blit(glass_surf, (x, y))
    # Outer border + inner bright rim
    pygame.draw.rect(screen, glow_color, (x, y, width, height), border_width, border_radius=12)
    light_edge = tuple(min(255, c + 90) for c in glow_color)
    pygame.draw.rect(screen, light_edge, (x + 1, y + 1, width - 2, height - 2), 1, border_radius=11)


def draw_button(x, y, width, height, text, color, text_color, glow_color, is_hovered=False):
    scale_offset = 5 if is_hovered else 0
    sx, sy = x - scale_offset, y - scale_offset
    sw, sh = width + scale_offset * 2, height + scale_offset * 2
    draw_glowing_box(sx, sy, sw, sh, color, glow_color, 5 if is_hovered else 2)
    font_size = 50 if is_hovered else 44
    font = get_font(font_size)
    # Text glow on hover
    if is_hovered:
        for goff in [4, 2]:
            gsurf = font.render(text, True, glow_color)
            gsurf.set_alpha(60)
            gr = gsurf.get_rect(center=(x + width // 2 + goff, y + height // 2 + goff))
            screen.blit(gsurf, gr)
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
    # Drop shadow on text
    shadow_surf = font.render(text, True, (0, 0, 0))
    shadow_surf.set_alpha(160)
    screen.blit(shadow_surf, text_rect.move(3, 3))
    screen.blit(text_surf, text_rect)


def draw_title_box(title, subtitle, theme_data):
    # Top accent bar
    bar_w = SCREEN_WIDHT - 80
    for i in range(6):
        alpha = int(255 * (1 - i / 6.0))
        bar_surf = pygame.Surface((bar_w, max(1, 4 - min(i, 2))), pygame.SRCALPHA)
        bar_surf.fill((*theme_data['accent'], alpha))
        screen.blit(bar_surf, (40, 8 + i))

    title_font = get_font(76)
    tw, th = title_font.size(title)
    title_x = SCREEN_WIDHT // 2 - tw // 2

    # Dark semi-transparent backing pill so title is ALWAYS readable on any bg
    backing = pygame.Surface((tw + 40, th + 16), pygame.SRCALPHA)
    backing.fill((0, 0, 0, 110))
    pygame.draw.rect(backing, (0, 0, 0, 110), backing.get_rect(), border_radius=14)
    screen.blit(backing, (title_x - 20, 12))

    # Black stroke outline (render offset in all 4 directions)
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
        stroke = title_font.render(title, True, (0, 0, 0))
        stroke.set_alpha(180)
        screen.blit(stroke, (title_x + dx, 18 + dy))

    # Main title in accent color
    title_surf = title_font.render(title, True, theme_data['accent'])
    screen.blit(title_surf, (title_x, 18))

    # Decorative ruled line with jewel endcaps
    line_y = 100
    pygame.draw.line(screen, theme_data['accent'], (80, line_y), (SCREEN_WIDHT - 80, line_y), 3)
    pygame.draw.line(screen, theme_data['accent'], (80, line_y + 5), (SCREEN_WIDHT - 80, line_y + 5), 1)
    accent_bright = tuple(min(255, c + 80) for c in theme_data['accent'])
    for ex, ey in [(80, line_y), (SCREEN_WIDHT - 80, line_y)]:
        pygame.draw.circle(screen, accent_bright, (ex, ey), 6)
        pygame.draw.circle(screen, (255, 255, 255), (ex, ey), 3)

    if subtitle:
        sf = get_font(30)
        sw2 = sf.size(subtitle)[0]
        sx = SCREEN_WIDHT // 2 - sw2 // 2
        for dx, dy in [(-1,1),(1,1),(0,2)]:
            sh_s = sf.render(subtitle, True, (0, 0, 0))
            sh_s.set_alpha(160)
            screen.blit(sh_s, (sx + dx, 68 + dy))
        screen.blit(sf.render(subtitle, True, theme_data['text']), (sx, 68))


# ─────────────────────────────────────────────────────────────────────────────
# HUD  (in-game score panel)
# ─────────────────────────────────────────────────────────────────────────────

def draw_pill(x, y, w, h, fill_color, border_color, alpha=210):
    """Draw a rounded pill/badge directly to the screen."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    r, g, b = fill_color[0], fill_color[1], fill_color[2]
    pygame.draw.rect(surf, (r, g, b, alpha), (0, 0, w, h), border_radius=h // 2)
    # Gloss sheen
    hi_surf = pygame.Surface((w - 10, h // 3), pygame.SRCALPHA)
    hi_surf.fill((255, 255, 255, 40))
    pygame.draw.rect(hi_surf, (255, 255, 255, 40), hi_surf.get_rect(), border_radius=h // 4)
    surf.blit(hi_surf, (5, 4))
    screen.blit(surf, (x, y))
    pygame.draw.rect(screen, border_color, (x, y, w, h), 2, border_radius=h // 2)


def draw_hud(screen, score, total_coins, bird, dark_color, accent_color, shadow_color, text_color):
    """Draw a polished in-game HUD with pill-badges — no black boxes."""
    font_big = get_font(46)
    font_sm = get_font(30)

    # ── Score badge ──
    score_str = f"  {score}"
    sw = font_big.size(score_str)[0] + 56
    draw_pill(10, 10, sw, 48, dark_color, accent_color, 210)
    # Star icon
    star_pts = [(int(34 + 10*math.cos(math.radians(-90 + i*36))),
                 int(34 + 10*math.sin(math.radians(-90 + i*36))))
                if i % 2 == 0 else
                (int(34 + 5*math.cos(math.radians(-90 + i*36))),
                 int(34 + 5*math.sin(math.radians(-90 + i*36))))
                for i in range(10)]
    pygame.draw.polygon(screen, (255, 220, 0), star_pts)
    sc_surf = font_big.render(score_str, True, accent_color)
    screen.blit(sc_surf, (46, 14))

    # ── Coins badge ──
    coin_str = f"  {total_coins}"
    cw = font_sm.size(coin_str)[0] + 46
    draw_pill(10, 65, cw, 38, dark_color, (200, 160, 0), 200)
    draw_heart(screen, 29, 84, 9, color=(255, 215, 0), outline_color=(200, 160, 0))
    c_surf = font_sm.render(coin_str, True, (255, 215, 0))
    screen.blit(c_surf, (38, 71))

    # ── Powerup pill badges ──
    py = 112
    if bird.immunity_time > 0:
        frac = min(1.0, bird.immunity_time / 5.0)
        draw_pill(10, py, 230, 52, (160, 20, 40), (255, 80, 110), 220)
        draw_heart(screen, 32, py + 14, 11, color=(255, 60, 90), outline_color=(255, 180, 190))
        im_surf = font_sm.render(f"IMMUNE  {bird.immunity_time:.1f}s", True, (255, 220, 225))
        screen.blit(im_surf, (50, py + 12))
        # Thin progress bar at bottom of pill
        pygame.draw.rect(screen, (80, 10, 20), (18, py + 44, 206, 4), border_radius=2)
        pygame.draw.rect(screen, (255, 100, 130), (18, py + 44, int(206 * frac), 4), border_radius=2)
        py += 62

    if bird.double_score_time > 0:
        frac = min(1.0, bird.double_score_time / 5.0)
        draw_pill(10, py, 230, 52, (120, 100, 0), (255, 240, 0), 220)
        # Mini star icon
        sp = [(int(30 + (8 if i%2==0 else 4)*math.cos(math.radians(-90+i*36))),
               int(py+14 + (8 if i%2==0 else 4)*math.sin(math.radians(-90+i*36))))
              for i in range(10)]
        pygame.draw.polygon(screen, (255, 240, 0), sp)
        ds_surf = font_sm.render(f"2x SCORE  {bird.double_score_time:.1f}s", True, (255, 255, 160))
        screen.blit(ds_surf, (50, py + 12))
        pygame.draw.rect(screen, (80, 70, 0), (18, py + 44, 206, 4), border_radius=2)
        pygame.draw.rect(screen, (255, 240, 0), (18, py + 44, int(206 * frac), 4), border_radius=2)


# ─────────────────────────────────────────────────────────────────────────────
# MENUS
# ─────────────────────────────────────────────────────────────────────────────

base_images = load_base_images()
bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)

score = 0
high_score = 0
scored_pairs = set()

clock = pygame.time.Clock()


def show_how_to_play():
    showing_help = True
    while showing_help:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        help_bg = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT - 100), pygame.SRCALPHA)
        help_bg.fill((0, 0, 0, 80))
        screen.blit(help_bg, (0, 100))
        draw_title_box('HOW TO PLAY', '', THEMES[current_theme])
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
            ("  HEART - Immunity 5s (vs pipes)", (255, 80, 100), 24),
            ("  STAR  - 2x Score 5s", (255, 215, 0), 24),
            ("", text_color, 24),
            ("BIRD SKINS:", accent_color, 28),
            ("  Buy with coins", text_color, 24),
            ("  Premium/Legendary = more boost", text_color, 24),
        ]
        current_y = 130
        for line_text, line_color, line_size in lines:
            if line_text:
                if "HEART" in line_text:
                    draw_heart(screen, 73, current_y + 8, 10, color=(255, 50, 80), outline_color=(255, 160, 160))
                    draw_text_with_shadow("  " + line_text, line_size, line_color, shadow_color, 76, current_y, offset=1)
                else:
                    draw_text_with_shadow(line_text, line_size, line_color, shadow_color, 60, current_y, offset=2)
            current_y += 32
        draw_text_with_shadow('SPACE or ESC: Back to Menu', 18, text_color, shadow_color, 20, SCREEN_HEIGHT - 40, offset=1)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key in (K_SPACE, K_ESCAPE):
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
        draw_pill(SCREEN_WIDHT - 250, 10, 235, 50, dark_color, (200, 160, 0), 210)
        draw_heart(screen, SCREEN_WIDHT - 232, 35, 11, color=(255, 215, 0), outline_color=(200, 150, 0))
        coin_font = get_font(34)
        cs = coin_font.render(f"  {total_coins} coins", True, (255, 215, 0))
        screen.blit(cs, (SCREEN_WIDHT - 220, 22))
        draw_title_box('FLAPPY BIRD', 'Press SPACE to Play', THEMES[current_theme])
        button_width = 240
        button_height = 70
        button_x = SCREEN_WIDHT // 2 - button_width // 2
        buttons = [
            (button_x, 180, "PLAY"),
            (button_x, 280, "SHOP"),
            (button_x, 380, "HOW TO PLAY"),
            (button_x, 480, "THEMES"),
            (button_x, 580, "QUIT"),
        ]
        for idx, (x, y, label) in enumerate(buttons):
            is_hovered = idx == selected_option
            draw_button(x, y, button_width, button_height, label, dark_color,
                        accent_color if is_hovered else text_color, accent_color, is_hovered)
        draw_text_with_shadow('UP/DOWN: Select | SPACE/CLICK: Confirm', 18, text_color, shadow_color,
                              10, SCREEN_HEIGHT - 40, offset=1)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    selected_option = (selected_option - 1) % len(buttons)
                    play_beep(600, 100)
                elif event.key == K_DOWN:
                    selected_option = (selected_option + 1) % len(buttons)
                    play_beep(500, 100)
                elif event.key == K_SPACE:
                    if selected_option == 0: play_beep(800, 150); return "play"
                    elif selected_option == 1: play_beep(800, 150); show_shop_menu()
                    elif selected_option == 2: play_beep(800, 150); show_how_to_play()
                    elif selected_option == 3: play_beep(800, 150); show_theme_menu()
                    elif selected_option == 4: play_beep(400, 200); pygame.quit(); sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                play_beep(800, 150); return "play"
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
            y_pos = 150 + i * 65
            is_selected = i == selected_theme
            if is_selected:
                draw_glowing_box(SCREEN_WIDHT // 2 - 130, y_pos - 8, 260, 55, theme['dark'], theme['accent'], 3)
                color = theme['accent']
            else:
                pygame.draw.rect(screen, theme['dark'], (SCREEN_WIDHT // 2 - 130, y_pos - 8, 260, 55), border_radius=8)
                pygame.draw.rect(screen, theme['accent'], (SCREEN_WIDHT // 2 - 130, y_pos - 8, 260, 55), 2, border_radius=8)
                color = theme['text']
            draw_text_with_shadow(theme['name'].upper(), 30, color, theme['shadow'],
                                  SCREEN_WIDHT // 2 - 80, y_pos + 6, offset=2)
        draw_text_with_shadow('UP/DOWN: Select | SPACE: Confirm | ESC: Back', 16, text_color,
                              shadow_color, 10, SCREEN_HEIGHT - 40, offset=1)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP: selected_theme = (selected_theme - 1) % len(THEMES); play_beep(600, 100)
                elif event.key == K_DOWN: selected_theme = (selected_theme + 1) % len(THEMES); play_beep(500, 100)
                elif event.key == K_SPACE:
                    current_theme = selected_theme
                    bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)
                    play_beep(800, 150); theme_menu_running = False
                elif event.key == K_ESCAPE:
                    play_beep(400, 100); theme_menu_running = False
        pygame.display.update()


def show_shop_menu():
    global total_coins, owned_bird_skins, text_color, accent_color, shadow_color, dark_color
    shop_running = True
    selected_skin = 0
    while shop_running:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        draw_title_box('BIRD SHOP', '', THEMES[current_theme])
        # Coins pill top-right
        draw_pill(SCREEN_WIDHT - 250, 10, 235, 50, dark_color, (200, 160, 0), 210)
        draw_heart(screen, SCREEN_WIDHT - 232, 35, 11, color=(255, 215, 0), outline_color=(200, 150, 0))
        cf = get_font(34)
        screen.blit(cf.render(f"  {total_coins} coins", True, (255, 215, 0)), (SCREEN_WIDHT - 220, 22))
        skins_per_screen = 4
        start_idx = (selected_skin // skins_per_screen) * skins_per_screen
        visible_skins = BIRD_SKINS[start_idx:start_idx + skins_per_screen]
        for i, skin_data in enumerate(visible_skins):
            actual_idx = start_idx + i
            skin_name, color, cost, powerup_boost, is_premium, is_legendary = skin_data
            y_pos = 130 + i * 140
            is_selected = actual_idx == selected_skin
            is_owned = actual_idx in owned_bird_skins
            box_color = tuple(min(255, c + 30) for c in dark_color) if is_selected else dark_color
            border_color = (255, 215, 0) if is_legendary else (accent_color if is_selected else shadow_color)
            draw_glowing_box(60, y_pos, 1080, 128, box_color, border_color, 5 if is_selected else 2)
            # Bird preview using unified renderer
            preview_surf = pygame.Surface((90, 80), pygame.SRCALPHA)
            preview_surf.fill((0, 0, 0, 0))
            draw_bird_shape(preview_surf, 45, 40, color, wing_frame=1, angle_deg=0, scale=1.4)
            screen.blit(preview_surf, (80, y_pos + 24))
            tag = ""
            tag_color = accent_color
            if is_legendary: tag = " ★ LEGENDARY"; tag_color = (255, 215, 0)
            elif is_premium: tag = " ♦ PREMIUM"; tag_color = (218, 165, 32)
            draw_text_with_shadow(skin_name + tag, 30, tag_color if tag else accent_color, shadow_color, 200, y_pos + 18, offset=2)
            draw_text_with_shadow(f"Boost: +{int((powerup_boost - 1) * 100)}%", 22, text_color, shadow_color, 200, y_pos + 56, offset=1)
            if is_owned:
                draw_text_with_shadow("✓ OWNED", 36, (60, 220, 60), shadow_color, 950, y_pos + 44, offset=2)
            else:
                cost_color = (255, 70, 70) if is_legendary else (255, 215, 0)
                draw_text_with_shadow(f"🪙 {cost}", 30, cost_color, shadow_color, 960, y_pos + 47, offset=2)
        # Page indicator
        total_pages = (len(BIRD_SKINS) + skins_per_screen - 1) // skins_per_screen
        cur_page = selected_skin // skins_per_screen + 1
        draw_text_with_shadow(f'Page {cur_page}/{total_pages}', 22, text_color, shadow_color,
                              SCREEN_WIDHT // 2 - 40, SCREEN_HEIGHT - 70, offset=1)
        draw_text_with_shadow('UP/DOWN: Select | SPACE: Buy | ESC: Back', 18, text_color, shadow_color,
                              20, SCREEN_HEIGHT - 40, offset=1)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP: selected_skin = (selected_skin - 1) % len(BIRD_SKINS); play_beep(600, 100)
                elif event.key == K_DOWN: selected_skin = (selected_skin + 1) % len(BIRD_SKINS); play_beep(500, 100)
                elif event.key == K_SPACE:
                    skin_data = BIRD_SKINS[selected_skin]
                    cost = skin_data[2]
                    is_legendary = skin_data[5]
                    if selected_skin not in owned_bird_skins:
                        if total_coins >= cost:
                            total_coins -= cost
                            owned_bird_skins.add(selected_skin)
                            if is_legendary: playVictorySound()
                            else: play_beep(800, 200)
                    else:
                        play_beep(400, 100)
                elif event.key == K_ESCAPE:
                    shop_running = False
        pygame.display.update()


def playVictorySound():
    if victory: play(victory)
    else:
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
            y_pos = 180 + i * 80
            is_selected = i == selected_diff_idx
            diff_colors = [(60, 200, 60), (255, 215, 0), (255, 120, 0), (220, 50, 50)]
            dc = diff_colors[i]
            if is_selected:
                draw_glowing_box(SCREEN_WIDHT // 2 - 120, y_pos - 10, 240, 65, dark_color, dc, 4)
                color = dc
            else:
                pygame.draw.rect(screen, dark_color, (SCREEN_WIDHT // 2 - 120, y_pos - 10, 240, 65), border_radius=8)
                pygame.draw.rect(screen, dc, (SCREEN_WIDHT // 2 - 120, y_pos - 10, 240, 65), 2, border_radius=8)
                color = text_color
            draw_text_with_shadow(diff_name.upper(), 34, color, shadow_color, SCREEN_WIDHT // 2 - 70, y_pos + 8, offset=2)
        draw_text_with_shadow('UP/DOWN: Select | SPACE/CLICK: Start', 16, text_color, shadow_color, 20, SCREEN_HEIGHT - 40, offset=1)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP: selected_diff_idx = (selected_diff_idx - 1) % len(DIFFICULTIES); play_beep(600, 100)
                elif event.key == K_DOWN: selected_diff_idx = (selected_diff_idx + 1) % len(DIFFICULTIES); play_beep(500, 100)
                elif event.key == K_SPACE: play_beep(800, 150); selecting_difficulty = False
            if event.type == MOUSEBUTTONDOWN:
                play_beep(800, 150); selecting_difficulty = False
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
        owned_birds = sorted(list(owned_bird_skins))
        for display_idx, bird_idx in enumerate(owned_birds):
            skin_name, color, cost, powerup_boost, is_premium, is_legendary = BIRD_SKINS[bird_idx]
            y_pos = 150 + display_idx * 120
            is_selected = display_idx == selected_bird_idx
            if is_selected:
                draw_glowing_box(150, y_pos, 900, 105, dark_color, accent_color, 4)
                color_text = accent_color
            else:
                pygame.draw.rect(screen, dark_color, (150, y_pos, 900, 105), border_radius=8)
                pygame.draw.rect(screen, accent_color, (150, y_pos, 900, 105), 2, border_radius=8)
                color_text = text_color
            # Preview using unified renderer
            preview_surf = pygame.Surface((90, 80), pygame.SRCALPHA)
            preview_surf.fill((0, 0, 0, 0))
            draw_bird_shape(preview_surf, 45, 40, color, wing_frame=display_idx % 4, angle_deg=0, scale=1.4)
            screen.blit(preview_surf, (175, y_pos + 12))
            tag = ""
            tag_color = color_text
            if is_legendary: tag = " ★"; tag_color = (255, 215, 0)
            elif is_premium: tag = " ♦"; tag_color = (218, 165, 32)
            draw_text_with_shadow(skin_name + tag, 36, tag_color, shadow_color, 290, y_pos + 14, offset=2)
            draw_text_with_shadow(f'Boost: +{int((powerup_boost - 1) * 100)}%', 24, (255, 215, 0), shadow_color, 290, y_pos + 58, offset=1)
        draw_text_with_shadow('UP/DOWN: Select | SPACE/CLICK: Confirm', 18, text_color, shadow_color,
                              20, SCREEN_HEIGHT - 40, offset=1)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP: selected_bird_idx = (selected_bird_idx - 1) % len(owned_birds); play_beep(600, 100)
                elif event.key == K_DOWN: selected_bird_idx = (selected_bird_idx + 1) % len(owned_birds); play_beep(500, 100)
                elif event.key == K_SPACE: selecting_bird = False
            if event.type == MOUSEBUTTONDOWN:
                selecting_bird = False
        pygame.display.update()
    return owned_birds[selected_bird_idx]


def show_game_over_menu(final_score, final_high_score, coins_earned=0, total_coins=0):
    global current_theme, bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color
    game_over_running = True
    selected_option = 0
    is_new_best = final_score >= final_high_score and final_score > 0
    while game_over_running:
        clock.tick(60)
        screen.blit(BACKGROUND, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT))
        overlay.set_alpha(130)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        panel_w, panel_h = 500, 620
        panel_x = SCREEN_WIDHT // 2 - panel_w // 2
        draw_glowing_box(panel_x, 15, panel_w, panel_h, dark_color, accent_color, 6)
        go_color = (255, 80, 80) if not is_new_best else (255, 215, 0)
        draw_text_with_shadow('GAME OVER', 68, go_color, shadow_color, panel_x + 60, 35, offset=4)
        if is_new_best:
            draw_text_with_shadow('★ NEW BEST! ★', 34, (255, 215, 0), shadow_color, panel_x + 100, 115, offset=2)
        draw_text_with_shadow(f'Score:     {final_score}', 44, text_color, shadow_color, panel_x + 50, 160, offset=2)
        draw_text_with_shadow(f'Best:      {final_high_score}', 40, (255, 215, 0), shadow_color, panel_x + 50, 218, offset=2)
        draw_text_with_shadow(f'+ {coins_earned} coins earned', 36, (100, 255, 100), shadow_color, panel_x + 50, 280, offset=2)
        draw_text_with_shadow(f'Total:     {total_coins} coins', 36, (255, 215, 0), shadow_color, panel_x + 50, 330, offset=2)
        # Divider
        pygame.draw.line(screen, accent_color, (panel_x + 30, 385), (panel_x + panel_w - 30, 385), 2)
        button_width, button_height = 360, 80
        button_x = panel_x + (panel_w - button_width) // 2
        buttons = [(button_x, 400, "PLAY AGAIN"), (button_x, 500, "MAIN MENU")]
        for idx, (x, y, label) in enumerate(buttons):
            is_hovered = idx == selected_option
            draw_button(x, y, button_width, button_height, label, dark_color,
                        accent_color if is_hovered else text_color, accent_color, is_hovered)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP: selected_option = (selected_option - 1) % len(buttons); play_beep(600, 100)
                elif event.key == K_DOWN: selected_option = (selected_option + 1) % len(buttons); play_beep(500, 100)
                elif event.key == K_SPACE: play_beep(800, 150); return selected_option
            if event.type == MOUSEBUTTONDOWN:
                play_beep(800, 150); return 0
        pygame.display.update()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GAME LOOP
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    while True:
        menu_result = show_main_menu()
        current_difficulty = show_difficulty_selector()
        selected_bird_skin_idx = show_bird_selector()

        _, GAME_SPEED, GRAVITY, PIPE_GAP = DIFFICULTIES[current_difficulty]

        skin_data = BIRD_SKINS[selected_bird_skin_idx]
        skin_name, bird_color, cost, powerup_boost, _, _ = skin_data
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
                        pygame.quit(); sys.exit()
                    if event.type == KEYDOWN:
                        if event.key in (K_SPACE, K_UP):
                            bird.bump(); play(wing); begin = False
                        elif event.key == K_t:
                            current_theme = (current_theme + 1) % len(THEMES)
                            bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)
                            bird = Bird(bird_imgs); bird_group.empty(); bird_group.add(bird)
                            ground_group.empty()
                            for i in range(2): ground_group.add(Ground(GROUND_WIDHT * i, ground_img))
                    if event.type == MOUSEBUTTONDOWN and event.button == 1:
                        bird.bump(); play(wing); begin = False

                draw_background(screen, THEMES[current_theme]["name"])
                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])
                    ground_group.add(Ground(GROUND_WIDHT - 20, ground_img))
                bird.begin()
                ground_group.update()
                draw_bird_direct(screen, bird, bird_color)
                ground_group.draw(screen)
                draw_text_with_shadow('GET READY!', 52, accent_color, shadow_color,
                                      SCREEN_WIDHT // 2 - 120, 150, offset=3)
                # Show selected bird name during get-ready
                draw_text_with_shadow(f'Bird: {skin_name}', 28, text_color, shadow_color,
                                      SCREEN_WIDHT // 2 - 80, 220, offset=2)
                pygame.display.update()

            playing = True
            floating_scores = []
            delta_time = 1 / 60.0
            powerup_group = pygame.sprite.Group()
            powerup_spawn_counter = 0
            powerup_spawn_rate = int(200 / powerup_boost)

            while playing:
                clock.tick(60)
                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit(); sys.exit()
                    if event.type == KEYDOWN:
                        if event.key in (K_SPACE, K_UP):
                            bird.bump(); play(wing)
                        elif event.key == K_t:
                            current_theme = (current_theme + 1) % len(THEMES)
                            bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme(base_images)
                    if event.type == MOUSEBUTTONDOWN and event.button == 1:
                        bird.bump(); play(wing)

                draw_background(screen, THEMES[current_theme]["name"])

                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])
                    ground_group.add(Ground(GROUND_WIDHT - 20, ground_img))

                if is_off_screen(pipe_group.sprites()[0]):
                    offscreen_pipes = [p for p in pipe_group.sprites() if is_off_screen(p)]
                    for p in offscreen_pipes:
                        pipe_group.remove(p)
                    if len(pipe_group) > 0:
                        rightmost_x = max(pipe.rect.x for pipe in pipe_group)
                    else:
                        rightmost_x = SCREEN_WIDHT
                    pipes = get_random_pipes(rightmost_x + PIPE_SPACING, pipe_pair_id)
                    pipe_pair_id += 1
                    pipe_group.add(pipes[0]); pipe_group.add(pipes[1])

                bird_group.update()
                ground_group.update()
                pipe_group.update()

                bird.immunity_time = max(0, bird.immunity_time - delta_time)
                bird.double_score_time = max(0, bird.double_score_time - delta_time)
                bird.score_multiplier = 2.0 if bird.double_score_time > 0 else 1.0

                powerup_spawn_counter += 1
                if powerup_spawn_counter > powerup_spawn_rate:
                    powerup_spawn_counter = 0
                    powerup_type = random.choice([Powerup.IMMUNITY, Powerup.DOUBLE_SCORE])
                    x = SCREEN_WIDHT + 150
                    y = random.randint(150, SCREEN_HEIGHT - 150)
                    powerup_group.add(Powerup(x, y, powerup_type, accent_color))

                powerups_to_remove = [p for p in powerup_group if not p.update(delta_time)]
                for p in powerups_to_remove: powerup_group.remove(p)

                powerup_collisions = pygame.sprite.groupcollide(bird_group, powerup_group, False, True, pygame.sprite.collide_rect)
                for bird_sprite in powerup_collisions:
                    for powerup in powerup_collisions[bird_sprite]:
                        if powerup.powerup_type == Powerup.IMMUNITY:
                            bird.immunity_time = 5.0
                        else:
                            bird.double_score_time = 5.0
                            score = int(score * 2)

                # Draw everything
                pipe_group.draw(screen)
                ground_group.draw(screen)

                # Draw bird with actual selected skin color
                draw_bird_direct(screen, bird, bird_color)

                # Draw powerups
                for powerup in powerup_group:
                    powerup.draw(screen)

                # Immunity shield visual around bird
                if bird.immunity_time > 0:
                    shield_pulse = int(3 * math.sin(pygame.time.get_ticks() / 80))
                    shield_surf = pygame.Surface((80 + shield_pulse * 2, 80 + shield_pulse * 2), pygame.SRCALPHA)
                    pygame.draw.ellipse(shield_surf, (100, 180, 255, 60),
                                        (0, 0, 80 + shield_pulse * 2, 80 + shield_pulse * 2))
                    pygame.draw.ellipse(shield_surf, (150, 220, 255, 120),
                                        (0, 0, 80 + shield_pulse * 2, 80 + shield_pulse * 2), 3)
                    screen.blit(shield_surf, (bird.rect.centerx - 40 - shield_pulse,
                                              bird.rect.centery - 40 - shield_pulse))

                # HUD
                draw_hud(screen, score, total_coins, bird, dark_color, accent_color, shadow_color, text_color)

                # Floating scores
                active_scores = []
                for fs in floating_scores:
                    if fs.update(delta_time):
                        active_scores.append(fs)
                        fs.draw(screen)
                floating_scores = active_scores

                pygame.display.update()

                # Collision detection — check EVERY frame before anything else clears sprites
                body_rect = pygame.Rect(bird.rect.centerx - 10, bird.rect.centery - 8, 20, 16)
                ground_collision = any(body_rect.colliderect(s.rect) for s in ground_group.sprites())
                pipe_collision = (
                    any(body_rect.colliderect(s.rect) for s in pipe_group.sprites())
                    and bird.immunity_time <= 0
                )
                ceiling_collision = bird.rect.top <= 5

                if ground_collision or pipe_collision or ceiling_collision:
                    play(hit)
                    coins_earned_this_run = int(score)
                    total_coins += coins_earned_this_run
                    high_score = max(high_score, score)
                    # Non-blocking death pause — keep event loop alive
                    death_timer = 0
                    while death_timer < 35:
                        clock.tick(60)
                        death_timer += 1
                        for ev in pygame.event.get():
                            if ev.type == QUIT:
                                pygame.quit(); sys.exit()
                    playing = False
                    continue

                for pipe in pipe_group:
                    if pipe.pair_id not in scored_pairs and pipe.rect.right < bird.rect.left:
                        scored_pairs.add(pipe.pair_id)
                        score_increment = int(bird.score_multiplier)
                        score += score_increment
                        floating_scores.append(FloatingScore(pipe.rect.centerx, pipe.rect.centery,
                                                              score_increment, accent_color, accent_color))
                        play(wing)

            menu_choice = show_game_over_menu(score, high_score, coins_earned_this_run, total_coins)
            if menu_choice == 1:
                play_again = False