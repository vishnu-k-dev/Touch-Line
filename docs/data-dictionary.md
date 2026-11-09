# Data dictionary

Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data) (attribution required wherever results are shown).
Raw files are fetched on demand into `data/raw/` (gitignored). Raw URL base:
`https://raw.githubusercontent.com/statsbomb/open-data/master/data`

## Chosen competition

**FIFA World Cup 2022**: `competition_id=43`, `season_id=106`. 64 matches, all with events, lineups and 360 freeze-frames.
Chosen because every match is one a reviewer can recognise and sanity-check, and 360 data exists for all of them.

## File layout

| File | Contents |
|---|---|
| `competitions.json` | One row per competition-season: `competition_id`, `season_id`, names, `match_available_360` |
| `matches/{competition_id}/{season_id}.json` | One row per match: `match_id`, date, home/away team and score, stage, stadium, referee |
| `events/{match_id}.json` | Array of events, about 2.6-3.8 MB per match |
| `lineups/{match_id}.json` | Two entries (one per team), each with a `lineup` array of players |
| `three-sixty/{match_id}.json` | Freeze-frames keyed by `event_uuid`, about 5-9 MB per match (not needed until after Day 2) |

## IDs

| ID | Where | Notes |
|---|---|---|
| `competition_id`, `season_id` | competitions, matches | Together identify a tournament edition |
| `match_id` | matches, file names | Integer; join key to events, lineups and 360 |
| event `id` | events | UUID string. This is the evidence reference the agent cites |
| `index` | events | 1-based order within the match |
| `possession` | events | Possession sequence number; groups events into possessions |
| `player.id`, `team.id` | events, lineups | Integers. Player *names* are long legal names, so always key on id |

## Event record (the fields we rely on)

| Field | Type | Meaning |
|---|---|---|
| `type.name` | string | 29 types seen in a single match (Pass, Carry, Pressure, Shot, Duel, ...) |
| `period` | int | 1-2 normal time, 3-4 extra time, **5 = penalty shootout** |
| `minute`, `second`, `timestamp` | int, int, `HH:MM:SS.mmm` | Clock within the period; the timestamp restarts each period |
| `team`, `possession_team`, `player`, `position` | `{id, name}` | Who did it and who had the ball |
| `location` | `[x, y]` | Pitch coordinates, see below. Absent on some events |
| `play_pattern.name` | string | How the possession started (Regular Play, From Corner, ...) |
| `under_pressure` | `true` or absent | Presence flag, not a boolean column |
| `related_events` | list of UUIDs | Links an event to e.g. its pass, pressure or shot |
| `duration` | float | Seconds |
| type-specific object | object | Key named after the type: `pass`, `shot`, `carry`, `duel`, ... |

### Pitch coordinates

120 x 80 grid. x runs 0-120 along the length and y 0-80 across it. **Every team is normalised to attack toward x=120**, so the coordinates are never flipped by half. Verified: observed max is exactly (120.0, 80.0).

### Shot (`type.name == "Shot"`)

| Field | Meaning |
|---|---|
| `shot.statsbomb_xg` | Expected-goals value, 0-1 |
| `shot.outcome.name` | Seen in the 5 matches: Saved, Blocked, Off T, Goal, Wayward, Post, Saved Off Target |
| `shot.end_location` | `[x, y, z]`, z is height. The pitch location is the event `location` |
| `shot.body_part.name`, `shot.technique.name`, `shot.type.name` | Left Foot, Normal, **Penalty**, Open Play, Free Kick |

## Lineup record

Per player: `player_id`, `player_name`, `player_nickname`, `jersey_number`, `country`, `cards[]`, `positions[]`.
`positions[]` holds each spell with `from`/`to` (`MM:SS`), `from_period`/`to_period`, and `start_reason`/`end_reason` (e.g. substitution, tactical shift). A player can have several position spells in a match.

## Shortlisted matches

