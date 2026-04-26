# DeepRead: Document Structure-Aware Reasoning to Enhance Agentic Search

<p align="center">
    <a href='https://arxiv.org/abs/2602.05014'><img src='https://img.shields.io/badge/arXiv-2602.05014-b31b1b'></a>
    <a href="https://github.com/Zhanli-Li/DeepRead/blob/main/LICENSE">
        <img height="21" src="https://img.shields.io/badge/License-Apache--2.0-ffffff?labelColor=d4eaf7&color=2e6cc4" alt="license">
    </a>
    <a href="https://deepwiki.com/Zhanli-Li/DeepRead"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</p>
<div style="text-align:center;">
    <img src="fig/DeepRead.png" alt="main fig" width="100%">
</div>

DeepRead is a document-structure-aware RAG agent. The code is organized around four explicit runtime boundaries: `agent`, `index`, `prompt`, and `tool`.

## Repository Layout
- `agent/`: CLI, LLM HTTP client, logging, and the agent loop.
- `index/`: document preprocessing: PDF OCR, Markdown parsing, corpus generation, and embedding index building.
- `prompt/`: system prompt construction.
- `tool/`: agent-callable tools. Each tool has its own file: `read_section.py`, `bm25_search.py`, `regex_search.py`, `vector_search.py`, `hybrid_search.py`, `semantic_retrieval.py`.
- `deepread.py`: unified command entrypoint.
- `index/paddleocr.sh`: Docker launcher for the PaddleOCRVL vLLM server used by PDF preprocessing.
- `demo/`: demo corpora and local embedding files.

