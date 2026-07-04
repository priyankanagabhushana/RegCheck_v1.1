# RegCheck v1.1: A Simple Explanation

## For the PhD Selection Committee

---

## What is RegCheck? (The Original Tool)

Imagine you are a scientist. Before you start an experiment, you write down exactly what you plan to do: how many people you will test, what you will measure, and how you will analyse the data. This is called a **registration** — it is like a recipe you commit to before cooking.

After the experiment, you write a paper describing what you actually did and found. In an ideal world, the paper matches the recipe exactly. But in practice, researchers sometimes change things along the way — maybe they tested fewer people than planned, or switched to a different statistical test, or measured something different from what they originally promised.

These changes are not always dishonest. Sometimes they are perfectly reasonable. But sometimes they can mislead readers. The problem is: **nobody checks**, because manually comparing a 20-page registration against a 30-page paper is exhausting and time-consuming.

**RegCheck** (the original tool, published by Cummins et al. in 2026) solves this by using AI to help reviewers compare registrations against papers. It works like this:

1. You upload both documents.
2. The tool chops them into small text pieces (called "chunks").
3. It converts each chunk into a numerical fingerprint (called an "embedding").
4. For each thing you want to compare (like "sample size" or "primary outcome"), it finds the most similar chunks from both documents.
5. An AI language model reads those chunks and decides whether they match.

This is clever and useful. But it has a fundamental limitation that my work addresses.

---

## The Problem with RegCheck's Approach

### The "Recipe Card" Problem

Think of it this way. Imagine you want to compare two recipes for chocolate cake.

**RegCheck's approach** is like taking both recipes, cutting them into individual sentences, mixing all the sentences together in a bowl, and then asking someone: "Based on these sentences, do you think these are the same recipe?"

This works well when the difference is obvious — like one recipe says "use butter" and the other says "use oil." The AI can spot that because the words are different.

But it fails when the difference is **hidden in the structure** rather than the words. For example:

- **Recipe A** says "bake at 180°C for 30 minutes." **Recipe B** says "bake at 150°C for 45 minutes." Both sentences look almost identical — they both mention baking, temperature, and time. A text-similarity system might say "these are very similar!" But anyone who bakes knows that 180°C vs 150°C is a huge difference that changes the entire result.

- **Recipe A** lists "2 eggs" under ingredients. **Recipe B** lists "2 eggs" under ingredients too — but if you look carefully at the actual cake photo, it clearly has a different texture, suggesting something else changed. The text matches, but the *outcome* doesn't.

- **Recipe A** says "use dark chocolate (70% cocoa)." **Recipe B** says "use milk chocolate." Both say "chocolate." Cosine similarity would rate these as very similar words. But anyone who bakes knows these produce completely different flavours.

This is exactly what happens in scientific papers. A registration might say "use ANCOVA with three covariates" and the paper might say "use a t-test." Both discuss "statistical analysis" and "group differences." The words are similar, but the *analytical structure* is completely different. RegCheck's text-chunk approach can miss this.

---

## What I Built: The Scientific Integrity Engine

Instead of improving RegCheck's text-matching, I restructured the entire internal architecture around one core idea:

**Don't compare text. Compile the documents into structured data first, then compare the data.**

Here is the analogy. Imagine you want to compare two buildings to see if they are the same design.

**RegCheck's approach (text comparison):**
Take photos of both buildings. Cut each photo into small squares. Compare the squares visually. If most squares look similar, conclude the buildings are the same.

**My approach (structured compilation):**
Take both blueprints. Extract the structured information: number of floors, room dimensions, materials used, electrical wiring layout. Then compare those structured specifications directly.

If the blueprint says "load-bearing wall: concrete" and the other says "load-bearing wall: wood," that is a critical structural difference — even though photos of both walls might look "similar."

---

## The Five Key Ideas (Explained Simply)

### Idea 1: The Scientific Contract (The Blueprint)

**What it is:**
Instead of chopping a document into text chunks, I built a system that reads the entire document and extracts structured information into a formal "contract" — like filling out a detailed form.

For a registration, the form captures:
- What hypotheses were planned (H1, H2, H3...)
- What outcomes would be measured (anxiety score, depression score...)
- How many people would be tested (N=200)
- What statistical methods would be used (ANCOVA, t-test...)
- What exclusion criteria were set (no suicidal ideation, no concurrent therapy...)
- Domain-specific details (for MRI: scanner settings like TR/TE values)

