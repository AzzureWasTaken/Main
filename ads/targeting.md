# MineX SMP — Reddit targeting

## Community targeting

Reddit requires a minimum audience size, so stack communities into one group per
ad set rather than running a separate ad set per subreddit.

### Group 1 — core Minecraft (primary)

```
r/Minecraft
r/MinecraftMemes
r/Minecraftbuilds
r/MinecraftOnePointTwenty
r/MinecraftBuddies
r/mcservers
r/MinecraftServer
```

`r/MinecraftBuddies` and `r/mcservers` are small but are the highest-intent
audiences on the platform — people there are explicitly looking for a server to
join. Expect a better conversion rate and a worse volume ceiling.

### Group 2 — adjacent gaming (scale)

```
r/gaming
r/pcgaming
r/survivalgaming
r/feedthebeast
r/technicalminecraft
```

Lower intent, much larger. Only open this once Group 1 has produced a headline
that converts — it will burn budget fast on an unproven ad.

### Exclude

```
r/admincraft
r/MinecraftPlugins
```

These are server *owners*, not players. They will click out of professional
curiosity and never join. Excluding them measurably improves cost per join.

## Interest targeting

Run as a separate ad set, not combined with communities — combining them makes
the result unreadable.

- Gaming → Sandbox Games
- Gaming → PC Gaming

Interest targeting reaches people outside the Minecraft subs who still play.
Broader, cheaper CPMs, weaker intent.

## Demographics

- **Age:** 18–24 primary, 25–34 secondary. Reddit's floor is 18 for ad
  targeting. The under-18 Minecraft audience is not addressable here at all,
  which is worth knowing before you judge the results — if your server skews
  young, Reddit is reaching their older siblings, not them.
- **Geo:** set deliberately. If the server is hosted in the EU, advertising in
  the US sells a 120ms ping. Start with the host region plus neighbours.
- **Device:** all. Most browsing is mobile; most *joining* is desktop. This gap
  is normal and is why Discord-as-destination matters — it bridges the session.
  Someone can tap the ad on a phone, join the Discord, and get the IP when they
  sit down at their PC that evening.

## Schedule

Weight toward **15:00–23:00 local**, heaviest Friday through Sunday. That is
when the audience is at a machine that can run the game. Daytime weekday
impressions are cheap for a reason.

## Measurement

| Metric | Where | Target |
|---|---|---|
| Clicks | Reddit Ads | — |
| Discord joins | Per-variant invite code | primary KPI |
| Server logins | Server-side, new UUIDs/day | true KPI |
| D7 retention | Server-side | tells you if it was worth it |

Reddit's own conversion tracking cannot see a Minecraft login, so the
invite-code split is doing the real attribution work here. Set it up before the
first impression — it cannot be reconstructed afterwards.

Watch the gap between Discord joins and server logins. If people are joining the
Discord and not the server, the ads are working and the welcome channel is not.
That is a cheap fix, but only if you are measuring both numbers separately.
