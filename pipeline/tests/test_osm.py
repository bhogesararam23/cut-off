import pytest

from cutoff.osm import clean_name, extract, parse_other_tags, population


def test_other_tags_are_parsed():
    t = parse_other_tags('"population"=>"1,200","name:es"=>"Los \\"Pozos\\"","surface"=>"gravel"')
    assert t == {"population": "1,200", "name:es": 'Los "Pozos"', "surface": "gravel"}
    assert parse_other_tags(None) == {} and parse_other_tags("") == {}


def test_population_is_read_leniently_and_never_invented():
    assert population({"population": "1,200"}) == 1200
    assert population({"population": "~300"}) == 300
    assert population({"population": "many"}) is None
    assert population({}) is None
    assert population({"population": "9" * 12}) is None


def test_names_are_plain_trimmed_text():
    assert clean_name("  Santa   Fe ") == "Santa Fe"
    assert clean_name("<script>x</script>") == "<script>x</script>"         # kept as text: the app never renders it as HTML
    assert clean_name("x" * 500) == "x" * 120
    assert clean_name(None) is None and clean_name("   ") is None and clean_name(float("nan")) is None


def test_missing_extract_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "nope.osm.pbf", (0, 0, 1, 1), tmp_path)
