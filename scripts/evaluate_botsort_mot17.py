#!/usr/bin/env python3
"""
Evaluate official and engineering BoT-SORT runtimes on MOT17 validation split.
"""

from __future__ import annotations

import argparse
import configparser
import csv
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_RUNTIME_ROOT = Path("/home/livablecity/geoview_runtime")
REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd: Path | None = None, env: dict | None = None):
    print("[run]", " ".join(cmd), flush=True)
    return subprocess.run(cmd,
                          cwd=str(cwd) if cwd else None,
                          env=env,
                          capture_output=True,
                          text=True,
                          check=True)


def list_train_sequences(mot17_root: Path):
    train_dir = mot17_root / "train"
    return sorted(path.name for path in train_dir.iterdir() if path.is_dir())


def val_half_start(num_images: int) -> int:
    return num_images // 2 + 1


def ensure_val_half_annotations(mot17_root: Path):
    for seq in list_train_sequences(mot17_root):
        seq_dir = mot17_root / "train" / seq
        img_dir = seq_dir / "img1"
        gt_dir = seq_dir / "gt"
        det_dir = seq_dir / "det"
        all_images = sorted(path.name for path in img_dir.iterdir() if path.suffix.lower() == ".jpg")
        start = val_half_start(len(all_images))

        gt_txt = gt_dir / "gt.txt"
        gt_val = gt_dir / "gt_val_half.txt"
        if not gt_val.exists():
            rows = []
            with open(gt_txt, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row:
                        continue
                    frame = int(float(row[0]))
                    if frame - 1 < start:
                        continue
                    row[0] = str(frame - start)
                    rows.append(row)
            with open(gt_val, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerows(rows)

        det_txt = det_dir / "det.txt"
        det_val = det_dir / "det_val_half.txt"
        if det_txt.exists() and not det_val.exists():
            rows = []
            with open(det_txt, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row:
                        continue
                    frame = int(float(row[0]))
                    if frame - 1 < start:
                        continue
                    row[0] = str(frame - start)
                    rows.append(row)
            with open(det_val, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerows(rows)


def build_trackeval_gt_root(mot17_root: Path, out_root: Path):
    gt_root = out_root / "trackeval_gt_val"
    if gt_root.exists():
        shutil.rmtree(gt_root)
    gt_root.mkdir(parents=True, exist_ok=True)

    seqmap_path = out_root / "mot17_val.seqmap"
    seq_lengths = {}
    seq_names = list_train_sequences(mot17_root)

    with open(seqmap_path, "w", encoding="utf-8") as file:
        file.write("name\n")
        for seq in seq_names:
            seq_dir = mot17_root / "train" / seq
            img_dir = seq_dir / "img1"
            all_images = sorted(path.name for path in img_dir.iterdir() if path.suffix.lower() == ".jpg")
            start = val_half_start(len(all_images))
            val_length = len(all_images) - start
            seq_lengths[seq] = val_length

            target_seq_dir = gt_root / seq
            (target_seq_dir / "gt").mkdir(parents=True, exist_ok=True)
            shutil.copy2(seq_dir / "gt" / "gt_val_half.txt", target_seq_dir / "gt" / "gt.txt")

            parser = configparser.ConfigParser()
            parser.read(seq_dir / "seqinfo.ini")
            parser["Sequence"]["seqLength"] = str(val_length)
            with open(target_seq_dir / "seqinfo.ini", "w", encoding="utf-8") as seqinfo_file:
                parser.write(seqinfo_file)
            file.write(f"{seq}\n")

    return gt_root, seqmap_path, seq_lengths


def evaluate_with_trackeval(trackeval_repo: Path, gt_root: Path, seqmap_file: Path,
                            trackers_root: Path, tracker_names: list[str],
                            output_root: Path):
    if str(trackeval_repo) not in sys.path:
        sys.path.insert(0, str(trackeval_repo))
    import numpy as np

    # TrackEval still references deprecated NumPy aliases under newer numpy releases.
    if not hasattr(np, "float"):
        np.float = float  # type: ignore[attr-defined]
    if not hasattr(np, "int"):
        np.int = int  # type: ignore[attr-defined]
    if not hasattr(np, "bool"):
        np.bool = bool  # type: ignore[attr-defined]
    import trackeval

    eval_config = trackeval.Evaluator.get_default_eval_config()
    eval_config["USE_PARALLEL"] = False
    eval_config["PRINT_RESULTS"] = True
    eval_config["PRINT_ONLY_COMBINED"] = False
    eval_config["PRINT_CONFIG"] = True
    eval_config["TIME_PROGRESS"] = True
    eval_config["PLOT_CURVES"] = False
    eval_config["OUTPUT_SUMMARY"] = True
    eval_config["OUTPUT_DETAILED"] = True

    dataset_config = trackeval.datasets.MotChallenge2DBox.get_default_dataset_config()
    dataset_config["BENCHMARK"] = "MOT17"
    dataset_config["SPLIT_TO_EVAL"] = "train"
    dataset_config["GT_FOLDER"] = str(gt_root)
    dataset_config["TRACKERS_FOLDER"] = str(trackers_root)
    dataset_config["OUTPUT_FOLDER"] = str(output_root)
    dataset_config["TRACKERS_TO_EVAL"] = tracker_names
    dataset_config["SEQMAP_FILE"] = str(seqmap_file)
    dataset_config["SKIP_SPLIT_FOL"] = True
    dataset_config["TRACKER_SUB_FOLDER"] = "data"
    dataset_config["OUTPUT_SUB_FOLDER"] = ""

    metrics_config = {"METRICS": ["HOTA", "CLEAR", "Identity"], "THRESHOLD": 0.5}

    evaluator = trackeval.Evaluator(eval_config)
    dataset_list = [trackeval.datasets.MotChallenge2DBox(dataset_config)]
    metrics_list = [
        trackeval.metrics.HOTA(metrics_config),
        trackeval.metrics.CLEAR(metrics_config),
        trackeval.metrics.Identity(metrics_config),
    ]
    return evaluator.evaluate(dataset_list, metrics_list)


def parse_trackeval_summary(summary_file: Path):
    with open(summary_file, "r", encoding="utf-8") as file:
        rows = [line.strip().split() for line in file if line.strip()]
    header = rows[0]
    values = rows[-1]
    return dict(zip(header, values))


def official_track(repo_dir: Path, mot17_root: Path, env_name: str):
    env = os.environ.copy()
    env["FASTREID_DATASETS"] = str(repo_dir / "fast_reid" / "datasets")
    cmd = [
        "conda",
        "run",
        "-n",
        env_name,
        "python",
        "tools/track.py",
        str(mot17_root),
        "--default-parameters",
        "--with-reid",
        "--benchmark",
        "MOT17",
        "--eval",
        "val",
        "--fp16",
        "--fuse",
    ]
    return run(cmd, cwd=repo_dir, env=env)


def official_results_dir(repo_dir: Path):
    return repo_dir / "YOLOX_outputs" / "yolox_x_ablation" / "track_results"


def engineering_track(hf_env: str, mot17_root: Path, out_root: Path):
    tracker_name = "botsort_engineering"
    tracker_data_root = out_root / "trackers" / tracker_name / "data"
    tracker_data_root.mkdir(parents=True, exist_ok=True)
    seq_artifact_root = out_root / "engineering_artifacts"
    seq_artifact_root.mkdir(parents=True, exist_ok=True)

    script_path = REPO_ROOT / "backend/applications/interface/hf_tracking_botsort.py"

    for seq in list_train_sequences(mot17_root):
        img_dir = mot17_root / "train" / seq / "img1"
        file_names = sorted(path.name for path in img_dir.iterdir() if path.suffix.lower() == ".jpg")
        file_names = file_names[val_half_start(len(file_names)):]
        seq_dir = seq_artifact_root / seq
        seq_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            "conda",
            "run",
            "-n",
            hf_env,
            "python",
            str(script_path),
            "--input_dir",
            str(img_dir),
            "--file_names",
            ",".join(file_names),
            "--output_video",
            str(seq_dir / f"{seq}.mp4"),
            "--output_preview",
            str(seq_dir / f"{seq}_preview.png"),
            "--output_trajectory",
            str(seq_dir / f"{seq}.json"),
            "--output_mot",
            str(tracker_data_root / f"{seq}.txt"),
            "--model_id",
            "StephanST/WALDO30",
            "--model_file",
            "WALDO30_yolov8l-p2_1024x1024.pt",
            "--tracker_config",
            str(REPO_ROOT / "backend/model/tracking/botsort/botsort.yaml"),
            "--imgsz",
            "1024",
            "--allowed_labels",
            "person",
            "--device",
            "auto",
        ]
        run(cmd, cwd=REPO_ROOT)


def copy_official_results(repo_dir: Path, out_root: Path):
    tracker_name = "botsort_official_reid"
    tracker_data_root = out_root / "trackers" / tracker_name / "data"
    tracker_data_root.mkdir(parents=True, exist_ok=True)
    source_root = official_results_dir(repo_dir)
    for txt_file in sorted(source_root.glob("*.txt")):
        shutil.copy2(txt_file, tracker_data_root / txt_file.name)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate official and engineering BoT-SORT on MOT17 val.")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--official-env", default="BoTSORTOfficial37")
    parser.add_argument("--hf-env", default="HFPyTorch310")
    parser.add_argument("--reuse-existing", action="store_true",
                        help="Reuse existing tracking results under eval/mot17_dual_botsort when present.")
    return parser.parse_args()


def tracker_results_exist(trackers_root: Path, tracker_name: str, expected_sequences: list[str]):
    tracker_data_root = trackers_root / tracker_name / "data"
    return tracker_data_root.exists() and all((tracker_data_root / f"{seq}.txt").exists()
                                              for seq in expected_sequences)


def main():
    args = parse_args()
    runtime_root = Path(args.runtime_root).resolve()
    mot17_root = runtime_root / "datasets" / "MOT17"
    botsort_repo = runtime_root / "BoT-SORT"
    trackeval_repo = runtime_root / "TrackEval"
    eval_root = runtime_root / "eval" / "mot17_dual_botsort"
    seq_names = list_train_sequences(mot17_root)
    if eval_root.exists() and not args.reuse_existing:
        shutil.rmtree(eval_root)
    eval_root.mkdir(parents=True, exist_ok=True)

    ensure_val_half_annotations(mot17_root)
    gt_root, seqmap_path, _seq_lengths = build_trackeval_gt_root(mot17_root, eval_root)

    trackers_root = eval_root / "trackers"
    if not tracker_results_exist(trackers_root, "botsort_official_reid", seq_names):
        official_track(botsort_repo, mot17_root, args.official_env)
        copy_official_results(botsort_repo, eval_root)
    else:
        print("[skip] Reusing existing official tracking results", flush=True)

    if not tracker_results_exist(trackers_root, "botsort_engineering", seq_names):
        engineering_track(args.hf_env, mot17_root, eval_root)
    else:
        print("[skip] Reusing existing engineering tracking results", flush=True)

    output_root = eval_root / "trackeval_output"
    evaluate_with_trackeval(trackeval_repo,
                            gt_root,
                            seqmap_path,
                            trackers_root,
                            ["botsort_official_reid", "botsort_engineering"],
                            output_root)

    report = {
        "official_readme_claim": {
            "MOTA": 0.805,
            "IDF1": 0.802,
            "HOTA": 0.650,
            "source": "NirAharon/BoT-SORT README MOT17 test set (BoT-SORT-ReID)",
        },
        "measured": {},
        "notes": [
            "MOT17 only covers MOTA/IDF1/HOTA. Anomaly Precision is not evaluated on this dataset.",
            "Engineering variant uses WALDO30 person detections filtered to label=person.",
            "Official environment was adjusted from torch 1.11/cu113 to torch 1.13.1/cu117 because torch 1.11 could not see the GPU on this machine.",
        ],
    }

    for tracker_name, variant in [
        ("botsort_official_reid", "official"),
        ("botsort_engineering", "engineering"),
    ]:
        summary_file = output_root / tracker_name / "pedestrian_summary.txt"
        summary = parse_trackeval_summary(summary_file)
        mota = float(summary["MOTA"]) / 100.0
        idf1 = float(summary["IDF1"]) / 100.0
        hota = float(summary["HOTA"]) / 100.0
        report["measured"][variant] = {
            "MOTA": mota,
            "IDF1": idf1,
            "HOTA": hota,
            "meets_threshold": mota >= 0.70 and idf1 >= 0.70,
            "summary_file": str(summary_file),
        }

    report["anomaly_precision"] = {
        "status": "Not Evaluated on MOT17",
        "threshold": 0.65,
        "reason": "MOT17 does not provide anomaly labels.",
    }

    report_path = eval_root / "dual_botsort_mot17_report.json"
    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
