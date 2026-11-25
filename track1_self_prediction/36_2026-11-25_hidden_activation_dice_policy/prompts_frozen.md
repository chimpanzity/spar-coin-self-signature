# Experiment 36: frozen prompts

One user message, no system message, no tools, thinking disabled, LF, no trailing newline. Shown for the prefix `5 2 6`; only the description line and the prefix vary. SHA-256 of every prompt is in `prompt_hashes.csv`.

### agent (sha256 `2689af595eb43d5399c574e624c4259b71ea1eddbf991db7f169ced88d9937a8`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is an agent.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

### shape (sha256 `50e937312613630352329918ed514a163b8240e39f18709999ce01558c8b0971`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

### self (sha256 `c1eb8a1044fea6b8190864b619a8ad921facdfe46a6f3ddc7dd5eaad8065318b`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is the language model answering this forecast.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

### generic (sha256 `55c4ff1961fac6bb7b026d21a7b507f772a36e97a36fc7fc4a364d972ce5b324`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

### direct (sha256 `edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe`; the prefix and a trailing separator are forced as the assistant turn)

```text
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
```
