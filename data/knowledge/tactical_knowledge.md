# Touchline AI tactical knowledge base

Each `##` section is one retrievable document. Written for an analyst who must separate measured facts from interpretation. Numbers given are rules of thumb, not laws.

## Expected goals (xG)

Expected goals (xG) estimates the probability that a shot becomes a goal, as a number from 0 to 1. The estimate comes from features of the shot: mainly where it was taken from, plus body part, how the chance was created and, in StatsBomb's model, the positions of players visible at the moment of the shot. A shot worth 0.10 xG is expected to score about once in ten attempts. Adding up xG over a match gives the number of goals a team would score on average from the chances it created. xG measures the quality of chances, not what actually happened, so it is the standard way to ask whether a result was deserved.

## Shot quality versus shot volume (xG per shot)

Total shots and total xG answer different questions. Shot volume is how often a team shoots; xG per shot (total xG divided by shots) is how good those shots were on average. A team can have many shots but low xG per shot if it shoots from distance or under pressure, and a team with few shots can still have high total xG if each shot was a clear chance. When comparing two teams, look at both: more shots with a lower xG per shot means more speculative attempts, while fewer shots with a higher xG per shot means more selective, higher quality chances.

## Non-penalty xG (npxG)

Non-penalty xG removes penalty kicks from the xG total. A penalty is worth roughly 0.78 xG on its own, so one penalty can make a team look far more dangerous than its open play was. Penalties depend on a refereeing decision and happen rarely, which makes them a poor guide to how well a team creates chances from play. When judging chance creation from open play, use npxG; when judging what a team was expected to score in the match, include penalties and say so.

## Why a team can lose despite higher xG

xG is an expectation, not a result, so a team can create better chances and still lose. Common reasons: finishing variance (even good chances score only some of the time), an excellent goalkeeper performance, and many low-quality shots that add up to a high xG total (ten shots of 0.10 xG sum to 1.0 xG, but the chance of scoring at least once from them is only about 65 percent, not certain). Game state also matters: a team that leads often defends deep and a trailing team shoots more, so xG totals can reflect who was chasing the game. A single match is a small sample, so a gap between xG and goals is often just chance. The xG numbers are measured facts; the reasons for a particular loss are interpretation and should be stated with that uncertainty.

## Finishing and goalkeeping: goals versus xG

Comparing goals with xG shows whether a team or player scored more or fewer goals than the chances suggested. Goals above xG is called overperformance and goals below xG underperformance. Over one match this difference is mostly noise: a single shot converted or missed swings the number. Over a full season, some elite finishers do beat their xG slightly, but most large gaps shrink toward zero as more shots are taken. The same applies to goalkeepers when comparing goals conceded with the xG they faced. Treat a one-match overperformance as luck unless there is other evidence such as repeated shot placement quality across many matches.

## Reading a shot map (location and distance)

Distance to goal and shooting angle are the biggest drivers of xG. In StatsBomb coordinates the pitch is 120 by 80, every team attacks toward x equals 120, and the centre of the goal is at about (120, 40). The penalty area spans x from 102 to 120 and y from 18 to 62. The six-yard box spans x from 114 to 120 and y from 30 to 50. Central shots near the six-yard box are the most valuable; shots from outside the penalty area are usually worth only a few percent each; shots from narrow angles near the byline are worth little. A shot map with many dots outside the box means low-quality attempts, while a cluster of shots inside the box means the team got into dangerous areas.

## Penalties in xG

A penalty kick is worth roughly 0.78 xG, far more than almost any shot from open play. Because of this, a team that wins a penalty gets a large xG boost from one decision. Report penalty xG separately from open-play xG when explaining a match, and use non-penalty xG to judge chance creation from play. Penalty-shootout kicks after extra time are a different thing and are not part of match xG.

## Set pieces: corners, free kicks and throw-ins

Many chances start from dead balls rather than open play. StatsBomb records how each possession began, for example from a corner, a free kick, a throw-in, a goal kick, the goalkeeper or a counter-attack. Corners and free kicks into the box often produce headers, which tend to be lower quality than shots at feet, while a quick throw-in or free kick can create a clean chance. When explaining where a team's chances came from, split them by how the possession started and say how many were set-piece chances versus open play.

## Game state and its effect on shots

Game state means whether a team is leading, level or trailing. It changes behaviour: teams that lead often drop deeper, give up territory and shoot less, while trailing teams push players forward and take more shots, often of lower quality. So a late burst of shots or xG may reflect a team chasing the game rather than dominating it. Match totals hide this, so when interpreting xG, check when the chances happened relative to the goals, and consider a team that scored early may have chosen to defend its lead.

## Pressing and PPDA

