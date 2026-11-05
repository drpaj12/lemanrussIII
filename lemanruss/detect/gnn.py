"""Gate-level GNN detectors (spec 4.3), PyTorch Geometric, CPU only.

`gnn-yasaei`: as read in yasaei2022gnn (arXiv 2204.11431): one-hot node class (17), three GCN
layers of 55 units, self-attention graph pooling ratio 0.6, max readout, MLP, dropout 0.5.
`gnn-a`: Method A of s6-methods.tex: GraphSAGE x3, 64 units, mean+max readout, features with
SCOAP and signal probability.
Epochs, batch size and seeds are reduced from the paper defaults to fit the CPU budget; the values
used are written next to every result (Settings).
"""

from __future__ import annotations

import os
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from lemanruss.detect import metrics
from lemanruss.detect.api import Detector
from lemanruss.detect.data import CircuitFile
from lemanruss.detect.features import cached, fill, sha256_of
from lemanruss.detect.isolated import isolated
from lemanruss.detect.netlist import N_CLASSES, Netlist, parse
from lemanruss.detect.scoap_feat import ScoapFeat


@dataclass(frozen=True)
class Settings:
    epochs: int
    batch: int
    lr: float = 1e-3

    @staticmethod
    def from_env(name: str) -> Settings:
        if name == "gnn-yasaei":
            return Settings(int(os.environ.get("LEMANRUSS_EPOCHS", "200")),
                            int(os.environ.get("LEMANRUSS_BATCH", "2")))
        return Settings(int(os.environ.get("LEMANRUSS_EPOCHS", "200")),
                        int(os.environ.get("LEMANRUSS_BATCH", "32")))


def parse_nl(path: Path) -> Netlist:
    return parse(path)


def scoap_for(path: Path) -> ScoapFeat | None:
    out = isolated("scoap", path)
    return out if isinstance(out, ScoapFeat) else None


def node_features(nl: Netlist, sc: ScoapFeat | None) -> np.ndarray:
    """Feature matrix. Without `sc`: the 17-class one-hot only (yasaei). With `sc`: Method A."""
    n = nl.n_nodes
    onehot = np.zeros((n, N_CLASSES), dtype=np.float32)
    onehot[np.arange(n), nl.cls] = 1.0
    if sc is None:
        return onehot
    indeg = np.bincount(nl.dst, minlength=n).astype(np.float32)
    outdeg = np.bincount(nl.src, minlength=n).astype(np.float32)
    lut_k = np.where(nl.rows > 0, nl.k, 0).astype(np.float32)
    idx = {name: i for i, name in enumerate(sc.names)}
    cc0 = np.zeros(n, dtype=np.float32)
    cc1 = np.zeros(n, dtype=np.float32)
    co = np.zeros(n, dtype=np.float32)
    p1 = np.full(n, 0.5, dtype=np.float32)
    have = np.zeros(n, dtype=np.float32)
    for v, net in enumerate(nl.net_of):
        j = idx.get(net)
        if j is None:
            continue
        cc0[v], cc1[v], co[v] = np.log1p(sc.cc0[j]), np.log1p(sc.cc1[j]), np.log1p(sc.co[j])
        if not np.isnan(sc.p1[j]):
            p1[v] = sc.p1[j]
        have[v] = 1.0
    # primary outputs carry no net of their own: borrow nothing, flag them by class one-hot
    extra = np.stack([
        np.log1p(indeg), np.log1p(outdeg), lut_k / 6.0, np.log1p(nl.rows.astype(np.float32)) / 4.0,
        cc0 / 10.0, cc1 / 10.0, co / 10.0, p1, have,
    ], axis=1).astype(np.float32)
    return np.hstack([onehot, extra])


