# Experiment 2 robustness: round 1, round bins, and what the labels change (2026-10-11)

Run btx1-20261010, paired items, Experiment 2 weighting. Motivated by the log review: RPS openings are almost fixed
(PAPER; 44 of 72 round-1 ties) and in MP the Matcher opens STAR and the Mismatcher TRIANGLE (Mismatcher wins round 1
in 60 of 72 games).

| rounds | RPS S | RPS S_false | RPS anon self-adv | MP S | MP S_false | MP anon self-adv | Fable-on-Fable RPS T/A/F |
|---|---:|---:|---:|---:|---:|---:|---|
| all | +1.8 | +3.9 | +1.9 | +1.5 | +3.5 | +2.8 | 53.4 / 45.0 / 38.8 |
| 2-20 | +1.0 | +2.9 | +1.8 | +1.5 | +3.4 | +3.0 | 50.8 / 44.7 / 41.1 |
| 6-20 | +2.5 | +3.0 | -0.7 | +1.8 | +5.0 | +3.2 | 51.3 / 44.3 / 39.0 |

Self-judge vs other-judge accuracy (TRUE label, pooled over models):

| | RPS round 1 | RPS 2-5 | RPS 6-20 | MP round 1 | MP 2-5 | MP 6-20 |
|---|---:|---:|---:|---:|---:|---:|
| self-judge | 58.3 | 49.3 | 42.6 | 75.0 | 63.9 | 58.0 |
| other judges | 37.5 | 43.9 | 40.8 | 75.0 | 61.1 | 53.0 |

In RPS the self-advantage is concentrated in round 1 and the opening rounds and is small by rounds 6-20 (+1.8 pp); in
MP every judge knows the opening convention (75% at round 1 for all) and the self-advantage grows later in the game
(+5.0 pp in rounds 6-20). Dropping round 1 lowers the RPS indices by about 1 pp and leaves MP unchanged.

Content of the label effect, RPS rounds 2-20: share of a judge's predictions that are the "down" move (the move the
target's previous move beats). Fable actually plays down 48% of the time (repeat 21%). The Fable judge predicting Fable
predicts down 47% under TRUE, 43% ANONYMOUS, 41% FALSE, so the true self-label nudges it toward its own habit. The
Astra judge predicts down 52-60% for every target regardless of label, and Astra and Fable judges predict repeats only
5-10% of the time against actual repeat rates of 21-32%.
