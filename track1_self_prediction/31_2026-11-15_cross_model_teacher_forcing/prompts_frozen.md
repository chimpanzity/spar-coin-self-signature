# Experiments 31 and 32: frozen model-facing prompts

Byte-exact text with the SHA-256 of its UTF-8 bytes. One user message, no system message, no tools, thinking disabled (Qwen3 template `enable_thinking=False`; Mistral via mistral_common tekken). No trailing newline.

## Experiment 31: archived instructions (the only user turn; source rolls are forced as the assistant turn)

### G (sha256 `edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe`)

```text
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
```

### F (sha256 `8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03`)

```text
Give me the output you predict from another instance of your model that is asked to do the following:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

Return exactly the 10 integers you predict that instance would output, separated by single spaces, with no other text.
```

Forced assistant prefix at position j: the source's authentic rolls 1..j-1 rendered exactly as Experiment 28's greedy output (`d d d`, single spaces), tokenised by the scorer, ending with the separator before roll j (empty at j = 1).

## Experiment 32: six prediction prompts (both predictors receive identical bytes)

### qwen-G-A (sha256 `7460c260e7bfa45673ea7feea36baafe8aedf5adc70e2211ed2600a9bdd64aaa`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Predict rolls 6 and 7 of that response. Return exactly two integers separated by a single space, with no other text.
```

### qwen-G-B (sha256 `d49a6903e16029b08ee03663290753c7693d81ef6228379ba9153675a7fcaa5e`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### qwen-G-C (sha256 `940332b8d516040648e67491d6327c4e9ec6fc0086af1b6be8c6aaa6514d74a1`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first six rolls it produced were: 5 2 6 3 1 4
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### mistral-G-A (sha256 `dc76ac20ad33f1de8c2f63222331995533b6ff1c64d645d5be06bd037e1b5060`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Predict rolls 6 and 7 of that response. Return exactly two integers separated by a single space, with no other text.
```

### mistral-G-B (sha256 `aaa3e346e5d5cee8f9830ed6c0952868124a8529c91efa77f7911f82fc273751`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### mistral-G-C (sha256 `1b412fa3c02a66edc8738d182da2ec87c5f30c030da07c4dc20f1e70041570fc`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first six rolls it produced were: 4 2 6 1 3 5
Predict roll 7 of that response. Return exactly one integer, with no other text.
```
