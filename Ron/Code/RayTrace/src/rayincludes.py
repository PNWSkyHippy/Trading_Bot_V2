# These remain the same for every frame in this particular shot.
common_scene1_settings = {
    "book": "2",
    "chapter": "6",
    "light1": "2,7,3,0.8",
    "light2": "-3,4,1,0.2",
}


# These are the only camera poses you direct by hand.
# Python generates every frame between them.
scene1_keyframes = [
    {
        "frame": 1,
        "camera": (46, 3, 32),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 16,
        "camera": (46, 10, 32),
        "lookat": (0, 2, 0),
        "vfov": 20,
    },
    {
        "frame": 32,
        "camera": (32, 10, 20),
        "lookat": (0, 2, 0),
        "vfov": 32,
    },
    {
        "frame": 48,
        "camera": (10, 5, 8),
        "lookat": (0, 0.5, 0),
        "vfov": 30,
    },
    {
        "frame": 64,
        "camera": (10, 6, -5),
        "lookat": (0, 2, 0),
        "vfov": 28,
    },
    {
        "frame": 80,
        "camera": (20, 12, -15),
        "lookat": (0, 2, 0),
        "vfov": 26,
    },
    {
        "frame": 96,
        "camera": (20, 18, -15),
        "lookat": (0, 2, 0),
        "vfov": 22,
    },
    {
        "frame": 112,
        "camera": (20, 24, -15),
        "lookat": (4, 0.5, 0),
        "vfov": 30,
    },
    {
        "frame": 128,
        "camera": (20, 24, -12),
        "lookat": (5, 0.6, 0),
        "vfov": 32,
    },
    {
        "frame": 144,
        "camera": (20, 30, -12),
        "lookat": (10, 0.7, 0),
        "vfov": 34,
    },
    {
        "frame": 160,
        "camera": (15, 24, -12),
        "lookat": (2, 1, 5, 0),
        "vfov": 36,
    },
    {
        "frame": 176,
        "camera": (15, 24, -12),
        "lookat": (2, 1.5, 0),
        "vfov": 38,
    },
    {
        "frame": 192,
        "camera": (15, 24, -12),
        "lookat": (2, 1.5, 0),
        "vfov": 40,
    },
]


# List of premade scenes to render
# credit https://github.com/RayTracing
SCENES_BOOK2 = [
    ("1", "1: Bouncing Spheres"),
    ("2", "2: Checkered Spheres"),
    ("3", "3: Earth Globe (Texture Map)"),
    ("4", "4: Perlin Noise Spheres"),
    ("5", "5: Planar Quads"),
    ("6", "6: Simple Light Box"),
    ("7", "7: Cornell Box"),
    ("8", "8: Cornell Box with Smoke"),
    ("9", "9: Final Complex Scene"),
]

# As this is a front end to a c++ ray tracing engine
#  we define the parameters needed for calling the tracer
#  with proper arguments
BOOK_BINARIES = {
    "Book 1: In One Weekend": {
        "mac_dir": "/Users/ronh/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "binary": "inoneweekend",
        "has_scenes": False,
        "default_res": (672, 378),
        "book_id": 1,
    },
    "Book 2: The Next Week": {
        "mac_dir": "/Users/ronh/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "binary": "inoneweekend",
        "has_scenes": True,
        "default_res": (600, 600),
        "book_id": 2,
    },
    "Book 3: The Rest of Your Life": {
        "mac_dir": "/Users/ronh/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "wsl_dir": "/mnt/c/Users/Linda/Trading_Bot_V2/Ron/Code/RayTrace/src",
        "binary": "inoneweekend",
        "has_scenes": False,
        "default_res": (600, 600),
        "book_id": 3,
    },
}

BOOK_SCENE_CHOICES = {
    "Book 1: In One Weekend": ["1: Default Book 1 Scene"],
    "Book 2: The Next Week": [label for _, label in SCENES_BOOK2],
    "Book 3: The Rest of Your Life": ["1: Default Book 3 Scene"],
}
