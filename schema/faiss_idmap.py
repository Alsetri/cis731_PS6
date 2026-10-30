"""
CIS 731 — PS 6: the FAISS int64-id to chunk_id mapping layer.

FAISS addresses vectors by non-negative int64. Our chunk_id is a 256-bit
SHA-256 digest. Something has to bridge them, and the bridge is where most
orphan-vector bugs live, so it is specified rather than improvised.

Mapping
    faiss_id = int(chunk_id[:16], 16) & 0x7FFF_FFFF_FFFF_FFFF
    i.e. the leading 64 bits of the digest, masked to 63 bits because FAISS
    reserves negative ids to mean "not found".

Collision risk
    63 usable bits, N = 120,000 vectors. By the birthday bound the collision
    probability is about N^2 / 2^64 = 1.44e10 / 1.84e19 ~= 7.8e-10. That is
    small, not zero, and a silent collision would hand a searcher the wrong
    document with full confidence. build_idmap therefore CHECKS for collisions
    rather than relying on the estimate.

Update and delete semantics (the part that bites)
    IndexIDMap2.add_with_ids does NOT replace an existing id. Calling it twice
    with the same id leaves TWO vectors under that id, and a search can return
    the stale one. Update must therefore be remove_ids followed by
    add_with_ids. This module demonstrates both behaviours rather than
    asserting them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import faiss
import numpy as np

ID_MASK = 0x7FFF_FFFF_FFFF_FFFF


def chunk_id_to_faiss_id(chunk_id: str) -> int:
    return int(chunk_id[:16], 16) & ID_MASK


def build_idmap(chunk_ids: list[str]) -> dict[int, str]:
    """int64 -> chunk_id sidecar, with an explicit collision check."""
    idmap: dict[int, str] = {}
    for cid in chunk_ids:
        fid = chunk_id_to_faiss_id(cid)
        if fid in idmap and idmap[fid] != cid:
            raise ValueError(
                f"int64 id collision: {fid} claimed by {idmap[fid]} and {cid}. "
                "Widen the id or switch to a sequential counter with a "
                "persisted mapping."
            )
        idmap[fid] = cid
    return idmap


def demo(n: int = 20_000, d: int = 384, seed: int = 20261027) -> dict:
    """Exercise add / search / update / delete and report what FAISS does."""
    rng = np.random.default_rng(seed)
    chunk_ids = [
        hashlib.sha256(f"genius:doc{i:06d}|0|v1.0.0".encode()).hexdigest()
        for i in range(n)
    ]
    idmap = build_idmap(chunk_ids)
    fids = np.array([chunk_id_to_faiss_id(c) for c in chunk_ids], dtype="int64")

    xb = rng.normal(size=(n, d)).astype("float32")
    xb /= np.linalg.norm(xb, axis=1, keepdims=True)

    index = faiss.IndexIDMap2(faiss.IndexFlatIP(d))
    index.add_with_ids(xb, fids)

    out: dict = {
        "n_vectors": n, "d": d,
        "distinct_faiss_ids": len(idmap),
        "collisions": n - len(idmap),
        "ntotal_after_add": index.ntotal,
    }

    # --- reconstruct: IndexIDMap2 (unlike IndexIDMap) can return the vector
    probe = int(fids[7])
    rec = index.reconstruct(probe)
    out["reconstruct_matches_original"] = bool(
        np.allclose(rec, xb[7], atol=1e-6)
    )

    # --- THE TRAP: add_with_ids on an existing id does not replace
    replacement = rng.normal(size=(1, d)).astype("float32")
    replacement /= np.linalg.norm(replacement)
    index.add_with_ids(replacement, np.array([probe], dtype="int64"))
    out["naive_readd"] = {
        "ntotal": index.ntotal,
        "grew_by": index.ntotal - n,
        "verdict": "add_with_ids DUPLICATED the id instead of replacing it"
        if index.ntotal > n else "replaced in place",
    }

    # --- the correct update: remove then add
    index.remove_ids(np.array([probe], dtype="int64"))
    after_remove = index.ntotal
    index.add_with_ids(replacement, np.array([probe], dtype="int64"))
    out["correct_update"] = {
        "ntotal_after_remove_all_copies": after_remove,
        "ntotal_after_readd": index.ntotal,
        "net_vs_original": index.ntotal - n,
        "note": "remove_ids removes EVERY copy of the id, so the duplicate "
                "created above is cleaned up in the same call",
    }
    out["update_reconstruct_is_new_vector"] = bool(
        np.allclose(index.reconstruct(probe), replacement[0], atol=1e-6)
    )

    # --- delete
    victim = int(fids[11])
    index.remove_ids(np.array([victim], dtype="int64"))
    out["after_delete_ntotal"] = index.ntotal
    try:
        index.reconstruct(victim)
        out["deleted_id_still_reconstructs"] = True
    except RuntimeError:
        out["deleted_id_still_reconstructs"] = False

    # Deleting from FAISS does not delete the sidecar entry; forgetting that
    # second step is exactly how an orphan is created.
    idmap.pop(victim, None)
    out["sidecar_entries_after_delete"] = len(idmap)
    out["orphan_check"] = {
        "faiss_ntotal": index.ntotal,
        "sidecar_size": len(idmap),
        "in_bijection": index.ntotal == len(idmap),
    }
    return out


if __name__ == "__main__":
    r = demo()
    Path("out").mkdir(exist_ok=True)
    Path("out/faiss_idmap.json").write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))