## News
- **2026.4.27** 🎉 We have refactored DeepRead's code to make it easier for you to use, develop, and maintain!
- **2026.3.16** 🔥 DeepRead has been featured in [New Intelligence (新智元)](https://mp.weixin.qq.com/s/BhvUQgREp4NOvb6axiWXiQ)!

## Quickstart
### 1) Environment
```bash
export OPENROUTER_API_KEY="<YOUR_OPENROUTER_KEY>"
export OPENROUTER_BASE_URL="https://api.openai.com/v1"
export OPENROUTER_MODEL="gpt-4o"

# Optional: embedding service
export EMBED_API_KEY="<YOUR_EMBEDDING_KEY>"
export EMBED_BASE_URL="http://127.0.0.1:8756/v1"
export EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"

# Optional: reranker service
export RERANK_API_KEY="<YOUR_RERANK_KEY>"
export RERANK_BASE_URL="https://api.siliconflow.cn/v1"
export RERANK_MODEL="Qwen/Qwen3-Reranker-8B"
```

### 2) Parse a Document
For PDFs, we recommend using PaddleOCRVL. It preserves document layout signals such as headings, tables, images, and reading order better than plain text extraction. DeepRead first converts the PDF to Markdown, then converts that Markdown into the structured `*_corpus.json` used by the agent.

```bash
bash index/paddleocr.sh

python deepread.py parse /path/to/doc.pdf -o /path/to/output --name doc
```

If you already have a parsed Markdown file, you can skip OCR and convert it directly into DeepRead format:
```bash
python deepread.py parse /path/to/doc.md -o /path/to/output --name doc
```

The Markdown parser recognizes headings as document nodes, keeps HTML/pipe tables as paragraph blocks, and records Markdown/HTML images as image paragraphs when present.

Build embeddings during parsing:
```bash
python deepread.py parse /path/to/doc.md \
  -o /path/to/output \
  --name doc \
  --build-embeddings \
  --embedding-model Qwen/Qwen3-Embedding-8B \
  --embed-base-url http://127.0.0.1:8756/v1 \
  --embed-api-key <YOUR_KEY>
```

Outputs include:
- `doc.md`
- `doc_corpus.json`
- `doc_emb.npy` and `doc_idmap.json` when `--build-embeddings` is enabled

### 3) Ask Questions
BM25 works without embeddings:
```bash
python deepread.py ask /path/to/output/doc_corpus.json "What is the question?"
```

Vector, hybrid, and semantic modes are available through a single shortcut:
```bash
python deepread.py ask /path/to/output/doc_corpus.json "What is the question?" --retrieval vector
python deepread.py ask /path/to/output/doc_corpus.json "What is the question?" --retrieval hybrid
python deepread.py ask /path/to/output/doc_corpus.json "What is the question?" --retrieval semantic
```

Neighbor expansion:
```bash
python deepread.py ask /path/to/output/doc_corpus.json "What is the question?" --neighbor-window 1,-1
```

## Retrieval Modes
DeepRead exposes several retrieval tools. The shortcut `--retrieval` selects the common mode, but the underlying tools can still be enabled or disabled independently.

### BM25
`--retrieval bm25` uses lexical BM25 over paragraph text. It does not need embeddings or a reranker, so it is the default and the safest mode for a fresh corpus.

```bash
python deepread.py ask doc_corpus.json "..." --retrieval bm25
```

Useful options:
- `--bm25-topk`: number of BM25 hits returned to the agent per tool call.
- `--disable-regex`: disables regex search if you want BM25-only behavior.

### Regex
Regex search is enabled by default unless `--disable-regex` is passed. It is useful when the agent needs exact names, numbers, codes, dates, or table labels. It is not selected by `--retrieval`; it is an additional tool available to the agent.

```bash
python deepread.py ask doc_corpus.json "..." --retrieval bm25 --disable-regex
```

Useful option:
- `--regex-topk`: number of regex hits returned per tool call.

### Vector
`--retrieval vector` is a single-stage embedding retrieval mode. The question is embedded once, then compared with the corpus embedding matrix by cosine similarity. This requires a corpus built with `--build-embeddings` and an embedding API for query embedding at ask time.

```bash
python deepread.py ask doc_corpus.json "..." --retrieval vector
```

Equivalent lower-level behavior:
- enables `vector_search`
- disables BM25 and regex shortcuts for a vector-only run

Useful options:
- `--vector-topk`: number of vector hits returned per tool call.
- `--embedding-model`, `--embed-base-url`, `--embed-api-key`: query embedding service configuration.

### Hybrid
`--retrieval hybrid` fuses BM25 and vector results. It first retrieves candidates from BM25 and vector search, normalizes the two score lists, then combines them using configurable weights. This is useful when you want lexical precision and semantic recall together.

```bash
python deepread.py ask doc_corpus.json "..." --retrieval hybrid
```

Useful options:
- `--hybrid-topk`: final number of fused hits returned.
- `--hybrid-topk-bm25`: BM25 candidate pool size before fusion.
- `--hybrid-topk-vec`: vector candidate pool size before fusion.
- `--hybrid-bm25-weight`: BM25 score weight, default `0.5`.
- `--hybrid-vector-weight`: vector score weight, default `0.5`.

### Semantic
`--retrieval semantic` is a two-stage retrieval mode:
1. Stage 1 recall gets candidates using `vector`, `bm25`, or `hybrid`.
2. Stage 2 rerank calls the reranker API and returns the top reranked passages.

By default, stage 1 is `vector`. Change it with `--semantic-stage1`.

```bash
python deepread.py ask doc_corpus.json "..." \
  --retrieval semantic \
  --semantic-stage1 vector
```

Use BM25 as stage 1 if you do not want embedding recall:
```bash
python deepread.py ask doc_corpus.json "..." \
  --retrieval semantic \
  --semantic-stage1 bm25
```

Use hybrid as stage 1:
```bash
python deepread.py ask doc_corpus.json "..." \
  --retrieval semantic \
  --semantic-stage1 hybrid \
  --semantic-stage1-hybrid-topk-bm25 50 \
  --semantic-stage1-hybrid-topk-vec 50
```

Useful options:
- `--semantic-topk1`: stage 1 candidate count before rerank.
- `--semantic-topk2`: final reranked hit count returned to the agent.
- `--semantic-stage1 vector|bm25|hybrid`: recall method used before reranking.
- `--rerank-api-key`, `--rerank-base-url`, `--rerank-model`: reranker service configuration.

If the reranker call fails, DeepRead falls back to the stage 1 order and records the rerank error in the log.

### Neighbor Window
`--neighbor-window up,down` expands each retrieved paragraph with nearby paragraphs from the same node. For example, `1,-1` adds one paragraph above and one below each hit. Use `0,0` to disable neighbor expansion.

```bash
python deepread.py ask doc_corpus.json "..." --neighbor-window 1,-1
```

## Demo
```bash
python deepread.py ask \
  demo/TradingAgent/TradingAgent_corpus.json \
  "Which roles are included in the overall TradingAgents framework?" \
  --retrieval semantic \
  --enable-multimodal \
  --log demo_trading.jsonl
```

```bash
python deepread.py ask \
  "demo/金山办公2023年报/11724-金山办公：金山办公2023年年度报告_corpus.json" \
  "公司有哪些累计投入金额超过一亿元的在研项目？" \
  --retrieval semantic \
  --neighbor-window 0,0 \
  --log demo_xx.jsonl
```

## Full Usage
```bash
python deepread.py --help
python deepread.py parse --help
python deepread.py ask --help
```

Common `ask` options:
- `--retrieval bm25|vector|hybrid|semantic`
- `--neighbor-window up,down`
- `--enable-multimodal`
- `--model`, `--base-url`, `--api-key`
- `--embedding-model`, `--embed-base-url`, `--embed-api-key`
- `--rerank-api-key`, `--rerank-base-url`, `--rerank-model`

## Notes
- Markdown is converted directly into DeepRead's structured corpus.
- PDF parsing requires `paddleocr` and `PaddleOCRVL`, or the Docker server launched by `index/paddleocr.sh`.
- `tiktoken` is optional; token counting falls back to a simple tokenizer when unavailable.

## Related Work
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [PageIndex](https://github.com/VectifyAI/PageIndex)

## Citation
If DeepRead is helpful, please cite:
```bibtex
@article{li2026deepread,
  title={DeepRead: Document Structure-Aware Reasoning to Enhance Agentic Search},
  author={Li, Zhanli and Tian, Huiwen and Luo, Lvzhou and Cao, Yixuan and Luo, Ping},
  journal={arXiv preprint arXiv:2602.05014},
  year={2026}
}
```

## License
See [LICENSE](LICENSE).
