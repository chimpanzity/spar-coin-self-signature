# NOTE: `*-false-protocol/` run below used the wrong shared-protocol prefix

The judge prompts in that run described the production method as
history_conditioned ("Each accepted outcome came from a fresh API request...
each request included the complete sequence of preceding accepted outcomes...")
even though the trajectories on display were produced by a DIFFERENT method.
The resulting data is informative only as a "judges-told-wrong-protocol"
diagnostic, not as the planned truthful-protocol identification run.

The truthful-protocol run for this method lives in the sibling run directory
without the `-false-protocol` suffix, with the shared prefix updated to
describe the method actually used to produce the sequences.
