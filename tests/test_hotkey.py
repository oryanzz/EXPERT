from maple_exp.hotkey import MOD_CONTROL, MOD_SHIFT, parse_hotkey


def test_function_keys():
    assert parse_hotkey("F11") == (0, 0x7A)
    assert parse_hotkey("f1") == (0, 0x70)
    assert parse_hotkey("F24") == (0, 0x87)


def test_named_keys():
    assert parse_hotkey("Pause") == (0, 0x13)
    assert parse_hotkey("ScrollLock") == (0, 0x91)
    assert parse_hotkey("Insert") == (0, 0x2D)


def test_modifier_combos():
    assert parse_hotkey("Ctrl+Shift+E") == (MOD_CONTROL | MOD_SHIFT, ord("E"))
    assert parse_hotkey("ctrl + shift + e") == (MOD_CONTROL | MOD_SHIFT, ord("E"))


def test_off_and_garbage():
    assert parse_hotkey("off") is None
    assert parse_hotkey("") is None
    assert parse_hotkey("F25") is None
    assert parse_hotkey("Ctrl+") is None
    assert parse_hotkey("Banana") is None
