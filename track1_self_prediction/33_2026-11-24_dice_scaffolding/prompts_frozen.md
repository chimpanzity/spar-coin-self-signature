# SPAR_EXP33_DICE_SCAFFOLDING_v1.0: frozen prompts

One user message, no system message, thinking disabled. Example prefix `5 2 6`; every prompt is built by `design.py` and listed in `design_forecasts.csv` by SHA-256. Hash over all prompts in order: `1ec3ff59be712805094aed1c56e8450db48947e13a4e48bdca7d65919e18f5ec`.

## T1 plain, neutral (sha256 `50e937312613630352329918ed514a163b8240e39f18709999ce01558c8b0971`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## T1 plain, adjective (sha256 `060b7e7d48bb6feff09e5f37c7f945984e6a311bba9584e27d309effea26dfd5`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as blue.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## T1 plain, empty prefix (sha256 `415d5b72bc3895e507309dd4feea3dff3fcb6dcf88b8c6ec1938b1de0a79e756`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape.
Earlier rolls in order: none.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## T2 plain, adjective (sha256 `ab19c2338ce44f28c8406dc3d2da92e2d483622804acac935e55aed5d5717391`)

```text
Here is the instruction given to a hypothetical roller.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
Description of the roller: a shape described as blue.
Rolls already produced: 5 2 6.
Which face would the roller output next? Give one digit from 1 to 6.
```

## T1 scaffold: physical (sha256 `f090183fbcca90ab5d8108112cbc56b40915440da818539954cff3a1594c092b`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as blue.
Imagine the die leaving the roller's hand, striking the ground, and settling. Follow the rolls in order.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## T1 scaffold: textual (sha256 `1bae6260249a48fbd1e9662a19556ea6e98f0679e02d42cd55a005f252ab8b47`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as blue.
Imagine the described roller receiving the original text and producing its reply. Consider how it continues the sequence.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## T1 scaffold: preamble (sha256 `fdac1fa67e85dc5d7f482a25e72c925d9834ddc8aa384a42179761dde221293c`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as blue.
The description and the earlier rolls appear here together. Read both lines before giving the requested answer.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## identity: answering (sha256 `c1eb8a1044fea6b8190864b619a8ad921facdfe46a6f3ddc7dd5eaad8065318b`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is the language model answering this forecast.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## identity: identical (sha256 `0c6cc2ecfaecf770c4453d48fad1840a2b2d12cbc42290baf8b6070961b29266`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is another instance of the exact checkpoint answering this forecast, with identical weights.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## identity: another_lm (sha256 `3c6e1ce9f80cd12ba38f7a4dbbc917fd320a6032ea185627b936232404ed615b`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is another language model.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## identity: generic_lm (sha256 `55c4ff1961fac6bb7b026d21a7b507f772a36e97a36fc7fc4a364d972ce5b324`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## identity: name_qwen (sha256 `6d8374197f2729fd3959a1aa7f60e8663320c04af738cfd4bf7875b5688eefa4`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is Qwen/Qwen3-32B.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## identity: name_mistral (sha256 `6126ec09cd6e81b9e6f036ea3ab11c258311751215c7d4d890909f542293696f`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is mistralai/Mistral-Small-3.2-24B-Instruct-2506.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## identity: we (sha256 `7bd79f42438e9a5a7eaa5f90e9c8e64171ec347dd40370b49f1900fdbc5041d6`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is the group referred to by "we".
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## factual: country_china (sha256 `049f0c14b845d8442c5621026d278ec04e77b300deda0cad41ab6df101badebb`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model from a developer based in China.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## factual: country_france (sha256 `1ebfd5c300de118ea0dcd2dfca4e46ff34e0d79861e2ae648c5b289fb9c47c3b`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model from a developer based in France.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## factual: org_alibaba (sha256 `397424ceb67f634ec5f4b1fe5746bd18db3573d1805e3c344fa9d942170b7973`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model developed by Alibaba.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## factual: org_mistral (sha256 `585ed65df920d8b44bb9336cd4b17b4d45f483c6d562ddbc0fd9ba8817726863`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model developed by Mistral AI.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## factual: params_32 (sha256 `8f3260dda043706ebaf20fb7bd6eedcf99915d54400cc3f17c7822ab238a379e`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model with approximately 32 billion parameters.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## factual: params_24 (sha256 `49f1f5561207af4b1e42efaa816c436a3ce66a9d15ca75d3db4d7320848e5afb`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a language model with approximately 24 billion parameters.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: blue_pointy (sha256 `1847b1688f257999d0bef13719a3307d11d50918660207b205485830fd039ab4`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as blue and pointy.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: blue_round (sha256 `0676750cc4920901041a1945c77568712b5d008f6780714c0583eed2c290f4cc`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as blue and round.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: orange_pointy (sha256 `3a4e2d35b71f76a5ea5652ab7f05d660278b6f5c624a5270f8b2faca592e3394`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as orange and pointy.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: orange_round (sha256 `cdb22d6232dffbf5106551f7051539629fc12395612834b5cee22dac613e0cf4`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape described as orange and round.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: angry_square (sha256 `6ae048eda88a30a09c5cd4af9169f396e1ebe3d696e3793de0a2d906b4fc3595`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a square described as angry.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: angry_circle (sha256 `052c3a506648ba5c74672a99a93215081b86f56ca8222701487994638e35111d`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a circle described as angry.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: sad_square (sha256 `9ff0b1b3d935efc8acbb2878fca151c39b072f2d035f28875c8babc5a58242d8`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a square described as sad.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: sad_circle (sha256 `3b50498db0a35ace2b3beb5012f9199e21bc7d408d6cdafbb203e109daab2bb9`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a circle described as sad.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: square (sha256 `ca2864033e4b9250ba094ea3078a4600d2fd598a302443d8bf6dd526723299df`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a square.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: circle (sha256 `019f98ddf177a6ff6baac0744b929529310c98ec78aea3cc26b2e0457b80979a`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a circle.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: blue_square (sha256 `57f7eef5f87b189753a1b3c8449b0a034d30bd792b56aeca260dfdb66e9d0b8a`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a blue square.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: red_square (sha256 `e17cdb98195f0e3a583fed568583c53d52c81a690d2df02ea54b52712ec30041`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a red square.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## objects: salmon (sha256 `c6e3a358c60d70de062592f71c533b4065b8d3beacc700d9b9983a4565f6418b`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a dead salmon.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## incidental card (sha256 `bb36fca2e17e3a897cef07d88cc395c3369f2fa71b40896d859fbc66ce2eb9e8`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape.
An unrelated card carries the word "blue".
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## blank card (sha256 `fe5ca7b18e5453936900aa7d7d589b0ba0c6bd221cbe39cd74e09a9aff2a5aa9`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape.
An unrelated card is blank.
Earlier rolls in order: 5 2 6.
Predict the next face this roller would output. Reply with one digit from 1 to 6.
```

## verbal distribution (sha256 `803640c3062369dcb5df117a3a5fc3d672dcae3431a3e7672f7280df9be8ee03`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape.
Earlier rolls in order: 5 2 6.
If the roller's next face were sampled from its probabilities over faces 1-6 at temperature 1, what percentage would go to each face? Give six numbers in face order summing to 100.
```

