import pygame, random, time, os, sys, math
from pygame.locals import *

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ── Constants ─────────────────────────────────────────────────────────────────
SCREEN_W = 1200
SCREEN_H = 800
SPEED     = 10
GRAVITY   = 2.5
GAME_SPEED = 15

GROUND_W  = 2 * SCREEN_W
GROUND_H  = 100
PIPE_W    = 80
PIPE_H    = 500
PIPE_GAP  = 150
PIPE_SPACING = 400

DIFFICULTIES = [
    ("Easy",    5,  0.6, 180),
    ("Normal",  8,  0.9, 150),
    ("Hard",   12,  1.2, 120),
    ("Extreme",16,  1.6, 100),
]
current_difficulty = 1

# ── Procedural audio engine ──────────────────────────────────────────────────
# All sounds synthesised with numpy so the game needs zero audio asset files.
# Falls back silently if numpy/mixer unavailable.

_snd_cache = {}

def _make_wave(freq, dur_ms, wavetype='sine', vol=0.45, attack=0.08, decay=0.15):
    if not HAS_NUMPY: return None
    try:
        sr = 44100; n = int(sr * dur_ms / 1000)
        t = np.linspace(0, dur_ms/1000, n, endpoint=False)
        if wavetype == 'sine':    w = np.sin(2*np.pi*freq*t)
        elif wavetype == 'square': w = np.sign(np.sin(2*np.pi*freq*t))
        elif wavetype == 'saw':   w = 2*(t*freq % 1) - 1
        elif wavetype == 'noise': w = np.random.uniform(-1,1,n)
        elif wavetype == 'tri':
            w = 2*np.abs(2*(t*freq % 1)-1)-1
        else: w = np.sin(2*np.pi*freq*t)
        env = np.ones(n)
        att = int(n*attack); dec = int(n*decay)
        if att > 0: env[:att] = np.linspace(0,1,att)
        if dec > 0: env[-dec:] = np.linspace(1,0,dec)
        w = w * env * vol
        stereo = np.column_stack([w,w])
        return pygame.sndarray.make_sound((stereo*32767).astype(np.int16))
    except: return None

def _make_chord(freqs, dur_ms, wavetype='sine', vol=0.3):
    if not HAS_NUMPY: return None
    try:
        sr = 44100; n = int(sr*dur_ms/1000)
        t = np.linspace(0,dur_ms/1000,n,endpoint=False)
        w = sum(np.sin(2*np.pi*f*t) for f in freqs) / len(freqs)
        att = int(n*0.05); dec = int(n*0.2)
        env = np.ones(n)
        if att>0: env[:att] = np.linspace(0,1,att)
        if dec>0: env[-dec:] = np.linspace(1,0,dec)
        w = w*env*vol
        stereo = np.column_stack([w,w])
        return pygame.sndarray.make_sound((stereo*32767).astype(np.int16))
    except: return None

def _make_sweep(f1, f2, dur_ms, wavetype='sine', vol=0.4):
    if not HAS_NUMPY: return None
    try:
        sr=44100; n=int(sr*dur_ms/1000)
        t=np.linspace(0,dur_ms/1000,n,endpoint=False)
        freq_env=np.linspace(f1,f2,n)
        phase=np.cumsum(freq_env/sr)*2*np.pi
        w=np.sin(phase)
        att=int(n*0.05); dec=int(n*0.25)
        env=np.ones(n)
        if att>0: env[:att]=np.linspace(0,1,att)
        if dec>0: env[-dec:]=np.linspace(1,0,dec)
        w=w*env*vol
        stereo=np.column_stack([w,w])
        return pygame.sndarray.make_sound((stereo*32767).astype(np.int16))
    except: return None

def _play(snd):
    if snd is None: return
    try:
        ch = pygame.mixer.find_channel(True)
        if ch: ch.play(snd)
    except: pass

# ── Pre-build all sound effects ───────────────────────────────────────────────

def _build_sfx():
    sfx = {}
    # Flap: quick upward sweep
    sfx['flap'] = _make_sweep(300, 600, 80, 'sine', 0.35)
    # Hit: descending noise burst + low thud
    sfx['hit'] = _make_sweep(400, 80, 250, 'noise', 0.55)
    # Select / navigate: soft click
    sfx['select_up']   = _make_wave(660, 60, 'sine', 0.25, 0.02, 0.4)
    sfx['select_down'] = _make_wave(520, 60, 'sine', 0.25, 0.02, 0.4)
    # Confirm / buy
    sfx['confirm'] = _make_chord([523,659,784], 180, 'sine', 0.35)
    # Deny / can't afford
    sfx['deny'] = _make_sweep(300, 150, 120, 'square', 0.3)
    # Score point: tiny ping
    sfx['point'] = _make_wave(880, 55, 'sine', 0.22, 0.01, 0.5)
    # Power-up collect: ascending arp
    sfx['powerup'] = _make_sweep(440, 1100, 200, 'sine', 0.38)
    # Victory / legendary skin: fanfare chord
    sfx['victory'] = _make_chord([523,659,784,1047], 500, 'sine', 0.4)
    # Death jingle: descending minor arp
    sfx['death'] = _make_sweep(440, 180, 300, 'tri', 0.35)
    return sfx

_SFX = {}

def init_audio():
    global _SFX
    try:
        pygame.mixer.quit()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        _SFX = _build_sfx()
    except: pass

def play_sfx(name):
    _play(_SFX.get(name))

# ── Theme music: looping background tracks generated procedurally ─────────────
# Each theme has a characteristic melody / arpeggio pattern.
# Music plays in a background thread so it never blocks the game loop.

import threading

_music_thread = None
_music_stop = threading.Event()
_current_music_theme = [None]

_THEME_MUSIC = {
    # name: list of (freq, dur_ms, wavetype, vol) notes — loops continuously
    "classic": [  # cheerful major pentatonic
        (523,200,'sine',0.18),(659,200,'sine',0.18),(784,200,'sine',0.18),
        (1047,300,'sine',0.20),(784,200,'sine',0.16),(659,200,'sine',0.16),
        (523,400,'sine',0.18),(0,100,None,0),
        (440,150,'sine',0.14),(523,150,'sine',0.14),(659,300,'sine',0.16),(0,200,None,0),
    ],
    "neon": [  # synth arpeggios, square waves
        (220,100,'square',0.12),(330,100,'square',0.12),(440,100,'square',0.14),
        (660,200,'square',0.16),(440,100,'square',0.12),(330,100,'square',0.10),
        (220,300,'square',0.12),(0,80,None,0),
        (165,100,'square',0.10),(220,100,'square',0.12),(330,200,'square',0.14),(0,150,None,0),
    ],
    "cybercity": [  # driving techno pattern with saw waves
        (110,80,'saw',0.10),(220,80,'saw',0.12),(165,80,'saw',0.10),(330,160,'saw',0.14),
        (110,80,'saw',0.10),(220,80,'saw',0.12),(247,80,'saw',0.10),(440,160,'saw',0.14),
        (0,60,None,0),(196,80,'saw',0.12),(392,120,'saw',0.14),(0,80,None,0),
    ],
    "hell": [  # ominous tritone intervals, deep
        (110,300,'square',0.15),(155,300,'square',0.15),(0,100,None,0),
        (98,400,'square',0.18),(0,100,None,0),(146,200,'square',0.14),
        (110,600,'sine',0.12),(0,200,None,0),
    ],
    "forest": [  # gentle arpeggios, sine
        (392,250,'sine',0.14),(494,250,'sine',0.14),(587,250,'sine',0.16),
        (698,350,'sine',0.18),(587,250,'sine',0.14),(494,250,'sine',0.12),
        (392,500,'sine',0.14),(0,150,None,0),
        (330,200,'sine',0.12),(440,200,'sine',0.14),(523,300,'sine',0.14),(0,200,None,0),
    ],
    "ocean": [  # flowing waves feel, gentle tri
        (262,300,'tri',0.12),(330,300,'tri',0.14),(392,300,'tri',0.14),
        (523,400,'tri',0.16),(392,300,'tri',0.12),(330,200,'tri',0.10),
        (262,500,'tri',0.12),(0,200,None,0),
    ],
    "sunset": [  # warm jazz-ish, sine
        (349,300,'sine',0.16),(440,300,'sine',0.18),(523,300,'sine',0.18),
        (698,400,'sine',0.20),(523,300,'sine',0.16),(440,200,'sine',0.14),
        (349,600,'sine',0.16),(0,200,None,0),
    ],
    "midnight": [  # slow ambient minor, quiet sine
        (220,500,'sine',0.12),(277,500,'sine',0.12),(0,200,None,0),
        (185,600,'sine',0.10),(247,600,'sine',0.10),(0,300,None,0),
        (196,400,'sine',0.12),(0,400,None,0),
    ],
}

def _music_loop(theme_name):
    pattern = _THEME_MUSIC.get(theme_name, _THEME_MUSIC["classic"])
    idx = 0
    while not _music_stop.is_set():
        freq, dur, wtype, vol = pattern[idx % len(pattern)]
        idx += 1
        if freq > 0 and wtype and HAS_NUMPY:
            try:
                snd = _make_wave(freq, dur, wtype, vol, attack=0.06, decay=0.3)
                if snd:
                    ch = pygame.mixer.find_channel(True)
                    if ch:
                        ch.play(snd)
                        # wait for note duration, checking stop flag
                        wait_ms = 0
                        step = 20
                        while wait_ms < dur and not _music_stop.is_set():
                            import time as _time
                            _time.sleep(step/1000)
                            wait_ms += step
                    else:
                        import time as _time
                        _time.sleep(dur/1000)
                else:
                    import time as _time
                    _time.sleep(dur/1000)
            except:
                import time as _time
                _time.sleep(dur/1000)
        else:
            import time as _time
            _time.sleep(dur/1000)

def start_music(theme_name):
    global _music_thread, _music_stop
    if _current_music_theme[0] == theme_name and _music_thread and _music_thread.is_alive():
        return
    stop_music()
    _current_music_theme[0] = theme_name
    _music_stop = threading.Event()
    _music_thread = threading.Thread(target=_music_loop, args=(theme_name,), daemon=True)
    _music_thread.start()

def stop_music():
    global _music_thread
    _music_stop.set()
    if _music_thread:
        _music_thread.join(timeout=0.3)
        _music_thread = None
    _current_music_theme[0] = None

wing = None; hit = None; victory = None  # legacy compat – now unused

# ── Themes ────────────────────────────────────────────────────────────────────
# Each theme has a custom painted background — see draw_background()
# accent must contrast against its own bg for legibility
THEMES = [
    # name        bg-sky            pipe            bird           ground           text              accent            shadow           dark-panel
    {"name":"classic",   "bg":(100,185,240), "pipe":(34,139,34),   "bird":(255,200,0),  "ground":(80,160,60),  "text":(255,255,255),"accent":(255,220,0),  "shadow":(20,60,20),  "dark":(30,90,30)},
    {"name":"neon",      "bg":(5,0,20),      "pipe":(255,20,147),  "bird":(0,255,255),  "ground":(40,0,60),    "text":(200,255,255),"accent":(255,255,0),  "shadow":(80,0,80),   "dark":(20,0,40)},
    {"name":"cybercity", "bg":(8,8,40),      "pipe":(0,200,60),    "bird":(255,80,255), "ground":(30,30,50),   "text":(160,255,160),"accent":(255,80,255), "shadow":(60,0,60),   "dark":(15,15,45)},
    {"name":"hell",      "bg":(80,0,0),      "pipe":(180,20,0),    "bird":(255,100,0),  "ground":(60,10,0),    "text":(255,220,80), "accent":(255,80,0),   "shadow":(80,20,0),   "dark":(50,5,0)},
    {"name":"forest",    "bg":(60,120,50),   "pipe":(100,60,20),   "bird":(255,220,0),  "ground":(40,100,30),  "text":(240,255,200),"accent":(160,240,80), "shadow":(20,50,10),  "dark":(25,65,15)},
    {"name":"ocean",     "bg":(0,80,160),    "pipe":(0,120,180),   "bird":(255,240,0),  "ground":(190,150,100),"text":(220,255,255),"accent":(0,220,200),  "shadow":(0,40,80),   "dark":(0,50,110)},
    {"name":"sunset",    "bg":(220,100,30),  "pipe":(160,60,20),   "bird":(255,20,120), "ground":(120,60,20),  "text":(255,240,180),"accent":(255,200,0),  "shadow":(100,30,0),  "dark":(140,50,10)},
    {"name":"midnight",  "bg":(5,5,25),      "pipe":(60,60,120),   "bird":(0,220,255),  "ground":(20,20,45),   "text":(180,220,255),"accent":(100,180,255),"shadow":(20,20,80),  "dark":(8,8,35)},
]
current_theme = 0

