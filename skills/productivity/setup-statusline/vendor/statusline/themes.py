"""Theme system for the statusline.

A `Theme` is a flat dataclass holding every colour the statusline draws.
Selection is layered (CLI flag → env var → config file → built-in default)
and resolution happens in `statusline_command.py::main`. See
`docs/adr/0002-theme-system.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]


def fg(r: int, g: int, b: int) -> str:
    return f'\033[38;2;{r};{g};{b}m'


def fg256(n: int) -> str:
    return f'\033[38;5;{n}m'


@dataclass(frozen=True)
class ModelColors:
    label:      str


@dataclass(frozen=True)
class Theme:
    name: str

    # Decorative slots (ANSI escapes)
    border:       str
    border_off:   str
    pwd:          str
    branch:       str
    commit:       str
    session:      str
    skills:       str
    time:         str
    tok:          str
    tok_dim:      str
    tok_day:      str
    tok_day_dim:  str
    cost:         str
    bar_fill:     str
    bar_empty:    str
    dim_green:    str
    label:        str
    ctx:          str
    ctx_dim:      str
    white_brt:    str
    arrow:        str
    dirty:        str
    icon_path:    str
    tok_icon:     str
    model:        str

    # Three-step ladder (fill_colour & day_cost_colour)
    safe:         str
    warn:         str
    alert:        str
    yellow:       str
    tok_arrow:    str

    # Per-model identity colour
    models:       dict[str, ModelColors]

    # Gradients
    grad_stops:      tuple[tuple[float, RGB], ...]
    grey_rgb:        RGB
    spark_stops:     tuple[tuple[float, RGB], ...]
    spec_gradients:  tuple[tuple[RGB, RGB, RGB], ...]
    spec_empty_ansi: str


CLAUDE_DARK = Theme(
    name        = 'claude-dark',

    # Monokai Classic palette:
    #   #f92672 pink   (249,  38, 114)
    #   #a6e22e green  (166, 226,  46)
    #   #66d9ef cyan   (102, 217, 239)
    #   #fd971f orange (253, 151,  31)
    #   #ae81ff purple (174, 129, 255)
    border      = fg256(244),
    border_off  = fg256(242),
    pwd         = fg(102, 217, 239),  # monokai cyan
    branch      = fg(166, 226,  46),  # monokai green
    commit      = fg256(244),
    session     = fg256(244),
    skills      = fg(253, 151,  31),  # monokai orange
    time        = fg256(244),
    tok         = fg(102, 217, 239),  # monokai cyan
    tok_dim     = fg256(244),
    tok_day     = fg(174, 129, 255),  # monokai purple
    tok_day_dim = fg256(240),
    cost        = fg(249,  38, 114),  # monokai pink
    bar_fill    = fg(166, 226,  46),  # monokai green
    bar_empty   = fg256(238),
    dim_green   = fg(166, 226,  46),  # monokai green
    label       = fg256(244),
    ctx         = fg(253, 151,  31),  # monokai orange
    ctx_dim     = fg256(248),
    white_brt   = fg256(15),
    arrow       = fg(166, 226,  46),  # monokai green
    dirty       = fg(253, 151,  31),  # monokai orange
    icon_path   = fg(102, 217, 239),  # monokai cyan
    tok_icon    = fg(253, 151,  31),  # monokai orange
    model       = fg(174, 129, 255),  # monokai purple

    safe        = fg(166, 226,  46),  # monokai green
    warn        = fg(253, 151,  31),  # monokai orange
    alert       = fg(249,  38, 114),  # monokai pink
    yellow      = fg(253, 151,  31),  # monokai orange (no yellow in classic palette)
    tok_arrow   = fg(253, 151,  31),  # monokai orange

    models = {
        'opus':   ModelColors(
            label      = fg(253, 151,  31),
        ),
        'sonnet': ModelColors(
            label      = fg(166, 226,  46),
        ),
        'haiku':  ModelColors(
            label      = fg(102, 217, 239),
        ),
        'other':  ModelColors(
            label      = fg(174, 129, 255),
        ),
    },


    grad_stops = (
        (0.00, (249,  38, 114)),  # #f92672 monokai pink
        (0.33, (180,  74, 255)),  # #b44aff purple
        (0.67, ( 74, 240, 192)),  # #4af0c0 mint/teal
        (1.00, ( 81, 162, 255)),  # #51a2ff blue
    ),
    grey_rgb    = (108, 108, 108),
    spark_stops = (
        (0.00, (179,  46,  32)),
        (0.50, (200,  55,  40)),
        (1.00, (204,  65,  51)),
    ),
    spec_gradients = (
        (( 20,  60, 200), ( 20, 180, 240), (100, 240, 255)),  # Ocean
        ((200,  80,  10), (245,  30, 100), (255, 160,  80)),  # Sunset
        (( 10, 120,  40), ( 80, 210,  20), (200, 255,  60)),  # Forest
        (( 80,  20, 200), (160,  60, 255), (220, 160, 255)),  # Lavender
        ((160,  20,  10), (240, 120,  10), (255, 220,  30)),  # Ember
        (( 20,  80, 160), ( 60, 180, 240), (210, 240, 255)),  # Arctic
        ((120,  50,  10), (200, 120,  20), (255, 200,  80)),  # Copper
        ((160,  10,  50), (240,  60, 130), (255, 180, 210)),  # Rose
        (( 10, 110,  90), ( 20, 210, 150), (120, 255, 200)),  # Mint
        (( 50,  10, 160), (180,  20, 220), (255, 100, 240)),  # Nebula
        ((140,  10, 180), ( 40, 100, 255), ( 20, 220, 200)),  # Aurora
        ((200, 160,  10), (240,  80,  20), (180,  20,  80)),  # Volcano
    ),
    spec_empty_ansi = fg256(233),
)


CLAUDE_LIGHT = Theme(
    name        = 'claude-light',

    border      = fg256(244),
    border_off  = fg256(246),
    pwd         = fg(0, 95, 175),
    branch      = fg256(28),
    commit      = fg256(243),
    session     = fg256(243),
    skills      = fg(160, 110, 30),
    time        = fg256(243),
    tok         = fg(40, 110, 150),
    tok_dim     = fg256(245),
    tok_day     = fg(70, 120, 130),
    tok_day_dim = fg256(247),
    cost        = fg(175, 80, 80),
    bar_fill    = fg256(28),
    bar_empty   = fg256(252),
    dim_green   = fg(60, 130, 70),
    label       = fg256(243),
    ctx         = fg(180, 100, 50),
    ctx_dim     = fg256(245),
    white_brt   = fg256(232),
    arrow       = fg(0, 135, 0),
    dirty       = fg(180, 110, 20),
    icon_path   = fg(40, 110, 160),
    tok_icon    = fg(160, 130, 20),
    model       = fg256(96),

    safe        = fg256(28),
    warn        = fg(180, 110, 20),
    alert       = fg(170, 50, 50),
    yellow      = fg(160, 130, 20),
    tok_arrow   = fg(0, 0, 0),

    models = {
        'opus':   ModelColors(
            label      = fg(150, 110,  20),
        ),
        'sonnet': ModelColors(
            label      = fg256(28),
        ),
        'haiku':  ModelColors(
            label      = fg(0, 95, 175),
        ),
        'other':  ModelColors(
            label      = fg256(96),
        ),
    },


    grad_stops = (
        (0.00, ( 30, 158,  60)),
        (0.25, (180, 172,  15)),
        (0.50, (191, 105,  15)),
        (0.75, (165,  30,  38)),
        (1.00, (128,  45, 158)),
    ),
    grey_rgb    = (160, 160, 160),
    spark_stops = (
        (0.00, (145,  35,  25)),
        (0.50, (165,  45,  32)),
        (1.00, (175,  55,  42)),
    ),
    spec_gradients = (
        (( 15,  45, 150), ( 15, 135, 180), ( 75, 180, 191)),  # Ocean
        ((150,  60,   8), (184,  22,  75), (191, 120,  60)),  # Sunset
        ((  8,  90,  30), ( 60, 158,  15), (150, 191,  45)),  # Forest
        (( 60,  15, 150), (120,  45, 191), (165, 120, 191)),  # Lavender
        ((120,  15,   8), (180,  90,   8), (191, 165,  23)),  # Ember
        (( 15,  60, 120), ( 45, 135, 180), (158, 180, 191)),  # Arctic
        (( 90,  38,   8), (150,  90,  15), (191, 150,  60)),  # Copper
        ((120,   8,  38), (180,  45,  98), (191, 135, 158)),  # Rose
        ((  8,  82,  68), ( 15, 158, 112), ( 90, 191, 150)),  # Mint
        (( 38,   8, 120), (135,  15, 165), (191,  75, 180)),  # Nebula
        ((105,   8, 135), ( 30,  75, 191), ( 15, 165, 150)),  # Aurora
        ((150, 120,   8), (180,  60,  15), (135,  15,  60)),  # Volcano
    ),
    spec_empty_ansi = fg256(254),
)


CATPPUCCIN_LATTE = Theme(
    name        = 'catppuccin-latte',

    border      = fg(140, 143, 161),
    border_off  = fg(156, 160, 176),
    pwd         = fg( 30, 102, 245),
    branch      = fg( 64, 160,  43),
    commit      = fg(108, 111, 133),
    session     = fg(108, 111, 133),
    skills      = fg(223, 142,  29),
    time        = fg(108, 111, 133),
    tok         = fg( 23, 146, 153),
    tok_dim     = fg(140, 143, 161),
    tok_day     = fg( 32, 159, 181),
    tok_day_dim = fg(156, 160, 176),
    cost        = fg(230,  69,  83),
    bar_fill    = fg( 64, 160,  43),
    bar_empty   = fg(188, 192, 204),
    dim_green   = fg( 64, 160,  43),
    label       = fg(140, 143, 161),
    ctx         = fg(254, 100,  11),
    ctx_dim     = fg(124, 127, 147),
    white_brt   = fg( 76,  79, 105),
    arrow       = fg( 64, 160,  43),
    dirty       = fg(254, 100,  11),
    icon_path   = fg( 32, 159, 181),
    tok_icon    = fg(223, 142,  29),
    model       = fg(136,  57, 239),

    safe        = fg( 64, 160,  43),
    warn        = fg(254, 100,  11),
    alert       = fg(210,  15,  57),
    yellow      = fg(223, 142,  29),
    tok_arrow   = fg(223, 142,  29),

    models = {
        'opus':   ModelColors(
            label      = fg(223, 142,  29),
        ),
        'sonnet': ModelColors(
            label      = fg( 64, 160,  43),
        ),
        'haiku':  ModelColors(
            label      = fg( 30, 102, 245),
        ),
        'other':  ModelColors(
            label      = fg(136,  57, 239),
        ),
    },


    grad_stops = (
        (0.00, ( 64, 160,  43)),
        (0.25, (223, 142,  29)),
        (0.50, (254, 100,  11)),
        (0.75, (210,  15,  57)),
        (1.00, (136,  57, 239)),
    ),
    grey_rgb    = (156, 160, 176),
    spark_stops = (
        (0.00, (230,  69,  83)),
        (0.50, (210,  15,  57)),
        (1.00, (254, 100,  11)),
    ),
    spec_gradients = (
        (( 32, 159, 181), ( 30, 102, 245), (  4, 165, 229)),  # Ocean
        ((254, 100,  11), (230,  69,  83), (223, 142,  29)),  # Sunset
        (( 64, 160,  43), ( 23, 146, 153), (223, 142,  29)),  # Forest
        ((136,  57, 239), (114, 135, 253), (234, 118, 203)),  # Lavender
        ((210,  15,  57), (254, 100,  11), (223, 142,  29)),  # Ember
        (( 32, 159, 181), (  4, 165, 229), (188, 192, 204)),  # Arctic
        ((254, 100,  11), (223, 142,  29), (230,  69,  83)),  # Copper
        ((234, 118, 203), (220, 138, 120), (221, 120, 120)),  # Rose
        (( 23, 146, 153), ( 64, 160,  43), (  4, 165, 229)),  # Mint
        ((136,  57, 239), (234, 118, 203), (114, 135, 253)),  # Nebula
        (( 23, 146, 153), ( 32, 159, 181), (136,  57, 239)),  # Aurora
        ((210,  15,  57), (230,  69,  83), (254, 100,  11)),  # Volcano
    ),
    spec_empty_ansi = fg256(254),
)


CATPPUCCIN_MOCHA = Theme(
    name        = 'catppuccin-mocha',

    border      = fg(127, 132, 156),
    border_off  = fg(108, 112, 134),
    pwd         = fg(137, 180, 250),
    branch      = fg(166, 227, 161),
    commit      = fg(166, 173, 200),
    session     = fg(166, 173, 200),
    skills      = fg(249, 226, 175),
    time        = fg(166, 173, 200),
    tok         = fg(148, 226, 213),
    tok_dim     = fg(127, 132, 156),
    tok_day     = fg(116, 199, 236),
    tok_day_dim = fg(108, 112, 134),
    cost        = fg(235, 160, 172),
    bar_fill    = fg(166, 227, 161),
    bar_empty   = fg( 69,  71,  90),
    dim_green   = fg(166, 227, 161),
    label       = fg(127, 132, 156),
    ctx         = fg(250, 179, 135),
    ctx_dim     = fg(166, 173, 200),
    white_brt   = fg(205, 214, 244),
    arrow       = fg(166, 227, 161),
    dirty       = fg(250, 179, 135),
    icon_path   = fg(116, 199, 236),
    tok_icon    = fg(249, 226, 175),
    model       = fg(203, 166, 247),

    safe        = fg(166, 227, 161),
    warn        = fg(250, 179, 135),
    alert       = fg(243, 139, 168),
    yellow      = fg(249, 226, 175),
    tok_arrow   = fg(249, 226, 175),

    models = {
        'opus':   ModelColors(
            label      = fg(249, 226, 175),
        ),
        'sonnet': ModelColors(
            label      = fg(166, 227, 161),
        ),
        'haiku':  ModelColors(
            label      = fg(137, 180, 250),
        ),
        'other':  ModelColors(
            label      = fg(203, 166, 247),
        ),
    },


    grad_stops = (
        (0.00, (166, 227, 161)),
        (0.25, (249, 226, 175)),
        (0.50, (250, 179, 135)),
        (0.75, (243, 139, 168)),
        (1.00, (203, 166, 247)),
    ),
    grey_rgb    = (108, 112, 134),
    spark_stops = (
        (0.00, (235, 160, 172)),
        (0.50, (243, 139, 168)),
        (1.00, (250, 179, 135)),
    ),
    spec_gradients = (
        ((116, 199, 236), (137, 180, 250), (137, 220, 235)),  # Ocean
        ((250, 179, 135), (235, 160, 172), (249, 226, 175)),  # Sunset
        ((166, 227, 161), (148, 226, 213), (249, 226, 175)),  # Forest
        ((203, 166, 247), (180, 190, 254), (245, 194, 231)),  # Lavender
        ((243, 139, 168), (250, 179, 135), (249, 226, 175)),  # Ember
        ((116, 199, 236), (137, 220, 235), (180, 190, 254)),  # Arctic
        ((250, 179, 135), (249, 226, 175), (235, 160, 172)),  # Copper
        ((245, 194, 231), (245, 224, 220), (242, 205, 205)),  # Rose
        ((148, 226, 213), (166, 227, 161), (137, 220, 235)),  # Mint
        ((203, 166, 247), (245, 194, 231), (180, 190, 254)),  # Nebula
        ((148, 226, 213), (116, 199, 236), (203, 166, 247)),  # Aurora
        ((243, 139, 168), (235, 160, 172), (250, 179, 135)),  # Volcano
    ),
    spec_empty_ansi = fg256(233),
)


THEMES: dict[str, Theme] = {
    CLAUDE_DARK.name:      CLAUDE_DARK,
    CLAUDE_LIGHT.name:     CLAUDE_LIGHT,
    CATPPUCCIN_LATTE.name: CATPPUCCIN_LATTE,
    CATPPUCCIN_MOCHA.name: CATPPUCCIN_MOCHA,
}


def resolve(name: str | None) -> Theme:
    if name and name in THEMES:
        return THEMES[name]
    return CLAUDE_DARK
