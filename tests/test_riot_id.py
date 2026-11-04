"""Tests de la lecture du Riot ID tapé dans l'appli (src/riot_games.py).

Aucun appel à l'API Riot ici : les tests doivent tourner sans clé, sur GitHub.
"""

import pytest

from riot_games import _player_file, split_riot_id


@pytest.mark.parametrize("text, expected", [
    ("TECHNIQUEMENT#99999", ("TECHNIQUEMENT", "99999")),
    ("  Mon Pseudo # EUW ", ("Mon Pseudo", "EUW")),   # espaces autour retirés, pas dedans
    ("Zoë#ÉtÉ", ("Zoë", "ÉtÉ")),                       # accents gardés
])
def test_riot_id_valide(text, expected):
    assert split_riot_id(text) == expected


@pytest.mark.parametrize("text", ["SansTag", "a#b#c", "#EUW", "Pseudo#", " # ", ""])
def test_riot_id_invalide(text):
    with pytest.raises(ValueError, match="Pseudo#TAG"):
        split_riot_id(text)


def test_nom_de_fichier_du_cache_sans_caractere_dangereux():
    # Un Riot ID ne doit jamais pouvoir écrire hors de data/app_cache/players/.
    path = _player_file("../../etc", "x/y")
    assert path.parent.name == "players"
    assert "/" not in path.name and "\\" not in path.name and ".." not in path.stem
