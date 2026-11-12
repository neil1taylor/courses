# Slides for narrated training video: research notes

Canvas used below: 1920x1080. For 1200x675, multiply every pixel value by 0.625.
"Source" means I read it. "Inference" means my own step from the sources, not a source claim.

## 1. Per-source notes

### Mayer, multimedia learning (read: primary text)
Source: Mayer (2021) chapter "Research-Based Principles for Designing Multimedia Instruction", UNH copy, https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf . I extracted the text of the PDF and read it. Effect sizes are medians of Cohen's d from Mayer's own meta-analysis.

| Principle | Tests supporting | Median d | What it says |
|---|---|---|---|
| Coherence | 18 of 19 | 0.86 | People "learn more deeply" when extraneous material is left out |
| Signaling | 26 of 28 | 0.70 | Cues that highlight the organisation of essential material help |
| Redundancy | 8 of 12 | 0.10 | Adding on-screen text to narrated graphics does not help |
| Spatial contiguity | 9 of 9 | 0.82 | Put words next to the graphic part they explain |
| Temporal contiguity | 8 of 8 | 1.31 | Present words and matching graphic together, not one after the other |
| Segmenting | 7 of 7 | 0.67 | Break the lesson into learner-paced parts |
| Pre-training | 10 of 10 | 0.78 | Teach the names of the key parts before the explanation |
| Modality | 18 of 19 | 1.00 | Graphics plus spoken words beat graphics plus printed words |
| Multimedia | 13 comparisons | 1.35 | Words plus pictures beat words alone |

