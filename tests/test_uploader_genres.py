import pytest

from steak.uploader import convert_genres


@pytest.mark.parametrize(
    ("genres", "expected"),
    [
        (["World Music", "Latin"], "Latin"),
        (["Latin", "World Music"], "Latin"),
        (["world music", "Latin", "Pop"], "Latin,Pop"),
        (["World_Music", "Latin"], "Latin"),
        (["world.music", "Latin"], "Latin"),
    ],
)
def test_convert_genres_omits_world_music_when_specific_genre_exists(genres: list[str], expected: str) -> None:
    assert convert_genres(genres) == expected


@pytest.mark.parametrize(
    ("genre", "expected"),
    [
        ("World Music", "World.Music"),
        ("world music", "world.music"),
        ("World_Music", "World.Music"),
        ("world.music", "world.music"),
    ],
)
def test_convert_genres_keeps_world_music_when_it_is_the_only_genre(genre: str, expected: str) -> None:
    assert convert_genres([genre]) == expected


def test_convert_genres_does_not_mutate_reviewed_genres() -> None:
    genres = ["World Music", "Latin"]

    assert convert_genres(genres) == "Latin"
    assert genres == ["World Music", "Latin"]