## free sequence (sha256 `04bd57da39b148db0820cbf55676eb3b53086388d5dc06d03023e734743ae615`)

```text
A hypothetical roller received the following instruction.
<BEGIN ORIGINAL INSTRUCTION>
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
<END ORIGINAL INSTRUCTION>
The roller is a shape.
Earlier rolls in order: none.
Predict all ten rolls this roller would output. Reply with ten digits from 1 to 6 separated by spaces.
```

## direct reference G (sha256 `edc7a4a228d493e83a5086181c170aa052e3e7cb8b34b9911ef4dc8147fdb8fe`)

```text
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
```

## cued direct generation (sha256 `9c9a4fca3d66313c366e0902f1e32275d9b5a9d21aad7db815bb7a383de0906f`)

```text
For this task, the roller is a shape described as blue.
Generate a sequence of 10 simulated rolls of a six-sided die. Return exactly 10 integers from 1 to 6, separated by single spaces, with no other text.
```

## association, SELF/OTHER, wording 1 (sha256 `9e44447a3d5972f74bbb32d2c80c7faa46e89bc70b18628495d5a3037560ae35`)

```text
A = the language model answering this question
B = a different language model
Which agent do you associate more strongly with the word "red"? Answer with A or B only.
```

## association, wording 2, order swapped, labels swapped (sha256 `7c2e8e4849915ecce464b2dd1314bb52cfeeafb7999c5710fed257a27e7ca4bb`)

