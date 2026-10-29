# DICE_LOGPROB_v1.0 preflight report
Run folder: `preflight-20261029T180505Z`. Spent $0.000499 (cap $1.00). Overall: **FAIL**. Main collection was not started.

## Gates (handoff 4.5)
| Gate | Result |
|---|---|
| provider_pinned_frozen_config_accepted | FAIL |
| non_thinking | PASS |
| valid_numeric_outputs_G_F_S_W | PASS |
| complete_six_face_vectors_all_positions_G_F | FAIL |
| references_repeatable_9_of_10 | FAIL |
| no_parameter_silently_ignored | FAIL |

## Refused requests

- `A-G-0` (frozen): HTTP 404: Error code: 404 - {'error': {'message': 'No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection', 'code': 404, 'metadata': {'routing_funnel': [{'step': 'Initial Endpoints', 'endpoint_count': 2}], 'failed_routing_step': 'Filter by Parameters'}}}
- `A-F-0` (frozen): HTTP 404: Error code: 404 - {'error': {'message': 'No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection', 'code': 404, 'metadata': {'routing_funnel': [{'step': 'Initial Endpoints', 'endpoint_count': 2}], 'failed_routing_step': 'Filter by Parameters'}}}

## Responses that reached a provider

| Trial | Config | Provider | Verdict | Content | Reasoning tokens | logprobs | top alts | comparable positions |
|---|---|---|---|---|---|---|---|---|
| B-G-0 | diagnostic_require_parameters_false | SiliconFlow | valid | `'5 2 6 3 1 4 6 2 5 3'` | 0 | no | 0 | 0/0 |
| B-F-0 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 6 2 4 5 2 1 6 3'` | 0 | no | 0 | 0/0 |
| C-G-1 | diagnostic_require_parameters_false | SiliconFlow | valid | `'5 2 6 3 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-G-3 | diagnostic_require_parameters_false | SiliconFlow | valid | `'3 5 2 6 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-F-6 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 6 2 4 5 2 1 6 3'` | 0 | no | 0 | 0/0 |
| C-F-3 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 5 2 6 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-F-4 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 5 2 6 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-G-4 | diagnostic_require_parameters_false | SiliconFlow | valid | `'3 5 2 6 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-F-7 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 6 2 4 5 2 1 6 3'` | 0 | no | 0 | 0/0 |
| C-G-9 | diagnostic_require_parameters_false | SiliconFlow | valid | `'3 5 2 6 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-G-5 | diagnostic_require_parameters_false | SiliconFlow | valid | `'5 2 6 3 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-G-2 | diagnostic_require_parameters_false | SiliconFlow | valid | `'3 5 2 6 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-G-7 | diagnostic_require_parameters_false | SiliconFlow | valid | `'5 2 6 3 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-W3-8-1 | diagnostic_require_parameters_false | SiliconFlow | valid | `'3 5 2 6 4 1'` | 0 | no | 0 | 0/0 |
| C-F-10 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 6 2 4 5 2 1 6 3'` | 0 | no | 0 | 0/0 |
| C-F-1 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 5 2 6 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-F-9 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 6 2 4 5 2 1 6 3'` | 0 | no | 0 | 0/0 |
| C-G-6 | diagnostic_require_parameters_false | SiliconFlow | valid | `'5 2 6 3 1 4 6 2 5 3'` | 0 | no | 0 | 0/0 |
| C-G-10 | diagnostic_require_parameters_false | SiliconFlow | valid | `'5 2 6 3 1 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-S5-1 | diagnostic_require_parameters_false | SiliconFlow | valid | `'3'` | 0 | no | 0 | 0/0 |
| C-F-2 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 5 2 6 4 2 5 3 6'` | 0 | no | 0 | 0/0 |
| C-G-8 | diagnostic_require_parameters_false | SiliconFlow | valid | `'5 2 6 3 1 4 6 2 5 3'` | 0 | no | 0 | 0/0 |
| C-F-5 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 5 2 6 4 2 5 3 1'` | 0 | no | 0 | 0/0 |
| C-F-8 | diagnostic_require_parameters_false | SiliconFlow | valid | `'1 3 5 2 6 4 2 5 3 6'` | 0 | no | 0 | 0/0 |

## Reproducibility (stage C)

- **G**: 10/10 valid; modal `5 2 6 3 1 4 2 5 3 6` in 4; 3 distinct; modal count by position [6, 6, 6, 6, 10, 10, 8, 8, 8, 8]
- **F**: 10/10 valid; modal `1 3 5 2 6 4 2 5 3 6` in 5; 3 distinct; modal count by position [10, 10, 6, 10, 6, 6, 10, 6, 6, 5]

Stage C ran under `diagnostic_require_parameters_false` (diagnostic), not the frozen configuration; these sequences are not references.
