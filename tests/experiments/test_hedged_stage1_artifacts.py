"""Grids and artifact writing for hedged-placement Stage 1 (prereg §6, §11).

Build verification never evaluates the deciding grids (§11); these tests
check grid construction, row machinery on synthetic cells, and the writer's
determinism and byte-identity.
"""

import json

from scripts.hedged_placement_stage1 import (
    Cell,
    battery_rows,
    quality_grid,
    resolve_run_dir,
    survival_grid,
    write_artifacts,
)


class TestGrids:
    def test_survival_grid_is_1620_cells(self):
        cells = survival_grid()
        assert len(cells) == 1620
        assert len(set(cells)) == 1620  # no duplicates

    def test_survival_cells_hold_quality_flat_high(self):
        for cell in survival_grid():
            assert cell.flat_high_quality
            assert cell.a_0 == 1.0 and cell.a_1 == 1.0
            assert cell.delta_clone == 0.0 and cell.rho_q == 0.0

    def test_survival_axes_match_prereg(self):
        cells = survival_grid()
        assert {c.p_c for c in cells} == {0.50, 0.80, 0.95}
        assert {c.q_k for c in cells} == {0.90, 0.99, 1.00}
        assert {(c.rho_c, c.rho_l) for c in cells} == {
            (0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.5, 0.5), (1.0, 1.0)
        }
        assert {c.rho_k for c in cells} == {0.0, 1.0}
        assert {c.g for c in cells} == {0.0, 0.10}
        assert {c.a_e for c in cells} == {0.70, 0.90, 1.00}

    def test_quality_grid_is_540_cells(self):
        cells = quality_grid()
        assert len(cells) == 540
        assert len(set(cells)) == 540

    def test_quality_cells_hold_prereg_constants(self):
        for cell in quality_grid():
            assert not cell.flat_high_quality
            assert cell.q_k == 0.99 and cell.rho_k == 0.0 and cell.g == 0.0
            assert cell.a_0 == 0.60

    def test_quality_axes_match_prereg(self):
        cells = quality_grid()
        profiles = {(c.p_c, c.p_l, c.rho_c, c.rho_l) for c in cells}
        assert profiles == {
            (0.50, 0.90, 0.0, 0.0),
            (0.90, 0.50, 0.0, 0.0),
            (0.80, 0.80, 0.0, 0.0),
            (0.80, 0.80, 1.0, 1.0),
            (0.95, 0.95, 0.0, 0.0),
        }
        assert {c.a_1 for c in cells} == {0.50, 0.70, 0.90, 1.00}
        assert {c.delta_clone for c in cells} == {0.00, 0.10, 0.20}
        assert {c.rho_q for c in cells} == {0.0, 0.5, 1.0}


class TestBatteryRows:
    def test_row_carries_params_stats_activation_and_label(self):
        cell = Cell(
            p_c=0.5, p_l=1.0, q_k=1.0, rho_c=0.0, rho_l=0.0, rho_k=0.0,
            g=0.0, a_e=1.0, rho_q=0.0, a_0=1.0, a_1=1.0, delta_clone=0.0,
            flat_high_quality=True,
        )
        rows = battery_rows([cell], quality_pass=False)
        assert len(rows) == 1
        row = rows[0]
        assert row["param.p_c"] == 0.5
        assert abs(row["delta_m"] - 0.375) < 1e-12
        assert row["activated"] is True
        assert row["refusal_reason"] == ""
        assert row["label"] == "POSITIVE"
        assert row["balance_error"] < 1e-12

    def test_silenced_cell_is_refused_not_labeled(self):
        cell = Cell(
            p_c=0.8, p_l=0.8, q_k=0.99, rho_c=1.0, rho_l=1.0, rho_k=0.0,
            g=0.0, a_e=0.9, rho_q=0.0, a_0=1.0, a_1=1.0, delta_clone=0.0,
            flat_high_quality=True,
        )
        row = battery_rows([cell], quality_pass=False)[0]
        assert row["activated"] is False
        assert row["refusal_reason"].startswith("CHANNEL_SILENCED")
        assert row["label"] == ""


