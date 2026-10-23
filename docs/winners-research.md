# Winners research

This note collects advice from people who won hackathons. It also checks the past OpenCV competition winners and compares both with Twice.

How the sources were read:

- Every source below was fetched and read on 23 October 2026. Pages that failed to load were dropped.
- The advice is paraphrased. A fetch tool summarised each page, so this note uses almost no direct quotes.
- Four pages were dropped because they failed to load or were not winner accounts: Medium (River Tam), Klaviyo's engineering blog, a Five.Co tips post and a dev.to post by an author with no wins.
- `opencv.org`, `hackster.io` and `opencv26.devpost.com` refused the fetch tool with HTTP 403. They loaded with `curl` and a browser user agent. The URLs below are the public pages.

## 1. Advice from hackathon winners

Eight sources. Some pages do not name the prize. Those cases are marked.

### 1. What I Learned from Winning a Hackathon

- Author: Jarrod Miller
- URL: https://activeprospect.com/blog/what-i-learned-from-winning-a-hackathon/
- Won: Yuuvis's first hackathon in Austin, Texas. The prize was $5,000 and a trip to Berlin.
- Advice:
  - Team with people you already know. The team could be blunt with each other and still trust each other.
  - Pick an idea you are sure you can build. A feature-rich tool that worked in the demo beat flashy ideas.
  - Learn what the judges want. They favoured software that could become a startup. Ambitious but unpolished entries lost.
  - Reliable, bug-free software and some luck mattered. Many strong teams competed.

### 2. A simple checklist to help you win (and have fun) at hackathons

- Author: Palash Taneja
- URL: https://www.freecodecamp.org/news/a-simple-checklist-to-help-you-win-or-have-fun-at-hackathons-98030be1a6c8/
- Won: The author says they won 4 of more than 10 hackathons. The page does not name the events or the prizes.
- Advice:
  - Solve a large problem. Real-world impact can be up to 25% of the score, so it beats a polished but trivial hack.
  - Build a demo that wows. Show the core function and let the audience try it.
  - Choose core function over design when you must choose. The author does so nine times in ten.
  - Aim at smaller sponsor API prizes, because few teams read them.

### 3. Lessons from Winning Five Hackathons

- Author: Ray Deck
- URL: https://sustained.substack.com/p/lessons-from-winning-five-hackathons
- Won: Prizes in most of six hackathons in 2022. The page names no events or amounts, except one small first prize.
- Advice:
  - Topic matters most. Ask what the sponsor values. The author lost one category by building for their own interest.
  - The demo video is the main thing judges see. Make it clear, shareable and about the sponsor's topic.
  - Cut features to ship before the deadline. A weak but working demo reached a shortlist.
  - Shipping is a skill. Entering often made each entry better.

### 4. We Won 1st Place Grand Prize at Cal Hacks

- Author: Dylan Lu
- URL: https://blog.dylanlu.com/cal-hacks-12/
- Won: First place Grand Prize at Cal Hacks 12.0, among 695 projects and more than 3,000 hackers.
- Advice:
  - Read last year's winners and aim to beat them.
  - Make the idea distinctive and useful to many people, because judges weigh impact.
  - Give one teammate the UI and the demo. Keep a hardcoded fallback for when features break.
  - Show only what works. The agent clicked unreliably, so the team limited the demo to keyboard actions.
  - Agree on the interfaces first so the team can build in parallel.

### 5. How To Win Hackathons

- Author: John Kim
- URL: https://getpushtoprod.substack.com/p/how-to-win-hackathons
- Won: The author reports about seven or eight wins and roughly $40,000 split with teammates. Two are named: TechCrunch Disrupt (the Esri sponsor prize) and an AI robotics hackathon in San Francisco (the grand prize).
- Advice:
  - Treat a hackathon as marketing. Sponsors want their tools used well and judges want a strong demo.
  - Build for the demo, not the product. Make the core feature reliable and simplify the rest.
  - Record a backup video in case the live demo fails.
  - Present gaps as deliberate tradeoffs.
  - Build rapport with sponsors early, and fit one project to several tracks.
  - Pick teammates you trust, and cover three roles: presenter, deep technical, integrator.

### 6. How to win at hackathons!

- Author: Jeremy Kintana (Substack, 14 August 2025)
- URL: https://jeremykintana.substack.com/p/how-to-win-at-hackathons
- Won: One first place, MadHacks 2023, which the author hedges ("I genuinely think we won"). The page also says they were never a finalist, which conflicts. Treat this source as the weakest.
- Advice:
  - Aim for a minimum presentable product, not a minimum viable one. Console errors are fine if the live demo works.
  - Learn the judging format and the prize tracks early.
  - Keep the team small and chosen before the event. Finish the core before extras.
  - Use a five-part pitch: problem, existing solutions, your solution, how you built it, what is next.