BIRD_SKINS = [
    ("Classic Gold",    (255,200,0),    0,     1.0, False, False),
    ("Royal Blue",      (25,100,200),   500,   1.3, False, False),
    ("Crimson Red",     (220,20,60),    750,   1.5, False, False),
    ("Emerald Green",   (50,205,50),    1000,  1.8, False, False),
    ("Electric Purple", (138,43,226),   1250,  2.0, False, False),
    ("Sunset Orange",   (255,140,0),    750,   1.5, False, False),
    ("Aqua Cyan",       (0,255,255),    1000,  1.8, False, False),
    ("Rose Pink",       (255,105,180),  1250,  2.0, False, False),
    ("Forest Guardian", (144,238,144),  2500,  2.5, True,  False),
    ("Ocean Blue",      (64,224,208),   2500,  2.5, True,  False),
    ("Sunset Blaze",    (255,165,0),    3500,  2.8, True,  False),
    ("Midnight Mystic", (186,85,211),   3500,  2.8, True,  False),
    ("Neon Cyber",      (0,255,255),    5000,  3.0, True,  False),
    ("Hellfire Dragon", (255,69,0),     7500,  3.2, True,  False),
    ("Rainbow Legend",  None,           15000, 5.0, True,  True),
]

owned_bird_skins = {0}
total_coins = 0
coins_earned_this_run = 0

pipe_pair_id = 0

RAINBOW_COLORS = [(255,60,60),(255,165,0),(255,240,0),(60,220,60),(60,140,255),(140,60,240)]

# ── Helpers ───────────────────────────────────────────────────────────────────

def lerp_color(c1, c2, t):
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def get_rainbow_color(t_offset=0):
    t = (pygame.time.get_ticks()/600.0 + t_offset) % 1.0
    idx = int(t*len(RAINBOW_COLORS))
    frac = t*len(RAINBOW_COLORS)-idx
    c1 = RAINBOW_COLORS[idx % len(RAINBOW_COLORS)]
    c2 = RAINBOW_COLORS[(idx+1) % len(RAINBOW_COLORS)]
    return tuple(int(c1[i]+(c2[i]-c1[i])*frac) for i in range(3))

def generate_beep(frequency=1000, duration=100, volume=0.3):
    try:
        if not HAS_NUMPY: return None
        sr = 44100; frames = int(duration*sr/1000)
        t = np.linspace(0, duration/1000, frames)
        ff = max(1, int(frames*0.1))
        wave = np.sin(2.0*np.pi*frequency*t)
        wave[:ff] *= np.linspace(0,1,ff); wave[-ff:] *= np.linspace(1,0,ff)
        wave = (wave*32767*volume).astype(np.int16)
        return pygame.sndarray.make_sound(wave)
    except: return None

def play_beep(freq=1000, dur=100):
    try:
        s = generate_beep(freq, dur, 0.5)
        if s:
            ch = pygame.mixer.find_channel()
            if ch: ch.play(s)
    except: pass

def play(sound):
    if sound:
        try: pygame.mixer.music.load(sound); pygame.mixer.music.play()
        except: pass

# ── Bird drawing ──────────────────────────────────────────────────────────────