Pressing intensity is measured with PPDA, which stands for passes allowed per defensive action. It is the number of passes the opposition makes in its own part of the pitch (usually the opponent's own 60 percent) divided by the defensive actions of the pressing team in that zone, typically tackles, interceptions, fouls and challenges. A lower PPDA means the team lets the opponent make fewer passes before disrupting them, so a more intense press. Rough rules of thumb: very aggressive pressing sides are often below about 10, and teams that defend in a deep block are often above 15, but values depend on the data provider and how defensive actions are defined, so only compare PPDA calculated the same way. PPDA says how often a team pressed, not whether the press won the ball in useful places.

## Pressure events and being under pressure

In StatsBomb data, a Pressure event is logged against the player who applies pressure to an opponent with the ball, so counting a team's Pressure events measures how often it pressured. Separately, an event such as a pass or a carry is flagged under pressure when the player doing it was being pressured. A team's pressure count rises when it presses more or when it simply has to defend more, so compare pressures with how much the opponent had the ball. The number of pressures by itself does not say whether the press was successful.

## High press, mid block and low block

These labels describe where a team defends. A high press tries to win the ball in the opponent's half, a mid block defends around the halfway line, and a low block defends deep near its own penalty area, giving up the ball and space in front. Event data cannot measure defensive line height directly because it does not track all players, but it can approximate it: the average position of a team's pressures, tackles and interceptions shows how high up the pitch it defended. A team with few pressures high up the pitch and many clearances and blocks near its own box is likely defending in a low block. This is an interpretation from defensive actions, not a measured formation.

## Counter-pressing and transitions

Counter-pressing, or gegenpressing, means pressing immediately after losing the ball to win it back before the opponent can organise a counter-attack. StatsBomb flags pressure applied within a short window after a turnover as counterpress. Transitions are the moments when possession switches. Teams that counter-press aim to attack the opponent while it is disorganised; teams that defend deep aim to win the ball and break quickly. StatsBomb also records when a possession began from a counter-attack, which shows how often a team created chances in transition rather than in settled attacks.

## Possession versus chance creation (pass share)

Having more of the ball is not the same as creating more chances. The event data used here gives pass share, a team's percentage of all passes in the match, as a proxy for possession; it is not time-based possession. A team with a high pass share can still produce little if the opponent sits in a low block and lets it pass in harmless areas, while a team with a low pass share can produce good chances by attacking quickly. To judge whether possession was useful, compare pass share with shots, xG and xG per shot rather than treating possession as an achievement on its own.

## Pass accuracy: what it does and does not tell you

Pass accuracy is the share of passes that reach a teammate. In StatsBomb data a pass with no outcome recorded counts as completed, and outcomes such as incomplete or out are logged only for failed passes. High pass accuracy often reflects safe, short passing and patient build-up; lower accuracy can come from direct, ambitious passing that tries to break lines or from playing against heavy pressure. Accuracy ignores where on the pitch passes happen and how risky they are, so a high number does not mean the team was effective. Use it together with shots, xG and territory, and do not treat it as a quality score on its own.

## Key passes and assists

Chance creators, the players who set up shots for their teammates, are identified by key passes and assists. A key pass is a pass that leads directly to a shot, and an assist is a pass that leads directly to a goal, so every assist is a key pass. In StatsBomb data these are flags on the pass event, which makes them easy to count per player. Key passes show who creates shooting chances, while assists depend heavily on whether the shooter finishes, so a player can have many key passes and few assists simply because teammates missed. Judging creators by key passes and the xG of the shots they set up is more stable than by assists alone.

## Shots on target

A shot on target is a shot that is a goal or is saved by the goalkeeper (including saved onto the post); shots blocked by defenders, off target or that hit the woodwork without a keeper touch are not counted here. The share of shots on target shows how often attempts tested the goalkeeper, but it ignores how good the chance was, so a team can have many on-target shots from low-xG positions. Use shots on target alongside xG: on-target shots with low xG are mostly easy saves, while on-target shots with high xG are real tests.

## Small samples: why one match is noisy

Football is low scoring, so single-match outcomes carry a large amount of randomness. One or two goals decide most games, and one shot or one save can swing the result and the goals-versus-xG gap. Match xG describes the chances created in that match, not how good a team is in general, and a team's real strength is better judged over many matches. When explaining a single match, say plainly that conclusions are tentative and that measured numbers such as xG and shot counts are more reliable than causal stories about why the result happened.

## Penalty shootouts

A penalty shootout is the tie-break after a knockout match that is level after extra time. Shootout kicks appear in event data as Shot events in a separate period, number five, but they are not part of the match: they are excluded from goals, shots and xG here and reported separately as shootout goals. A match that finishes 3-3 and is decided on penalties is a draw in match statistics, with the shootout result recorded alongside. Shootout results are tied to nerve and goalkeeping rather than match performance, and should not be used to explain how the 120 minutes went.

## Substitutions and tactical shifts

StatsBomb records substitutions and tactical shifts as events, so you can see when a team changed personnel or shape. This helps explain changes in a match, for example a shift in pressing or a new striker after the hour, but the data records what changed and when, not why. Interpretations about a coach's intention are inference. A good explanation connects a change at a specific minute to a measurable change afterward, such as more shots or fewer pressures, and labels the link as a likely explanation, not a proven cause.

## What event data cannot tell you

Event data records on-ball actions such as passes, carries, shots, pressures and duels. It does not track every player's movement, so it cannot measure formations from video, exact defensive line height, off-ball runs or player speed and distance. StatsBomb 360 data adds freeze-frames, the positions of the players visible to the camera at each event, but only for part of the pitch and only at the moment of the event, so it is a snapshot, not continuous tracking. Any claim about formations, off-ball movement or physical load goes beyond this dataset and must be marked as unsupported rather than guessed.

## Action-value models (xT and VAEP)

Some models value every on-ball action, not only shots. Expected threat (xT) divides the pitch into zones and values each by how likely possession there leads to a goal soon, so passes and carries that move the ball into more dangerous zones add value. VAEP values every action by how much it changes the probability of scoring and conceding. These credit build-up play and defensive actions that shot-based xG ignores. They are different metrics from the xG used here and are not calculated in this product; if asked about them, explain the idea and say they are not available.

## Measurement versus interpretation

Every answer should separate two things. A measured fact is a count or sum computed directly from the event data, such as shots, xG, pass accuracy or goals, and it can be traced to specific events. An interpretation is an explanation of why something happened, such as a tactical reason for a result, and it can be wrong. Label measured facts with the numbers and the events behind them, label interpretations as inference, and state limits plainly: single matches are noisy, event data lacks tracking, and some metrics are not computed. If the data does not support a claim, say so instead of guessing.