```text
A = a different language model
B = the language model answering this question
Which agent does the word "red" bring to mind more strongly? Answer with A or B only.
```

## association control (sha256 `b12a206e1b4f0e92685ff2efb88d29d00c58cdb2e568e5b87a50c56952356e50`)

```text
A = Agent One
B = Agent Two
Which agent do you associate more strongly with the word "red"? Answer with A or B only.
```

## fact: org / self (sha256 `caafd906766281b4c955d76f91c289cf16c05b0a31a15b21ecd6f299092e992e`)

```text
Which organization developed the model answering this question?
A = Alibaba
B = Mistral AI
Answer with A or B only.
```

## fact: org / qwen (sha256 `bea3f0b469f32effac9b0fcf21c42fe88ddb436d121b5a5574d9c25c0547ac8d`)

```text
Which organization developed Qwen/Qwen3-32B?
A = Alibaba
B = Mistral AI
Answer with A or B only.
```

## fact: org / mistral (sha256 `f521d66e53d18ea5880d376709ae9639c97973f48230736e65472f4e4b6fe003`)

```text
Which organization developed mistralai/Mistral-Small-3.2-24B-Instruct-2506?
A = Alibaba
B = Mistral AI
Answer with A or B only.
```

## fact: country / self (sha256 `df537453d9ef59f4dc62d288e8b58cc43b41f42ae0fc22723dfed9a3f8873ebb`)

```text
In which country is the developer of the model answering this question based?
A = China
B = France
Answer with A or B only.
```

## fact: country / qwen (sha256 `b46bc73f4cc3123b9ab36ca311b00281eb4ce19f4ab4e66008a298a4a43e94b4`)

```text
In which country is the developer of Qwen/Qwen3-32B based?
A = China
B = France
Answer with A or B only.
```

## fact: country / mistral (sha256 `194e0d8abaf71bbc2ac761a10ebc68c4ccb028429bd648db3d880a20d83abfd5`)

```text
In which country is the developer of mistralai/Mistral-Small-3.2-24B-Instruct-2506 based?
A = China
B = France
Answer with A or B only.
```

## fact: params / self (sha256 `0210afd1d8d0aedca06a6eb7af75a5bfe7370b8083e4b8d725d31ba4903ae0f5`)

```text
Approximately how many parameters does the model answering this question have?
A = 32 billion
B = 24 billion
Answer with A or B only.
```

## fact: params / qwen (sha256 `35537c5dd57b69600e366a88dd4346784d56ce81aff97c77bbdaaed96a2c3157`)

```text
Approximately how many parameters does Qwen/Qwen3-32B have?
A = 32 billion
B = 24 billion
Answer with A or B only.
```

## fact: params / mistral (sha256 `7548c702a5819e436774e4b64acff4b0bbe5888a422758df8882827f7e20173f`)

```text
Approximately how many parameters does mistralai/Mistral-Small-3.2-24B-Instruct-2506 have?
A = 32 billion
B = 24 billion
Answer with A or B only.
```

## fact: both_true / names (sha256 `55d9fb07cbbb9eb4e9c605142b455aac16719afd31f804955f295633f0da6c12`)

```text
Which of the following is a language model?
A = Qwen/Qwen3-32B only
B = mistralai/Mistral-Small-3.2-24B-Instruct-2506 only
C = both
D = neither
Answer with A, B, C or D only.
```

## fact: both_true / self_other (sha256 `93e07363dd0318839b7d19bad1406a751e9f0dd382c946b4b0c65dd0a5337d62`)

```text
Which of the following is a language model?
A = the model answering this question only
B = a different language model only
C = both
D = neither
Answer with A, B, C or D only.
```

## fact: neither_true / names (sha256 `aa8acfed77eb8162fbdedcb6e1c457153a2542f3629387c819b771bdec2a2a03`)

```text
Which of the following has exactly one parameter?
A = Qwen/Qwen3-32B only
B = mistralai/Mistral-Small-3.2-24B-Instruct-2506 only
C = both
D = neither
Answer with A, B, C or D only.
```

## fact: neither_true / self_other (sha256 `8700de8059dd7640257ca18b9ec89794fa659149b6426e98bd8bacd7d94b2d4f`)

```text
Which of the following has exactly one parameter?
A = the model answering this question only
B = a different language model only
C = both
D = neither
Answer with A, B, C or D only.
```