class GnnDetector(Detector):
    seeded = True

    def __init__(self, name: str) -> None:
        self.name = name
        self.cfg = Settings.from_env(name)
        self.use_scoap = name == "gnn-a"
        self.ablate = name == "gnn-a-nosc"  # Method A features without SCOAP and probability
        self.graphs: dict[str, Any] = {}
        self.model: Any = None

    def prepare(self, circuits: Sequence[CircuitFile]) -> None:
        fill("nl", circuits, parse_nl)
        if self.use_scoap:
            fill("scoap", circuits, scoap_for)

    def _graph(self, cf: CircuitFile) -> Any | None:
        import torch
        from torch_geometric.data import Data

        # Keyed by the circuit file's own content hash, not cf.id (Peter 2026-11-02): an id is
        # assigned per release/style and is not unique across them, so two different circuits
        # from two releases/styles sharing an id must not share a graph.
        key = sha256_of(cf.path)
        g = self.graphs.get(key)
        if g is None:
            nl = cached("nl", cf, parse_nl)
            sc = cached("scoap", cf, scoap_for) if self.use_scoap else None
            if self.use_scoap and sc is None:
                return None  # Odin III timed out or refused: not scored
            if self.ablate:
                z = np.zeros(0)
                sc = ScoapFeat([], z, z, z, z, False, False)
            x = torch.from_numpy(node_features(nl, sc))
            ei = torch.from_numpy(np.stack([nl.src, nl.dst])).long()
            g = Data(x=x, edge_index=ei)
            self.graphs[key] = g
        return g

    def _build(self, in_dim: int) -> Any:
        import torch
        from torch import nn
        from torch_geometric.nn import (
            GCNConv,
            SAGEConv,
            SAGPooling,
            global_max_pool,
            global_mean_pool,
        )

        yasaei = self.name == "gnn-yasaei"
        hid = 55 if yasaei else 64

        class Net(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                pairs = [(in_dim, hid), (hid, hid), (hid, hid)]
                if yasaei:
                    self.convs = nn.ModuleList(GCNConv(a, b) for a, b in pairs)
                    self.pool = SAGPooling(hid, ratio=0.6)
                    self.head = nn.Sequential(nn.Linear(hid, 2))
                else:
                    self.convs = nn.ModuleList(SAGEConv(a, b) for a, b in pairs)
                    self.head = nn.Sequential(
                        nn.Linear(2 * hid, hid), nn.ReLU(), nn.Dropout(0.5), nn.Linear(hid, 2)
                    )

            def forward(self, data: Any) -> Any:
                x, ei, b = data.x, data.edge_index, data.batch
                for conv in self.convs:
                    x = torch.nn.functional.dropout(
                        torch.relu(conv(x, ei)), 0.5, training=self.training)
                if yasaei:
                    x, ei, _, b, _, _ = self.pool(x, ei, batch=b)
                    h = global_max_pool(x, b)
                else:
                    h = torch.cat([global_mean_pool(x, b), global_max_pool(x, b)], dim=1)
                return self.head(h)

        return Net()

    def _logits(self, model: Any, graphs: list[Any], batch: int) -> np.ndarray:
        import torch
        from torch_geometric.loader import DataLoader

        model.eval()
        out: list[float] = []
        with torch.no_grad():
            for data in DataLoader(graphs, batch_size=batch, shuffle=False):
                lg = model(data)
                out += (lg[:, 1] - lg[:, 0]).tolist()
        return np.array(out)

    def fit(self, train: Sequence[CircuitFile], y_train: Sequence[int],
            val: Sequence[CircuitFile], y_val: Sequence[int], seed: int) -> None:
        import copy

        import torch
        from torch_geometric.data import Data
        from torch_geometric.loader import DataLoader

        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)
        torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "4")))
        pairs = list(zip(train, y_train, strict=True))
        cap = int(os.environ.get("LEMANRUSS_MAX_TRAIN", "0"))
        if cap and len(pairs) > cap:  # CPU budget: a seeded random subset of the training set
            pairs = random.Random(1000 + seed).sample(pairs, cap)
        tr_all = [(self._graph(c), y) for c, y in pairs]
        va_all = [(self._graph(c), y) for c, y in zip(val, y_val, strict=True)]
        gtr = [g for g, _ in tr_all if g is not None]
        y_train = [y for g, y in tr_all if g is not None]
        gva = [g for g, _ in va_all if g is not None]
        y_val = [y for g, y in va_all if g is not None]
        gtr = [Data(x=g.x, edge_index=g.edge_index, y=torch.tensor([y]))
               for g, y in zip(gtr, y_train, strict=True)]
        if not gtr:
            raise ValueError(
                f"{self.name}: no training graph could be built ({len(pairs)} circuits; Odin III "
                "SCOAP unavailable, timed out or refused on all of them)")
        in_dim = gtr[0].x.shape[1]
        model = self._build(in_dim)
        n_pos = max(sum(y_train), 1)
        n_neg = max(len(y_train) - n_pos, 1)
        w = torch.tensor([0.5 / n_neg, 0.5 / n_pos]) * len(y_train)  # equalise the classes
        opt = torch.optim.Adam(model.parameters(), lr=self.cfg.lr)
        gen = torch.Generator().manual_seed(seed)
        best, best_state = -1.0, None
        for _epoch in range(self.cfg.epochs):
            model.train()
            for data in DataLoader(gtr, batch_size=self.cfg.batch, shuffle=True,
                                   generator=gen):
                opt.zero_grad()
                loss = torch.nn.functional.cross_entropy(model(data), data.y, weight=w)
                loss.backward()
                opt.step()
            a = metrics.auroc(self._logits(model, gva, self.cfg.batch).tolist(), list(y_val))
            if a is not None and a > best:
                best, best_state = a, copy.deepcopy(model.state_dict())
        if best_state is not None:
            model.load_state_dict(best_state)
        self.model = model

    def score(self, circuits: Sequence[CircuitFile]) -> list[float]:
        assert self.model is not None
        graphs = [self._graph(c) for c in circuits]
        ok = [g for g in graphs if g is not None]
        vals = iter(self._logits(self.model, ok, self.cfg.batch).tolist() if ok else [])
        return [float("nan") if g is None else float(next(vals)) for g in graphs]


def make_gnn(name: str) -> GnnDetector:
    return GnnDetector(name)