Key points:
- Redundancy is weak and bounded. Mayer says the effect "can be diminished or even reversed" when the lesson is slow, learner-paced, or the text is short or reworded. Our slides are narrated, system-paced and short, so the safe reading is: put few words on screen, and never the full narration.
- Coherence: his examples are interesting but irrelevant facts and extra video clips. Both hurt. Effect is strongest for system-paced lessons and low-working-memory learners.
- Pre-training does not help high-prior-knowledge learners. Our learners are new to the topic, so it applies. This is the word list before the explanation.
- Other numbers in circulation differ. A 2017 review reports redundancy d = 0.87 and signaling d = 0.46 (search summary of https://onlinelibrary.wiley.com/doi/abs/10.1111/jcal.12197 , abstract not read). Independent meta-analyses of signaling give about 0.35 to 0.38 (secondary summary, not checked). Use the 2021 chapter and state the year.

### Assertion-evidence (Alley, Garner; read: primary paper plus site)
- Site: https://www.assertion-evidence.com/ . It says to build on "succinct messages (assertions)" supported by "visual evidence rather than bulleted lists". The home page gives no font or word rules and does not summarise research.
- Paper: Garner and Alley (2013), International Journal of Engineering Education, https://writing.engr.psu.edu/ae_comprehension.pdf (text extracted and read).
- Structure: a sentence headline of "no more than two lines", then a graphic that supports it, "as few words as possible" in the body. The authors say the headline is a one-sentence summary of what is said aloud, so it serves signaling, coherence and redundancy together.
- Experiment: 110 engineering students, same 1000-word narration for both groups. Common-practice slides averaged 41.5 words; assertion-evidence slides averaged 21.2 words, each with a graphic. On eight AE slides, parts of the graphic appeared on cue when named in the narration.
- Results: AE group better on comprehension; delayed test ten days later d = 0.89 (p < 0.001); a sequence-recall test d = 0.81. No clear difference in recall of plain facts. AE group also reported lower mental effort.
- Limits: one topic (MRI), engineering students, one lab session. Other Penn State studies (summarised in search results, not read) point the same way, mainly for complex ideas, not for recall of facts.

### Reynolds, Presentation Zen (read: his design tips page)
Source: https://www.garrreynolds.com/design-tips
- "Nothing in your slide should be superfluous." "Your slides should have plenty of empty space."
- Borrows signal-to-noise ratio: "The highest possible signal-to-noise ratio is desirable in design."
- Type: "The problem... is not that text in the slide is too big, but that it is way too small." "Make it big and make it clear."
- "The best slides may have no text at all." Slides support the narration; they do not replace the speaker.
- Tip list includes "Make images large", "Use the principle of Contrast", "Use the principle of Rule of Thirds", "Limit the use of animation".
- No numbers. It is craft advice, not research. His "empty space" idea is about giving one item room, not about leaving a slide half unused.

### Duarte, glance test (read: partial)
- Duarte's book page https://www.duarte.com/resources/books/slideology/ gives only the question: will the audience "understand the main point of your slide in 3 seconds". It says nothing on hierarchy or whitespace.
- Search summaries (not primary) say slides are "glance media" and that a signal-to-noise score of 5:1 or better passes. I could not verify the 5:1 figure at Duarte's site. Treat as unconfirmed.
- I did not read slide:ology itself. Hierarchy and space advice from Duarte is not sourced here.

### Video producers and universities (read: two pages; others from search summaries)
- CU Boulder, https://www.colorado.edu/learningdesign/faculty-support/best-practices-videos : at least 18pt for a standard 16:9 presentation; for HD (1080p) video "at least 48pt"; high contrast; minimal animation; split text-heavy slides.
- Columbia Teachers College, https://www.tc.columbia.edu/digitalfuturesinstitute/learning--technology/instructional-guides--resources/self-paced-learning-guides/tips-for-using-powerpoint-to-record-an-instructional-video : "6x6" (six lines, six words a line); "less is more" so students listen, not read; many watch on phones, where small text is "unreadable"; reveal items one at a time; high contrast.
- Universities in search results (UGA, Virginia Tech, McGill, UConn; summaries only): 24pt body and 44pt titles minimum for projected slides. These are for rooms, not video.
- American Evaluation Association (search summary): says fixed word counts are outdated; prefer visuals.
- Pluralsight: **not reachable.** Public pages only say authors get a slide template and that slides should be simple. The font and word rules sit in the private author kit. LinkedIn Learning and Coursera: **not reachable.** Only a blog says LinkedIn wants 400 to 500 words of script per video.

### 16:9 safe areas (read: search summaries only)
Search results (Premiere Pro, DEV Community, Wikipedia "Safe area (television)"; pages not opened):
- Old convention: action-safe 90% of frame (5% margin), title-safe 80% (10% margin). Modern SMPTE ST 2046-1: 93% and 90%. EBU R95: 93% and 88%.
- At 1920x1080, 80% is 1536x864: margins of 192px sides and 108px top and bottom (arithmetic).
- For online video, keep text out of the bottom 8% where the player bar sits.
- Nothing I found says how much of the frame content should fill. See section 5.

## 2. Rules for our slides

1. **One idea per slide, stated as a sentence headline of at most two lines.** Alley: sentence headline, two lines at most. Mayer coherence d = 0.86; segmenting d = 0.67. Headline is 56 to 72px.
2. **Target 20 words or fewer on screen, hard limit 30.** The AE group had 21.2 words per slide and beat the 41.5-word group (d 0.81 to 0.89). Columbia 6x6 gives 36 as a ceiling. Words in labels count. Exempt the word list type.
3. **Never put the narration on screen.** Mayer redundancy (d = 0.10, reversed when text is short or reworded); modality d = 1.00; Reynolds. Captions already carry the narration. Slide text is key words, not sentences. Exception: the headline.
4. **Build with the narration.** Show each element as it is spoken, nothing before. Temporal contiguity d = 1.31; AE study showed graphic parts on cue; Columbia "reveal one at a time"; user's "build with the narration". Everything already shown stays, dimmed to about 55% opacity once the next element appears (inference, from signaling).
5. **Signal the current item.** Marker blue (or heavier stroke) on the item being spoken about, everything else grey. Signaling d = 0.70.
6. **Put labels on the thing they name.** No legend, no key below. Spatial contiguity d = 0.82. A label sits within about 24px of its shape.
7. **Name the parts before using them.** Word list or "terms" slide comes first, one term at a time. Pre-training d = 0.78 (new learners).
8. **Type size: body 44px minimum at 1920 wide, labels in diagrams 36px minimum, headline 56 to 72px.** CU says 48pt at 1080p (a "pt" on a 1080-high slide is about one pixel at 1:1, so this is 48px). Reynolds: too small is the usual fault. Phones watch at about one fifth of 1080p width, so 36px type is about 7px tall on a phone. Treat 36px as the floor, not the goal (inference).
9. **Only two or three sizes per slide.** One big thing, one medium, one small at most. Reynolds contrast; Duarte glance test. A reader should say what the slide is about in 3 seconds.
10. **Keep content inside the 80% title-safe box where it matters, with a 120px side margin and 80px top and bottom as a working rule.** The old 80% rule is 192px and 108px; the 93% and 90% modern standards allow 96px/54px or less. 120px and 80px sit between (inference). No text in the bottom 90px.
11. **Fill the frame with the one thing, not with many things.** Content block 65 to 80% of the safe width and at least 55% of the height, vertically centred or top-anchored with intent. Empty space is good only around a large item (Reynolds); a small item in a large empty slide is not empty space, it is a small slide. Inference: no source gives a fill percentage.
12. **Black on white, one accent.** High contrast (CU, Columbia). Marker blue only for what is being talked about. Contrast ratio at least 7:1 for text (WCAG AAA, inference); black on white is 21:1.
13. **Pictures over words.** Every slide has a visual or a big number or one big word. A slide that is only a paragraph is not allowed. Multimedia d = 1.35; assertion-evidence.
14. **No decoration.** No logos, footers, page numbers, clip art, transitions beyond a 200 to 300ms fade. Coherence d = 0.86; Reynolds signal-to-noise; CU "minimal animation".
15. **Keep slides short in time.** One slide, one segment, usually 15 to 45 seconds of narration (inference, from segmenting plus the glance test). Split a slide that needs more.

## 3. Slide types

All use: background #fff, text #111, accent marker blue, Red Hat Display for headlines, Red Hat Text for body. Safe box: left/right 120px, top 80px, bottom 90px (content area 1680x910). Headline top-left, aligned to the left edge, unless stated.

**Title or opening**
- Centre-left block, vertically centred. Line 1: course or unit name at 96px, 2 lines max. Line 2: one sentence, the promise ("By the end you will know why the vault is there"), 44px, grey #555.
- A hand-drawn illustration of Northgate Freight (a truck, a vault door) fills the right 40% (about 700px wide, 700px high). It draws in once at the start.
- No kicker, no logo, no number. At most 14 words of text.

**Diagram that builds up**
- Headline: one sentence, 64px, top, max two lines, 1680px wide.
- Diagram area: from y=240 to y=990, full 1680px width. Diagram fills at least 80% of that area. One central shape at 300px or more.
- Labels 36 to 40px, placed beside the shape. Parts appear in the order spoken. Current part in blue with thick stroke; earlier parts grey. Arrows draw in over about 600ms.
- No body text. A caption line under 10 words at most, 40px, only if a sentence needs it.

**Question with answers**
- Question as headline, 64px, up to 2 lines, nothing else above it. It appears first, with narration reading it.
- Answers: a single column of up to 4 cards, each 1680px wide (or two columns of 820px with a 40px gap), 120px tall, 44px text, 2px black outline, letter A to D in a 72px circle on the left. Gap 24px.
- Cards appear one at a time as read. Keep each answer to 12 words or fewer. No hint text, no instruction line.

**Answer reveal**
- Same layout as the question. Wrong answers fade to 30% opacity. The right answer scales to 105% with a blue outline and a blue tick.
- Below, one line only, 48px: the reason in 15 words or fewer. Reason appears as the narration gives it. Do not repeat the question.

**"Watch for this" tip**
- Headline: the pitfall as a sentence, 64px.
- Left 55%: a drawing of the mistake (hand-drawn, blue marker circle or cross on the problem). Right 40%: a single boxed line, 48px, blue left bar 8px, "Do this instead: ..." in 12 words or fewer.
- Alternative if there is no drawing: one centred sentence at 80px with the key word in blue. Nothing else.

**Word list or recap**
- Headline: 56px, "Four words you need" (number is the count). Max 4 terms per slide; split a longer list across slides (Mayer segmenting).
- Two columns by two rows. Each cell 800x300: term 56px bold, definition 40px, 10 words or fewer, grey under it. Hairline rule between cells.
- Cells appear one at a time as each term is spoken. Current cell's term in blue. A small hand-drawn icon, about 120px, left of each term is allowed.
- This is the one type where the 20-word target is exceeded: up to 50 words, because it is a reference slide.

**Summary or "remember one thing"**
- One sentence only, the takeaway, set at 96 to 120px in Red Hat Display, left-aligned, 3 lines at most, in the vertical centre of the safe box. The key phrase in blue.
- Beside or under it, one hand-drawn picture of the idea, at least 500px high, filling the rest of the slide. If there is no picture, make the sentence the picture: 120px and fill 70% of the width.
- The sentence appears first, with narration. A second line (what to do next, 48px) appears last. No kicker.

**Score**
- Centre. The number as the hero: "3 of 4" at 240px, Red Hat Display bold, black; "of 4" in grey. Under it one plain line, 56px: "You can explain why the vault is there." (what the score means, not a grade).
- If the score is unknown at video time (the video cannot know it), do not show a score slide. Replace with a "what to check" slide using the summary type. This is a design call, not from sources.
- Under 12 words of text.

## 4. The owner's example summary slide

What is wrong, in order of weight:
1. **Wrong hierarchy.** The heading "You know why the vault is there" is the message but is dwarfed by nothing; it is the only large item, and the real content sits below it in small text. The eye has nowhere to land after the heading. Fails the 3-second glance test.
2. **Too much text, in the wrong place.** Four sentences of "Remember" is a paragraph. If it is read aloud it is redundant (Mayer redundancy, modality d = 1.00); if it is not, it is clutter. AE slides averaged 21 words; this slide's paragraph alone is near that.
3. **Dead elements.** "Your check score" with a dash shows nothing and takes a column. "Unit complete" kicker adds no information (coherence d = 0.86; Reynolds "nothing superfluous").
4. **Small type in thin columns.** Two narrow columns of small text break the 36 to 44px minimum for video and the phone-viewing risk (Columbia).
5. **Empty space that is not working.** About 60% of the frame is blank because everything is small, not because anything has room. Reynolds' empty space frames a large item; this is unused area.
6. **No build.** All of it shows at once, so it cannot follow the narration (temporal contiguity d = 1.31).

What it should look like (summary type above):
- No kicker, no score column (move the score to the score slide or drop it).
- Narration says the four sentences. On screen: the one-sentence takeaway only, such as "The vault is there so a stolen laptop is not a stolen company" (example wording, not from the course), at 100px, left, key phrase in blue, filling about 70% of the safe width over two or three lines.
- A hand-drawn picture of the vault on the right, about 600px high, drawing in as the sentence is spoken.
- Optionally, as the narration reaches the last sentence, one 48px "Next: ..." line at the bottom.
- Result: about 12 words, two large things, content block over 60% of the height.

## 5. Where the sources disagree or are weak

- **Redundancy vs assertion-evidence.** Mayer says no on-screen text with narration; Alley says a full-sentence headline. Garner and Alley argue the headline is a summary, not a repeat. Mayer's own boundary conditions (short, reworded text) allow it. Rule 3 keeps both: headline allowed, sentences not.
- **Effect sizes move.** Redundancy is d 0.10 in 2021 and 0.87 in a 2017 abstract (as summarised). Signaling is 0.70, 0.46, or about 0.35 in other meta-analyses. I used the 2021 chapter I read, and these numbers show direction, not precision.
- **Mayer's studies are short lab lessons**, mostly with university students and narrated animation. Our slides are different (questions, word lists). The principles probably carry over; no study tests our slide types.
- **Alley's evidence** is one lab study with the authors as designers and one topic. The comparison also differs in word count and graphics, so the cause is not isolated to the headline.
- **Duarte and Reynolds give no numbers** in what I could read. The 5:1 figure is secondary. Duarte's hierarchy and whitespace advice is unread.
- **Font sizes conflict.** Universities say 24pt (rooms), CU says 48pt at 1080p video, Columbia gives no number. Rule 8 follows CU, because it is the only one written for 1080p video. The phone figure is my arithmetic.
- **Words per slide:** 6x6 (36), 40 to 50 (one LinkedIn article), AEA says counts are outdated. Only the Garner and Alley study ties a count (21 words) to results.
- **Pluralsight, LinkedIn Learning and Coursera rules were not reachable.** I cannot say what Pluralsight's style is beyond "simple".
- **Safe areas** come from search summaries of broadcast pages I did not open. Modern streaming ignores overscan; the margins are for phone crops and player bars.
- **Frame-fill percentage** has no source. Rule 11 is my judgement.
