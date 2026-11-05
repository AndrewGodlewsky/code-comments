# Related systems and researchers

Research date: 2026-11-05. This targeted review asks what already exists for preserving useful project knowledge, generating explanations, and maintaining context for coding agents. It does not select a product workflow or claim novelty. No tools were installed, authors contacted, or reported experiments reproduced.

The closest prior work already covers most individual ingredients: dependency-aware documentation generation, change-triggered refresh, repository maps, persistent rationale skills, and experience-memory policies. The remaining project question is narrower: whether selective, maintained explanation **beside the edited code**, compared with equivalent accessible information elsewhere, improves subsequent changes enough to offset its lifecycle cost. Existing documentation-quality scores cannot answer that question.

## Search and access record

Searches combined named candidates with narrower queries, including `RepoAgent documentation repository maintenance`, `DocAgent multi agent code documentation`, `Google Code Wiki`, `Cognition DeepWiki`, `aider repository map`, `Sourcegraph Cody context graph`, `ACE Agentic Context Engineering`, `SWE-agent memory documentation`, `CodeResearch documentation agent`, and `inline rationale comments agent skill github`. Follow-up reading used authors' papers, official documentation, and linked repositories. Secondary results were discovery leads only.

All access below occurred on 2026-11-05. Paper versions are explicit; living documentation and repository READMEs are snapshots observed that day, not pinned release guarantees. The descriptions say which portions were inspected. Public availability is separate from successful installation or reproducibility. The search is English-language, selected, and non-exhaustive; no registry-wide or systematic literature search was conducted.

## Implementations and evidence

### 1. RepoAgent: maintenance of generated repository documentation

