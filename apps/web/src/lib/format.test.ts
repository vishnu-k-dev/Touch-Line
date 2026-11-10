import { describe, expect, it } from "vitest";
import { dateLabel, fmt, shortId, xgStory } from "./format";
import type { Match, MatchStats, TeamStats } from "./types";

const team = (name: string, goals: number, xg: number, shootout: number | null = null) =>
  ({ team: name, goals, xg, shootout_goals: shootout }) as TeamStats;
const match = {} as Match;
const stats = (home: TeamStats, away: TeamStats) => ({ home, away }) as MatchStats;

describe("fmt", () => {
  it("rounds, pads and handles missing values", () => {
    expect(fmt(2.4899)).toBe("2.49");
    expect(fmt(3, 0)).toBe("3");
    expect(fmt(0.1666, 3)).toBe("0.167");
    expect(fmt(null)).toBe("–");
    expect(fmt(undefined)).toBe("–");
  });
});

describe("shortId / dateLabel", () => {
  it("shortens a StatsBomb event id", () => {
    expect(shortId("87e2e8be-e11d-43d6-b9fd-fab92bf1bfb1")).toBe("87e2e8be");
  });
  it("formats an ISO date without a timezone shift", () => {
    expect(dateLabel("2022-12-18")).toBe("18 Dec 2022");
    expect(dateLabel("2022-11-01")).toBe("1 Nov 2022");
  });
});

describe("xgStory", () => {
  it("flags the side with more xG that lost", () => {
    expect(xgStory(match, stats(team("Argentina", 1, 2.49), team("Saudi Arabia", 2, 0.15)))).toBe("Argentina had more xG (2.49 v 0.15) but lost");
    expect(xgStory(match, stats(team("Japan", 2, 1.25), team("Germany", 1, 2.77)))).toContain("Germany had more xG");
  });
  it("says nothing when the higher-xG side won, or xG is level", () => {
    expect(xgStory(match, stats(team("A", 3, 2), team("B", 0, 0.5)))).toBeNull();
    expect(xgStory(match, stats(team("A", 1, 1), team("B", 1, 1)))).toBeNull();
    expect(xgStory(match, undefined)).toBeNull();
  });
  it("describes a draw decided on penalties differently from a plain draw", () => {
    expect(xgStory(match, stats(team("Morocco", 0, 0.57, 3), team("Spain", 0, 0.49, 0)))).toBe(
      "Morocco had more xG (0.57 v 0.49); level after extra time, decided on penalties",
    );
    expect(xgStory(match, stats(team("A", 0, 1.2), team("B", 0, 0.4)))).toBe("A had more xG (1.20 v 0.40) but could not break through");
  });
});