For a publication, the same form is filled out with what the paper actually reports.

**The analogy:**
Think of it like a tax form. The IRS doesn't want your free-form essay about your finances. They want specific fields filled in: income, deductions, dependents. Once both forms are filled in, comparing them is straightforward — you just check each field.

That is exactly what the Scientific Contract does. It turns free-form scientific prose into a structured form that can be compared field by field.

**Why this matters:**
Instead of asking "do these text chunks look similar?", the system asks "is the value of `outcome.measure` the same in both contracts?" That is a precise, unambiguous question with a definitive answer.

---

### Idea 2: The Three Representations (Three Different Blueprints)

**What it is:**
I built three separate structured representations (called "IRs" — Intermediate Representations):

1. **Protocol IR** — What the study *planned* to do (extracted from the registration)
2. **Execution IR** — What the study *actually* did (extracted from the publication)
3. **Evidence IR** — The supporting proof for every claim (which paragraph, table, or figure backs up each finding)

**The analogy:**
Imagine you are an architect reviewing a building project:

- The **Protocol IR** is the original blueprint submitted for approval.
- The **Execution IR** is the "as-built" survey of the finished building.
- The **Evidence IR** is the inspection photos, material receipts, and structural test results that prove each part of the building was built correctly.

When you compare the blueprint to the as-built survey, you can spot differences. But when you also have the inspection evidence, you can determine *whether each difference is justified or not*.

**Why this matters:**
The original RegCheck just compared text. My system compares structured plans against structured reports, AND tracks the evidence for every piece of information. This means when the system says "the primary outcome changed," it can also show you exactly which paragraph in the registration defined it and which table in the publication reports a different one.

---

### Idea 3: The Constraint Engine (The Building Inspector's Checklist)

**What it is:**
Before asking the AI to make any judgements, the system runs a set of formal rules — like a building inspector's checklist. Each rule checks a specific thing and gives one of three answers:

- **SATISFIED** — The rule passes. Everything is in order.
- **VIOLATED** — The rule fails. There is a definite problem.
- **UNCERTAIN** — There is not enough information to decide. A human needs to look.

The six core rules are:

| Rule | What it checks | What it catches |
|------|---------------|-----------------|
| C1 | Are the primary outcomes identical? | Outcome switching (the most serious deviation) |
| C2 | Does the reported sample size make sense? | Undocumented participant dropout |
| C3 | Are the statistical methods the same? | Analysis model changes (e.g., ANCOVA → t-test) |
| C4 | Are all registered hypotheses addressed? | Silently dropped hypotheses |
| C5 | Can every claim trace back to a registered plan? | Post-hoc findings presented as if they were planned |
| C6 | Were exclusion criteria added after data collection? | Potential data filtering to get desired results |

**The analogy:**
Think of airport security screening. There are two levels:

1. **The X-ray machine (deterministic rules):** It checks every bag against clear, fixed rules. Is there a knife? Is there a liquid over 100ml? These checks never hallucinate — they either find the item or they don't. They are fast, reliable, and explainable.

2. **The human officer (the AI):** For bags that the X-ray flags as suspicious, a human officer examines them more carefully. They use judgement, context, and experience to decide if the item is actually dangerous.

My Constraint Engine is the X-ray machine. The AI language model is the human officer. The system first runs all the deterministic rules, and only asks the AI to look at cases where the rules are uncertain or where semantic understanding is needed.

**Why this matters:**
This means the system never asks the AI to do arithmetic (it checks sample sizes with math), never asks the AI to compare two exact strings (it checks outcome names directly), and never asks the AI to detect the absence of something (it checks hypothesis presence structurally). The AI is only used where it actually adds value — for understanding nuance, context, and ambiguity.

---

### Idea 4: The Pluggable Constraint System (The Modular Inspection Kit)

**What it is:**
The Constraint Engine is designed like a modular toolkit. The six core rules are always loaded. But anyone can write a new rule and plug it in without changing the system.

For example, I built two MRI-specific rules:

- **MRI-C1:** Checks that scanner settings (TR, TE, field strength) match between registration and publication.
- **MRI-C2:** Checks that cross-vendor robustness tests (which were pre-registered) were actually reported.

A clinical trials researcher could write rules about CONSORT compliance. A psychology researcher could write rules about manipulation check reporting. Each domain gets its own rules without touching the core system.

