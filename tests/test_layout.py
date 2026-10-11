from maple_exp.layout import fitted_height


def test_window_hugs_its_content():
    assert fitted_height(content_css=700, dpr=1.0, max_px=1300) == 700


def test_scaled_screens_use_physical_pixels():
    assert fitted_height(content_css=700, dpr=1.5, max_px=1300) == 1050


def test_never_taller_than_the_space_on_screen():
    assert fitted_height(content_css=1200, dpr=1.0, max_px=900) == 900


def test_never_collapses_below_a_usable_height():
    assert fitted_height(content_css=50, dpr=1.0, max_px=900) == 320
