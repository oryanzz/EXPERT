from maple_exp.layout import fitted_height


def test_window_hugs_its_content():
    assert fitted_height(content_css=700, dpr=1.0, max_px=1300) == 700


def test_scaled_screens_use_physical_pixels():
    assert fitted_height(content_css=700, dpr=1.5, max_px=1300) == 1050


def test_never_taller_than_the_space_on_screen():
    assert fitted_height(content_css=1200, dpr=1.0, max_px=900) == 900


def test_never_collapses_below_a_usable_height():
    assert fitted_height(content_css=50, dpr=1.0, max_px=900) == 320


from maple_exp.layout import dock_position  # noqa: E402

PRIMARY = (0, 0, 2560, 1392)      # work area (taskbar excluded)
ABOVE = (0, -1440, 2560, 0)       # a second monitor above it


def test_windowed_game_with_room_docks_beside_it():
    game = (86, 109, 2006, 1309)  # client area of a 1920x1200 window
    assert dock_position(game, [PRIMARY], win_w=424) == (2030, 78)


def test_full_screen_game_moves_expert_to_the_other_monitor():
    game = (0, 0, 2560, 1440)
    assert dock_position(game, [PRIMARY, ABOVE], win_w=424) == (2560 - 424 - 16, -1440 + 16)


def test_full_screen_game_on_a_single_monitor_uses_the_top_right_corner():
    game = (0, 0, 2560, 1440)
    assert dock_position(game, [PRIMARY], win_w=424) == (2560 - 424 - 16, 16)
