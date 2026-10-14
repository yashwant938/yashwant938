<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="./assets/header-mobile.svg" />
    <img src="./assets/header.svg" alt="Yashwant — Systems × GenAI. C++, Linux and LLVM; RAG, LLM applications and AI tooling." width="100%" />
  </picture>
</p>

<p align="center">
  <strong>Software engineer · Systems × GenAI · M.Tech, IIIT Delhi</strong>
</p>

<p align="center">
  <a href="https://yashwant938.github.io/portfolio-/"><strong>Explore my portfolio &amp; project case studies ↗</strong></a> &nbsp; / &nbsp;
  <a href="#selected-work">Projects</a> &nbsp; / &nbsp;
  <a href="https://github.com/qualcomm/eld/pulls?q=is%3Apr+author%3Ayashwant938+is%3Amerged">Merged contributions</a> &nbsp; / &nbsp;
  <a href="https://www.linkedin.com/in/yash-rana-3a7252265/">LinkedIn</a>
</p>

I build across **systems engineering and generative AI**—from C++ linker fixes and Linux concurrency to retrieval-backed assistants and LLM-powered developer tools.

I care about what happens around the core algorithm: **reproducible failures, useful evidence, reliable APIs, and a product people can inspect and use.**

At **IBM India Software Labs**, I worked on the **IBM Z C/C++ compiler**, resolved **8+ production defects**, and implemented an **MCP service for compiler-diagnostic retrieval**. Software Engineer: July 2025–September 2026; intern: January–July 2025.

