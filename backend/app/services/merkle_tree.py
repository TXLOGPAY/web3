"""Merkle Tree implementation for trade data integrity anchoring."""
import hashlib
import json
from typing import Any


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _hash_leaf(value: str) -> bytes:
    """Hash a single leaf value (prefixed to prevent second pre-image attacks)."""
    return _sha256(b"\x00" + value.encode("utf-8"))


def _hash_nodes(left: bytes, right: bytes) -> bytes:
    """Hash two child nodes together (prefixed)."""
    return _sha256(b"\x01" + left + right)


class MerkleTree:
    """Binary Merkle Tree for trade document data."""

    def __init__(self, leaves: list[str]):
        if not leaves:
            raise ValueError("At least one leaf is required")
        self.leaves_raw = leaves
        self.leaf_hashes = [_hash_leaf(leaf) for leaf in leaves]
        self.root = self._build_root(self.leaf_hashes)

    def _build_root(self, nodes: list[bytes]) -> bytes:
        if len(nodes) == 1:
            return nodes[0]

        # Pad with duplicate of last element if odd count
        if len(nodes) % 2 == 1:
            nodes = nodes + [nodes[-1]]

        next_level = []
        for i in range(0, len(nodes), 2):
            next_level.append(_hash_nodes(nodes[i], nodes[i + 1]))

        return self._build_root(next_level)

    @property
    def root_hex(self) -> str:
        return self.root.hex()

    @property
    def root_bytes(self) -> bytes:
        return self.root

    def get_proof(self, leaf_index: int) -> list[dict]:
        """Generate Merkle proof for a leaf at given index."""
        proof = []
        nodes = list(self.leaf_hashes)
        idx = leaf_index

        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes = nodes + [nodes[-1]]

            if idx % 2 == 0:
                sibling_idx = idx + 1
                proof.append({"hash": nodes[sibling_idx].hex(), "position": "right"})
            else:
                sibling_idx = idx - 1
                proof.append({"hash": nodes[sibling_idx].hex(), "position": "left"})

            next_level = []
            for i in range(0, len(nodes), 2):
                next_level.append(_hash_nodes(nodes[i], nodes[i + 1]))

            nodes = next_level
            idx //= 2

        return proof

    def verify_proof(self, leaf_value: str, proof: list[dict], root_hex: str) -> bool:
        """Verify that a leaf is part of the tree given a proof."""
        current = _hash_leaf(leaf_value)
        for step in proof:
            sibling = bytes.fromhex(step["hash"])
            if step["position"] == "right":
                current = _hash_nodes(current, sibling)
            else:
                current = _hash_nodes(sibling, current)
        return current.hex() == root_hex


def build_trade_merkle_tree(trade_data: dict[str, Any]) -> MerkleTree:
    """Build a Merkle tree from a trade record dictionary."""
    leaves = []
    for key in sorted(trade_data.keys()):
        value = trade_data[key]
        leaves.append(f"{key}:{json.dumps(value, ensure_ascii=False, sort_keys=True)}")
    return MerkleTree(leaves)


def compute_merkle_root(trade_data: dict[str, Any]) -> str:
    """Quick helper: compute and return the hex root from trade data."""
    tree = build_trade_merkle_tree(trade_data)
    return tree.root_hex