Qinyu Luo, Yining Ye, and collaborators at Tsinghua, Renmin, and Siemens developed RepoAgent. Its Python analysis builds a project structure and caller/callee context, generates object documentation in dependency order, and uses Git changes to refresh affected documentation. Its pre-commit integration and separate Markdown output make maintenance an implemented feature, rather than just an aspiration. Read the method, update mechanism, and evaluation in [the February 2024 paper, v1](https://arxiv.org/html/2402.16667v1), plus the [official README](https://github.com/OpenBMB/RepoAgent/blob/main/README.md).

The paper reports blind preferences for generated versus existing human documentation of approximately 70% and 91% on Transformers and LlamaIndex, with three evaluators. These are documentation preferences, not subsequent repair outcomes or long-term drift measurements. The reusable lesson is change detection and dependency-aware refresh; the alternative is generated external descriptions, not compulsory inline prose. Code is public under [Apache-2.0](https://raw.githubusercontent.com/OpenBMB/RepoAgent/main/LICENSE). Neither successful automation nor a preferred description guarantees recovery of undocumented historical rationale.

### 2. DocAgent: repository-aware inline docstring generation

Dayu Yang, Antoine Simoulin, Xin Qian, and collaborators produced DocAgent; the paper identifies work at Meta with author affiliations also including Apple and Google DeepMind. Navigator analysis orders code topologically; Reader, Searcher, Writer, Verifier, and Orchestrator roles generate Python docstrings. Read methodology, evaluation definitions, experiment setup, and result tables in [the ACL 2025 demonstration paper](https://aclanthology.org/2025.acl-demo.44.pdf).

For GPT-4o mini, reported completeness rises from 0.815 with snippet-based chat to 0.934 with DocAgent; helpfulness rises from 2.95 to 3.88. These measure documentation, using deterministic checks and model judging, rather than future edits. Checking whether mentioned entities exist cannot establish every semantic claim's truth. Dependency ordering is relevant to authoring; the inspected study does not establish successive-change maintenance. The [public implementation](https://github.com/facebookresearch/DocAgent) includes generation and evaluation entry points under an inspected [MIT license](https://raw.githubusercontent.com/facebookresearch/DocAgent/main/LICENSE). This is a close generation baseline, but inline docstrings are not equivalent to selective decision rationale.

### 3. CODEDOC: explicit quality criteria and dependency context

Tingxu Han, Wei Song, Ziming Li, and collaborators describe CODEDOC in an [October 20, 2026 preprint](https://arxiv.org/html/2610.27634v1). Read its definition, method, reported comparisons, and [artifact usage/evidence sections](https://github.com/ControllableModel/CodeDoc). It combines AST/call relationships with standards-derived requirements and judge feedback. Crucially, the README says it writes per-entity Markdown files: the paper's discussion of docstrings does not prove its implementation edits comments inline.

Across ten Python repositories, authors report documentation-quality improvements of 11.6–17.0% over RepoAgent and 21.4–29.6% over a long-context baseline, about an order of magnitude fewer tokens per entity than that baseline, and human/judge rank correlation of 0.72. Shared generation and judging criteria warrant independent downstream checks. This is generation-cost evidence, not cheaper subsequent coding. No longitudinal refresh result was established. The public repository advertises MIT, but the attempted raw license URL returned 404; licensing should be rechecked before reuse. Its criterion sets and comparison drivers are candidates to inspect, not endorsed requirements for Code Comments.

### 4. Google Code Wiki: a regenerated explanation layer

Google's announcement credits Fergus Hurley, Pedro Rodriguez, Rafael Marques, and Omar Shams. The system describes source-linked repository wikis, Gemini chat, and generated architecture/class/sequence diagrams, refreshed after code changes. Read the full [November 13, 2025 announcement](https://developers.googleblog.com/en/introducing-code-wiki-accelerating-your-code-understanding/).

This is a meaningful alternative: a derived explanation layer can reduce manual synchronization without making every external document a competing authority. The announcement supplies product descriptions and productivity claims, not a controlled comparison of editing outcomes or weaker models. Its CLI extension is described there as forthcoming; this reading does not establish its later availability. No reusable engine implementation or applicable engine license was verified. Code Comments should compare against effective regeneration where appropriate, rather than assume only manually maintained documents exist.

### 5. Cognition DeepWiki: hosted knowledge accessible to agents

Cognition's [DeepWiki launch](https://cognition.com/blog/deepwiki) describes the public counterpart of Devin Wiki/Search. The official [MCP announcement](https://cognition.com/blog/deepwiki-mcp-server) provides question answering, wiki contents, and structure access for indexed repositories. Read both announcements and the [CognitionAI README](https://github.com/CognitionAI/deepwiki/blob/main/README.md), which says repositories displaying its badge receive automatic refresh.

Its relevance is discoverability: an agent can retrieve external repository explanations through tools, so an inline-versus-doc comparison must account for retrieval access. These inspected sources provide no controlled longitudinal coding result, weaker-model comparison, or refresh accuracy measurement. The public README/MCP interface does not establish that the underlying generator is open source; third-party projects named DeepWiki must not be attributed to Cognition. This is a candidate service baseline, subject to version/freshness controls, rather than a reusable authoring engine established by this review.

### 6. Aider and Sourcegraph: derive navigable context from code

The Aider project sends a budgeted map of symbols and signatures, ranked through dependency relationships, alongside editing requests. Read its [repository-map documentation](https://aider.chat/docs/repomap.html), [tree-sitter design article](https://aider.chat/2023/10/22/repomap.html), and [FAQ](https://aider.chat/docs/faq.html). The FAQ explicitly reports weaker models becoming confused by maps and sometimes trying to edit them; this is implementation experience, not a controlled capability-stratified experiment. Generated structural context offers a baseline that avoids authoring prose for facts derivable from syntax. The [implementation is public](https://github.com/Aider-AI/aider); it was not run here.

Sourcegraph's team documents retrieval from search and a code graph containing definitions, references, symbols, and doc comments. Graph data can be refreshed through indexing or CI uploads. Read [Cody context](https://sourcegraph.com/docs/cody/core-concepts/context) and [code graph](https://sourcegraph.com/docs/cody/core-concepts/code-graph). These pages establish mechanisms, not comparative outcomes. For this project, both systems separate finding relationships from preserving reasons absent from code. A graph can complement useful comments; it is not necessarily an alternative store of the same truth.

### 7. ACE: maintain experience as evolving playbooks

Qizheng Zhang, Changran Hu, and collaborators at Stanford, SambaNova, and UC Berkeley present Agentic Context Engineering. Generation, reflection, and curation update playbooks through incremental changes rather than repeated wholesale summaries. Read method, benchmark setup, and cost discussions in [v3, March 29, 2026](https://arxiv.org/html/2510.04618v3). Its principal agent evaluation is AppWorld, with finance and other domain tasks, not successive repository edits. Reported agent improvements and matching a production leaderboard system with a smaller open model support investigating context adaptation, but not an inline-comment conclusion.

The [official repository](https://github.com/ace-agent/ace) exposes components and evaluation material under [Apache-2.0](https://raw.githubusercontent.com/ace-agent/ace/main/LICENSE.txt). Reuse candidates are incremental curation and comparison methods. A playbook may preserve procedures or cross-task experience that would be awkward to attach to one function. Code-level staleness and changing interface obligations remain separate questions.

### 8. REM: memory lifecycle can matter more than retrieval

Xinyi Lisa Chen, Pedro Herrero-Vidal, and collaborators report work performed at Amazon. REM stores phased summaries of completed trajectories, supplies a short document initially, gates detailed implementation records on failed validation, and removes that record after one exposure. Read methods, setup, results, and limitations in [v1, October 19, 2026](https://arxiv.org/html/2610.27377v1).

On 99 SWE-ContextBench Lite tasks, three Sonnet 4.5 replicates resolve 27.6% with REM versus 24.9% without memory. **The paired difference is not statistically significant: exact McNemar p=0.22.** Reported cost-weighted tokens fall 17%. Comparisons of retrieval accuracy reuse other systems' benchmark-reported configurations, rather than rerunning all under one retriever. The pool is fixed: authors explicitly leave evolving memories and aging fixes untested. Model-dependent harm also cautions against universal benefit. No public implementation/license was verified. This supplies lifecycle ideas and a qualified positive direction, not proof that cheaper agents can replace stronger ones or that inline knowledge survives maintenance.

### 9. MemUse: delivered memory may never influence useful work

Changran Xu, Zeju Li, and Qiang Xu propose evidence-linked evaluation of memory use in [Delivered, Not Used, v1, November 1, 2026](https://arxiv.org/html/2611.01718v1). Read methods, experiment setup, Table 2, and interpretation. Across 500 SWE-bench Verified tasks, mini-SWE-agent with gpt-6-luna runs four memory configurations four times: 8,000 memory episodes plus 2,000 baseline episodes. MemGovern, Mem0, and TencentDB provide contrasting retrieval/update mechanisms; writable stores accumulate across a historically ordered task sequence.

Resolve-rate differences remain within 0.4 percentage points, all reported 95% intervals include zero, and recorded episode costs rise 8.8–293.2%. The judge assesses relevance, novelty, influence, and observed effects; this is trajectory attribution, not randomized causal proof of individual entries. The authors identify provenance overlap between some MemGovern cards and benchmark repair material. No implementation/license was verified. This recent preprint argues for recording exposure and use separately from task success and testing an ordinary no-memory baseline. Its scope does not establish that all persistent context is ineffective.

### 10. Keep the Why: a directly relevant existing rationale skill

Oliver Zehentleitner's [Keep the Why](https://github.com/oliver-zehentleitner/keep-the-why) preserves decisions, rejected alternatives, constraints, and incidents in Git-tracked `context/` Markdown. Its [skill](https://raw.githubusercontent.com/oliver-zehentleitner/keep-the-why/main/skills/keep-the-why/SKILL.md) includes capture, historical recovery, interviews, and maintenance through contradiction resolution and supersession. Read those mode definitions and the experiment's [design](https://raw.githubusercontent.com/oliver-zehentleitner/keep-the-why/main/experiments/rejected-change/README.md) and [result summary](https://raw.githubusercontent.com/oliver-zehentleitner/keep-the-why/main/experiments/rejected-change/results/SUMMARY.md); individual transcripts were not audited.

Twenty fresh Claude Code/Sonnet 5 sessions tested one retry-wrapper fixture. Seven of ten controls offered an already-rejected change as an option, versus none with recorded rationale. **Neither arm broke the wrapper.** Median wall time was 43 versus 18 seconds. Both arms loaded the skill, so this isolates rationale availability in one fixture, not skill activation or inline placement. The artifact explicitly limits generalization. Its [MIT license](https://raw.githubusercontent.com/oliver-zehentleitner/keep-the-why/main/LICENSE) was inspected. This is the closest reusable rationale-preservation candidate found; an external context file can own unique historical knowledge rather than duplicate implementation.

### 11. Doxygen: one authored source, several presentations

The Doxygen project's [manual](https://www.doxygen.nl/manual/docblocks.html) explains how structured source comments become documentation; the [homepage](https://www.doxygen.nl/) lists generated formats and cross-references. Read the comment-block, placement, and output descriptions. Regenerating presentations from source comments eliminates manual synchronization between those presentations, although authors must still update incorrect comments. This mechanism is established tooling, not an LLM outcome study; no experiment was run here.

It challenges the premise that an external reference necessarily creates a second authored truth. Reusing extraction/rendering may serve both local editing and global explanation. It cannot recover a reason that was never recorded or certify arbitrary prose accuracy.

### 12. Python doctest: executable examples as maintained knowledge

Python's standard-library maintainers document [doctest](https://docs.python.org/3/library/doctest.html), which executes interactive examples in docstrings or text files and checks their expected output. Read the introduction, factorial example, and usage descriptions. Running examples supplies a mechanical maintenance signal that prose-only summaries lack.

This is an alternative for behavior that can be expressed through examples, not proof that examples communicate rejected alternatives or all valid inputs. An unchecked rationale sentence remains unchecked even when its neighboring example passes. No coding-agent performance or lifecycle-cost effect is established by the manual. Before inventing a prose validator, consider whether an existing executable example or acceptance test can own the behavioral claim.

## Implications for Code Comments

Our [historical review](historical-comment-design.md) supplies the background already read: Knuth separates authoring from generated presentations; Naur distinguishes possessing text from understanding change; Parnas emphasizes boundaries; Pike warns about undetected prose drift. The systems above make these tensions concrete without resolving them. This comparison does not claim a new reading of those full books.

A differentiated, still-unproven hypothesis is that **evidence-backed explanation at a consequential edit boundary preserves otherwise unavailable constraints across fresh sessions and successive changes, at lower total cost than equivalent external knowledge under comparable retrieval**. Tests must separate information from placement, and generation quality from later correctness. They should include stale and superseded knowledge, model capability, and the full writing/updating/retrieval/correction bill. The [evaluation protocol](evaluation-protocol.md) owns the experimental design.

Build-versus-reuse implications are conditional: inspect DocAgent/RepoAgent/CODEDOC for authoring and dependency machinery; Keep the Why for rationale capture and maintenance; ACE/REM for curation and delivery policies; MemUse for diagnostics; existing maps, generated wikis, and executable examples for alternatives. There is no reason yet to rebuild all of these mechanisms. Nor does their existence show that a portable inline skill has already achieved the project's combined outcome.

The narrow skill search found rationale instructions and Keep the Why, but no inspected artifact demonstrating equivalent-information inline placement, repeated maintenance, weaker-model gains, and end-to-end savings together. That is a scoped search result, not a novelty claim. `CodeResearch` resolved to an [open code-model research community](https://huggingface.co/CodeResearch), not a verified comment-maintenance system. SWE-agent search hits included interface documentation and memory extensions; these were not treated as evidence that the base agent already maintains project rationale. Global instruction files are another context location, covered in [coding-agent evidence](agent-context-evidence.md), rather than substitutes for every local or historical explanation.