My [portfolio](https://yashwant938.github.io/portfolio-/#work) brings together **five featured projects**, linker contributions, implementation details, and code links. Search by technology or explore systems, AI/ML, applications, and research.

## Selected work

Five featured projects, in the same order as my [portfolio](https://yashwant938.github.io/portfolio-/#work).

<table>
<tr>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/#eld"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/eld.svg" /><img src="./assets/projects/eld.svg" alt="Dimensional concept illustration for Qualcomm ELD contributions" width="100%" /></picture></a>
<sub><strong>SYSTEMS · C++ · OPEN SOURCE</strong></sub>
<h3><a href="https://github.com/qualcomm/eld">Qualcomm ELD Contributions</a></h3>
<p><strong>Two merged fixes</strong> in an ELF linker built on LLVM:</p>
<ul>
<li><a href="https://github.com/qualcomm/eld/pull/2065"><strong>#2065</strong></a> — Fixed a PHDRS/FILEHDR layout crash.</li>
<li><a href="https://github.com/qualcomm/eld/pull/2011"><strong>#2011</strong></a> — Added GNU-compatible handling of numeric <code>-O</code> options.</li>
</ul>
<p>Focused regression testing across six architecture configurations. Each PR records the verification scope.</p>
<p><code>C++</code> <code>LLVM</code> <code>Linux</code> <code>lit / FileCheck</code></p>
<a href="https://github.com/qualcomm/eld/pulls?q=is%3Apr+author%3Ayashwant938">Explore the contributions →</a>
</td>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/#legal-lens"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/legal-lens.svg" /><img src="./assets/projects/legal-lens.svg" alt="Dimensional concept illustration for Legal Lens 2.0" width="100%" /></picture></a>
<sub><strong>GENAI · RAG · INFORMATION RETRIEVAL</strong></sub>
<h3><a href="https://github.com/ZainiiiBoyx278/legal-lens">Legal Lens 2.0</a></h3>
<p>Contributed hybrid BM25 + MiniLM retrieval over a 1,871-page historical IPC PDF, with reciprocal rank fusion, page-linked evidence, and cited research briefs.</p>
<p>Local scope/intent classification and a RAG assistant with document-excerpt fallback.</p>
<p><code>Python</code> <code>FastAPI</code> <code>Next.js</code> <code>MiniLM</code></p>
<a href="https://yashwant938.github.io/portfolio-/#legal-lens">Case study →</a> · <a href="https://github.com/ZainiiiBoyx278/legal-lens/pulls?q=is%3Apr+author%3Ayashwant938+is%3Amerged">My project PRs</a>
</td>
</tr>
<tr>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/#real-estate"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/real-estate.svg" /><img src="./assets/projects/real-estate.svg" alt="Dimensional concept illustration for Real Estate Aggregator" width="100%" /></picture></a>
<sub><strong>BACKEND / PROPERTY MARKETPLACE</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/#real-estate">Real Estate Aggregator</a></h3>
<p>A PHP/Slim property marketplace connecting searchable listings, account workflows, MySQL persistence, Razorpay integration, and generated PDF contracts.</p>
<p><strong>Full-stack prototype</strong></p>
<p><code>PHP</code> <code>Slim</code> <code>MySQL</code> <code>JavaScript</code> <code>Razorpay</code> <code>TCPDF</code></p>
<a href="https://github.com/yashwant938/E-Commerce">Source &amp; architecture ↗</a>
</td>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/#gpt2-summarization"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/gpt2-summarization.svg" /><img src="./assets/projects/gpt2-summarization.svg" alt="Dimensional concept illustration for GPT-2 Review Summarization" width="100%" /></picture></a>
<sub><strong>NLP / COURSEWORK EXPERIMENT</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/#gpt2-summarization">GPT-2 Review Summarization</a></h3>
<p>A notebook experiment fine-tuning GPT-2 to turn Amazon Fine Food Reviews into short summaries, covering data preparation, training, checkpointing, and generation.</p>
<p><strong>ML coursework · evaluation corrections documented</strong></p>
<p><code>Python</code> <code>PyTorch</code> <code>Hugging Face</code> <code>pandas</code> <code>Jupyter</code></p>
<a href="https://github.com/yashwant938/CSE508_Winter2024_A4_MT23107">Notebook &amp; findings ↗</a>
</td>
</tr>
<tr>
<td colspan="2" valign="top">
<p><a href="https://yashwant938.github.io/portfolio-/#cpp-systems"><img src="./assets/projects/cpp-systems.webp" alt="Live C++ Concepts code workspace with an unordered_map example" width="520" /></a></p>
<sub><strong>C++ / SYSTEMS / INTERACTIVE LEARNING</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/#cpp-systems">C++ Concepts &amp; Systems Lab</a></h3>
<p>Interactive C++ lessons and a C++17 filesystem lab exploring containers, recursive operations, and concurrency.</p>
<ul><li>Step-through simulations, an editable compiler workspace, quizzes, and an optional Gemini tutor.</li><li>cd / ls / cp / mv / rm; sequential and threaded variants with synchronized output.</li></ul>
<p><code>C++17</code> <code>std::filesystem</code> <code>std::thread</code> <code>Linux</code> <code>React</code> <code>Monaco</code></p>
<p>Two complementary labs: browser teaching simulations and an educational filesystem interpreter. Includes timing scripts; no measured speedup claimed.</p>
<a href="https://yashwant938.github.io/CompilerCppTopics/">Live demo ↗</a> · <a href="https://github.com/yashwant938/CompilerCppTopics">Concepts source ↗</a> · <a href="https://github.com/yashwant938/OOPD-Project">Systems source ↗</a> · <a href="https://yashwant938.github.io/portfolio-/#cpp-systems">Case study →</a>
</td>
</tr>
</table>

<details>
<summary><strong>Earlier projects &amp; explorations</strong></summary>

<p>More prototypes and learning projects, preserved in the <a href="https://yashwant938.github.io/portfolio-/archive.html#work">portfolio archive</a>. Illustrations below are concept artwork.</p>

<table>
<tr>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#llvm-bugsquad"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/llvm-bugsquad.svg" /><img src="./assets/projects/llvm-bugsquad.svg" alt="Dimensional concept illustration for LLVM BugSquad" width="100%" /></picture></a>
<sub><strong>GENAI × SYSTEMS · DEVELOPER TOOLS</strong></sub>
<h3><a href="https://github.com/yashwant938/LLVMBugSquad">LLVM BugSquad</a></h3>
<p>Compiler investigation workspace with model-assisted routing, isolated LLVM recipes, SQLite history, resumable events, and hashed evidence exports.</p>
<p><strong>Status:</strong> synthetic replay demo. Live model/worker integration validation pending.</p>
<p><code>Python</code> <code>FastAPI</code> <code>Docker</code> <code>LLM APIs</code></p>
<a href="https://yashwant938.github.io/portfolio-/archive.html#llvm-bugsquad">Case study →</a> · <a href="https://github.com/yashwant938/LLVMBugSquad#readme">Source &amp; setup</a>
</td>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#newsscript"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/newsscript.svg" /><img src="./assets/projects/newsscript.svg" alt="Dimensional concept illustration for NewsScript" width="100%" /></picture></a>
<sub><strong>GENAI · FULL-STACK APPLICATIONS</strong></sub>
<h3><a href="https://github.com/yashwant938/NewsScript">NewsScript</a></h3>
<p>RSS ingestion, deduplication, and heuristic ranking feed a script-drafting workspace with optional Gemini/OpenAI generation, saved articles, and text/PDF exports.</p>
<p><strong>Status:</strong> local prototype with a template fallback. Live-provider validation and deployment hardening are pending.</p>
<p><code>TypeScript</code> <code>Next.js</code> <code>Prisma</code> <code>LLM APIs</code></p>
<a href="https://yashwant938.github.io/portfolio-/archive.html#newsscript">Case study →</a> · <a href="https://github.com/yashwant938/NewsScript#readme">Source &amp; setup</a>
</td>
</tr>
<tr>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#moodpet"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/moodpet.svg" /><img src="./assets/projects/moodpet.svg" alt="Dimensional concept illustration for MoodPet" width="100%" /></picture></a>
<sub><strong>DESKTOP / PRODUCTIVITY</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/archive.html#moodpet">MoodPet</a></h3>
<p>A native Windows companion that combines an animated desktop pet with focus sessions, local activity history, persistent streaks, and a productivity dashboard.</p>
<p><strong>Local Windows application</strong></p>
<p><code>Python</code> <code>PySide6</code> <code>SQLite</code> <code>Windows APIs</code></p>
<a href="https://github.com/yashwant938/MoodPet">Source &amp; setup ↗</a>
</td>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#quizzes-by-iron"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/quizzes-by-iron.svg" /><img src="./assets/projects/quizzes-by-iron.svg" alt="Dimensional concept illustration for Quizzes by Iron" width="100%" /></picture></a>
<sub><strong>REAL-TIME / MULTIPLAYER</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/archive.html#quizzes-by-iron">Quizzes by Iron</a></h3>
<p>An event-driven multiplayer quiz with host-controlled rooms, QR-code joins, timed questions, server-side scoring, and live leaderboards.</p>
<p><strong>Web application · room state held in one server process</strong></p>
<p><code>React</code> <code>Node.js</code> <code>Express</code> <code>Socket.IO</code> <code>Vite</code></p>
<a href="https://quizzesbyiron.vercel.app">Open app ↗</a> · <a href="https://github.com/yashwant938/quizzesbyiron">Source ↗</a>
</td>
</tr>
<tr>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#bio-literature"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/bio-literature.svg" /><img src="./assets/projects/bio-literature.svg" alt="Dimensional concept illustration for Bioinformatics Literature &amp; Graph Explorer" width="100%" /></picture></a>
<sub><strong>NLP / RESEARCH VISUALIZATION</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/archive.html#bio-literature">Bioinformatics Literature &amp; Graph Explorer</a></h3>
<p>A related pair of research tools: an extremophile literature-mining pipeline and an interactive chemical–gene graph that makes prepared relationships and publication references easier to explore.</p>
<p><strong>Research capstone · two connected repositories</strong></p>
<p><code>Python</code> <code>pandas</code> <code>Entrez</code> <code>Streamlit</code> <code>NetworkX</code></p>
<a href="https://github.com/yashwant938/3DKnolwedgeGraph">Graph explorer ↗</a> · <a href="https://github.com/yashwant938/ExtremophilesData">Mining pipeline ↗</a>
</td>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#android-classifier"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/android-classifier.svg" /><img src="./assets/projects/android-classifier.svg" alt="Dimensional concept illustration for Android Image Classifier" width="100%" /></picture></a>
<sub><strong>APPLIED ML / ANDROID</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/archive.html#android-classifier">Android Image Classifier</a></h3>
<p>An Android app that runs a bundled quantized MobileNet model locally to classify a selected gallery image and display its predicted label.</p>
<p><strong>Educational mobile prototype</strong></p>
<p><code>Kotlin</code> <code>Jetpack Compose</code> <code>TensorFlow Lite</code> <code>MobileNet</code></p>
<a href="https://github.com/yashwant938/ImageClassification">Android source ↗</a>
</td>
</tr>
<tr>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#image-captioning"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/image-captioning.svg" /><img src="./assets/projects/image-captioning.svg" alt="Dimensional concept illustration for Voice–Vision: Image Captioning" width="100%" /></picture></a>
<sub><strong>COMPUTER VISION / LANGUAGE GENERATION</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/archive.html#image-captioning">Voice–Vision: Image Captioning</a></h3>
<p>A Flask image-captioning prototype combining InceptionV3 visual features with an LSTM language decoder to turn an uploaded image into a caption.</p>
<p><strong>Earlier ML prototype</strong></p>
<p><code>Python</code> <code>Flask</code> <code>TensorFlow / Keras</code> <code>InceptionV3</code> <code>LSTM</code></p>
<a href="https://github.com/yashwant938/Voice-Vision-Communication">Explore the prototype ↗</a>
</td>
<td width="50%" valign="top">
<a href="https://yashwant938.github.io/portfolio-/archive.html#decrypter-analyzer"><picture><source media="(prefers-reduced-motion: reduce)" srcset="./assets/projects/static/decrypter-analyzer.svg" /><img src="./assets/projects/decrypter-analyzer.svg" alt="Dimensional concept illustration for Decrypter &amp; Analyzer" width="100%" /></picture></a>
<sub><strong>SECURITY EDUCATION / WEB TOOLS</strong></sub>
<h3><a href="https://yashwant938.github.io/portfolio-/archive.html#decrypter-analyzer">Decrypter &amp; Analyzer</a></h3>
<p>An educational PHP toolkit exploring hash demonstrations and basic website configuration inspection through browser-based forms and result panels.</p>
<p><strong>Educational prototype for authorized lab use</strong></p>
<p><code>PHP</code> <code>JavaScript</code> <code>MySQL</code> <code>HTML / CSS</code></p>
<a href="https://github.com/yashwant938/Decrypter-Analyzer">Source &amp; scope ↗</a>
</td>
</tr>
</table>

</details>

## From issue to pull request

<p align="center">
  <a href="https://github.com/qualcomm/eld/pulls?q=is%3Apr+author%3Ayashwant938">
    <picture>
      <source media="(max-width: 600px)" srcset="./assets/contribution-flow-mobile.svg" />
      <img src="./assets/contribution-flow.svg" alt="My contribution workflow: reproduce the failure, make a focused patch, verify with regression tests, and submit a pull request with evidence." width="100%" />
    </picture>
  </a>
</p>

**A recent example:** [ELD #2134 — preserve AArch64 feature flags](https://github.com/qualcomm/eld/pull/2134). A one-line C++ fix, a regression that failed before the change, and **18 passing focused test runs** across two AArch64 configurations. PR open for review.

**AI tooling:** [Hugging Face smolagents #2949](https://github.com/huggingface/smolagents/pull/2949) — **Draft** AST-validation fix for unpacking aliases in context managers, with tool export/reload regression coverage. The PR records **70 focused pytest passes**; scope acceptance and contributor review are pending.

<details>
<summary><strong>More open-source contributions and verification scope</strong></summary>

- **[ARM/AArch64 LTO fix · #2129](https://github.com/qualcomm/eld/pull/2129) · Open** — Preserve native object generation with `--save-temps`. Full LTO, ThinLTO, and explicit assembly-output coverage; 16 focused tests passed, followed by the updated regression on all six target configurations.
- **[Build guidance · #2127](https://github.com/qualcomm/eld/pull/2127) · Open** — Document the LLVM `main` baseline and source/build path guidance following a [maintainer discussion](https://github.com/qualcomm/eld/discussions/887#discussioncomment-18761658).
- **[React ChatBotify · #366](https://github.com/react-chatbotify/react-chatbotify/pull/366) · Open** — Submitted chat-history HTML sanitization, URL checks, and an optional sanitizer callback with tests.

Statuses checked **13 October 2026**. ELD #2011 and #2065 are merged; #2134, #2129, and #2127 remain open. smolagents #2949 is a draft; React ChatBotify #366 remains open. Results above describe focused tests recorded in the PRs, not full-suite runs or live integration validation of every project.

</details>

<details>
<summary><strong>Algorithms and coding practice</strong></summary>

[DSA](https://github.com/yashwant938/DSA) · [CSES](https://github.com/yashwant938/CSES) · [LeetCode daily work](https://github.com/yashwant938/LeetcodeDailyCode) · [A-to-Z series](https://github.com/yashwant938/AtoZ100DaysSeries) · [Earlier LeetCode practice](https://github.com/yashwant938/DailyLeetcode) · [Striver A-to-Z](https://github.com/yashwant938/StriverAtozz)

</details>

## Toolbox

| Systems engineering | GenAI & applied ML | Backend & delivery |
| :--- | :--- | :--- |
| C / C++, Linux, GDB | RAG, BM25, MiniLM, RRF | Python, FastAPI, SQL |
| LLVM, CMake, Ninja, lit | LLM APIs, PyTorch, Hugging Face | TypeScript, Next.js, Docker |
| Filesystems, concurrency | TensorFlow Lite, scikit-learn | PySide6, PHP, MySQL |

---

**Let's build at the intersection of systems and AI.** [Visit my portfolio ↗](https://yashwant938.github.io/portfolio-/) · [Connect on LinkedIn →](https://www.linkedin.com/in/yash-rana-3a7252265/)