### 7. Hackathon Winning 101: Insider Tips from a Seasoned Participant

- Author: Dhruv Mehta (DEV Community, 1 July 2024)
- URL: https://dev.to/dhruv194/hackathon-winning-101-insider-tips-from-a-seasoned-participant-2k9d
- Won: The author says they won HackOn 2020, HackJaipur 2020, ETHIndia'22 and Aptos Winter School'23. The page gives no placements or amounts.
- Advice:
  - Build a product that solves a problem, not a project.
  - Validate the idea with research and say how it could grow.
  - Build a working prototype that judges can try.
  - Write a short, clear README that explains the process, the technology and the reasons.

### 8. How to Win Your First Hackathon: A Complete Guide

- Author: Hardik Gayner (DEV Community)
- URL: https://dev.to/imhardik/how-to-win-your-first-hackathon-a-complete-guide-4dkl
- Won: RTHack twice in a row. The page gives no prizes.
- Advice:
  - Pick teammates with complementary skills.
  - Study the challenge and learn what the judges expect before you write code.
  - Build a working core before extra features, and reserve time to test and fix bugs.
  - Show the product working live when the rules allow it.

## 2. Past OpenCV competition winners

| Year | Competition | Winners | Source |
|---|---|---|---|
| 2021 | OpenCV AI Competition (OAK-D, sponsored by Intel) | 1st Cortic Tigers, "Democratizing A.I. using the OAK-D" ($20K). 2nd Caleta, "NeoCam: Real-time telemonitoring of preterm neonates" ($10K). 3rd Cerebros, "Next-Generation Electric Wheelchair" ($5K). | https://opencv.org/opencv-ai-competition-2021/ |
| 2022 | OpenCV AI Competition, Core track | 1st Recycling Rush, "Aquatic Recycling via Autonomous Duckweed Collection in Lake Titicaca" ($5,000). 2nd DeViTech, "Red Dot Scanner: A laser-based optical 3D scanner" ($3,000). 3rd Demacia, "Virtual Point-to-Read Learning System" ($2,000). | https://opencv.org/opencv-ai-competition-2022/ |
| 2023 | OpenCV AI Competition 2023 (Hackster, Khadas, Seeed) | 1st B-AROL-O, "Four-legged Robot Ensuring Intelligent Sprinkler Automation" (FREISA). 2nd "OpenCV for Exoplanet Detection". 3rd "IC4U - Robot Guide Dog for Visually Impaired People". | https://www.hackster.io/contests/opencv-ai-competition-2023, https://www.seeedstudio.com/blog/2024/01/16/announcing-the-champions-of-the-opencv-ai-competition-2023/, https://github.com/B-AROL-O/FREISA |
| 2024 | none found | I found no OpenCV competition winners for 2024. A web search turned up none. | none |
| 2025 | OpenCV Perception Challenge for Bin-Picking (not the AI Competition) | Grand Prize ($18,000) GBP2025. 2nd SEU_WYL_trained. 3rd JPose. Special one-shot prize SEU_WYL_oneshot. More than 450 teams. | https://opencv.org/?p=32653 |

Notes on the table:

