"""Persist intermediate ingest artifacts under data/ for demo inspection."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.config import CHUNKS_DIR, EMBEDDINGS_DIR, RAW_DIR


def _stem(scheme_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", scheme_name.lower()).strip("-") or "scheme"


def export_raw_documents(documents: list[dict[str, Any]], raw_dir: Path | None = None) -> list[Path]:
    """Write cleaned plain-text docs to data/raw/."""
    directory = raw_dir or RAW_DIR
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for doc in documents:
        path = directory / f"{_stem(doc['scheme_name'])}.txt"
        path.write_text(doc["text"], encoding="utf-8")
        paths.append(path)
    return paths


def export_chunks(chunks: list[dict[str, Any]], chunks_dir: Path | None = None) -> Path:
    """Write chunks as JSONL and a readable all_chunks.txt."""
    directory = chunks_dir or CHUNKS_DIR
    directory.mkdir(parents=True, exist_ok=True)

    all_jsonl = directory / "all_chunks.jsonl"
    with all_jsonl.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    by_scheme: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        by_scheme.setdefault(chunk["scheme_name"], []).append(chunk)

    for scheme_name, items in by_scheme.items():
        path = directory / f"{_stem(scheme_name)}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for chunk in items:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        # Per-scheme readable txt
        txt_path = directory / f"{_stem(scheme_name)}.txt"
        txt_path.write_text(_format_chunks_txt(items), encoding="utf-8")

    # Combined readable txt
    all_txt = directory / "all_chunks.txt"
    all_txt.write_text(_format_chunks_txt(chunks), encoding="utf-8")
    return all_txt


def _format_chunks_txt(chunks: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for chunk in chunks:
        blocks.append(
            "\n".join(
                [
                    "=" * 72,
                    f"chunk_id:     {chunk.get('id', '')}",
                    f"scheme_name:  {chunk.get('scheme_name', '')}",
                    f"category:     {chunk.get('category', '')}",
                    f"chunk_index:  {chunk.get('chunk_index', '')}",
                    f"source_url:   {chunk.get('source_url', '')}",
                    f"ingested_at:  {chunk.get('ingested_at', '')}",
                    f"char_len:     {len(chunk.get('text', '') or '')}",
                    "-" * 72,
                    "TEXT:",
                    chunk.get("text", "") or "",
                    "",
                ]
            )
        )
    return "\n".join(blocks)


def export_embeddings_txt(
    records: list[dict[str, Any]],
    *,
    embeddings_dir: Path | None = None,
    model_name: str = "",
) -> Path:
    """
    Write human-readable embedding dumps.

    Each record needs: id, text, scheme_name, category, chunk_index,
    source_url, embedding (list[float]).
    """
    directory = embeddings_dir or EMBEDDINGS_DIR
    directory.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "HDFC MF RAG — chunk embeddings (readable dump)",
        f"model: {model_name}",
        f"total_vectors: {len(records)}",
        f"dims: {len(records[0]['embedding']) if records else 0}",
        "",
    ]

    by_scheme: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_scheme.setdefault(str(rec.get("scheme_name", "unknown")), []).append(rec)

    for rec in records:
        emb = rec["embedding"]
        preview = (rec.get("text") or "").replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "..."
        vector_str = ", ".join(f"{float(x):.6f}" for x in emb)
        lines.extend(
            [
                "=" * 72,
                f"chunk_id:     {rec.get('id', '')}",
                f"scheme_name:  {rec.get('scheme_name', '')}",
                f"category:     {rec.get('category', '')}",
                f"chunk_index:  {rec.get('chunk_index', '')}",
                f"source_url:   {rec.get('source_url', '')}",
                f"dims:         {len(emb)}",
                f"text_preview: {preview}",
                "-" * 72,
                "FULL_TEXT:",
                rec.get("text", "") or "",
                "-" * 72,
                "EMBEDDING_VECTOR:",
                vector_str,
                "",
            ]
        )

    all_path = directory / "all_embeddings.txt"
    all_path.write_text("\n".join(lines), encoding="utf-8")

    for scheme_name, items in by_scheme.items():
        scheme_lines: list[str] = [
            f"scheme: {scheme_name}",
            f"model: {model_name}",
            f"vectors: {len(items)}",
            f"dims: {len(items[0]['embedding']) if items else 0}",
            "",
        ]
        for rec in items:
            emb = rec["embedding"]
            vector_str = ", ".join(f"{float(x):.6f}" for x in emb)
            scheme_lines.extend(
                [
                    "=" * 72,
                    f"chunk_id:    {rec.get('id', '')}",
                    f"chunk_index: {rec.get('chunk_index', '')}",
                    f"dims:        {len(emb)}",
                    "-" * 72,
                    "FULL_TEXT:",
                    rec.get("text", "") or "",
                    "-" * 72,
                    "EMBEDDING_VECTOR:",
                    vector_str,
                    "",
                ]
            )
        (directory / f"{_stem(scheme_name)}.txt").write_text(
            "\n".join(scheme_lines), encoding="utf-8"
        )

    # Compact one-vector-per-line index (easier to skim dims)
    index_path = directory / "embeddings_index.txt"
    index_lines = [
        f"model={model_name}",
        "format: chunk_id | scheme | chunk_index | dims | first_8_values ...",
        "",
    ]
    for rec in records:
        emb = rec["embedding"]
        head = ", ".join(f"{float(x):.4f}" for x in emb[:8])
        index_lines.append(
            f"{rec.get('id', '')} | {rec.get('scheme_name', '')} | "
            f"{rec.get('chunk_index', '')} | {len(emb)} | [{head}, ...]"
        )
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    return all_path
