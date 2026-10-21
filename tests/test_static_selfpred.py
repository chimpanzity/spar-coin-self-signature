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
    assert [m.label for m in config.MODELS] == ["astra", "fable"]
    assert [c["config"] for c in config.QWEN_CONFIGS] == ["R_off", "R_high"]
    assert all(c["temperature"] == 0.0 and c["provider"] == "SiliconFlow" for c in config.QWEN_CONFIGS)
    # animal: 100 + 400 + 400 + 100 + 400 + 80; dice: 100 + 400 + 100 + 400
    assert config.calls_per_model() == 1480 + 1000
    assert config.total_calls() == 4 * 2480


# ---------------------------------------------------------------- parse check --
from spar_dynamic.static_selfpred import parse_check


def _res(text, finish="stop", tool_calls=False, ok=True):
    return dict(ok=ok, error="" if ok else "boom", text=text, finish_reason=finish, tool_calls=tool_calls)


def test_parse_check_covers_every_prompt_once():
    items = parse_check.build_prompt_list("octopus")
    assert len(items) == 27      # plus the animal object prompt, run first
    assert {i["cell"] for i in items} == (set(config.ANIMAL_CELLS) | set(config.DICE_CELLS)) - {"animal_object"}


def test_parse_check_flags_tool_use_and_truncation():
    assert parse_check.response_category("int", _res("4", tool_calls=True))["category"] == "tool_use"
    assert parse_check.response_category("int", _res("<tool_call>{}</tool_call>"))["category"] == "tool_use"
    assert parse_check.response_category("int", _res("4", finish="tool_calls"))["category"] == "tool_use"
    assert parse_check.response_category("int", _res("4", finish="length"))["category"] == "truncated"
    assert parse_check.response_category("int", _res("", ok=False))["category"] == "transport_error"


def test_parse_check_classifies_with_pilot_parsers():
    assert parse_check.classify("int", "4")["category"] == "valid"
    assert parse_check.classify("int", "<think>\n\n</think>\n\n4")["category"] != "valid"
    assert parse_check.classify("letter", "O")["value"] == "o"
    assert parse_check.classify("animal", "Octopus")["value"] == "octopus"
    assert parse_check.classify("seq", "4 1 6 3 2 5 5 2 6 1")["category"] == "valid"


def test_parse_check_fail_rule():
    s = {"qwen|R_off|dice_self": {"nonvalid_rate": 0.40}, "qwen|R_off|ALL": {"nonvalid_rate": 0.1},
         "qwen|R_high|dice_self": {"nonvalid_rate": 0.0}, "qwen|R_high|ALL": {"nonvalid_rate": 0.39}}
    v = parse_check.verdicts(s, "qwen")
    assert v["R_off"]["fails"] and not v["R_high"]["fails"]