All have events, lineups and 360. xG is summed over periods 1-4 (shootout excluded).

| match_id | Match | Score | Shots | xG | Why it is useful |
|---|---|---|---|---|---|
| 3869685 | Argentina - France (Final) | 3-3 (pens) | 20 / 10 | 2.76 / 2.27 | Extra time and a shootout; exercises period 5 handling |
| 3857300 | Argentina - Saudi Arabia | 1-2 | 15 / 3 | 2.49 / 0.15 | Clearest "created more, lost" case |
| 3857284 | Germany - Japan | 1-2 | 26 / 12 | 2.77 / 1.25 | Same pattern, higher volume |
| 3869354 | England - France (QF) | 1-2 | 16 / 8 | 2.35 / 0.84 | Same pattern, knockout stage |
| 3869220 | Morocco - Spain (R16) | 0-0 (pens) | 6 / 12 | 0.57 / 0.49 | Low-xG match, shootout, pressing-heavy: good for PPDA |

The shortlist is also saved in `data/samples/selected_matches.json`.

## 360 freeze-frames

Array of `{event_uuid, visible_area, freeze_frame}`. `event_uuid` equals an event `id` (verified: 2854 of 2854 entries for Argentina-Saudi Arabia match an event). `freeze_frame` lists the players the camera could see at that moment, each with `teammate`, `actor`, `keeper` and `location [x, y]`. `visible_area` is a polygon of the visible pitch region. Only part of the pitch is visible per frame, so it is not full tracking.

## Derived tables and fields (added after the first inspection)

| Item | Source and rule |
|---|---|
| `player_minutes` | From `Starting XI`, `Substitution` and red-card events (`foul_committed.card` / `bad_behaviour.card`), converted to elapsed minutes using each period's length from its `Half End` event. **Not** from lineup `positions[]`: in the two extra-time matches those spells contain backwards spells (e.g. from 120:05 in period 4 to 81:37 in period 2) and substituted-off players recorded as playing on. Check: each team's minutes sum to 11 × match length in all 5 matches. |
| Match clock | `minute` is cumulative within a half but **restarts in extra time** (period 3 starts at 90:00, period 4 at 105:00), so elapsed time must be computed per period. |
| `shots.defenders_in_cone`, `cone_visible`, `nearest_defender` | From the 360 freeze-frame of the same event (`event_uuid` equals the event `id`; 126 of 128 shots have one). Coordinates are identical to event coordinates (the frame's `actor` equals the event `location` in all 126). `visible_area` runs exactly to the goal line, so the posts are probed at x=119.5. **Lower bound**: 11 of 25 blocked shots show 0 defenders in the lane even when `cone_visible`. |
| PPDA | Opponent passes with x ≤ 72 (their own 60%) ÷ this team's tackles, interceptions, fouls committed and `Dribbled Past` events with x ≥ 48, periods 1-4. |
| `Dribbled Past` | A defender beaten by a dribble; counted as a failed defensive challenge in PPDA. |

## Rules and edge cases for the pipeline

1. **Exclude `period == 5` shots from xG and shot counts.** Shootout kicks are real Shot events and would otherwise inflate totals (the final has 8, Morocco-Spain has 7). Keep them as their own "shootout" category.
2. **Penalties are Shot events with `shot.type.name == "Penalty"`** (xG about 0.78). Report with and without penalties, because they distort "chance quality" claims.
3. **`statsbomb_xg` was present on every non-shootout shot** in the five matches, but the loader must still tolerate a missing value rather than assume it.
4. **Lineups and events can disagree on name spelling**; join on `player.id`, never on name.
5. **Store each event's full JSON in `events.raw_data`** (plan from the PRD) so type-specific fields are not lost.
6. **Event-data limits:** there is no full player tracking and no formations from video. `Pressure` events exist (361 in the final), so a PPDA-style metric is computable, but only from logged defensive actions.
