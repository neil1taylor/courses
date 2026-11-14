# Brief: cold read of video module scripts

You are a fresh reviewer of narrated video module scripts for a course. Do not edit any file; report only.

Read first: ~/Projects/claude-skills/skills/blog-writing/references/cold-read.md (apply its questions), ~/Projects/claude-skills/skills/blog-writing/references/course-text.md (voice rules), and the checklist in ~/.claude/skills/course-video/SKILL.md under "The check, before any audio is made". The approved outline is W/<course folder>/video/outline.json.

Each script is W/<course folder>/video/<unit>.json (spoken words are each cue's `say`; slide text is in each cue's `slide`, diagrams in `sketches`; screenshots are files named in `img`, relative to the unit page, which you can open). Its unit page is W/<course folder>/<unit>.html.

For each script, read the narration top to bottom as a listener who has not seen the unit, then check it against the unit. Answer the cold-read questions, then:
8. Which spoken fact, explanation or advice is in neither the unit nor the outline? Quote it.
9. Which "Watch for this" tip describes behaviour that is normal?
10. Which "but", "only" or "unlike" does not state the true condition?
11. Which named thing is used before it is introduced in that module?
Also flag: a words-slide definition that doesn't match the unit; a screenshot that doesn't show what the narration says while it is up; a number that differs from the unit, two numbers for one event, or counts that don't add up; a statement slide without a sketch (other than the check-step opener); a raw identifier, flag or CIDR spoken in a way a listener can't follow; a sentence a trainer wouldn't say aloud; vague verbs (run, handle, manage, look after) where who-does-what matters; a fact made wrong by shortening; a question whose answer this or an earlier module hasn't taught; two sentences that contradict each other; a result framed as the product failing where the unit gives advice; any region or zone name, "in our lab", "generally available", "Beta" or date in narration or slide text (inside real terminal output and screenshots is fine); a wrong "Next:" line (it must name the next module in the outline).

Known and accepted, don't flag: "If you remember one thing, make it the sentence on the screen." (required); "When we tried it, …"; shortened answer options and question heads (the narration says the full question); check questions that review an earlier module; facts cut for length that no outcome or check needs.

Report per module: each problem on one line with the exact quote and a suggested fix. Skip praise. Under 15 lines per module.
