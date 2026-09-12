# Risk thresholds

> **These numbers are engineering placeholders. They are not INCOIS criteria.**
>
> Before any public claim, demo to a judge, or word of this reaching a fisherman,
> replace them with the published INCOIS Ocean State Forecast criteria and cite
> the source next to each row. Never present invented safety thresholds as
> official. `backend/dhruva/risk/thresholds.py` reads this table's values and
> carries the same warning as `PROVISIONAL = True`.

Every advisory built on this table carries: *advisory only, follow official
INCOIS and IMD warnings.*

## Per boat class

Significant wave height (H_s) and sustained wind. A 9 m FRP boat is not a 24 m
trawler, so one table would be wrong for everyone.

| Boat class | Caution H_s | No-go H_s | Caution wind | No-go wind |
|---|---|---|---|---|
| FRP / country craft < 12 m | 2.0 m | 3.0 m | 20 kt | 28 kt |
| Mechanised 12–20 m | 2.5 m | 3.5 m | 25 kt | 33 kt |
| Deep-sea > 20 m | 3.5 m | 4.5 m | 30 kt | 40 kt |

## Absolute overrides

These ignore boat class and ignore every favourable signal. They are evaluated
**before** the per-class table, and any one of them forces NO-GO.

| Rule | Condition | Verdict |
|---|---|---|
| `CYCLONE-A1` | Active cyclone warning within 300 km | NO-GO |
| `LIGHTNING-A2` | Lightning within 50 km | NO-GO |
| `TSUNAMI-A3` | Any tsunami alert in force | NO-GO |

## Rule IDs

Each rule that fires is recorded by ID on the evidence bundle, so a verdict can
be traced to the line that produced it rather than to "the model decided".

| ID | Meaning |
|---|---|
| `WAVE-C2` / `WAVE-N3` | Wave height reached caution / no-go for the boat class |
| `WIND-C2` / `WIND-N3` | Wind reached caution / no-go for the boat class |
| `CYCLONE-A1`, `LIGHTNING-A2`, `TSUNAMI-A3` | Absolute overrides above |
| `DATA-U0` | A threshold variable was unavailable, so no verdict is possible |

## Missing data is not safety

`DATA-U0` exists because the dangerous failure here is silent. If wave height
could not be fetched, the answer is **UNKNOWN**, never SAFE. A system that
returns "safe" when it simply does not know is worse than one that returns
nothing, because a crew acts on it.