- The 2021 and 2022 rows match `docs/research.md`, with two caveats. That file calls NeoCam "preterm baby breathing via depth" and Cerebros "EEG wheelchair". The official page does not say either. A Spanish university news item calls NeoCam "contactless baby monitoring" (https://datalab.uca.es/news/caleta-team-wins-the-opencv-ai-competition-region/). The "education kit" label for Cortic Tigers is also not on the official page.
- The 2023 Hackster page lists project names and author names in a jumbled order. I list project names only. Seeed's post names B-AROL-O as the Grand Prize winner and says the team did well in earlier competitions (same Seeed URL).
- The 2025 final scores came from live runs on a real robot cell: GBP2025 scored 14, SEU_WYL_trained 13, JPose 13 (https://opencv.org/?p=32653). Intrinsic says most top solutions used multiview pose estimation (https://www.intrinsic.ai/blog/posts/accelerating-advances-in-ai-driven-perception-to-unlock-new-value-for-industry).

### Pattern in what won

- **A person or a place sits in the title.** Premature babies, a wheelchair user, Lake Titicaca, a visually impaired person, a garden. The 2021 to 2023 podium titles name a human need or a real site (sources in the table).
- **A physical system is common.** Most podium titles name a kit, a robot, a scanner or a wheelchair. Twice has no hardware, so it cannot lean on that.
- **Real-world proof is rewarded.** The OpenCV chief executive said the 2025 winners "proved their AI models in the real world, on a real robot" (https://opencv.org/?p=32653).
- **Teams return.** B-AROL-O won in 2023 after earlier strong showings (Seeed URL above). Cortic Tigers won the global first prize in 2021 and also appears in the North America regional list on the same page (https://opencv.org/opencv-ai-competition-2021/).
- **The report and code carried the score in 2022.** The 2022 rules gave 80% of the credit to the technical report and working code and 20% to a video of about five minutes (https://opencv.org/opencv-ai-competition-2022/).

The 2026 rubric on Devpost weights technical execution 30%, innovation 20%, real-world impact 20%, user experience 10%, documentation and presentation 10%, and cloud delivery, reproducibility and responsible operation 10%. It requires a working web endpoint or an arranged live screen-share, a video of five minutes or less, and failure cases (https://opencv26.devpost.com/).

## 3. Checklist against Twice

Source numbers refer to section 1. Every repo file named here exists in this branch.

| Advice | Sources | Where Twice meets it | Gap |
|---|---|---|---|
| Ship a working core and cut scope | 1, 2, 3, 5, 6, 8 | `docs/spec.md`, "Non-goals (cut for scope)" lists video, room maps, 3D and accounts. `docs/critique-round1.md`, row "Scope is five projects", limits the entry to photos and 3 to 6 spots. | None on scope. The core only counts if a judge can run it, see the next row. |
| The judge must reach the demo on the first click | 2, 3, 4, 5, 6, 7, 8 | `README.md`, "What a judge can try in two minutes": **Try the sample check** needs no camera and ends in a signed report. `docs/img/demo.mp4` is a 46-second recording. | **No live AWS endpoint.** The Devpost rules ask for a working web endpoint or an arranged screen-share. The owner must run `deploy/deploy.sh` and fill the "Live demo" line (`deploy/README.md`, "Before you submit"). |
| Keep a fallback for when the demo breaks | 4, 5 | The sample flow uses prepared photos instead of the camera (`README.md`, step 2 of "What a judge can try in two minutes"). The recording `docs/img/demo.mp4` exists. | The sample damage is synthetic (`README.md`, "Responsible use"). A judge may read the sample as staged. |
| The video is what judges see, so open with the problem | 2, 3, 5, 6 | `docs/video-script.md`, section "0:00 to 0:20, The bill", opens with the Hertz bill. The README embeds a glare GIF and the recording. | None for the file. The 2 min 30 s film is `docs/video/twice-demo.mp4` (source in `video/twice-demo`). It still needs a YouTube or Vimeo upload for Devpost. |
| Solve a real problem with clear impact | 1, 2, 4, 7 | `README.md`, "Why", cites the Hertz $440 bill and the House subcommittee letter. `docs/report.md`, section 1 ("Problem"). | **No real user evidence.** `docs/critique-round1.md` and `docs/critique-round3.md` use persona panels, not real renters or landlords. |
| Learn the judging criteria and the sponsor's goals | 1, 2, 3, 5, 6 | `docs/research.md`, "Competition facts". The README table names the OpenCV 5 calls, and the agent tools map to the Agentic Vision path (`README.md`, "How it works"). | `README.md` makes no COOL claim, so the Best Use of COOL path is not met. The Cloud delivery criterion (10%) depends on the missing live deploy. |
| Write a clear README and report that explain process and choices | 3, 6, 7 | `docs/report.md` sections 1 to 9 cover problem, users, system, computer vision, agent, evidence, evaluation, responsible operation and limitations. These match the technical report list on Devpost. `docs/evaluation.md` has a failure gallery (section 10). | The Lambda latency is not measured (`deploy/README.md`, "Before you submit", step 4). The README has no "what is next" section. Future work is only in `docs/report.md`, section 10, and source 6 ends its pitch with it. |
| Present limits as deliberate choices | 5, and Devpost asks for failure cases | `docs/evaluation.md`, section 11 "Limitations", and `docs/report.md`, section 9. The "Can't judge" class turns an uncertain case into a stated answer (`README.md`, "Responsible use"). | **No labelled real damage pairs.** The real-photo benchmark measures false alarms only (`docs/evaluation.md`, section 11). Strict engine recall is 0.74, not the 0.90 headline. |
| Choose teammates you trust, with complementary roles | 1, 5, 6, 8 | The repo does not say who is on the team. | Not checkable from the repo. Check the Devpost team page and the grant check-in rules. |

### Extra row from section 2 (one source family, not section 1)

| Advice | Source | Where Twice meets it | Gap |
|---|---|---|---|
| Prove it on real hardware or real data | https://opencv.org/?p=32653 | `server/eval/real_bench.py` runs 40 real photo pairs from the Oxford sequences. | Those pairs hold no damage. Twice has no real move-in and move-out pairs with labelled damage, so it cannot yet show recall on real scratches. |

### Open items to fix before submission

1. Run `deploy/deploy.sh`, add the Function URL, and run the sample check once to a green stamp.
2. Photograph a small real set: a few cars and rooms, with real move-in and move-out pairs, and label the damage. Report recall on it next to the synthetic numbers.
3. Show the product to a few real renters and write down what they said. Replace persona feedback where you can.
