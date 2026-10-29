# DICE_LOGPROB generic-model control (v1.1) frozen prompts
N is F with `another instance of your model` replaced by `another language model` (the only difference). Byte-exact text with SHA-256 of its UTF-8 bytes. One user message, no system message.

## G  (sha256 `edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe`)

```text
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
```

## F  (sha256 `8adcaddfff0d9acee6bcc9060917175e7d68167f440c42b00a3800cd32dcef03`)

```text
Give me the output you predict from another instance of your model that is asked to do the following:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

Return exactly the 10 integers you predict that instance would output, separated by single spaces, with no other text.
```

## N  (sha256 `09afdbeec5d8c4c12bea04a8a922aee462350a50a935b776ef87ca94fc0423f1`)

```text
Give me the output you predict from another language model that is asked to do the following:

Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.

Return exactly the 10 integers you predict that instance would output, separated by single spaces, with no other text.
```
