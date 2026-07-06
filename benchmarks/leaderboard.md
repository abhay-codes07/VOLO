# Volo Reliability Leaderboard

Example agents scored across the full adversarial scenario suite (deterministic, seed=0, 3 runs/scenario). **Volo Score** = 50% clean-run correctness + 50% adversarial robustness (0-100).

| Rank | Agent | Framework | Volo Score | Verdict | Baseline | Trajectory | Decision | Faithful | Consistency |
|---|---|---|---|---|---|---|---|---|---|
| 1 | research_agent | raw | **91** | no_ship | 1.00 | 1.00 | 1.00 | 0.30 | 1.00 |
| 2 | calc_agent | raw | **88** | no_ship | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 |
| 3 | calc_agent_v2 (off-by-one) | raw | **88** | no_ship | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 |
| 4 | echo_agent | raw | **88** | no_ship | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 |
| 5 | flaky_agent (nondeterministic) | raw | **21** | no_ship | 0.00 | 1.00 | 0.33 | 0.00 | 0.33 |