def draw_bird_shape(surface, cx, cy, body_color, wing_frame=0, angle_deg=0, scale=1.0):
    cos_a = math.cos(math.radians(-angle_deg))
    sin_a = math.sin(math.radians(-angle_deg))
    def rot(x, y):
        return int(cx+(x*cos_a-y*sin_a)*scale), int(cy+(x*sin_a+y*cos_a)*scale)
    is_rb = body_color is None
    bc = get_rainbow_color(0.0) if is_rb else body_color
    hc = get_rainbow_color(0.15) if is_rb else body_color
    wc = get_rainbow_color(0.3) if is_rb else tuple(max(0,c-40) for c in body_color)
    tc = get_rainbow_color(0.45) if is_rb else tuple(min(255,c+30) for c in body_color)
    # Shadow ellipse under body
    sx,sy = rot(0, 4)
    pygame.draw.ellipse(surface, (0,0,0,60), (sx-int(14*scale), sy-int(5*scale), int(28*scale), int(10*scale)))
    # Tail
    pygame.draw.polygon(surface, tc, [rot(-14,-2),rot(-21,-8),rot(-18,1),rot(-14,4)])
    pygame.draw.polygon(surface, tuple(max(0,c-20) for c in tc), [rot(-12,2),rot(-21,6),rot(-16,6)])
    # Body
    body_pts = [rot(-12,-5),rot(10,-7),rot(14,0),rot(10,7),rot(-10,6)]
    body_hi = tuple(min(255,c+55) for c in bc)
    pygame.draw.polygon(surface, bc, body_pts)
    pygame.draw.polygon(surface, body_hi, body_pts, 2)
    # Wing
    wo = [-6,-11,-6,0][wing_frame%4]
    wpts = [rot(-2,-4),rot(8,-8+wo),rot(9,-2+wo//2),rot(0,0)]
    pygame.draw.polygon(surface, wc, wpts)
    pygame.draw.polygon(surface, tuple(max(0,c-30) for c in wc), wpts, 2)
    # Head
    hx,hy = rot(13,-1)
    hr = int(9*scale)
    pygame.draw.circle(surface, hc, (hx,hy), hr)
    pygame.draw.circle(surface, tuple(min(255,c+60) for c in hc), (hx,hy), hr, 2)
    # Eye
    ex,ey = rot(17,-4)
    pygame.draw.circle(surface, (255,255,255), (ex,ey), int(4*scale))
    pygame.draw.circle(surface, (20,20,20), rot(18,-5), int(2*scale))
    pygame.draw.circle(surface, (255,255,255), rot(19,-6), max(1,int(1.2*scale)))
    # Beak
    pygame.draw.polygon(surface, (255,160,0), [rot(19,-2),rot(27,-1),rot(19,3)])
    pygame.draw.polygon(surface, (200,110,0), [rot(19,-2),rot(27,-1),rot(19,3)], 1)

def create_bird_graphics(color):
    imgs = []
    for f in range(4):
        s = pygame.Surface((100,90), pygame.SRCALPHA); s.fill((0,0,0,0))
        draw_bird_shape(s, 50,45, color, wing_frame=f, angle_deg=0, scale=1.0)
        imgs.append(s.convert_alpha())
    return imgs

# ── Heart ─────────────────────────────────────────────────────────────────────

def draw_heart(surface, cx, cy, size, color=(255,50,80), outline_color=(255,120,140)):
    r = max(2, int(size*0.55))
    lx,ly = int(cx-size*0.28), int(cy-size*0.15)
    rx,ry = int(cx+size*0.28), int(cy-size*0.15)
    pts = [(int(cx-size*0.85),int(cy-size*0.05)),
           (int(cx+size*0.85),int(cy-size*0.05)),
           (int(cx),int(cy+size*0.90))]
    pygame.draw.circle(surface, color, (lx,ly), r)
    pygame.draw.circle(surface, color, (rx,ry), r)
    pygame.draw.polygon(surface, color, pts)
    hi = tuple(min(255,c+80) for c in color)
    pygame.draw.circle(surface, hi, (lx-int(r*0.2),ly-int(r*0.25)), max(1,int(r*0.45)))
    pygame.draw.circle(surface, outline_color, (lx,ly), r, 2)
    pygame.draw.circle(surface, outline_color, (rx,ry), r, 2)
    pygame.draw.polygon(surface, outline_color, pts, 2)

# ── Pipe graphics ─────────────────────────────────────────────────────────────

def create_pipe(color):
    """Metallic pipe with proper lighting — light from top-left."""
    surf = pygame.Surface((PIPE_W, PIPE_H))
    base = tuple(max(0,c-50) for c in color)
    light = tuple(min(255,c+90) for c in color)
    dark  = tuple(max(0,c-80) for c in color)
    surf.fill(base)
    # Left specular strip
    pygame.draw.rect(surf, light, (2,0,8,PIPE_H))
    # Slightly lighter left-centre strip
    mid_light = tuple(min(255,c+30) for c in color)
    pygame.draw.rect(surf, mid_light, (10,0,20,PIPE_H))
    # Right dark shadow strip
    pygame.draw.rect(surf, dark, (PIPE_W-10,0,10,PIPE_H))
    pygame.draw.rect(surf, (0,0,0), (PIPE_W-4,0,4,PIPE_H))
    # Horizontal ring bands
    for y in range(0, PIPE_H, 40):
        pygame.draw.rect(surf, dark,  (0,y,PIPE_W,6))
        pygame.draw.rect(surf, light, (0,y,PIPE_W,2))
    # Rivet bolts
    for y in range(20, PIPE_H, 40):
        for bx in [6, PIPE_W-6]:
            pygame.draw.circle(surf, dark,  (bx,y), 4)
            pygame.draw.circle(surf, light, (bx-1,y-1), 2)
    # Ground reflection strip at very bottom
    pygame.draw.rect(surf, light, (0, PIPE_H-8, PIPE_W, 4))
    return surf

def create_ground(color):
    surf = pygame.Surface((GROUND_W, GROUND_H))
    # Base fill
    surf.fill(color)
    # Darker lower half (underground depth)
    deep = tuple(max(0,c-50) for c in color)
    surf.fill(deep, (0, GROUND_H//2, GROUND_W, GROUND_H//2))
    # Alternating tile pattern
    tile_dark = tuple(max(0,c-30) for c in color)
    for x in range(0, GROUND_W, 40):
        for y in range(0, GROUND_H//2, 20):
            if (x//40 + y//20) % 2 == 0:
                pygame.draw.rect(surf, tile_dark, (x,y,40,20))
    # Top highlight strip (specular from sky light)
    top_light = tuple(min(255,c+70) for c in color)
    pygame.draw.rect(surf, top_light, (0,0,GROUND_W,4))
    mid_light = tuple(min(255,c+40) for c in color)
    pygame.draw.rect(surf, mid_light, (0,4,GROUND_W,3))
    # Grass blades on top (for natural themes)
    grass = tuple(min(255,c+60) for c in color)
    for x in range(0, GROUND_W, 12):
        offset = (x*7) % 5
        pygame.draw.line(surf, grass, (x,0), (x+3-offset, -6), 2)
    return surf

# ── Themed backgrounds ────────────────────────────────────────────────────────

def _grad(surf, top_col, bot_col, y0=0, y1=None):
    """Fill vertical gradient onto surf between y0 and y1."""
    if y1 is None: y1 = surf.get_height()
    h = y1-y0
    for y in range(h):
        t = y/max(1,h-1)
        c = lerp_color(top_col, bot_col, t)
        pygame.draw.line(surf, c, (0,y0+y), (surf.get_width(),y0+y))

def _cloud(surf, cx, cy, r, color=(255,255,255), alpha=200):
    """Draw a fluffy cloud group at (cx,cy)."""
    cs = pygame.Surface((r*5, r*3), pygame.SRCALPHA)
    for ox,oy,cr in [(0,0,r),(r,int(-r*0.3),int(r*0.8)),(-r,int(-r*0.2),int(r*0.7)),
                      (int(r*0.5),int(-r*0.5),int(r*0.65)),(int(-r*0.5),int(-r*0.5),int(r*0.6))]:
        cx2,cy2 = r*2+ox, r+oy
        pygame.draw.circle(cs, (*color,alpha), (cx2,cy2), cr)
    # Bottom flat cut
    pygame.draw.rect(cs, (0,0,0,0), (0,r+int(r*0.3),r*5,r*2))
    surf.blit(cs, (cx-r*2, cy-r))

def build_background_classic():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    _grad(surf, (100,185,255), (200,235,255), 0, SCREEN_H - GROUND_H)
    # Sun with rays
    sx2, sy2 = 920, 95
    for ang in range(0, 360, 20):
        ex = sx2 + int(80*math.cos(math.radians(ang)))
        ey = sy2 + int(80*math.sin(math.radians(ang)))
        pygame.draw.line(surf, (255,235,80), (sx2,sy2), (ex,ey), 3)
    pygame.draw.circle(surf, (255,245,120), (sx2,sy2), 50)
    pygame.draw.circle(surf, (255,255,200), (sx2,sy2), 36)
    _cloud(surf, 120,140,44,(255,255,255),220)
    _cloud(surf, 380,100,36,(255,255,255),210)
    _cloud(surf, 660,155,50,(255,255,255),200)
    _cloud(surf, 950,120,40,(255,255,255),215)
    # Far snow-capped mountains
    far_pts = [(0, SCREEN_H-GROUND_H)]
    for mx in range(0, SCREEN_W+60, 90):
        mh = 180 + (mx*17+31)%120
        far_pts += [(mx, SCREEN_H-GROUND_H-mh), (mx+45, SCREEN_H-GROUND_H)]
    far_pts.append((SCREEN_W, SCREEN_H-GROUND_H))
    pygame.draw.polygon(surf, (155,175,200), far_pts)
    for mx in range(0, SCREEN_W+60, 90):
        mh = 180 + (mx*17+31)%120
        peak = (mx+22, SCREEN_H-GROUND_H-mh)
        cap = [(mx+10, SCREEN_H-GROUND_H-mh+35), peak, (mx+35, SCREEN_H-GROUND_H-mh+28)]
        pygame.draw.polygon(surf, (240,245,255), cap)
    # Mid-mountains
    mid_pts = [(0, SCREEN_H-GROUND_H)]
    for mx in range(-30, SCREEN_W+80, 70):
        mh = 100 + (mx*13+7)%90
        mid_pts += [(mx, SCREEN_H-GROUND_H-mh), (mx+35, SCREEN_H-GROUND_H)]
    mid_pts.append((SCREEN_W, SCREEN_H-GROUND_H))
    pygame.draw.polygon(surf, (90,140,75), mid_pts)
    # Near foothills
    near_pts = [(0, SCREEN_H-GROUND_H)]
    for mx in range(-20, SCREEN_W+60, 55):
        mh = 45 + (mx*11+3)%50
        near_pts += [(mx, SCREEN_H-GROUND_H-mh), (mx+28, SCREEN_H-GROUND_H)]
    near_pts.append((SCREEN_W, SCREEN_H-GROUND_H))
    pygame.draw.polygon(surf, (55,110,45), near_pts)
    surf.fill((70,145,50), (0, SCREEN_H-GROUND_H, SCREEN_W, GROUND_H))
    return surf


def build_background_neon():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    surf.fill((4, 0, 16))
    vanish_y = SCREEN_H - GROUND_H - 20
    for xi in range(0, SCREEN_W+1, 80):
        pygame.draw.line(surf, (60,0,90), (xi,SCREEN_H), (SCREEN_W//2,vanish_y), 1)
    for di in range(0, 9):
        t = di/8.0
        yg = int(vanish_y + (SCREEN_H-vanish_y)*t*t)
        pygame.draw.line(surf, (60,0,90), (0,yg), (SCREEN_W,yg), 1)
    # Distant city
    random.seed(99)
    for bx in range(0, SCREEN_W, 40):
        bh = random.randint(60,200)
        by = SCREEN_H-GROUND_H-bh
        pygame.draw.rect(surf, (10,0,22), (bx,by,36,bh))
        for wy in range(by+8, SCREEN_H-GROUND_H-8, 14):
            for wx in range(bx+5, bx+32, 11):
                if random.random() > 0.4:
                    wc = random.choice([(255,200,0),(0,200,255),(255,50,150),(100,255,100)])
                    pygame.draw.rect(surf, wc, (wx,wy,4,6))
    # Alternating neon lines
    neon_cols = [(255,0,200),(0,255,200),(255,220,0),(0,180,255),(255,80,0),(150,0,255)]
    random.seed(77)
    for ni in range(28):
        nc = neon_cols[ni % len(neon_cols)]
        x1 = random.randint(0, SCREEN_W)
        y1 = random.randint(40, SCREEN_H-GROUND_H-40)
        angle = random.uniform(0, math.pi)
        length = random.randint(80, 250)
        x2 = int(x1 + length*math.cos(angle))
        y2 = int(y1 + length*math.sin(angle)*0.4)
        gs = pygame.Surface((SCREEN_W, SCREEN_H))
        gs.fill((0,0,0)); gs.set_colorkey((0,0,0))
        pygame.draw.line(gs, nc, (x1,y1), (x2,y2), 7)
        gs.set_alpha(28)
        surf.blit(gs, (0,0))
        pygame.draw.line(surf, nc, (x1,y1), (x2,y2), 2)
    # Neon circles
    for cx2,cy2,r2,nc2 in [(200,300,40,(255,0,200)),(700,250,55,(0,255,200)),(1050,350,35,(255,220,0))]:
        gs2 = pygame.Surface((r2*4,r2*4))
        gs2.fill((0,0,0)); gs2.set_colorkey((0,0,0))
        pygame.draw.circle(gs2, nc2, (r2*2,r2*2), r2)
        gs2.set_alpha(22)
        surf.blit(gs2, (cx2-r2*2,cy2-r2*2))
        pygame.draw.circle(surf, nc2, (cx2,cy2), r2, 2)
    return surf


def build_background_cybercity():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    _grad(surf,(8,8,45),(18,14,62))
    random.seed(77)
    for bx in range(0, SCREEN_W, 50):
        bh = random.randint(100,360)
        by = SCREEN_H-GROUND_H-bh
        col = random.choice([(20,20,55),(15,15,50),(25,20,62)])
        pygame.draw.rect(surf,col,(bx,by,44,bh))
        for wy in range(by+8, SCREEN_H-GROUND_H-5, 14):
            for wx in range(bx+5, bx+40, 10):
                if random.random() > 0.35:
                    wc = random.choice([(0,255,120),(255,60,255),(60,200,255)])
                    pygame.draw.rect(surf,wc,(wx,wy,4,6))
        ax = bx+22
        pygame.draw.line(surf,(80,80,130),(ax,by),(ax,by-22),2)
        pygame.draw.circle(surf,(255,50,50),(ax,by-24),3)
    for nx,ny,nc in [(300,200,(255,50,200)),(700,250,(0,255,180)),(1000,180,(255,200,0))]:
        pygame.draw.rect(surf,nc,(nx,ny,80,25),2)
    random.seed(55)
    for _ in range(100):
        rx=random.randint(0,SCREEN_W); ry=random.randint(0,SCREEN_H-GROUND_H)
        pygame.draw.line(surf,(80,160,220),(rx,ry),(rx-2,ry+14),1)
    return surf


def build_background_hell():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    _grad(surf,(130,8,0),(55,0,0),0,SCREEN_H-GROUND_H)
    # Lava glow at ground line
    for lw in range(6,0,-1):
        lg = pygame.Surface((SCREEN_W, lw*12))
        lg.fill((0,0,0)); lg.set_colorkey((0,0,0))
        lc = (min(255,200+lw*8), min(255,lw*18), 0)
        lg.fill(lc)
        lg.set_alpha(int(38*(1-lw/6)))
        surf.blit(lg,(0,SCREEN_H-GROUND_H-lw*12))
    pygame.draw.rect(surf,(200,55,0),(0,SCREEN_H-GROUND_H-8,SCREEN_W,10))
    # Multiple volcanoes
    volcanoes = [(200,160),(550,200),(900,178),(1150,140),(380,118)]
    for vx2,vw2 in volcanoes:
        vh2 = int(vw2*1.2)
        vy2 = SCREEN_H-GROUND_H
        dark = max(0, 58-vw2//6)
        pygame.draw.polygon(surf,(dark,0,0),
            [(vx2-vw2//2,vy2),(vx2,vy2-vh2),(vx2+vw2//2,vy2)])
        pygame.draw.polygon(surf,(210,55,0),
            [(vx2-28,vy2-vh2+15),(vx2,vy2-vh2-5),
             (vx2+28,vy2-vh2+15),(vx2+12,vy2-vh2),(vx2-12,vy2-vh2)])
        for ls in range(3):
            lsx = vx2-20+ls*20
            pygame.draw.line(surf,(255,100,0),(lsx,vy2-vh2+20),(lsx+8,vy2-vh2+60),2)
        random.seed(vx2)
        for _ in range(12):
            ex2 = vx2+random.randint(-50,50); ey2 = vy2-vh2-random.randint(10,80)
            ec2 = random.choice([(255,80,0),(255,180,0),(255,40,0)])
            pygame.draw.circle(surf,ec2,(ex2,ey2),random.randint(2,4))
    # Stalactites from ceiling
    random.seed(13)
    for si in range(0, SCREEN_W, 65):
        sh2 = random.randint(25,95)
        sc2 = (90+random.randint(0,35),0,0)
        pygame.draw.polygon(surf,sc2,[(si,0),(si+32,0),(si+22,sh2),(si+10,sh2)])
        pygame.draw.circle(surf,(255,70,0),(si+16,sh2+7),5)
    # Demon silhouettes
    demon_positions = [(150,SCREEN_H-GROUND_H-55),(480,SCREEN_H-GROUND_H-60),
                       (750,SCREEN_H-GROUND_H-50),(1050,SCREEN_H-GROUND_H-58)]
    for dx2,dy2 in demon_positions:
        pygame.draw.ellipse(surf,(40,0,0),(dx2-12,dy2,24,30))
        pygame.draw.circle(surf,(50,0,0),(dx2,dy2-8),12)
        pygame.draw.polygon(surf,(60,0,0),[(dx2-10,dy2-16),(dx2-16,dy2-34),(dx2-4,dy2-18)])
        pygame.draw.polygon(surf,(60,0,0),[(dx2+10,dy2-16),(dx2+16,dy2-34),(dx2+4,dy2-18)])
        pygame.draw.circle(surf,(255,40,0),(dx2-4,dy2-10),3)
        pygame.draw.circle(surf,(255,40,0),(dx2+4,dy2-10),3)
        pygame.draw.polygon(surf,(35,0,0),[(dx2,dy2+5),(dx2-30,dy2-10),(dx2-20,dy2+10)])
        pygame.draw.polygon(surf,(35,0,0),[(dx2,dy2+5),(dx2+30,dy2-10),(dx2+20,dy2+10)])
    return surf


def build_background_forest():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    _grad(surf,(60,120,45),(110,170,65),0,SCREEN_H-GROUND_H)
    # Sun rays
    sun_x2,sun_y2 = 580,25
    for ang2 in range(-28,30,5):
        ex2 = sun_x2+int(800*math.sin(math.radians(ang2))); ey2 = SCREEN_H
        rsurf = pygame.Surface((SCREEN_W,SCREEN_H))
        rsurf.fill((0,0,0)); rsurf.set_colorkey((0,0,0))
        pygame.draw.line(rsurf,(255,240,160),(sun_x2,sun_y2),(ex2,ey2),16)
        rsurf.set_alpha(12)
        surf.blit(rsurf,(0,0))
    pygame.draw.circle(surf,(255,245,140),(sun_x2,sun_y2),32)
    # Far treeline
    random.seed(42)
    for tx in range(-30, SCREEN_W+40, 42):
        th2 = random.randint(100,180)
        tc2 = (20+random.randint(0,15),70+random.randint(0,20),15+random.randint(0,10))
        pygame.draw.rect(surf,(55,35,15),(tx+16,SCREEN_H-GROUND_H-25,8,30))
        for tl in range(3):
            tcr = th2//2-tl*16; tcy2 = SCREEN_H-GROUND_H-th2+tl*28
            pygame.draw.polygon(surf,tc2,[(tx,tcy2+tcr*2),(tx+42,tcy2+tcr*2),(tx+21,tcy2)])
    # Mid-layer large trees
    random.seed(88)
    for tx2 in range(-20, SCREEN_W+30, 65):
        th3 = random.randint(200,320)
        tc3 = (28+random.randint(0,20),90+random.randint(0,25),20+random.randint(0,15))
        pygame.draw.rect(surf,(75,45,18),(tx2+26,SCREEN_H-GROUND_H-50,14,55))
        pygame.draw.line(surf,(55,30,10),(tx2+30,SCREEN_H-GROUND_H-45),(tx2+32,SCREEN_H-GROUND_H-5),2)
        for tl2 in range(4):
            tcr2 = th3//2-tl2*22; tcy3 = SCREEN_H-GROUND_H-th3+tl2*38
            pygame.draw.polygon(surf,tc3,[(tx2,tcy3+tcr2*2),(tx2+65,tcy3+tcr2*2),(tx2+32,tcy3)])
            hi3 = tuple(min(255,c+25) for c in tc3)
            pygame.draw.polygon(surf,hi3,[(tx2+12,tcy3+tcr2),(tx2+52,tcy3+tcr2),(tx2+32,tcy3+8)])
    # Ferns
    random.seed(55)
    for fx2 in range(0, SCREEN_W, 35):
        fh2 = random.randint(15,35)
        for fb in range(5):
            fangle = -60+fb*30
            fex = fx2+int(fh2*math.cos(math.radians(fangle)))
            fey = SCREEN_H-GROUND_H-int(fh2*abs(math.sin(math.radians(fangle))))
            pygame.draw.line(surf,(40,110,25),(fx2,SCREEN_H-GROUND_H),(fex,fey),2)
    # Fireflies
    random.seed(17)
    for _ in range(30):
        ffx=random.randint(0,SCREEN_W); ffy=random.randint(SCREEN_H-GROUND_H-350,SCREEN_H-GROUND_H-60)
        ffs=pygame.Surface((10,10))
        ffs.fill((0,0,0)); ffs.set_colorkey((0,0,0))
        pygame.draw.circle(ffs,(200,255,80),(5,5),4)
        ffs.set_alpha(160)
        surf.blit(ffs,(ffx,ffy))
    # Mushrooms
    for mux in range(60, SCREEN_W, 180):
        muy = SCREEN_H-GROUND_H
        pygame.draw.rect(surf,(220,200,190),(mux,muy-22,8,20))
        pygame.draw.ellipse(surf,(200,40,40),(mux-10,muy-32,28,14))
        pygame.draw.circle(surf,(230,80,80),(mux+4,muy-30),7)
        for dot in [(-3,2),(4,4),(7,-1)]:
            pygame.draw.circle(surf,(255,240,240),(mux+4+dot[0],muy-28+dot[1]),2)
    return surf


def build_background_ocean():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    _grad(surf,(0,90,190),(0,50,130))
    _grad(surf,(80,190,255),(0,110,195),0,70)
    # Caustic light ellipses
    random.seed(88)
    for _ in range(45):
        cx2=random.randint(0,SCREEN_W); cy2=random.randint(70,SCREEN_H-GROUND_H-60)
        cr2=random.randint(18,50)
        cs2=pygame.Surface((cr2*2,cr2//2*2+4))
        cs2.fill((0,0,0)); cs2.set_colorkey((0,0,0))
        pygame.draw.ellipse(cs2,(140,220,255),(0,0,cr2*2,max(4,cr2//2*2)))
        cs2.set_alpha(22)
        surf.blit(cs2,(cx2-cr2,cy2-cr2//2))
    # Sandy floor
    pygame.draw.rect(surf,(175,135,90),(0,SCREEN_H-GROUND_H-22,SCREEN_W,28))
    _grad(surf,(185,145,100),(160,120,75),SCREEN_H-GROUND_H-22,SCREEN_H-GROUND_H)
    # Seaweed
    random.seed(33)
    for sx2 in range(0, SCREEN_W, 30):
        swh=random.randint(40,120)
        swc=random.choice([(0,140,50),(0,160,40),(20,120,45)])
        for seg in range(swh//14):
            swy=SCREEN_H-GROUND_H-20-seg*14
            swx2=sx2+int(8*math.sin(seg*0.8+sx2*0.05))
            pygame.draw.line(surf,swc,(swx2,swy+14),(swx2,swy),3)
            pygame.draw.ellipse(surf,tuple(min(255,c+30) for c in swc),(swx2+2,swy,10,5))
    # Coral
    random.seed(23)
    for cx3 in range(0, SCREEN_W, 48):
        ch2=random.randint(25,80)
        cc2=random.choice([(230,80,80),(255,130,90),(190,70,160),(255,170,40),(220,120,200)])
        bx3=cx3+24; by3=SCREEN_H-GROUND_H-18
        pygame.draw.line(surf,cc2,(bx3,by3),(bx3,by3-ch2),4)
        pygame.draw.line(surf,cc2,(bx3,by3-ch2//2),(bx3-14,by3-ch2//2-20),3)
        pygame.draw.line(surf,cc2,(bx3,by3-ch2//2),(bx3+14,by3-ch2//2-20),3)
        pygame.draw.circle(surf,tuple(min(255,c+40) for c in cc2),(bx3,by3-ch2),7)
    # Fish
    random.seed(66)
    for _ in range(18):
        fx3=random.randint(50,SCREEN_W-50); fy3=random.randint(100,SCREEN_H-GROUND_H-80)
        fs2=random.randint(12,26)
        fc=random.choice([(255,180,0),(0,200,255),(255,80,80),(100,255,100),(255,120,200),(200,100,255)])
        pygame.draw.ellipse(surf,fc,(fx3-fs2,fy3-fs2//2,fs2*2,fs2))
        pygame.draw.polygon(surf,tuple(max(0,c-40) for c in fc),
            [(fx3-fs2,fy3),(fx3-fs2-fs2//2,fy3-fs2//3),(fx3-fs2-fs2//2,fy3+fs2//3)])
        pygame.draw.circle(surf,(255,255,255),(fx3+fs2//2,fy3-2),3)
        pygame.draw.circle(surf,(0,0,0),(fx3+fs2//2,fy3-2),2)
        pygame.draw.line(surf,tuple(min(255,c+60) for c in fc),(fx3,fy3-fs2//2+2),(fx3,fy3+fs2//2-2),2)
    # Bubbles
    random.seed(44)
    for _ in range(55):
        bx4=random.randint(0,SCREEN_W); by4=random.randint(80,SCREEN_H-GROUND_H-40)
        br2=random.randint(3,10)
        bs2=pygame.Surface((br2*2,br2*2))
        bs2.fill((0,0,0)); bs2.set_colorkey((0,0,0))
        pygame.draw.circle(bs2,(180,230,255),(br2,br2),br2)
        pygame.draw.circle(bs2,(240,250,255),(br2,br2),br2,1)
        bs2.set_alpha(60)
        surf.blit(bs2,(bx4-br2,by4-br2))
    return surf


def build_background_sunset():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    _grad(surf,(200,80,20),(255,140,35),0,SCREEN_H//3)
    _grad(surf,(255,140,35),(255,180,60),SCREEN_H//3,int(SCREEN_H*0.6))
    _grad(surf,(255,180,60),(220,95,25),int(SCREEN_H*0.6),SCREEN_H-GROUND_H)
    # Large sun drooping to horizon
    sun_x3=SCREEN_W//2; sun_y3=SCREEN_H-GROUND_H-16; sun_r3=72
    for sr3 in range(130,60,-12):
        sg3=pygame.Surface((sr3*2,sr3*2))
        sg3.fill((0,0,0)); sg3.set_colorkey((0,0,0))
        sc3=(min(255,210+int(45*(1-sr3/130))),min(255,90+int(90*(1-sr3/130))),0)
        pygame.draw.circle(sg3,sc3,(sr3,sr3),sr3)
        sg3.set_alpha(int(50*(1-sr3/130)))
        surf.blit(sg3,(sun_x3-sr3,sun_y3-sr3))
    pygame.draw.circle(surf,(255,210,50),(sun_x3,sun_y3),sun_r3)
    pygame.draw.circle(surf,(255,240,120),(sun_x3,sun_y3),int(sun_r3*0.65))
    # Horizon reflection streak
    for hr in range(8,0,-1):
        hg2=pygame.Surface((SCREEN_W,hr*3))
        hg2.fill((255,200,50)); hg2.set_alpha(int(16*(1-hr/8)))
        surf.blit(hg2,(0,SCREEN_H-GROUND_H-hr*3))
    _cloud(surf,160,140,42,(140,45,0),170)
    _cloud(surf,500,95,55,(120,38,0),155)
    _cloud(surf,880,160,38,(150,50,0),165)
    _cloud(surf,1100,110,45,(130,42,0),160)
    # City silhouette
    random.seed(66)
    for bx5 in range(0, SCREEN_W, 44):
        bh5=random.randint(35,130)
        pygame.draw.rect(surf,(20,8,0),(bx5,SCREEN_H-GROUND_H-bh5,40,bh5))
        for wy5 in range(SCREEN_H-GROUND_H-bh5+8,SCREEN_H-GROUND_H-8,14):
            for wx5 in range(bx5+5,bx5+36,10):
                if random.random()>0.55:
                    pygame.draw.rect(surf,(255,180,30),(wx5,wy5,3,5))
    pygame.draw.rect(surf,(255,170,40),(0,SCREEN_H-GROUND_H-4,SCREEN_W,6))
    return surf


def build_background_midnight():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    _grad(surf,(4,4,22),(12,8,38))
    # Stars
    random.seed(42)
    for _ in range(200):
        stx=random.randint(0,SCREEN_W); sty=random.randint(0,int(SCREEN_H*0.85))
        stsz=random.randint(1,3); stb=random.randint(140,255)
        pygame.draw.circle(surf,(stb,stb,min(255,stb+20)),(stx,sty),stsz)
    pygame.draw.line(surf,(255,255,255),(280,90),(325,155),2)
    pygame.draw.line(surf,(200,200,255),(850,60),(880,100),1)
    # Moon
    mx2,my2=int(SCREEN_W*0.82),88
    pygame.draw.circle(surf,(255,252,220),(mx2,my2),48)
    ms2=pygame.Surface((100,100),pygame.SRCALPHA)
    pygame.draw.circle(ms2,(4,4,22,220),(70,50),45)
    surf.blit(ms2,(mx2-50,my2-50))
    for cr3x,cr3y,cr3r in [(mx2-15,my2+10,8),(mx2+18,my2-12,5),(mx2+5,my2+20,4),(mx2-20,my2-15,6)]:
        pygame.draw.circle(surf,(200,195,170),(cr3x,cr3y),cr3r)
        pygame.draw.circle(surf,(140,135,110),(cr3x,cr3y),cr3r,2)
    for mr in range(70,52,-5):
        mg=pygame.Surface((mr*2,mr*2))
        mg.fill((0,0,0)); mg.set_colorkey((0,0,0))
        pygame.draw.circle(mg,(200,200,255),(mr,mr),mr)
        mg.set_alpha(int(12*(1-(mr-52)/18)))
        surf.blit(mg,(mx2-mr,my2-mr))
    # Aurora borealis
    for ab in range(5):
        asurf2=pygame.Surface((SCREEN_W,55))
        asurf2.fill((0,0,0)); asurf2.set_colorkey((0,0,0))
        acols=[(0,200,100),(0,150,200),(100,0,200),(0,220,180),(50,180,255)]
        ac2=acols[ab]
        for ax3 in range(0, SCREEN_W, 4):
            ay3=int(18*math.sin(ax3*0.016+ab*1.3)+28)
            pygame.draw.line(asurf2,ac2,(ax3,ay3+4),(ax3,ay3+14),3)
        asurf2.set_alpha(20)
        surf.blit(asurf2,(0,110+ab*42))
    for cg_x,cg_r,cg_c in [(400,130,(0,60,220)),(800,90,(90,0,180)),(200,65,(0,80,200))]:
        cgg=pygame.Surface((cg_r*4,cg_r))
        cgg.fill((0,0,0)); cgg.set_colorkey((0,0,0))
        pygame.draw.ellipse(cgg,cg_c,(0,0,cg_r*4,cg_r))
        cgg.set_alpha(28)
        surf.blit(cgg,(cg_x-cg_r*2,SCREEN_H-GROUND_H-cg_r//2))
    return surf


BG_BUILDERS = {
    "classic":   build_background_classic,
    "neon":      build_background_neon,
    "cybercity": build_background_cybercity,
    "hell":      build_background_hell,
    "forest":    build_background_forest,
    "ocean":     build_background_ocean,
    "sunset":    build_background_sunset,
    "midnight":  build_background_midnight,
}

# ── Powerup ───────────────────────────────────────────────────────────────────

class Powerup(pygame.sprite.Sprite):
    IMMUNITY = 0
    DOUBLE_SCORE = 1

    def __init__(self, x, y, powerup_type, color):
        super().__init__()
        self.powerup_type = powerup_type
        self.x = x; self.y = y
        self.lifetime = 10.0; self.elapsed = 0.0; self.pulse_time = 0.0
        # Transparent sprite — we draw manually each frame
        self.image = pygame.Surface((50,50), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x,y))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt):
        self.elapsed += dt; self.pulse_time += dt
        self.rect.x -= GAME_SPEED
        self.rect.y = int(self.y + 8*math.sin(self.pulse_time*2.5))
        return self.elapsed < self.lifetime

    def draw(self, screen):
        cx, cy = self.rect.center
        scale = 1.0 + 0.2*math.sin(self.pulse_time*3.5)
        size = int(22*scale)

        # ─── GLOW TECHNIQUE ────────────────────────────────────────────────
        # pygame.draw ignores the alpha byte of colours on SRCALPHA surfaces,
        # so every shape renders fully opaque → black box.
        # Fix: plain Surface + colorkey(black) + set_alpha + BLEND_RGB_ADD.
        # BLEND_RGB_ADD adds the glow light on top without painting over bg.
        # ───────────────────────────────────────────────────────────────────

        if self.powerup_type == self.IMMUNITY:
            for gi in range(6, 0, -1):
                gs = size + gi * 5
                gsurf = pygame.Surface((gs * 2, gs * 2))
                gsurf.fill((0, 0, 0))
                gsurf.set_colorkey((0, 0, 0))
                r2 = max(2, int(gs * 0.55))
                lx2 = int(gs - gs*0.28); ly2 = int(gs - gs*0.15)
                rx2 = int(gs + gs*0.28); ry2 = int(gs - gs*0.15)
                pts2 = [(int(gs - gs*0.85), int(gs - gs*0.05)),
                        (int(gs + gs*0.85), int(gs - gs*0.05)),
                        (int(gs),           int(gs + gs*0.90))]
                pygame.draw.circle(gsurf, (255, 60, 80), (lx2, ly2), r2)
                pygame.draw.circle(gsurf, (255, 60, 80), (rx2, ry2), r2)
                pygame.draw.polygon(gsurf, (255, 60, 80), pts2)
                gsurf.set_alpha(int(52 * (1 - gi / 6.0)))
                screen.blit(gsurf, (cx - gs, cy - gs),
                            special_flags=pygame.BLEND_RGB_ADD)
            draw_heart(screen, cx, cy, size, (255, 50, 80), (255, 180, 190))
            pygame.draw.circle(screen, (255, 255, 255),
                               (cx - int(size*0.3), cy - int(size*0.4)),
                               max(2, int(size*0.18)))

        else:
            for gi in range(6, 0, -1):
                gs = size + gi * 5
                gsurf = pygame.Surface((gs * 3, gs * 3))
                gsurf.fill((0, 0, 0))
                gsurf.set_colorkey((0, 0, 0))
                gpts = []
                for i in range(10):
                    ang = math.radians(-90 + i*36) + self.pulse_time*0.8
                    gr  = gs if i % 2 == 0 else gs * 0.42
                    gpts.append((int(gs*1.5 + gr*math.cos(ang)),
                                 int(gs*1.5 + gr*math.sin(ang))))
                pygame.draw.polygon(gsurf, (255, 210, 0), gpts)
                gsurf.set_alpha(int(52 * (1 - gi / 6.0)))
                screen.blit(gsurf, (cx - int(gs*1.5), cy - int(gs*1.5)),
                            special_flags=pygame.BLEND_RGB_ADD)
            pts = []
            for i in range(10):
                ang = math.radians(-90 + i*36) + self.pulse_time*0.8
                r   = size if i % 2 == 0 else size * 0.42
                pts.append((int(cx + r*math.cos(ang)), int(cy + r*math.sin(ang))))
            ipts = []
            for i in range(10):
                ang = math.radians(-90 + i*36) + self.pulse_time*0.8
                r   = size*0.55 if i % 2 == 0 else size * 0.22
                ipts.append((int(cx + r*math.cos(ang)), int(cy + r*math.sin(ang))))
            pygame.draw.polygon(screen, (255, 210, 0),   pts)
            pygame.draw.polygon(screen, (255, 255, 160), ipts)
            pygame.draw.polygon(screen, (200, 140, 0),   pts, 2)
            pygame.draw.circle(screen,  (255, 255, 200), (cx, cy), max(2, size // 4))

# ── FloatingScore ─────────────────────────────────────────────────────────────

class FloatingScore:
    def __init__(self, x, y, score, color):
        self.x=x; self.y=y; self.score=score; self.color=color
        self.lifetime=1.0; self.elapsed=0.0
    def update(self, dt):
        self.elapsed+=dt; self.y-=55*dt
        return self.elapsed<self.lifetime
    def draw(self, screen):
        alpha = int(255*(1-self.elapsed/self.lifetime))
        font = get_font(52)
        txt = f"+{int(self.score)}"
        sh = font.render(txt, True, (0,0,0)); sh.set_alpha(alpha//2)
        screen.blit(sh, (int(self.x-sh.get_width()//2)+2, int(self.y)+2))
        ts = font.render(txt, True, self.color); ts.set_alpha(alpha)
        screen.blit(ts, (int(self.x-ts.get_width()//2), int(self.y)))

# ── Sprite classes ────────────────────────────────────────────────────────────

class Bird(pygame.sprite.Sprite):
    def __init__(self, images):
        super().__init__()
        self.images = images; self.speed = SPEED; self.current_image = 0
        self.image = images[0]; self.rotated_image = images[0]
        self.rect = self.image.get_rect()
        self.rect.x = SCREEN_W//6; self.rect.y = SCREEN_H//2
        self.center_pos = (self.rect.centerx, self.rect.centery)
        self.mask = pygame.mask.from_surface(self.image)
        self.immunity_time = 0.0; self.double_score_time = 0.0; self.score_multiplier = 1.0
    def update(self):
        self.current_image = (self.current_image+1)%4
        self.speed += GRAVITY
        self.center_pos = (self.center_pos[0], self.center_pos[1]+self.speed)
        ang = min(max(-self.speed*2,-25),80)
        self.rotated_image = pygame.transform.rotate(self.images[self.current_image],-ang)
        self.rect = self.rotated_image.get_rect(center=self.center_pos)
        self.mask = pygame.mask.from_surface(self.rotated_image)
        self.image = self.images[self.current_image]
    def bump(self):
        self.speed = -SPEED; self.center_pos = (self.rect.centerx, self.rect.centery)
    def begin(self):
        self.current_image = (self.current_image+1)%3
        self.image = self.images[self.current_image]

class Pipe(pygame.sprite.Sprite):
    def __init__(self, inverted, xpos, ysize, image, pair_id):
        super().__init__()
        self.image = image; self.pair_id = pair_id; self.scored = False
        self.rect = self.image.get_rect(); self.rect.x = xpos
        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect.y = -(self.rect.h - ysize)
        else:
            self.rect.y = SCREEN_H - ysize
        self.mask = pygame.mask.from_surface(self.image)
    def update(self): self.rect.x -= GAME_SPEED

class Ground(pygame.sprite.Sprite):
    def __init__(self, xpos, image):
        super().__init__()
        self.image = image; self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.x = xpos; self.rect.y = SCREEN_H - GROUND_H
    def update(self): self.rect.x -= GAME_SPEED

def is_off_screen(sprite): return sprite.rect.right < 0

_last_pipe_center = None

def get_random_pipes(xpos, pair_id):
    global _last_pipe_center
    playfield_h = SCREEN_H - GROUND_H
    gap = PIPE_GAP
    min_cy = int(playfield_h * 0.22)
    max_cy = int(playfield_h * 0.78)
    if _last_pipe_center is None:
        cy = random.randint(min_cy, max_cy)
    else:
        delta = int(playfield_h * 0.32)
        lo = max(min_cy, _last_pipe_center - delta)
        hi = min(max_cy, _last_pipe_center + delta)
        cy = random.randint(lo, hi)
    _last_pipe_center = cy
    bot_h = max(60, playfield_h - cy - gap // 2)
    bot_h = min(bot_h, playfield_h - gap - 60)
    top_h = max(60, playfield_h - bot_h - gap)
    return (Pipe(False, xpos, bot_h, pipe_img, pair_id),
            Pipe(True,  xpos, top_h, pipe_img, pair_id))

# ── Init ──────────────────────────────────────────────────────────────────────

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption('Flappy Bird')
init_audio()

BACKGROUND = None
pipe_img = None
ground_img = None

def draw_bird_direct(screen, bird, bird_color):
    ang = min(max(-bird.speed*2,-25),80)
    draw_bird_shape(screen, bird.rect.centerx, bird.rect.centery,
                    bird_color, wing_frame=bird.current_image%4, angle_deg=ang, scale=1.2)

def apply_theme(base=None):
    global BACKGROUND, pipe_img, ground_img
    theme = THEMES[current_theme]
    builder = BG_BUILDERS.get(theme["name"])
    BACKGROUND = builder() if builder else pygame.Surface((SCREEN_W,SCREEN_H))
    pipe_img  = create_pipe(theme["pipe"])
    ground_img = create_ground(theme["ground"])
    bird_imgs = create_bird_graphics(theme["bird"])
    start_music(theme["name"])
    return bird_imgs, pipe_img, ground_img, theme["text"], theme["accent"], theme["shadow"], theme["dark"]

def load_base_images(): return {}

# ── GUI helpers ───────────────────────────────────────────────────────────────

_font_cache = {}
def get_font(size):
    if size not in _font_cache: _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]

def draw_text(surface, text, size, color, x, y, shadow_col=(0,0,0), offset=3):
    """Render text with a clean drop-shadow and NO background box."""
    font = get_font(size)
    for i in range(offset,0,-1):
        sh = font.render(text, True, shadow_col)
        sh.set_alpha(int(180*(i/offset)))
        surface.blit(sh, (x+i, y+i))
    surface.blit(font.render(text, True, color), (x,y))

def draw_text_centered(surface, text, size, color, cy, shadow_col=(0,0,0), offset=3):
    font = get_font(size)
    w = font.size(text)[0]
    draw_text(surface, text, size, color, SCREEN_W//2-w//2, cy, shadow_col, offset)

def draw_panel(x, y, w, h, fill_col, border_col, border_w=2, radius=12):
    """
    Rounded glass panel.  Technique:
    - Drop shadow: plain surface + set_alpha → no black box
    - Panel body: SRCALPHA surface + draw.rect(border_radius) → rounded corners
      (draw.rect on SRCALPHA DOES respect border_radius for corner transparency)
    - Sheen/shadow bands: drawn directly with reduced-alpha plain surface then
      clipped by blitting onto panel with BLEND_RGBA_MIN so they don't overflow
    """
    # ── Drop shadow ──
    for sh_off in range(7, 0, -1):
        ss = pygame.Surface((w + sh_off*2, h + sh_off*2))
        ss.fill((0, 0, 0))
        ss.set_colorkey((255, 0, 255))          # magenta = transparent
        ss.fill((255, 0, 255))
        pygame.draw.rect(ss, (0, 0, 0), (0, 0, w+sh_off*2, h+sh_off*2), border_radius=radius+sh_off)
        ss.set_alpha(int(50 * (1 - sh_off / 7)))
        screen.blit(ss, (x - sh_off, y + sh_off + 2))

    # ── Panel body (rounded, semi-transparent) ──
    # SRCALPHA + draw.rect with border_radius correctly clips corners to alpha=0
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    r, g, b = fill_col[0], fill_col[1], fill_col[2]
    pygame.draw.rect(panel, (r, g, b, 215), (0, 0, w, h), border_radius=radius)

    # Top sheen strip — drawn as SRCALPHA rect then blitted onto panel
    sh_h = max(3, h // 5)
    sheen = pygame.Surface((w - 8, sh_h), pygame.SRCALPHA)
    pygame.draw.rect(sheen,
                     (min(255,r+65), min(255,g+65), min(255,b+65), 50),
                     (0, 0, w-8, sh_h), border_radius=6)
    panel.blit(sheen, (4, 4))

    # Bottom depth shadow — thin dark strip
    bot_h = max(2, h // 12)
    depth = pygame.Surface((w - 8, bot_h), pygame.SRCALPHA)
    pygame.draw.rect(depth, (0, 0, 0, 45), (0, 0, w-8, bot_h), border_radius=4)
    panel.blit(depth, (4, h - bot_h - 3))

    screen.blit(panel, (x, y))

    # ── Border + inner rim ──
    pygame.draw.rect(screen, border_col, (x, y, w, h), border_w, border_radius=radius)
    light = tuple(min(255, c + 80) for c in border_col)
    pygame.draw.rect(screen, light, (x+1, y+1, w-2, h-2), 1, border_radius=radius-1)


def draw_pill(x, y, w, h, fill_col, border_col, alpha=215):
    """Pill badge using SRCALPHA + draw.rect(border_radius) — correct approach."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    r, g, b = fill_col[0], fill_col[1], fill_col[2]
    pygame.draw.rect(surf, (r, g, b, alpha), (0, 0, w, h), border_radius=h // 2)
    # Gloss sheen
    sheen = pygame.Surface((w - 10, h // 3), pygame.SRCALPHA)
    pygame.draw.rect(sheen, (255, 255, 255, 45), (0, 0, w-10, h//3), border_radius=h // 4)
    surf.blit(sheen, (5, 4))
    screen.blit(surf, (x, y))
    pygame.draw.rect(screen, border_col, (x, y, w, h), 2, border_radius=h // 2)


def draw_title(title, subtitle=None):
    theme = THEMES[current_theme]
    acc = theme['accent']
    font = get_font(76)
    tw, th = font.size(title)
    tx = SCREEN_W // 2 - tw // 2

    # Backing: plain surface filled black + set_alpha, clipped with border_radius
    # via SRCALPHA so corners are transparent
    backing = pygame.Surface((tw + 52, th + 16), pygame.SRCALPHA)
    pygame.draw.rect(backing, (0, 0, 0, 125), (0, 0, tw+52, th+16), border_radius=14)
    screen.blit(backing, (tx - 26, 14))

    # Stroke outline (8-direction black shadow)
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
        st = font.render(title, True, (0, 0, 0))
        st.set_alpha(150)
        screen.blit(st, (tx + dx, 18 + dy))
    screen.blit(font.render(title, True, acc), (tx, 18))

    # Ruled line
    ly = 104
    pygame.draw.line(screen, acc, (70, ly), (SCREEN_W-70, ly), 3)
    pygame.draw.line(screen, acc, (70, ly+6), (SCREEN_W-70, ly+6), 1)
    bl = tuple(min(255, c+80) for c in acc)
    for ex in [70, SCREEN_W-70]:
        pygame.draw.circle(screen, bl, (ex, ly), 6)
        pygame.draw.circle(screen, (255, 255, 255), (ex, ly), 3)

    if subtitle:
        sf = get_font(30)
        sw = sf.size(subtitle)[0]
        sx = SCREEN_W // 2 - sw // 2
        for dx, dy in [(-1,1),(1,1),(0,2)]:
            s2 = sf.render(subtitle, True, (0,0,0)); s2.set_alpha(140)
            screen.blit(s2, (sx+dx, 72+dy))
        screen.blit(sf.render(subtitle, True, theme['text']), (sx, 72))



def draw_button(x, y, w, h, text, fill, text_col, border_col, hovered=False):
    if hovered:
        x-=4; y-=4; w+=8; h+=8
        draw_panel(x,y,w,h,fill,border_col,border_w=4,radius=14)
    else:
        draw_panel(x,y,w,h,fill,border_col,border_w=2,radius=12)
    font_size = 50 if hovered else 44
    font = get_font(font_size)
    ts = font.render(text,True,text_col)
    tr = ts.get_rect(center=(x+w//2, y+h//2))
    sh = font.render(text,True,(0,0,0)); sh.set_alpha(160)
    screen.blit(sh, tr.move(3,3))
    if hovered:
        gs = font.render(text,True,border_col); gs.set_alpha(50)
        screen.blit(gs, tr.move(-2,-2))
    screen.blit(ts, tr)


def draw_hud(score, total_coins, bird):
    theme = THEMES[current_theme]
    acc=theme['accent']; dc=theme['dark']
    font_big=get_font(46); font_sm=get_font(30)
    # Score pill
    ss = f"  {score}"
    sw = font_big.size(ss)[0]+56
    draw_pill(10,10,sw,50,dc,acc,215)
    # Star icon inside pill
    for i in range(10):
        a=math.radians(-90+i*36); ri=10 if i%2==0 else 5
        sx2=int(32+ri*math.cos(a)); sy2=int(35+ri*math.sin(a))
        if i==0: star_pts=[(sx2,sy2)]
        else: star_pts.append((sx2,sy2))
    pygame.draw.polygon(screen,(255,220,0),star_pts)
    screen.blit(font_big.render(ss,True,acc),(42,14))
    # Coins pill
    cs=f"  {total_coins}"
    cw=font_sm.size(cs)[0]+46
    draw_pill(10,68,cw,38,dc,(180,140,0),205)
    draw_heart(screen,28,87,9,(255,210,0),(180,140,0))
    screen.blit(font_sm.render(cs,True,(255,210,0)),(36,74))
    # Powerup pills
    py=116
    if bird.immunity_time>0:
        frac=min(1.0,bird.immunity_time/5.0)
        draw_pill(10,py,235,55,(150,15,35),(255,80,110),225)
        draw_heart(screen,30,py+16,11,(255,60,90),(255,160,170))
        screen.blit(font_sm.render(f"IMMUNE  {bird.immunity_time:.1f}s",True,(255,200,210)),(50,py+14))
        pygame.draw.rect(screen,(80,5,15),(18,py+47,210,4),border_radius=2)
        pygame.draw.rect(screen,(255,90,120),(18,py+47,int(210*frac),4),border_radius=2)
        py+=65
    if bird.double_score_time>0:
        frac=min(1.0,bird.double_score_time/5.0)
        draw_pill(10,py,235,55,(110,95,0),(255,235,0),225)
        sp=[(int(28+(8 if i%2==0 else 4)*math.cos(math.radians(-90+i*36))),
             int(py+18+(8 if i%2==0 else 4)*math.sin(math.radians(-90+i*36)))) for i in range(10)]
        pygame.draw.polygon(screen,(255,235,0),sp)
        screen.blit(font_sm.render(f"2x SCORE  {bird.double_score_time:.1f}s",True,(255,255,160)),(50,py+14))
        pygame.draw.rect(screen,(70,60,0),(18,py+47,210,4),border_radius=2)
        pygame.draw.rect(screen,(255,235,0),(18,py+47,int(210*frac),4),border_radius=2)

# ── Init theme ────────────────────────────────────────────────────────────────

base_images = load_base_images()
bird_imgs, pipe_img, ground_img, text_color, accent_color, shadow_color, dark_color = apply_theme()
score=0; high_score=0; scored_pairs=set()
clock = pygame.time.Clock()

# ── Menus ─────────────────────────────────────────────────────────────────────

def show_how_to_play():
    running=True
    while running:
        clock.tick(60)
        screen.blit(BACKGROUND,(0,0))
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,70)); screen.blit(ov,(0,0))
        draw_title('HOW TO PLAY')
        lines=[
            ("CONTROLS",accent_color,30),
            ("  SPACE / UP / CLICK — Flap",text_color,24),
            ("  T — Cycle themes in-game",text_color,24),
            ("",text_color,24),
            ("GAMEPLAY",accent_color,30),
            ("  Pass pipes to score",text_color,24),
            ("  Score = coins earned",text_color,24),
            ("",text_color,24),
            ("POWERUPS",accent_color,30),
            ("  Heart = 5s pipe immunity",(255,90,110),24),
            ("  Star  = 2x score 5s",(255,215,0),24),
            ("",text_color,24),
            ("SHOP",accent_color,30),
            ("  Buy skins for coin boosts",text_color,24),
        ]
        cy=122
        for txt,col,sz in lines:
            if txt: draw_text(screen,txt,sz,col,60,cy,shadow_color,2)
            cy+=34
        draw_text(screen,'SPACE or ESC to go back',20,text_color,20,SCREEN_H-38,shadow_color,1)
        for ev in pygame.event.get():
            if ev.type==QUIT: pygame.quit(); sys.exit()
            if ev.type==KEYDOWN and ev.key in (K_SPACE,K_ESCAPE): play_sfx('deny'); running=False
        pygame.display.update()


def show_main_menu():
    global current_theme,bird_imgs,pipe_img,ground_img,text_color,accent_color,shadow_color,dark_color,total_coins
    sel=0
    while True:
        clock.tick(60)
        screen.blit(BACKGROUND,(0,0))
        # Coin badge
        draw_pill(SCREEN_W-248,10,234,50,dark_color,(180,140,0),215)
        draw_heart(screen,SCREEN_W-230,35,11,(255,210,0),(180,140,0))
        screen.blit(get_font(32).render(f"  {total_coins} coins",True,(255,210,0)),(SCREEN_W-218,22))
        draw_title('FLAPPY BIRD','Press SPACE or click to Play')
        bw,bh=260,68; bx=SCREEN_W//2-bw//2
        btns=[(bx,185,"PLAY"),(bx,283,"SHOP"),(bx,381,"HOW TO PLAY"),(bx,479,"THEMES"),(bx,577,"QUIT")]
        for i,(x,y,lbl) in enumerate(btns):
            draw_button(x,y,bw,bh,lbl,dark_color,accent_color if i==sel else text_color,accent_color,i==sel)
        draw_text(screen,'UP/DOWN: Select   SPACE: Confirm',18,text_color,10,SCREEN_H-38,shadow_color,1)
        for ev in pygame.event.get():
            if ev.type==QUIT: pygame.quit(); sys.exit()
            if ev.type==KEYDOWN:
                if ev.key==K_UP: sel=(sel-1)%len(btns); play_sfx('select_up')
                elif ev.key==K_DOWN: sel=(sel+1)%len(btns); play_sfx('select_down')
                elif ev.key==K_SPACE:
                    play_sfx('confirm')
                    if sel==0: return "play"
                    elif sel==1: show_shop_menu()
                    elif sel==2: show_how_to_play()
                    elif sel==3: show_theme_menu()
                    elif sel==4: pygame.quit(); sys.exit()
            if ev.type==MOUSEBUTTONDOWN: play_sfx('confirm'); return "play"
        pygame.display.update()


def show_theme_menu():
    global current_theme,bird_imgs,pipe_img,ground_img,text_color,accent_color,shadow_color,dark_color
    sel=current_theme
    while True:
        clock.tick(60)
        screen.blit(BACKGROUND,(0,0))
        draw_title('SELECT THEME')
        # Show two columns of 4
        for i,theme in enumerate(THEMES):
            col_x = SCREEN_W//2-310 if i<4 else SCREEN_W//2+10
            row_y = 120+(i%4)*148
            is_sel=(i==sel)
            tc=theme['dark'] if not is_sel else tuple(min(255,c+30) for c in theme['dark'])
            draw_panel(col_x,row_y,300,135,tc,theme['accent'],4 if is_sel else 2)
            # Mini sky preview
            sky_s=pygame.Surface((280,50),pygame.SRCALPHA)
            _grad(sky_s,theme['bg'],tuple(max(0,c-30) for c in theme['bg']))
            pygame.draw.rect(sky_s,(0,0,0,0),sky_s.get_rect(),border_radius=6)
            screen.blit(sky_s,(col_x+10,row_y+8))
            # Bird preview swatch
            bsurf=pygame.Surface((40,35),pygame.SRCALPHA); bsurf.fill((0,0,0,0))
            draw_bird_shape(bsurf,20,17,theme['bird'],wing_frame=1,scale=0.9)
            screen.blit(bsurf,(col_x+20,row_y+18))
            # Pipe colour swatch
            pygame.draw.rect(screen,theme['pipe'],(col_x+70,row_y+18,20,30))
            pygame.draw.rect(screen,tuple(min(255,c+60) for c in theme['pipe']),(col_x+72,row_y+20,5,26))
            # Name
            draw_text(screen,theme['name'].upper(),28,
                      theme['accent'] if is_sel else theme['text'],
                      col_x+12,row_y+68,theme['shadow'],2)
            if is_sel:
                draw_text(screen,"SELECTED",20,(255,255,100),col_x+12,row_y+100,theme['shadow'],1)
        draw_text(screen,'UP/DOWN: Select   SPACE: Apply   ESC: Back',16,text_color,10,SCREEN_H-38,shadow_color,1)
        for ev in pygame.event.get():
            if ev.type==QUIT: pygame.quit(); sys.exit()
            if ev.type==KEYDOWN:
                if ev.key==K_UP: sel=(sel-1)%len(THEMES); play_sfx('select_up')
                elif ev.key==K_DOWN: sel=(sel+1)%len(THEMES); play_sfx('select_down')
                elif ev.key==K_LEFT: sel=(sel-4)%len(THEMES); play_sfx('select_up')
                elif ev.key==K_RIGHT: sel=(sel+4)%len(THEMES); play_sfx('select_down')
                elif ev.key==K_SPACE:
                    current_theme=sel
                    bird_imgs,pipe_img,ground_img,text_color,accent_color,shadow_color,dark_color=apply_theme()
                    play_sfx('confirm'); return
                elif ev.key==K_ESCAPE: play_sfx('deny'); return
        pygame.display.update()


def show_shop_menu():
    global total_coins,owned_bird_skins,text_color,accent_color,shadow_color,dark_color
    sel=0; per=4
    while True:
        clock.tick(60)
        screen.blit(BACKGROUND,(0,0))
        draw_title('BIRD SHOP')
        draw_pill(SCREEN_W-248,10,234,50,dark_color,(180,140,0),215)
        draw_heart(screen,SCREEN_W-230,35,11,(255,210,0),(180,140,0))
        screen.blit(get_font(32).render(f"  {total_coins} coins",True,(255,210,0)),(SCREEN_W-218,22))
        start=( sel//per)*per
        for i,sd in enumerate(BIRD_SKINS[start:start+per]):
            ai=start+i; sn,sc,cost,pb,isp,isl=sd
            yp=118+i*158; is_sel=(ai==sel); is_owned=(ai in owned_bird_skins)
            bc2=tuple(min(255,c+25) for c in dark_color) if is_sel else dark_color
            bc3=(255,215,0) if isl else (accent_color if is_sel else shadow_color)
            draw_panel(55,yp,1085,148,bc2,bc3,5 if is_sel else 2)
            # Bird preview
            ps=pygame.Surface((100,85),pygame.SRCALPHA); ps.fill((0,0,0,0))
            draw_bird_shape(ps,50,42,sc,wing_frame=1,scale=1.5); screen.blit(ps,(70,yp+30))
            # Tag
            tag=""; tag_c=accent_color
            if isl: tag=" ★ LEGENDARY"; tag_c=(255,215,0)
            elif isp: tag=" ♦ PREMIUM"; tag_c=(218,165,32)
            draw_text(screen,sn+tag,30,tag_c,195,yp+18,shadow_color,2)
            draw_text(screen,f"Powerup Boost: +{int((pb-1)*100)}%",22,text_color,195,yp+58,shadow_color,1)
            # Bar showing boost level
            bar_len=int(min(400,(pb-1)*200))
            pygame.draw.rect(screen,(40,40,40),(195,yp+88,400,10),border_radius=5)
            bar_c=(255,215,0) if isl else (tag_c if isp else accent_color)
            if bar_len>0: pygame.draw.rect(screen,bar_c,(195,yp+88,bar_len,10),border_radius=5)
            # Price / owned
            if is_owned:
                draw_text(screen,"✓ OWNED",36,(60,220,60),970,yp+54,shadow_color,2)
            else:
                cc=(255,70,70) if isl else (255,215,0)
                draw_text(screen,f"{cost} coins",30,cc,970,yp+54,shadow_color,2)
        pages=(len(BIRD_SKINS)+per-1)//per; pg=sel//per+1
        draw_text(screen,f'Page {pg}/{pages}  |  UP/DOWN: Select   SPACE: Buy   ESC: Back',18,text_color,20,SCREEN_H-38,shadow_color,1)
        for ev in pygame.event.get():
            if ev.type==QUIT: pygame.quit(); sys.exit()
            if ev.type==KEYDOWN:
                if ev.key==K_UP: sel=(sel-1)%len(BIRD_SKINS); play_sfx('select_up')
                elif ev.key==K_DOWN: sel=(sel+1)%len(BIRD_SKINS); play_sfx('select_down')
                elif ev.key==K_SPACE:
                    sd=BIRD_SKINS[sel]
                    if sel not in owned_bird_skins and total_coins>=sd[2]:
                        total_coins-=sd[2]; owned_bird_skins.add(sel)
                        if sd[5]: play_sfx('victory')
                        else: play_sfx('confirm')
                    else: play_sfx('deny')
                elif ev.key==K_ESCAPE: return
        pygame.display.update()


def show_difficulty_selector():
    global current_theme,bird_imgs,pipe_img,ground_img,text_color,accent_color,shadow_color,dark_color
    sel=1
    while True:
        clock.tick(60)
        screen.blit(BACKGROUND,(0,0))
        draw_title('SELECT DIFFICULTY')
        diff_cols=[(60,200,60),(255,215,0),(255,120,0),(220,50,50)]
        for i,(dn,sp,gr,gp) in enumerate(DIFFICULTIES):
            yp=160+i*130; is_sel=(i==sel); dc2=diff_cols[i]
            fc=tuple(min(255,c+20) for c in dark_color) if is_sel else dark_color
            draw_panel(SCREEN_W//2-200,yp,400,115,fc,dc2,5 if is_sel else 2)
            draw_text(screen,dn.upper(),38,dc2 if is_sel else text_color,SCREEN_W//2-180,yp+14,shadow_color,2)
            draw_text(screen,f"Speed: {sp}  |  Gravity: {gr}  |  Gap: {gp}px",20,text_color,SCREEN_W//2-180,yp+62,(0,0,0),1)
            if is_sel: draw_text(screen,"▶ SELECTED",20,(255,255,100),SCREEN_W//2-180,yp+88,shadow_color,1)
        draw_text(screen,'UP/DOWN: Select   SPACE: Start',16,text_color,10,SCREEN_H-38,shadow_color,1)
        for ev in pygame.event.get():
            if ev.type==QUIT: pygame.quit(); sys.exit()
            if ev.type==KEYDOWN:
                if ev.key==K_UP: sel=(sel-1)%len(DIFFICULTIES); play_sfx('select_up')
                elif ev.key==K_DOWN: sel=(sel+1)%len(DIFFICULTIES); play_sfx('select_down')
                elif ev.key==K_SPACE: play_sfx('confirm'); return sel
            if ev.type==MOUSEBUTTONDOWN: play_sfx('confirm'); return sel
        pygame.display.update()


def show_bird_selector():
    global current_theme,text_color,accent_color,shadow_color,dark_color
    sel=0
    while True:
        clock.tick(60)
        screen.blit(BACKGROUND,(0,0))
        draw_title('CHOOSE YOUR BIRD')
        owned=sorted(owned_bird_skins)
        for di,bi in enumerate(owned):
            sn,sc,cost,pb,isp,isl=BIRD_SKINS[bi]
            yp=128+di*130; is_sel=(di==sel)
            fc=tuple(min(255,c+25) for c in dark_color) if is_sel else dark_color
            bc4=(255,215,0) if isl else (accent_color if is_sel else shadow_color)
            draw_panel(140,yp,900,120,fc,bc4,5 if is_sel else 2)
            ps=pygame.Surface((90,80),pygame.SRCALPHA); ps.fill((0,0,0,0))
            draw_bird_shape(ps,45,40,sc,wing_frame=di%4,scale=1.4); screen.blit(ps,(158,yp+18))
            tag=""; tc5=accent_color
            if isl: tag=" ★"; tc5=(255,215,0)
            elif isp: tag=" ♦"; tc5=(218,165,32)
            draw_text(screen,sn+tag,36,tc5,270,yp+14,shadow_color,2)
            draw_text(screen,f"Boost: +{int((pb-1)*100)}%",24,(255,210,0),270,yp+62,shadow_color,1)
        draw_text(screen,'UP/DOWN: Select   SPACE: Confirm',18,text_color,10,SCREEN_H-38,shadow_color,1)
        for ev in pygame.event.get():
            if ev.type==QUIT: pygame.quit(); sys.exit()
            if ev.type==KEYDOWN:
                if ev.key==K_UP: sel=(sel-1)%len(owned); play_sfx('select_up')
                elif ev.key==K_DOWN: sel=(sel+1)%len(owned); play_sfx('select_down')
                elif ev.key in (K_SPACE,K_RETURN): return owned[sel]
            if ev.type==MOUSEBUTTONDOWN: return owned[sel]
        pygame.display.update()


def show_game_over(final_score, hs, coins, tc):
    global current_theme,bird_imgs,pipe_img,ground_img,text_color,accent_color,shadow_color,dark_color
    sel=0; is_best=final_score>=hs and final_score>0
    while True:
        clock.tick(60)
        screen.blit(BACKGROUND,(0,0))
        ov=pygame.Surface((SCREEN_W,SCREEN_H)); ov.set_alpha(130); ov.fill((0,0,0)); screen.blit(ov,(0,0))
        pw,ph=520,590; px=SCREEN_W//2-pw//2
        draw_panel(px,20,pw,ph,dark_color,accent_color,5)
        go_c=(255,80,80) if not is_best else (255,215,0)
        draw_text_centered(screen,'GAME OVER',70,go_c,38,shadow_color,4)
        if is_best: draw_text_centered(screen,'★  NEW BEST!  ★',32,(255,215,0),118,shadow_color,2)
        draw_text(screen,f'Score:',40,text_color,px+50,168,shadow_color,2)
        draw_text(screen,f'{final_score}',40,accent_color,px+280,168,shadow_color,2)
        draw_text(screen,f'Best:',36,(255,215,0),px+50,220,shadow_color,2)
        draw_text(screen,f'{hs}',36,(255,215,0),px+280,220,shadow_color,2)
        pygame.draw.line(screen,accent_color,(px+30,265),(px+pw-30,265),1)
        draw_text(screen,f'+{coins} coins earned',34,(100,255,100),px+50,278,shadow_color,2)
        draw_text(screen,f'Total: {tc} coins',32,(255,210,0),px+50,325,shadow_color,2)
        pygame.draw.line(screen,accent_color,(px+30,370),(px+pw-30,370),1)
        bw2,bh2=380,78; bx2=px+(pw-bw2)//2
        for i,(lbl,by2) in enumerate([("PLAY AGAIN",385),("MAIN MENU",475)]):
            draw_button(bx2,by2,bw2,bh2,lbl,dark_color,
                        accent_color if i==sel else text_color,accent_color,i==sel)
        for ev in pygame.event.get():
            if ev.type==QUIT: pygame.quit(); sys.exit()
            if ev.type==KEYDOWN:
                if ev.key==K_UP: sel=(sel-1)%2; play_sfx('select_up')
                elif ev.key==K_DOWN: sel=(sel+1)%2; play_sfx('select_down')
                elif ev.key==K_SPACE: play_sfx('confirm'); return sel
            if ev.type==MOUSEBUTTONDOWN: play_sfx('confirm'); return 0
        pygame.display.update()

# ── Main game loop ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    while True:
        show_main_menu()
        current_difficulty = show_difficulty_selector()
        selected_skin_idx  = show_bird_selector()

        _, GAME_SPEED, GRAVITY, PIPE_GAP = DIFFICULTIES[current_difficulty]
        sn,bird_color,cost,powerup_boost,_,_ = BIRD_SKINS[selected_skin_idx]
        bird_imgs = create_bird_graphics(bird_color)

        play_again = True
        while play_again:
            score=0; scored_pairs=set(); pipe_pair_id=0; coins_earned_this_run=0
            _last_pipe_center = None

            bird_group  = pygame.sprite.Group()
            bird        = Bird(bird_imgs); bird_group.add(bird)

            ground_group = pygame.sprite.Group()
            for i in range(2): ground_group.add(Ground(GROUND_W*i, ground_img))

            pipe_group = pygame.sprite.Group()
            for i in range(3):
                p1,p2=get_random_pipes(SCREEN_W+PIPE_SPACING*i, pipe_pair_id)
                pipe_pair_id+=1; pipe_group.add(p1,p2)

            # ── GET READY ──
            waiting=True
            while waiting:
                clock.tick(60)
                screen.blit(BACKGROUND,(0,0))
                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])
                    ground_group.add(Ground(GROUND_W-20,ground_img))
                bird.begin(); ground_group.update()
                pipe_group.draw(screen); ground_group.draw(screen)
                draw_bird_direct(screen, bird, bird_color)
                draw_text_centered(screen,'GET READY!',56,accent_color,160,shadow_color,3)
                draw_text_centered(screen,f'Bird: {sn}',28,text_color,228,shadow_color,2)
                for ev in pygame.event.get():
                    if ev.type==QUIT: pygame.quit(); sys.exit()
                    if ev.type==KEYDOWN:
                        if ev.key in (K_SPACE,K_UP): bird.bump(); play_sfx('flap'); waiting=False
                        elif ev.key==K_t:
                            current_theme=(current_theme+1)%len(THEMES)
                            bird_imgs,pipe_img,ground_img,text_color,accent_color,shadow_color,dark_color=apply_theme()
                            bird=Bird(bird_imgs); bird_group.empty(); bird_group.add(bird)
                            ground_group.empty()
                            for i in range(2): ground_group.add(Ground(GROUND_W*i,ground_img))
                    if ev.type==MOUSEBUTTONDOWN and ev.button==1: bird.bump(); play_sfx('flap'); waiting=False
                pygame.display.update()

            # ── PLAYING ──
            playing=True; float_scores=[]; dt=1/60.0
            powerup_group=pygame.sprite.Group(); pu_counter=0
            pu_rate=int(200/powerup_boost)

            while playing:
                clock.tick(60)
                # events
                for ev in pygame.event.get():
                    if ev.type==QUIT: pygame.quit(); sys.exit()
                    if ev.type==KEYDOWN:
                        if ev.key in (K_SPACE,K_UP): bird.bump(); play_sfx('flap')
                        elif ev.key==K_t:
                            current_theme=(current_theme+1)%len(THEMES)
                            bird_imgs,pipe_img,ground_img,text_color,accent_color,shadow_color,dark_color=apply_theme()
                    if ev.type==MOUSEBUTTONDOWN and ev.button==1: bird.bump(); play_sfx('flap')

                # ground recycling
                if is_off_screen(ground_group.sprites()[0]):
                    ground_group.remove(ground_group.sprites()[0])
                    ground_group.add(Ground(GROUND_W-20,ground_img))

                # pipe recycling — collect ALL offscreen first, then spawn
                offscreen=[p for p in pipe_group if is_off_screen(p)]
                if offscreen:
                    for p in offscreen: pipe_group.remove(p)
                    rx=max((p.rect.x for p in pipe_group), default=SCREEN_W)
                    p1,p2=get_random_pipes(rx+PIPE_SPACING,pipe_pair_id)
                    pipe_pair_id+=1; pipe_group.add(p1,p2)

                # update
                bird_group.update(); ground_group.update(); pipe_group.update()
                bird.immunity_time      = max(0,bird.immunity_time-dt)
                bird.double_score_time  = max(0,bird.double_score_time-dt)
                bird.score_multiplier   = 2.0 if bird.double_score_time>0 else 1.0

                # powerup spawning
                pu_counter+=1
                if pu_counter>pu_rate:
                    pu_counter=0
                    pt=random.choice([Powerup.IMMUNITY,Powerup.DOUBLE_SCORE])
                    powerup_group.add(Powerup(SCREEN_W+150,random.randint(150,SCREEN_H-160),pt,accent_color))

                # powerup updating
                dead_pu=[p for p in powerup_group if not p.update(dt)]
                for p in dead_pu: powerup_group.remove(p)

                # powerup collision
                hits=pygame.sprite.groupcollide(bird_group,powerup_group,False,True,pygame.sprite.collide_rect)
                for _,plist in hits.items():
                    for pu in plist:
                        if pu.powerup_type==Powerup.IMMUNITY: bird.immunity_time=5.0
                        else: bird.double_score_time=5.0; score=int(score*2)

                # ── COLLISION CHECK (before draw so no 1-frame ghost) ──
                body=pygame.Rect(bird.rect.centerx-10,bird.rect.centery-8,20,16)
                ground_hit=any(body.colliderect(s.rect) for s in ground_group)
                pipe_hit=(any(body.colliderect(s.rect) for s in pipe_group) and bird.immunity_time<=0)
                ceil_hit=bird.rect.top<=5

                if ground_hit or pipe_hit or ceil_hit:
                    play_sfx('hit')
                    play_sfx('death')
                    coins_earned_this_run=int(score); total_coins+=coins_earned_this_run
                    high_score=max(high_score,score)
                    # Non-blocking death pause
                    for _ in range(36):
                        clock.tick(60)
                        for ev in pygame.event.get():
                            if ev.type==QUIT: pygame.quit(); sys.exit()
                    playing=False
                    continue

                # scoring
                for p in pipe_group:
                    if p.pair_id not in scored_pairs and p.rect.right<bird.rect.left:
                        scored_pairs.add(p.pair_id)
                        inc=int(bird.score_multiplier); score+=inc
                        float_scores.append(FloatingScore(p.rect.centerx,p.rect.centery,inc,accent_color))
                        play_sfx('point')

                # ── DRAW ──
                screen.blit(BACKGROUND,(0,0))
                pipe_group.draw(screen); ground_group.draw(screen)
                draw_bird_direct(screen,bird,bird_color)

                # powerups
                for pu in powerup_group: pu.draw(screen)

                # immunity shield — plain surface + colorkey, no SRCALPHA
                if bird.immunity_time>0:
                    sp2=int(4*math.sin(pygame.time.get_ticks()/70))
                    sr=46+sp2
                    sh_s=pygame.Surface((sr*2+4, sr*2+4))
                    sh_s.fill((0,0,0)); sh_s.set_colorkey((0,0,0))
                    pygame.draw.ellipse(sh_s,(80,160,255),(2,2,sr*2,sr*2))
                    sh_s.set_alpha(55)
                    screen.blit(sh_s,(bird.rect.centerx-sr-2,bird.rect.centery-sr-2),
                                special_flags=pygame.BLEND_RGB_ADD)
                    sh_s2=pygame.Surface((sr*2+4, sr*2+4))
                    sh_s2.fill((0,0,0)); sh_s2.set_colorkey((0,0,0))
                    pygame.draw.ellipse(sh_s2,(140,210,255),(2,2,sr*2,sr*2),3)
                    sh_s2.set_alpha(130)
                    screen.blit(sh_s2,(bird.rect.centerx-sr-2,bird.rect.centery-sr-2),
                                special_flags=pygame.BLEND_RGB_ADD)

                draw_hud(score,total_coins,bird)

                # floating scores
                float_scores=[fs for fs in float_scores if fs.update(dt)]
                for fs in float_scores: fs.draw(screen)

                pygame.display.update()

            choice=show_game_over(score,high_score,coins_earned_this_run,total_coins)
            if choice==1: play_again=False