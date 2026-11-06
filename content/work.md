---
title: Norman Bui, work & projects
description: The long version of Norman Bui's resume: what each role and project involved, the decisions behind them, and what the results were.
type: article
---

[← home](index.html)

# Work & projects

*The long version, with the detail a one-page resume leaves out.*

A resume line says what happened. It has no room for what the work started from, what I tried, or how much the numbers actually prove. That is what this page is for.

[Home](index.html) · [Resume PDF](resume/swe/Norman_Bui_Resume.pdf) · [Email](mailto:normanbui23@gmail.com) · [GitHub](https://github.com/nbui23)

---

## Where I bring the most value {#value}

- **Backend and data infrastructure**: production systems with real reliability constraints
- **Developer tooling**: internal tools and CI that make a team faster
- **Applied AI**: agentic and RAG features that still need predictable, grounded behavior

---

## Contents {#contents}

- [Experience](#experience): [Canadian Tire](#ctc), [Electronic Arts](#ea), [Autodesk](#autodesk), [Public Health Agency of Canada](#phac), [Bedarra](#bedarra), [Kongsberg Geospatial](#kongsberg), [Health Canada](#health-canada), [National Defence](#dnd), [NAV CANADA](#navcan), [Correctional Service Canada](#csc)
- [Projects](#projects): [Latch](#latch), [Orbital Refuelling Simulator](#orbital), [Riverbreak](#riverbreak), [CruxOS](#cruxos), [ThinkPad home lab](#homelab), [SocialSaplings](#socialsaplings)
- [Education](#education)
- [Skills](#skills)

---

## Experience {#experience}

### Canadian Tire Corporation {#ctc}

*Software Developer · July 2026 to present · Toronto*

I work on agentic software development lifecycles. Most of my time goes to an internal documentation generator that teammates run from GitHub Copilot.

Service documentation goes stale in a predictable way. Someone writes it once, moves teams, and the service changes underneath it. After that nobody trusts it, so nobody updates it. The tool regenerates documentation from the code, and on every later run it edits only the pages the code has moved under.

It has a model-free half and a model half. The first is static analysis over one commit. It produces a fact sheet, where each fact is a structured record carrying the file and line it came from: routes, module dependencies, configuration keys, messaging, service catalog entries, and, from the git history, who owns which parts and what recent work changed. It covers twelve languages on tree-sitter (Java, Kotlin, TypeScript, JavaScript, Python, C#, Go, PHP, C and C++, Ruby, Dart, Rust), plus iOS, Android, and Flutter build files. Each one needed its own extraction rules, and most of them turned up a shared rule that needed fixing rather than a special case. The same half writes the reference pages, with no model at all.

The model half starts with a planner agent. It reads the fact sheet and the code, and decides which topic pages this repository needs, with one brief per page. The plan is kept in the repository, so a developer can edit it and later runs don't reshuffle pages a reviewer has already read. Then each page gets a writer of its own, which reads the code with the fact sheet as its map. An earlier version gave the model the fact sheet alone. Today the writers read the code too, and every claim still points at a file and line.

The result is a documentation tree: an overview, an architecture page with generated Mermaid diagrams, an API surface, the planned topic pages, and a glossary for developers, plus a page for analysts who never open the repository. That last one took the most work. Early drafts expanded a banner code into the name of a real company that had nothing to do with the system, listed downstream services that did not exist, and stated the direction of an integration the facts did not cover. I wrote the rules it runs under: do not expand an abbreviation the record does not expand, do not name a counterparty the facts do not name, and write "not on the record" rather than guess a direction. They live in the prompt rather than in a review checklist, so swapping the model does not lose them.

Nothing a model writes goes straight to a reader. Once a page is written, a second pass checks its claims against the code one at a time, and anything that does not hold goes into the pull request's description for the reviewer. Model-free checks catch dead links, and versions the build files pin, like SDK levels and runtime versions, stated differently on a page. The run commits in two parts, the pages a person reads and the generated reference, and opens a draft pull request in Azure DevOps. A page whose evidence has not moved gets no new ask, and a stale one is edited rather than rewritten. A companion code-review plugin flags the pages a change under review makes stale. Finished pages publish to Confluence when a team asks.

In October I rewrote the whole tool from TypeScript to Rust. The rewrite went one piece at a time against an oracle: the TypeScript version's output recorded per language and per stage on a pinned set of public and internal repositories, and each Rust piece had to match it byte for byte before it merged. Most of the work was in what the two runtimes disagree on. Tree-sitter in Node counts columns in UTF-16 units, JavaScript sorts strings by code unit, and the YAML and JSON readers accept different inputs, and each of those differences is now pinned by a test. Once every piece matched, the TypeScript was deleted. It is now about 100,000 lines of Rust with over 1,100 tests, built in Azure DevOps as one executable for six platforms, with nothing to install at run time. Dart and Rust support came in during the same stretch.

Most of my recent time has gone to measuring it. A change that makes one page better can make another worse, and reading a few pages by eye does not tell the two apart. So every change runs against a fixed set of production repositories, and a judge model grades the output against a rubric frozen before the first draw. I calibrated the judge against my own grades until we agreed, then measured how much it moves when it grades identical output twice (about **±0.03**). A difference smaller than that does not count. A second check asks the pages a fixed set of questions written from the code, and a fresh model answers from the pages alone. That one showed the pages kept ownership and structure but lost the business terms a reader most needed.

That finding led to a new stage. Before any page is planned, one agent session per module, running on the GitHub Copilot SDK, reads only that module and writes down what matters in it, four sessions at a time. A final pass reconciles them into a ranked record that the planner and every writer read. I picked it over three other designs in a graded A/B test across four repositories. The agents' citations sometimes ran a few lines past the end of a file, so a model-free check clamps or drops each one; dead citations went from **10 to 0** across 2,100. It shipped behind a flag at first, and now runs by default. I also tested whether Confluence could add to the record. Its claims checked out, but they moved nothing the judge grades, so it stayed out.

For runs where the pipeline brings its own model, cost per run came down **38x**. I ran candidates over judged repository checkouts and compared their pages against the same signals, instead of picking a model on reputation. The cheap one held at zero invented names. I measured prompt structure the same way. Caching the fact sheet halves cold-start cost, but at the volume we run, the choice of model was worth roughly twenty times more.

The judge and the question check measure what a page set leaves out, not what it gets wrong. So I checked one 22-page technical set against the code, claim by claim. **32 of 1,694** claims were wrong or misleading (**1.9%**), against a bar of 15% I set before starting. No page went above 8%, and every quoted snippet matched its cited lines. The weaker half was citations: 142 correct claims cited lines that did not quite show them. Re-runs got cheaper too. The checker used to re-check every claim on a page after a one-line edit, and now checks only the lines the run changed, which cut a re-run's cost by about **40%**, while still catching a wrong line planted by hand.

### Electronic Arts {#ea}

*Software Developer Intern · May 2025 to August 2025 · The Sims · Kotlin, AI agents, automated testing*

I worked on the infrastructure that tests the game under load, so the team can tell whether a feature still holds up when a lot of people use it at once.

The load-testing pipeline was passing about **35%** of its runs when I started, and people had mostly stopped reading the results. Almost none of the failures were about the game. They were authentication failures against backend services and environment setup problems on the CI runners. I worked through them and got the pipeline to a **100%** pass rate.

I also integrated **10 or more** new game features into the load-testing frameworks, with automated coverage and performance metrics tracked per feature, so the suite kept testing the current game rather than last quarter's.

Separately, I helped build Servo, an LLM-powered system that plays the game to find bugs. I measured model performance and built foundations for better soak testing, where the failures only appear after hours of continuous play.

### Autodesk {#autodesk}

*Software Developer Intern · January 2025 to April 2025 · Fusion · TypeScript, Java, GraphQL*

Fusion keeps manufacturing data in the cloud, and some of it loses the relationships that tie a part back to the design it came from. Nothing looks broken at that point. The failure shows up later in a workflow that depended on the relationship, which makes it awkward to trace back.

I built the validation and repair infrastructure for that: detection of missing manufacturing data across cloud workflows, and the repair path behind it. The repair algorithm is **O(n)** with concurrency controls and runs **8x** faster than the approach it replaced, with the parallelism tuned so a large repair could not overwhelm the services it called.

I deployed GraphQL endpoints so validation and repair run on their own rather than after someone reports a problem, closed permission and error-handling gaps in workflows carrying sensitive customer data, and fixed part-numbering errors that only appeared in uncommon configurations. Every change kept **100%** test coverage under Mocha, Chai, and Sinon.

### Public Health Agency of Canada {#phac}

*Data Scientist Intern · September 2024 to December 2024 · Python, LLMs, RAG, master data management*

Epidemiological research runs on literature review, and literature review is slow enough to limit which questions get asked at all. I built an LLM-assisted workflow for it with Imperial College London and the World Health Organization, along with the master data management infrastructure meant to make global health data available in a standard shape.

I evaluated embedding models with Ollama to check retrieval quality in the RAG system. That gave the team a baseline to tune against, which they did not have before, so changes could be compared instead of argued about.

I also prototyped a paper collection pipeline with GPT-4o, as a proof of concept for PDF retrieval and metadata extraction at a scale nobody wanted to do by hand.

### Bedarra Corporation {#bedarra}

*Student Researcher · August 2024 to October 2024 · Python, RAG, LangChain, FAISS*

Language models handle common languages well because the training data is full of them, and handle obscure ones badly for the same reason. This was research into whether retrieval could close that gap for Factor and K, where documentation exists but is sparse and idiosyncratic.

I built the RAG systems, benchmarked embedding models and chunking strategies against retrieval quality (the usual defaults are tuned for prose, and these corpora are mostly code and terse reference material), and used LangChain to pull real code examples and documentation into each answer rather than letting the model recall something from a language that merely looks similar.

### Kongsberg Geospatial {#kongsberg}

*Software Developer Intern · May 2024 to August 2024 · TerraLens · C++, Qt, Python, GIS*

I was the only developer on the Solutions Engineering team, building the demo applications that show clients in aviation, defense, and government what the TerraLens SDK does with their own data. These get shown live, so performance counted as a product requirement.

I integrated LiDAR, WMTS, and S-57 data into a single view and optimized the render pipeline to a **consistent 60 or more frames per second** with real-time object tracking, added system monitoring for GPU, CPU, and RAM, and modernized the Qt interface.

I also built an automated airspace classification framework that removed a manual categorization step, and automated VFR and terrain data processing, cutting aggregation time by more than **40%**.

### Health Canada {#health-canada}

*Data Scientist Intern · September 2023 to December 2023 · Python, ML, NLP, ETL*

Chemical risk assessment pulls data from a lot of sources, and the system doing the pulling was failing often enough that analysts had started working around it.

I rebuilt the organization-wide federated chemical search with BS4 and lxml, adding fault tolerance and rate limiting, which raised the query success rate by **20%**. The failures were mostly source sites throttling or rejecting requests, so the work was in how the system behaved as a client rather than in parsing.

On top of that I built a scraping framework with unittest and test-driven development, expanding accessible data sources by **113%** at **100%** coverage. Source sites change shape without warning, and the tests are what tell you which one broke.

I also built random forest classifiers with pandas, NumPy, SciPy, and scikit-learn to predict chemical toxicity, and a knowledge graph pipeline using Neo4j, CoreNLP, and Stanza that extracts semantic triples from medical literature.

### Department of National Defence {#dnd}

*Data Scientist Intern · June 2023 to November 2023 · Python, LLMs, RAG, NLP*

Tax documentation is long, heavily cross-referenced, and unpleasant to search, which made it a reasonable target for retrieval. I built a chatbot on a RAG architecture that answers questions across **20 or more** tax documents.

The NLP pipeline used NLTK for tokenization, contextual analysis, and named entity recognition. Vector search ran on FAISS with SQLite3 behind it for embedding storage and retrieval.

### NAV CANADA {#navcan}

*Software Developer Intern · May 2023 to August 2023 · C++, Qt, PowerShell, GIS*

Air traffic control software has an unusual performance profile. The average case being fast counts for little when a controller is watching the screen in real time and notices every stall.

I optimized the data management algorithm in an internal data tool, cutting storage use by **60%** and improving automated analysis performance by **30%**. I fixed several rendering bugs in the ATC software, worth **16%** on frame rate overall, and improved how geospatial data is imported and validated.

I also automated network configuration with PowerShell, which cut manual setup work by more than **95%**.

### Correctional Service Canada {#csc}

*Software Developer Intern · May 2022 to April 2023 · C#, .NET, ASP.NET, JavaScript*

My first software job, on a public-facing victim services portal. The people using it are often in difficult circumstances, and the service is a government obligation, so accessibility work came first.

I brought the application up to WCAG 2.1 Level AA using the WET framework, for a service with **100 or more daily users**, and built ASP.NET fixes for interface defects in the victim information delivery application.

*[Back to contents](#contents)*

---

## Projects {#projects}

### Latch {#latch}

*Local-first macOS focus blocker · Electron, TypeScript, Swift, Chromium extension, native messaging · [GitHub](https://github.com/nbui23/latch) · [Download](https://github.com/nbui23/latch/releases)*

Most focus apps are easy to get around because they only exist at the UI layer. I wanted one where starting a session meant the blocking held through a browser restart, a crash, or a casual attempt to work around it, while still behaving like a normal Mac app.

An Electron app owns session control, blocklists, and the interface. A one-time privileged helper written in Swift does the system-level enforcement. Electron itself stays unprivileged and talks to the helper over a local socket, which keeps the privileged code small and easy to audit. An optional Chromium extension gives the blocked page an intentional look instead of a browser error, and a native messaging host connects the two.

Most of the engineering went into what happens when something goes wrong, since a blocker that quietly stops working is worse than no blocker at all:

- Starting a session writes the intent to disk first, then calls the helper, then marks the session active. Stopping runs the same steps in reverse. Because the on-disk state always records what was being attempted, recovery can be mechanical rather than a guess.
- Recovery itself is a policy table over session state and hosts-file markers, covering all four crash windows around writes and removals. The unit tests exercise all seven rows of that table.
- Latch wraps its edits to the system hosts file in start and end markers, so it can tell whether its own block is still in place and clean up only its own lines.
- The helper reads newline-terminated JSON with a size cap and a socket receive timeout, so a stalled or malformed client cannot hold up its single-threaded accept loop.
- Shared Zod schemas across IPC, helper responses, native messaging, and app config reject malformed payloads at each boundary instead of letting them through to the runtime.
- The app checks the Chrome native messaging manifest and rewrites it when it is missing or wrong, which removes an entire category of confusing bug report.

The desktop app, helper, extension bundle, and native messaging host are packaged into one macOS release, so installing four cooperating pieces feels like installing one thing.

### Orbital Refuelling Simulator {#orbital}

*Synthetic spacecraft telemetry with hybrid anomaly monitoring · Python, Streamlit, scikit-learn, IsolationForest, LoRA fine-tuning, pytest · [GitHub](https://github.com/nbui23/orbital-refuelling) · [Demo](https://orbital-refueling-telemetry-simulator.streamlit.app/)*

Autonomous propellant transfer makes a good monitoring problem because several subsystems move at once: robotic alignment, docking loads, seal pressure, transfer pressure, flow rate, pump behavior, thermal state, attitude. A few faults are plain threshold violations. Most of the interesting ones only look wrong once you notice several signals drifting together.

Mission phase is what makes that judgement possible. During approach, zero propellant flow is expected. During main transfer, zero flow means something has gone badly wrong. The same pressure reading can be normal in one phase and a problem in another, so the system has to know where in the mission it is before scoring anything.

The simulator generates a reproducible **410-second** mission at 2 Hz across nine phases: approach, arm alignment, docking, seal check, pressure equalization, main transfer, leak check, disconnect, retreat. It tracks mass transfer and updates donor and receiver pressure, line pressure, flow rate, pump current, temperatures, attitude, arm state, and interface loads as the phase changes. Nine anomaly scenarios are injected where they physically make sense, and each perturbs the signals it should: partial blockage drops flow while raising line pressure and pump current, arm misalignment raises end-effector error and interface loads, unstable slosh oscillates flow, pressure, and propellant temperature together. Fixed seeds keep every scenario stable enough to test against.

Monitoring runs in two layers that stay out of each other's way. Deterministic rules own the hard limits, with warning and critical thresholds scoped per phase so an expected ramp does not fire an alert, and raw alerts grouped into event windows so an oscillating signal does not fill the operator view with near-identical rows. Alongside them, one IsolationForest per phase scores **17** numeric features against nominal behavior for that phase and produces an advisory score from 0 to 1. If bus voltage drops too far or seal pressure falls after the seal is established, the rule fires whatever the model thinks of it.

A score on its own does not tell an operator much, so there is attribution underneath it. For anomalous rows, the explainer replaces each feature with that phase's nominal mean and measures how far the anomaly score falls, which ranks the signals pushing it up. Above that sits a fine-tuned explainer: a Qwen2.5-0.5B LoRA adapter trained on deterministic synthetic instruction data, which turns rule alerts, advisory scores, and attribution output into a short written explanation. It scored **4.86 out of 5** on a deterministic rubric over 100 held-out examples, against 3.69 for the base model. It reads the monitoring output and never produces it, so it cannot detect an anomaly or set a severity.

The scenarios show why both layers exist. Partial blockage trips the rules and the model together. Sensor drift and unstable slosh raise the model's anomaly rate while staying under every hard threshold, so the rules have nothing to say about them.

This is a learning project rather than flight software, and the model cards say so. The data comes from one simplified generator. IsolationForest scores each timestep on its own with no temporal model. The thresholds are illustrative and not taken from spacecraft engineering documentation. The explainer was trained and evaluated on template-generated text, not real operations data.

### Riverbreak {#riverbreak}

*Typographic river detection and layout reranking · Python, PyTorch, U-Net, ONNX Runtime, JavaScript, HTML Canvas · [GitHub](https://github.com/nbui23/riverbreak) · [Demo](https://nbui23.github.io/riverbreak/)*

Typographic rivers are the whitespace channels that appear when justified text stretches word gaps into accidental vertical or diagonal paths. A reader spots one immediately. A layout engine has a harder time, because a river emerges across lines and line-breaking is normally optimized one line at a time. Every line can score well on its own while the paragraph has a channel running down it.

The project has four parts. A Knuth-Plass-style line breaker with beam search, implemented in the browser so per-line spacing is available as data instead of being hidden inside browser text layout. A geometric detector that traces whitespace corridors by gap-center alignment, diagonal drift tolerance, and chain length, fast enough to update while a slider moves. A small U-Net that takes a 256 by 256 grayscale paragraph render and returns a per-pixel probability map. And a reranker that turns detection into a layout decision.

I wrote the geometric detector first because the demo needed to respond instantly to a dragged slider, which rules out a model that takes a second. It also generated the weak labels that trained the first models. It is still in the demo and still in the benchmark reports now that the neural detector exists, so the comparison stays visible.

Training used 128 synthetic weak-label paragraphs with focal loss, chosen because river pixels are a sparse minority class. Evaluation used **24 hand-labeled validation and 24 hand-labeled test images**, kept away from the synthetic data, since otherwise the benchmark would only measure agreement with the label generator. Thresholds were picked on validation and applied unchanged to test. The focal-loss SmallUNet reached **test Dice 0.5018 and IoU 0.3349**, against 0.4182 and 0.2644 for the heuristic baseline. That is a small benchmark, so I read the numbers as direction and failure-analysis material rather than a statistical result.

The checkpoint exports to a single ONNX model that runs in the browser as an optional overlay, with ONNX Runtime Web loaded only when the toggle is switched on and inference running on CPU WASM against the rasterized paragraph canvas. The file is around 30 MB and a pass takes hundreds of milliseconds to seconds, so live neural stays opt-in while the geometric overlay stays instant.

The reranker generates a bounded set of candidate layouts around the current settings, scores each as classical demerits plus a weighted river-severity term, and shows the baseline and the winner side by side with changed lines flagged. Severity comes from the geometric detector rather than a live U-Net pass, because six forward passes per rerank would make the interaction sluggish. The scoring function is isolated, so swapping in the model later touches one place.

### CruxOS {#cruxos}

*Full-stack decision support for climbing · Next.js, TypeScript, Prisma, SQLite, Expo, React Native · [GitHub](https://github.com/nbui23/cruxos)*

Training logs are easy to build and rarely get used, because logging was never the hard part. Working out what to do next week is. CruxOS is built around that question.

There are two clients with different jobs. An Expo mobile app handles session capture, where speed is the only thing that matters, since logging has to happen at the gym or it does not happen. A Next.js web app handles review, analysis, and reports, where there is more screen and more patience. They share TypeScript logic.

Training, recovery, and workload signals turn into weekly recommendations through explicit rules rather than a model. When the system says to back off, it can point at the signals that led there, and a climber is far more likely to follow advice they can check.

Prisma and SQLite keep sessions, recovery signals, and reports consistent across mobile capture and web review, with tests around the recommendation logic and the API flows carrying data between the two clients.

### ThinkPad home lab {#homelab}

*Ubuntu media and automation stack on an X220 · Docker Compose, systemd, gluetun, Tailscale, ufw, Grafana*

A decade-old ThinkPad X220 running Ubuntu, treated as real infrastructure rather than a toy. Most of what I have learned from it has been operational.

- Media lives on a dedicated disk mounted into every container at the same path, so hardlinks work across libraries and an import does not duplicate the file.
- Only the download client routes through the VPN container. Working that out took a while: Cloudflare-gated sources kept failing because the service solving the challenge and the client replaying its cookie have to share one exit IP, since the clearance cookie is bound to the address that solved it. Putting both behind the VPN fixed the mismatch and broke it differently, because Cloudflare will not hand a solvable challenge to a datacenter IP at all. Moving both outside and leaving only the traffic that needs the tunnel inside it was the answer.
- Tailscale handles access from outside the house, with ufw denying incoming by default and allowing the local subnet and the tailnet interface. Turning a firewall on over SSH, on a machine I am usually not near, means arming a timed rollback first and then verifying on a fresh connection, because the session you are already in survives on the established-connection rule and proves nothing.
- Push alerts cover service health and disk space, and every app's config backups sync off the box daily to another machine. That job runs under launchd rather than cron, so a run missed while the laptop is asleep fires on wake instead of being skipped.
- The X220 exposes a force-discharge control, which gives whole-system watts off the battery gauge while still on AC. The machine draws **9.4 W**, about $12 a year, and the backlight accounts for 0.77 W of it. Measuring first saved me from optimizing the wrong thing.

### SocialSaplings {#socialsaplings}

*Hackathon-winning reforestation platform · HTML/SCSS, JavaScript, Bootstrap, Node.js, Express, Firebase · [Devpost](https://devpost.com/software/socialsaplings) · [GitHub](https://github.com/nbui23/socialsaplings)*

First place at KuriusHacks, leading a cross-functional team. The platform reads a user's location, pulls environmental data for it, and recommends tree species suited to where they actually are, with a Google Maps dashboard showing reforestation metrics and global impact data.

*[Back to contents](#contents)*

---

## Education {#education}

### Carleton University

*Bachelor of Computer Science (Honours) · 3.9/4.0 GPA · Graduated Spring 2026*

**Coursework**

- **Theory and algorithms:** Algorithms I and II, Discrete Structures I and II, Graph Analytics
- **Systems and security:** Operating Systems, Systems Programming, Applied Cryptography
- **Software engineering:** Software Engineering, Object-Oriented Programming, Software Quality Assurance, Programming Paradigms, Data Structures, Human-Computer Interaction
- **Data and applications:** Database Management Systems, Web Development, Mobile Multimedia
- **Math and statistics:** Calculus I and II, Linear Algebra, Statistical Modeling

**Awards:** Dean's Honour List every year, President's Scholarship, Henry Marshall Tory Scholarship, Chalmers Jack MacKenzie Scholarship, Harry S. Southam Scholarship.

*[Back to contents](#contents)*

---

## Skills {#skills}

**Languages:** Python, TypeScript, JavaScript, C++, C#, Kotlin, Java, SQL, PHP, HTML/CSS

**AI and ML:** LLMs, agentic AI, fine-tuning with LoRA and PEFT, RAG, LangGraph, LangChain, FAISS, Ollama, Hugging Face, Sentence Transformers, scikit-learn, IsolationForest, PyTorch, ONNX Runtime, pandas, NumPy, NLTK, tree-sitter static analysis

**Backend and data:** FastAPI, Node.js, Express, Flask, Spring Boot, .NET, ASP.NET, GraphQL, PostgreSQL, PostGIS, pgvector, MySQL, MongoDB, SQLite, Prisma, Neo4j, Firebase

**Frontend and apps:** Next.js, React Native, Expo, Electron, Qt, Streamlit

**Infrastructure and practices:** Docker, Docker Compose, CI/CD, TDD, Grafana, observability, Linux, systemd, networking and VPN routing, Tailscale, Cloudflare Workers, PowerShell, pytest, unittest, Mocha, Chai, Sinon, Selenium, WCAG 2.1, Agile

**Spoken languages:** English, French, Vietnamese

---

[← home](index.html) · [back to contents](#contents)
