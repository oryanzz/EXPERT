from pathlib import Path

from maple_exp.paths import app_dirs


def test_source_install_keeps_everything_in_the_project_folder():
    res, data = app_dirs(frozen=False, code_dir=Path("C:/EXPERT"), bundle_dir=None, env={})
    assert res == data == Path("C:/EXPERT")


def test_exe_reads_ui_from_the_bundle_and_keeps_data_in_localappdata():
    env = {"LOCALAPPDATA": "C:/Users/me/AppData/Local"}
    res, data = app_dirs(frozen=True, code_dir=Path("C:/tmp/_MEI1"), bundle_dir=Path("C:/tmp/_MEI1"), env=env)
    assert res == Path("C:/tmp/_MEI1")
    assert data == Path("C:/Users/me/AppData/Local/EXPERT")


def test_data_dir_override():
    env = {"LOCALAPPDATA": "C:/x", "EXPERT_DATA_DIR": "D:/portable/data"}
    _, data = app_dirs(frozen=True, code_dir=Path("C:/tmp"), bundle_dir=Path("C:/tmp"), env=env)
    assert data == Path("D:/portable/data")
    _, data = app_dirs(frozen=False, code_dir=Path("C:/EXPERT"), bundle_dir=None, env=env)
    assert data == Path("D:/portable/data")
