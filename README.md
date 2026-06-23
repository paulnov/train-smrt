# AI Training Coach: Smash your PR 🦿

**ChatGPT has aced training physiology, but it doesn't know about you:** your goals, your skills, how well you follow advice, what kind of advice you find useful. And your training plan needs to update according to life constraints: travel, illness, fatigue, schedule pressure, or changes of plans.

This repo structure puts all this info into a GPT context window to **massively upgrade the quality and personalization of your training advice.** As you work with the coach, you can improve and tweak it to be more and more tuned to the kind of feedback that works for you.

**TL;DR for everything below: Clone repo, run Codex, start talking.**

<figure>
  <img src="assets/train-readme.png" alt="Training analysis that actually makes sense">
</figure>

## Why this beats Strava / Garmin AI coaches

The app platforms want to generate coaching advice entirely from app data. This would be cool, but it seems hopeless to me, because the subjective info you share with a coach is essential. Maybe you took it easy because you were feeling sick, or it was deathly hot, or you were running on boulders, or you went fast because you were running with a friend or accidentally coded your ride as a run.

The narrative is essential to the plan; **the coach needs to know how you're feeling in your own words.** The 2026 iterations of AI coaches are laughably bad. This is 100x better; it just works.

## Initial content

This is seeded with a time slice of my training plans from November 2025 when I was training to beat a 5k PR. I updated the goal partway in, hence some inconsistency in the docs.

The HTML files show the current quarterly and weekly plans, and the last few daily updates. The agents archives these automatically as time passes.

I like my advice grounded in physiology and evidence, hence the relatively technical nature of the AI feedback. I found GPT's default mode to be excessively inspirational and vapid, so I toned it way down in `AGENTS.md`. I discovered that I liked having a coach who was mildly annoyed when I didn't stick with the plan. Experiment and change the tone to whatever works for you.

## Getting Started

1. Edit `markdown/notes-on-user.md` with background info on your experience and your goals.
2. Create a `markdown/quarter-plan-YYYY-MM.md` with goals, constraints, and target events. Add an `app-index` block if you want the homepage to show a specific title and date range. Or just skip this step and narrate your plan to Codex in step 3.
3. In Codex / Claude Code, ask the coach to make you a draft plan for the quarter. Negotiate / discuss until you're happy with it.
4. Ask the coach to draft your first weekly plan, providing any schedule or travel constraints that need to be considered.
5. Review, discuss, make it work to your liking. I never edit the weekly files directly, I just talk to the AI like I would with a real coach and the AI updates the plan.
6. **Get outside and follow the plan!**
7. Tell Codex how it went. It's good to put a lot of information here, because it will keep getting used in the days ahead.
8. Whenever you want, ask the coach to write you a daily advice file. These are more detailed and provide analysis of past workouts, adjustments to plans going forward. I do this every few days. If you're just sticking with the weekly plan, it's not necessary. The content of the example advice files is varied, because it usually involves answers to questions I put on the command line, like "why u make me do strides every day."

The coach will move old stuff to `markdown/archive/` in order to keep the repo clean. You can change the frequency, or anything about this, by editing `AGENTS.md`.

## Role of markdown and HTML

This is still in a state of flux. The first iteration of this project was all markdown, but the navigable HTML files are a big UI improvement. Currently the system uses the markdown files as the source of truth and generates the HTML from them. I set it up like this because I thought I would occasionally want to edit the markdown --- but I pretty much never do, so I'll probably cut the markdown phase from the loop entirely.

## Things that worked well

**Tell the coach how you felt.** My initial tendency was always to push harder than the plan called for. More is better, right? Every time I did this, the coach dialed back my next day's workout for more recovery. I'm sure this reduced my injury risk and gradually taught me to actually follow the advice. Feeling sick, concerned about injury risk, pushed your HR past the targets, put it all in your report.

**Ask why.** I learned a ton about training physiology through this plan. After decades of sub-optimal training I finally learned why "go as hard as you can every time you're out there" isn't the best.

**Update the reference files.** There are placeholder files in `markdown/` for you to add info about race history, HR zones, exercise catalogs, etc. These can all finetune the advice you get. The more permanent info you give the coach, the less you need to explain each time. Common knowledge is good. You can say "HR went to 165 in the last tempo" and the coach knows what this means.

**Ask the AI to take stock of the whole repo.** The custom instructions can get out of date or contradictory, it's good to do a cleanup once in a while.

## Things that could be improved

- **Lock down the formats you like.** The formats of the weekly plans drift, because there isn't a template, I'm constantly asking for changes, and the AI is often adding weird things and lingo and then propagating them into future plans. Once you get a format you like, lock it down into a template and instruct the agent to use it everytime. This sort of works, sometimes.
- **Link to Strava/Garmin (?)** I occasionally copy/pasted my splits and HR info into the Codex window if I wanted more analysis. It would be nice to pull these directly from Strava or Garmin. It might work. But you really need to stop the AI from treating the data as the source of truth, because it's meaningless without the narrative context. So it might be better just to summarize the parts that you think are useful or want feedback on. The AI isn't great at prioritizing or ignoring information, so if you stop for ice cream it will keep on acting like you had a terrible split.
- **Link to resting HR/HRV.** They say resting HR provides advance info on recovery / illness. So it would be cool if the coach just had this info in the context without you needing to share it.
- **Improve the HTML UI?** Would this be better in a web app with text boxes? I'm not sure, I kind of like the back-and-forth with the coach in the Codex window. YMMV.

- **If you build on this, I would love to hear from you.**
