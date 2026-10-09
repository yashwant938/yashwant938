<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="./assets/header-mobile.svg" />
    <img src="./assets/header.svg" alt="Yashwant — Systems software engineer. C++, Linux, compilers, and developer tools." width="100%" />
  </picture>
</p>

<p align="center">
  <strong>Systems Software Engineer at IBM India Software Labs · M.Tech, IIIT Delhi</strong>
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/yash-rana-3a7252265/"><strong>LinkedIn ↗</strong></a> &nbsp; · &nbsp;
  <a href="#merged-upstream-work">Open-source contributions</a> &nbsp; · &nbsp;
  <a href="#selected-projects">Selected projects</a>
</p>

I work on C/C++ systems and build developer tools. I enjoy turning a failure into a small reproducer, understanding the root cause, and writing a regression test that keeps it fixed.

My public work spans **linker correctness, Linux concurrency, backend systems, and AI-assisted tooling**.

## Merged upstream work

Contributions to **[Qualcomm ELD](https://github.com/qualcomm/eld)**, an ELF linker built on LLVM:

| Merged PR | Contribution |
| :--- | :--- |
| **[#2065](https://github.com/qualcomm/eld/pull/2065)** | **ELF header layout correctness.** Fixed a crash caused by assigning addresses to headers outside the output layout. Added regression coverage for `PHDRS` / `FILEHDR` cases. |
| **[#2011](https://github.com/qualcomm/eld/pull/2011)** | **GNU-compatible command-line handling.** Accepted numeric `-O` levels as ignored compatibility options, with validation for malformed values. |

Both contributions include focused regression testing across **six architecture configurations**: ARM, AArch64, Hexagon, RISC-V 32/64, and x86-64. Each PR records the validation scope.

<details>
<summary><strong>More ELD work: LTO, build guidance, and maintainer discussion</strong></summary>

- **[ARM/AArch64 LTO fix · #2129](https://github.com/qualcomm/eld/pull/2129)** — Keep `--save-temps` on the native-object path. Full LTO, ThinLTO, and explicit assembly-output coverage; 16 focused tests passed.
- **[Build guidance · #2127](https://github.com/qualcomm/eld/pull/2127)** — Clarify the LLVM `main` baseline and recommend paths without spaces.
- **[Contributor-experience discussion](https://github.com/qualcomm/eld/discussions/887#discussioncomment-18761658)** — Reported LLVM compatibility and lit path issues encountered while building under Ubuntu/WSL; the maintainer invited the README update.

The two PRs above were open as of October 9, 2026. Local verification used focused tests, not the full ELD suite.

</details>

## Selected projects

<table>
<tr>
<td width="50%" valign="top">
<h3><a href="https://github.com/yashwant938/OOPD-Project">C++ Filesystem &amp; Concurrency Lab</a></h3>
<p>Sequential and threaded filesystem commands, recursive directory traversal, and workload timing scripts. A practical study of concurrency and I/O tradeoffs.</p>
<p><code>C++17</code> <code>Linux</code> <code>std::filesystem</code></p>
<a href="https://github.com/yashwant938/OOPD-Project#readme">Explore the implementation →</a>
</td>
<td width="50%" valign="top">
<h3><a href="https://github.com/ZainiiiBoyx278/legal-lens">Legal Lens 2.0</a></h3>
<p>Contributed hybrid BM25 + MiniLM retrieval, page-linked PDF evidence, research-brief export, and local question classification to a collaborative document-research app.</p>
<p><code>Python</code> <code>FastAPI</code> <code>Next.js</code> <code>RAG</code></p>
<a href="https://github.com/ZainiiiBoyx278/legal-lens#readme">Explore the project →</a> · <a href="https://github.com/ZainiiiBoyx278/legal-lens/pulls?q=is%3Apr+author%3Ayashwant938+is%3Amerged">My merged work</a>
</td>
</tr>
<tr>
<td width="50%" valign="top">
<h3><a href="https://github.com/yashwant938/LLVMBugSquad">LLVM BugSquad</a></h3>
<p>A compiler-investigation workbench with isolated workers, persistent run history, resumable event streams, and evidence exports.</p>
<p><strong>Status:</strong> synthetic replay demo available; live model/compiler integration validation is pending.</p>
<p><code>LLVM</code> <code>Python</code> <code>Docker</code> <code>TypeScript</code></p>
<a href="https://github.com/yashwant938/LLVMBugSquad#readme">Architecture &amp; implementation →</a>
</td>
<td width="50%" valign="top">
<h3><a href="https://github.com/yashwant938/MoodPet">MoodPet</a></h3>
<p>A native Windows productivity app with focus timers, durable session history, and a Qt dashboard. Regression tests cover timer, storage, and activity-tracking behavior.</p>
<p><code>Python</code> <code>PySide6</code> <code>SQLite</code> <code>Windows</code></p>
<a href="https://github.com/yashwant938/MoodPet#readme">Explore the desktop app →</a>
</td>
</tr>
</table>

**Also built:** [Interactive C++ Concepts Lab](https://github.com/yashwant938/CompilerCppTopics) · [Real-time multiplayer quiz](https://github.com/yashwant938/quizzesbyiron)

## Tools I work with

| Systems & debugging | Backend & tooling | Retrieval & applications |
| :--- | :--- | :--- |
| C / C++, Linux, GDB | Python, FastAPI, SQL | BM25, MiniLM, RAG |
| LLVM, CMake, Ninja, lit | Git, Docker, REST, SSE | TypeScript, React, Next.js |

I keep my ongoing algorithms practice in **[DSA](https://github.com/yashwant938/DSA)**.

---

**Interested in C++ systems, compiler tooling, backend engineering, or AI developer tools?** [Connect with me on LinkedIn →](https://www.linkedin.com/in/yash-rana-3a7252265/)
