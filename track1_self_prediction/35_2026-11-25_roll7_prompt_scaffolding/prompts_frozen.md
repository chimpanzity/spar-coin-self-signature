# Experiment 35: frozen model-facing prompts

Byte-exact text with the SHA-256 of its UTF-8 bytes. One user message, no system message, no tools, LF, no trailing newline. Both models receive identical bytes.

### qwen-B (sha256 `d49a6903e16029b08ee03663290753c7693d81ef6228379ba9153675a7fcaa5e`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### qwen-GAP (sha256 `8c1586bbebe0fc3eeb6e1470af285550fcaa6fd40d4667aa1f23071d8de3c118`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Roll 6 is not shown. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### qwen-SLOT (sha256 `65a6de12f9c9bf079c54d82227d1ad7a7aaf2662949c00ccf665b7b7665d830d`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Roll 6: [blank]. Roll 7: [predict this position]. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### qwen-THINK (sha256 `ccc4fa7ba7e0cb418e64ed4acb83faffc56c1766b5c49a8472ec77dc683aa606`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Think through your prediction carefully before answering. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### qwen-INFER (sha256 `b0bdbfd88db1ec36e8afce374915d88173e6c414cf5fb0ded2a95cd706c94495`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
First consider what the instance would have produced for roll 6. Use that estimate to predict roll 7 of that response, without outputting your estimate for roll 6. Return exactly one integer, with no other text.
```

### qwen-IMAGINE (sha256 `77fcb5327a8bea6f85379ae7626b3bb418906723071c435461907edcdb4a947b`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 5 2 6 3 1
Imagine continuing the same simulated die-rolling response for two more rolls, in order. Keep the first imagined roll (roll 6) to yourself. Predict roll 7 of that response using the second imagined roll. Return exactly one integer, with no other text.
```

### mistral-B (sha256 `aaa3e346e5d5cee8f9830ed6c0952868124a8529c91efa77f7911f82fc273751`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### mistral-GAP (sha256 `b7381419d8ac5413b285cbc00cca435e77c81717ebe88ef5a444340f9aed8710`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Roll 6 is not shown. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### mistral-SLOT (sha256 `e429650413ac59a67a66c381c65feecfb5d52f5ffaf2af3ba4f0dbf0786d9802`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Roll 6: [blank]. Roll 7: [predict this position]. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### mistral-THINK (sha256 `38dbafea364cb88456e010c6882c5ef9fc64a0710b63022bcb7f3fd5a9721e91`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Think through your prediction carefully before answering. Predict roll 7 of that response. Return exactly one integer, with no other text.
```

### mistral-INFER (sha256 `27523a9023fcf53b7878d6a7dd22c9001f53261ce3e8e777561c3a53d8e0532a`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
First consider what the instance would have produced for roll 6. Use that estimate to predict roll 7 of that response, without outputting your estimate for roll 6. Return exactly one integer, with no other text.
```

### mistral-IMAGINE (sha256 `a8294fb0192198b014dc79a341f523a3fdf04ad62a0198908826eb4319849670`)

```text
A language-model instance received the following instruction:
<ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
</ORIGINAL INSTRUCTION>
The first five rolls it produced were: 4 2 6 1 3
Imagine continuing the same simulated die-rolling response for two more rolls, in order. Keep the first imagined roll (roll 6) to yourself. Predict roll 7 of that response using the second imagined roll. Return exactly one integer, with no other text.
```
