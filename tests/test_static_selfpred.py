from spar_dynamic.dice_pilot import prompts as dice_v31
from spar_dynamic.favorite_animal import prompts as animal_v1
from spar_dynamic.static_selfpred import config, prompts


def test_prompt_consistency_runs():
    prompts.assert_consistency()


def test_object_prompts_match_pilots():
    assert prompts.ANIMAL_OBJECT == animal_v1.PHASE1_PROMPT
    assert prompts.DICE_OBJECT == dice_v31.PHASE1_PROMPT


def test_self_prompts_match_pilots():
    for pos in prompts.ANIMAL_POSITIONS:
        assert prompts.animal_self(pos) == animal_v1.phase2a_prompt(pos)
    for pos in prompts.DICE_ORDINALS:
        assert prompts.dice_self(pos) == dice_v31.phase2_prompt(pos)


def test_controls_do_not_address_model_as_respondent():
    for pos in prompts.ANIMAL_POSITIONS:
        assert "you" not in prompts.animal_neutral(pos).lower().replace("your favorite", "")
        assert "your response" not in prompts.animal_generic(pos)
    for pos in prompts.DICE_ORDINALS:
        assert "your response" not in prompts.dice_generic(pos)


def test_supplied_prompt_names_the_word():
    t = prompts.animal_supplied("octopus", "penultimate")
    assert '"octopus"' in t
    assert t.count("penultimate") == 2


def test_render_all_covers_every_cell():
    text = prompts.render_all()
    for header in ("ANIMAL OBJECT", "ANIMAL SELF", "ANIMAL GENERIC (", "ANIMAL GENERIC NAME",
                   "ANIMAL NEUTRAL", "ANIMAL SUPPLIED", "DICE OBJECT", "DICE SELF",
                   "DICE SINGLE ROLL", "DICE GENERIC"):
        assert header in text


def test_panel_and_call_budget():
    assert config.PANEL == ("astra", "fable", "qwen")
    assert all(m.label in config.PANEL for m in config.MODELS)
    # animal: 100 + 400 + 400 + 100 + 400 + 80; dice: 100 + 400 + 100 + 400
    assert config.calls_per_model() == 1480 + 1000
    assert config.total_calls() == 3 * 2480
