# Experiment 38: frozen model-facing prompts

One user message, no system message, no tools, LF, no trailing newline, thinking disabled (Qwen3 template `enable_thinking=False`; Mistral via mistral_common tekken). Both predictors receive identical bytes. Every prompt is listed with its SHA-256 in `design_prompts.csv`; the templates and the k = 5 anchors are shown here.

## Templates

Common head (Experiment 32, byte-exact), then the rolls line and an ending. k rolls are shown for SLOT and B, k + 1 for C.

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first {k words} rolls it produced were: {r1 ... rk}
```

For k = 1 the line is `The first roll it produced was: {r1}`.

| Condition | Ending |
|---|---|
| SLOT | `Roll {k+1}: [blank]. Roll {k+2}: [predict this position]. Predict roll {k+2} of that response. Return exactly one integer, with no other text.` |
| B | `Predict roll {k+2} of that response. Return exactly one integer, with no other text.` |
| C (k+1 rolls shown) | `Predict roll {k+2} of that response. Return exactly one integer, with no other text.` |

## Anchors (k = 5)

### exp35-qwen-SLOT (sha256 `65a6de12f9c9bf079c54d82227d1ad7a7aaf2662949c00ccf665b7b7665d830d`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Roll 6: [blank]. Roll 7: [predict this position]. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### exp32-qwen-G-B (sha256 `d49a6903e16029b08ee03663290753c7693d81ef6228379ba9153675a7fcaa5e`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### exp32-qwen-G-C (sha256 `940332b8d516040648e67491d6327c4e9ec6fc0086af1b6be8c6aaa6514d74a1`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first six rolls it produced were: 5 2 6 3 1 4
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### exp35-mistral-SLOT (sha256 `e429650413ac59a67a66c381c65feecfb5d52f5ffaf2af3ba4f0dbf0786d9802`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Roll 6: [blank]. Roll 7: [predict this position]. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### exp32-mistral-G-B (sha256 `aaa3e346e5d5cee8f9830ed6c0952868124a8529c91efa77f7911f82fc273751`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### exp32-mistral-G-C (sha256 `1b412fa3c02a66edc8738d182da2ec87c5f30c030da07c4dc20f1e70041570fc`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first six rolls it produced were: 4 2 6 1 3 5
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

## Example (SLOT, k = 4, sha256 `fda572ffa877d5695a4166e26e493b13d47330c2d10af16a787c900dc2acaa57`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first four rolls it produced were: 5 2 6 3
Roll 5: [blank]. Roll 6: [predict this position]. Predict roll 6 of that response. Return exactly one integer, with no other text.
```