class TestWriter:
    def _tiny_inputs(self):
        manifest = {
            "preregistration_commit": "ca262178b327d5657973054cb06049c0050a568f",
            "implementation_commit": "deadbeef",
            "source_sha256": "abc123",
            "grids": {"survival_cells": 2, "quality_cells": 1},
        }
        controls = {"probability_balance": {"passed": True}}
        srows = [
            {"param.p_c": 0.5, "delta_m": 0.375, "activated": True,
             "refusal_reason": "", "label": "POSITIVE", "balance_error": 0.0},
            {"param.p_c": 0.8, "delta_m": 0.0, "activated": False,
             "refusal_reason": "CHANNEL_SILENCED.CARRIER", "label": "",
             "balance_error": 0.0},
        ]
        qrows = [
            {"param.p_c": 0.8, "v_q.pooled": 0.02, "activated": True,
             "refusal_reason": "", "label": "QUALITY_POSITIVE",
             "balance_error": 0.0},
        ]
        summary = {"battery": "DECISION_EARNED"}
        return manifest, controls, srows, qrows, summary

    def test_writes_exactly_the_five_prereg_artifacts(self, tmp_path):
        run_dir = tmp_path / "run"
        write_artifacts(run_dir, *self._tiny_inputs())
        names = sorted(p.name for p in run_dir.iterdir())
        assert names == [
            "controls.json", "manifest.json", "quality.csv",
            "summary.json", "survival.csv",
        ]

    def test_byte_identical_across_reruns(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        write_artifacts(a, *self._tiny_inputs())
        write_artifacts(b, *self._tiny_inputs())
        for name in ("manifest.json", "controls.json", "survival.csv",
                     "quality.csv", "summary.json"):
            assert (a / name).read_bytes() == (b / name).read_bytes(), name

    def test_manifest_is_valid_json_with_prereg_commit(self, tmp_path):
        run_dir = tmp_path / "run"
        write_artifacts(run_dir, *self._tiny_inputs())
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["preregistration_commit"].startswith("ca26217")

    def test_csv_columns_are_union_of_row_keys(self, tmp_path):
        run_dir = tmp_path / "run"
        write_artifacts(run_dir, *self._tiny_inputs())
        header = (run_dir / "survival.csv").read_text().splitlines()[0]
        for col in ("param.p_c", "delta_m", "activated", "label"):
            assert col in header.split(",")


class TestRunDirResolution:
    def test_first_run_gets_base_name(self, tmp_path):
        assert resolve_run_dir(tmp_path, "hedged-stage1").name == "hedged-stage1"

    def test_rerun_is_labelled_replication(self, tmp_path):
        (tmp_path / "hedged-stage1").mkdir()
        assert (
            resolve_run_dir(tmp_path, "hedged-stage1").name
            == "hedged-stage1-replication-1"
        )
        (tmp_path / "hedged-stage1-replication-1").mkdir()
        assert (
            resolve_run_dir(tmp_path, "hedged-stage1").name
            == "hedged-stage1-replication-2"
        )


from scripts.hedged_placement_stage1 import build_manifest, summarize


class TestSummarize:
    def _rows(self):
        srows = [
            {"param.p_c": 0.5, "delta_m": 0.375, "v_q.pooled": float("nan"),
             "activated": True, "refusal_reason": "", "label": "POSITIVE"},
            {"param.p_c": 0.8, "delta_m": 0.001, "v_q.pooled": float("nan"),
             "activated": True, "refusal_reason": "", "label": "NEUTRAL"},
            {"param.p_c": 0.9, "delta_m": 0.0,
             "activated": False,
             "refusal_reason": "CHANNEL_SILENCED.CARRIER", "label": ""},
        ]
        qrows = [
            {"param.p_c": 0.8, "delta_m": 0.0, "v_q.pooled": 0.02,
             "v_q.mass_pooled": 0.3, "activated": True,
             "refusal_reason": "", "label": "QUALITY_POSITIVE"},
            {"param.p_c": 0.8, "delta_m": 0.0, "v_q.pooled": float("nan"),
             "v_q.mass_pooled": 0.0, "activated": False,
             "refusal_reason": "CHANNEL_SILENCED.INFORMATION", "label": ""},
        ]
        controls = {"probability_balance": {"passed": True}}
        return srows, qrows, controls

    def test_counts_refusals_labels_and_readings(self):
        srows, qrows, controls = self._rows()
        s = summarize(srows, qrows, controls)
        assert s["cells"]["survival_total"] == 3
        assert s["cells"]["survival_activated"] == 2
        assert s["refusals"]["survival"] == {"CHANNEL_SILENCED.CARRIER": 1}
        assert s["labels"]["survival"] == {"POSITIVE": 1, "NEUTRAL": 1}
        assert s["refusals"]["quality"] == {"CHANNEL_SILENCED.INFORMATION": 1}
        readings = s["battery_readings"]
        assert readings["site_choice"] == "SITE_CHOICE_DECISION_EARNED"
        assert readings["quality_choice"] == "QUALITY_CHOICE_DECISION_EARNED"

    def test_extrema_carry_cell_params(self):
        srows, qrows, controls = self._rows()
        s = summarize(srows, qrows, controls)
        assert s["extrema"]["survival_delta_m_max"]["value"] == 0.375
        assert s["extrema"]["survival_delta_m_max"]["param.p_c"] == 0.5
        assert s["extrema"]["quality_v_q_max"]["param.p_c"] == 0.8

    def test_failed_controls_refuse_battery(self):
        srows, qrows, _ = self._rows()
        s = summarize(srows, qrows, {"x": {"passed": False}})
        assert s["battery_readings"]["battery"] == "REFUSED"


class TestBuildManifest:
    def test_manifest_pins_prereg_and_source(self):
        m = build_manifest()
        assert m["preregistration_commit"] == (
            "ca262178b327d5657973054cb06049c0050a568f"
        )
        assert len(m["source_sha256"]) == 64
        assert m["grids"]["survival_cells"] == 1620
        assert m["grids"]["quality_cells"] == 540
        assert m["thresholds"]["epsilon_m"] == 0.01
        assert m["thresholds"]["min_quality_stratum_mass"] == 0.05