**The analogy:**
Think of a smartphone. The core operating system (iOS or Android) handles the basics — calls, messages, apps. But you can install apps for specific needs: a fitness app, a banking app, a recipe app. Each app extends the phone's capabilities without requiring Apple or Google to rebuild the operating system.

My Constraint Engine works the same way. The core handles the universal rules (outcomes, sample size, hypotheses). Domain experts install their own "apps" (constraint plugins) for specialized needs.

**Why this matters:**
This is what makes the system a *platform* rather than a *script*. The original RegCheck is a well-built tool for a specific task. My system is an extensible platform that can grow with the scientific community's needs.

---

### Idea 5: Explicit Uncertainty (The System That Says "I Don't Know")

**What it is:**
Every result from the system includes an uncertainty flag. When the system cannot determine something with confidence, it says so explicitly:

- "I cannot verify the sample size because the publication does not report the actual N."
- "I cannot confirm whether this claim is supported because the relevant table is in a supplementary file I could not access."
- "The exclusion criteria changed, but I cannot tell if this was justified without reading the authors' explanation."

Each uncertainty flag includes:
- A reason *why* the system is uncertain
- What data *would* resolve the uncertainty
- A suggested action for the human reviewer

**The analogy:**
Imagine a doctor who, when unsure about a diagnosis, says "I need to run more tests" rather than guessing. That is much more trustworthy than a doctor who confidently gives a wrong diagnosis.

Most AI systems are like the second doctor — they always give an answer, even when they should say "I don't know." My system is designed to be like the first doctor. When the evidence is incomplete, it says so, and it tells you exactly what additional evidence would help.

**Why this matters:**
This directly supports RegCheck's core philosophy: the human reviewer is the final decision-maker. The system's job is to *facilitate* human judgement, not replace it. By being explicit about what it doesn't know, the system helps reviewers focus their attention where it matters most.

---

## How Everything Fits Together

Here is the complete workflow, in simple terms:

```
Step 1: PARSE
    Upload registration PDF and publication PDF.
    The parser reads them and produces clean text.

Step 2: COMPILE (The Scientific Contract)
    For each document, extract structured information:
    - Hypotheses, outcomes, sample sizes, methods, claims
    - Domain-specific parameters (if applicable)
    - Evidence links (which paragraph supports which finding)
    This produces two "filled-in forms": the Protocol IR and Execution IR.

Step 3: BUILD GRAPHS
    Convert each form into a network diagram (graph):
    - Each hypothesis, outcome, and method becomes a node (a point)
    - Relationships between them become edges (lines)
    For example: "Outcome O1 is tested by Analysis SA1" becomes an edge.

Step 4: COMPARE (Three Layers)

    Layer 1 — Deterministic Rules (the checklist):
    Check each rule: outcomes match? sample size consistent?
    methods the same? Every claim traceable?

    Layer 2 — Graph Comparison (the structural diff):
    Compare the two network diagrams.
    What nodes were added, removed, or changed?
    What relationships changed? (e.g., an outcome was
    originally tested by ANCOVA but is now tested by t-test)

    Layer 3 — AI Reasoning (the human officer):
    For ambiguous cases, ask the AI to interpret the
    difference and assess its significance.

Step 5: SCORE (Four Axes)
    For each deviation found, score it on four independent scales:
    - Scientific Severity: How serious is this? (S0 trivial → S5 critical)
    - Bias Risk: Could this introduce bias? (none → critical)
    - Evidence Quality: How strong is the evidence? (insufficient → high)
    - Confidence: How sure are we? (low → high)

Step 6: REPORT
    Generate a structured report showing:
    - Side-by-side comparison of registration vs publication
    - Every deviation with its severity score and evidence
    - Suggested questions for the authors (for serious deviations)
    - Explicit uncertainties where human review is needed
```

---

## What Makes This Different from RegCheck (Summary)

| Aspect | RegCheck (Original) | What I Built |
|--------|-------------------|--------------|
| **How documents are represented** | Cut into text chunks and converted to numerical fingerprints | Compiled into structured "forms" with typed fields (like filling in a tax return) |
| **How comparison works** | Find the most similar text chunks, ask AI if they match | Check structured fields directly with rules, then use AI only for ambiguous cases |
| **How evidence is tracked** | Retrieved text passages shown to the user | Every piece of information linked to its source (paragraph, table, figure, page number) |
| **How deviations are scored** | Single severity score | Four independent axes: severity, bias risk, evidence quality, confidence |
| **When the system is unsure** | Not explicitly stated | Explicitly says "I don't know" with reasons and suggested next steps |
| **How domain knowledge is added** | Change the prompts | Write a new rule and plug it in (like installing an app) |
| **What the AI does** | Judges everything | Judges only what the rules cannot determine |

---

## A Concrete Example: Why This Matters

Here is a real scenario that shows the difference:

**The setup:**
A clinical trial registers "Primary outcome: GAD-7 Anxiety Scale" (a standard 7-item questionnaire for anxiety). In the publication, the primary outcome is "State-Trait Anxiety Inventory (STAI)" (a different 20-item questionnaire for anxiety).

Both are well-validated anxiety measures. Both would appear in a methods section with very similar wording: "Anxiety was measured using a validated self-report questionnaire."

**What RegCheck would likely do:**
Find the text chunks about anxiety measurement from both documents. Notice they are very similar (both mention anxiety, measurement, self-report). Conclude: probably no deviation.

**What my system does:**
Check the structured field `registration.outcomes[0].measure` against `publication.outcomes[0].measure`.
- Registration: "GAD-7 Anxiety Scale"
- Publication: "State-Trait Anxiety Inventory (STAI)"
- These are not equal.
- Rule C1 (Primary Outcome Equality) is VIOLATED.
- Severity: S5 (Bias-Critical) — this is the most serious type of deviation.
- The system reports: "Primary outcome changed from GAD-7 to STAI. This may affect the interpretation of all reported results."

**Why the difference matters:**
GAD-7 and STAI measure related but different constructs. GAD-7 measures *generalized anxiety disorder symptoms*. STAI measures *state and trait anxiety*. A treatment could improve one but not the other. Switching between them after seeing the data is a well-documented form of bias called "outcome switching."

RegCheck's text-similarity approach might miss this because the words are similar. My system catches it because it compares the *typed field*, not the *surrounding text*.

---

## The MRI Example: Domain-Specific Intelligence

Here is another example that shows the pluggable constraint system:

**The setup:**
A neuroimaging study registers specific MRI scanner settings: TR (repetition time) = 2000ms, TE (echo time) = 30ms, and commits to testing whether their findings are consistent across different scanner manufacturers (cross-vendor robustness checks).

In the publication:
- TR is reported as 1500ms (changed from 2000ms)
- Cross-vendor robustness checks are silently dropped
- The uncertainty quantification method is downgraded from "bootstrap confidence intervals with physics-informed signal-to-noise estimation" to just "p-values with FDR correction"

**What a generic tool would do:**
Compare the methods sections as text. Both mention "MRI acquisition" and "fMRI BOLD sequence" and "3 Tesla scanner." The text is very similar. Likely no deviation detected.

**What my system does:**
The MRI-specific constraint plugins check each parameter field:
- MRI-C1 detects TR changed: 2000ms → 1500ms (this affects signal characteristics)
- MRI-C2 detects cross-vendor checks were dropped (this was pre-registered)
- The structured comparison detects the uncertainty quantification downgrade

**Why this matters:**
TR=2000ms vs TR=1500ms changes the signal-to-noise ratio, temporal resolution, and BOLD signal characteristics. This is a meaningful methodological change that could affect the validity of the results. But in text, both values appear in nearly identical sentences about "MRI acquisition parameters." Only a system that *understands* what TR means (through the domain-specific constraint) can reliably catch this.

---

## What This Means for the Future of RegCheck

I am NOT proposing to replace RegCheck. I am proposing a complementary internal architecture that could make RegCheck's existing strengths more powerful:

1. **Better explainability:** When the system flags a deviation, reviewers see the exact constraint violated, the typed fields that differ, and the full evidence chain. This gives them everything they need to make their own informed judgement.

2. **Better extensibility:** Domain experts can write their own constraint rules without modifying the core system. A clinical trials researcher, a psychologist, and a neuroscientist can each have specialized rules that plug into the same platform.

3. **Better honesty:** The system explicitly says "I don't know" when evidence is incomplete, rather than guessing. This builds trust with reviewers and aligns with RegCheck's philosophy that the human is the final decision-maker.

4. **Better evaluation:** Because every deviation is linked to a specific rule and a specific structured field, researchers can systematically evaluate which rules work well, which produce false alarms, and where the AI adds genuine value beyond the rules.

---

## In One Sentence

**RegCheck compares documents. This system compiles them into structured specifications, validates them against formal rules, and uses AI only where rules cannot determine the answer — making the system more explainable, extensible, and honest about what it does and does not know.**
