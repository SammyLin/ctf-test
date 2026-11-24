"""Score every CLI's task folders against the answer key and print a scorecard.

usage: python3 score.py [runs_dir]        (default: ~/ctf-runs)
       python3 score.py demo              (self-check)

runs_dir/<cli>/<task>/ is the folder that CLI worked in: the unzipped task, as the CLI left it.
Needs the answer key in ./key (not published with this repo). The three fix tasks also need
the installed task variants in ./work to run the hidden tests.
"""
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = HERE / "key"
WORK = HERE / "work"
TASKS = ["audit", "b1", "b2", "qa", "v1"]
FACETS = [("安全審查", ["audit"]), ("bug 修正", ["b1", "b2"]), ("跨模組理解", ["qa"]), ("看截圖除錯", ["v1"])]
SKIP = {".git", "node_modules", "dist", ".nx", ".yarn"}


def sh(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
    return p.stdout + p.stderr


def changes(task, run):
    """Compare a task folder with its zip. Returns (changed or new files, deleted files)."""
    z = zipfile.ZipFile(HERE / "tasks" / f"{task}.zip")
    original = {n for n in z.namelist() if not n.endswith("/")}
    changed, deleted = [], []
    for name in original:
        f = run / name
        if not f.is_file():
            deleted.append(name)
        elif f.read_bytes() != z.read(name):
            changed.append(name)
    for f in run.rglob("*"):
        rel = f.relative_to(run)
        if f.is_file() and not SKIP & set(rel.parts) and rel.as_posix() not in original:
            changed.append(rel.as_posix())
    return sorted(changed), sorted(deleted)


def match_audit(findings, key):
    """Return (planted ids hit, findings that hit nothing)."""
    hit, other = set(), []
    for f in findings:
        path, line = str(f.get("file", "")).replace("\\", "/").lstrip("./"), f.get("line")
        ids = [k["id"] for k in key if path.endswith(k["file"]) and isinstance(line, int) and k["from"] <= line <= k["to"]]
        hit.update(ids)
        if not ids:
            other.append(f)
    return sorted(hit), other


def score_audit(run):
    key = json.loads((KEY / "audit_key.json").read_text())
    try:
        findings = json.loads((run / "findings.json").read_text(encoding="utf-8-sig"))
        assert isinstance(findings, list)
    except Exception as e:  # missing or malformed output scores zero
        return {"points": 0, "text": f"命中 0/{len(key)}，findings.json 無法使用（{type(e).__name__}）"}
    hit, other = match_audit([f for f in findings if isinstance(f, dict)], key)
    return {"points": len(hit), "hit": hit, "other": other,
            "text": f"命中 {len(hit)}/{len(key)}（{'、'.join(hit) or '無'}），共回報 {len(findings)} 項，清單外 {len(other)} 項待人工判定"}


def score_qa(run):
    f = run / "answers.md"
    if not f.exists():
        return {"points": None, "text": "沒有 answers.md"}
    names = set(zipfile.ZipFile(HERE / "tasks" / "qa.zip").namelist())
    cited = sorted(set(re.findall(r"packages/[\w@./-]+\.\w+", f.read_text(errors="replace"))))
    fake = [p for p in cited if p not in names]
    return {"points": None, "fabricated": fake,
            "text": f"人工評分 __/32；引用 {len(cited)} 個檔案路徑，其中不存在 {len(fake)} 個"}


def score_fix(task, run):
    changed, deleted = changes(task, run)
    code = [c for c in changed if c.startswith("packages/")]
    if not code and not deleted:
        return {"points": 0, "text": "未通過，沒有修改任何程式碼"}
    var = WORK / "variants" / task
    if not var.is_dir():
        return {"points": None, "changed": code, "text": f"待判定：改了 {len(code)} 個檔案，需要 ./work 才能跑隱藏測試"}
    pkg, tdir, tfile, runner = json.loads((KEY / "hidden" / "tests.json").read_text())[task]
    try:  # copy the CLI's changes onto the installed variant, test, then restore it
        for name in code:
            (var / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(run / name, var / name)
        for name in deleted:
            (var / name).unlink(missing_ok=True)
        stat = sh(["git", "diff", "--numstat", "HEAD", "--", "*test*"], var)
        removed = sum(int(l.split()[1]) for l in stat.splitlines() if l.split()[1].isdigit())
        shutil.copy(KEY / "hidden" / tfile, var / pkg / tdir / tfile)
        if runner == "jest":
            out = sh(["node", str(var / ".yarn/releases/yarn-4.18.1.cjs"), "jest", f"{tdir}/{tfile}"], var / pkg)
            m = re.search(r"Tests:\s+(?:(\d+) failed, )?(?:(\d+) passed, )?(\d+) total", out)
        else:
            out = sh(["npx", "vitest", "run", f"{tdir}/{tfile}"], var / pkg)
            m = re.search(r"Tests\s+(?:(\d+) failed \| )?(?:(\d+) passed )?\((\d+)\)", out)
        passed, total = (int(m.group(2) or 0), int(m.group(3))) if m else (0, 0)
    finally:
        subprocess.run(["git", "reset", "-q", "--hard"], cwd=var)
        subprocess.run(["git", "clean", "-fdq"], cwd=var)
    ok = total > 0 and passed == total
    weak = f"，刪改既有測試 {removed} 行" if removed else ""
    return {"points": int(ok), "changed": code,
            "text": f"{'通過' if ok else '未通過'}（隱藏測試 {passed}/{total}，改了 {len(code)} 個檔案{weak}）"}


def main(runs_dir):
    if not (KEY / "audit_key.json").exists():
        sys.exit("key/ not found. Scoring needs the answer key, which is kept out of the public repo.")
    if not runs_dir.is_dir():
        sys.exit(f"{runs_dir} not found. Pass the folder that holds <cli>/<task>/.")
    planted = len(json.loads((KEY / "audit_key.json").read_text()))
    clis = sorted(d.name for d in runs_dir.iterdir() if d.is_dir() and any((d / t).is_dir() for t in TASKS))
    runs = {}
    for cli in clis:
        for task in TASKS:
            run = runs_dir / cli / task
            if run.is_dir():
                print(f"scoring {cli}/{task} ...", file=sys.stderr)
                runs[(cli, task)] = score_audit(run) if task == "audit" else score_qa(run) if task == "qa" else score_fix(task, run)
    lines = ["# 計分表", "", "| 面向 | 題目 | " + " | ".join(clis) + " |", "|---|---|" + "---|" * len(clis)]
    for facet, tasks in FACETS:
        for task in tasks:
            lines.append(f"| {facet} | {task} | " + " | ".join(runs.get((c, task), {"text": "未執行"})["text"] for c in clis) + " |")
    totals = []
    for c in clis:
        pts = [runs[(c, t)]["points"] for t in ("audit", "b1", "b2", "v1") if (c, t) in runs]
        pending = sum(p is None for p in pts)
        totals.append(f"**{sum(p or 0 for p in pts)}/{planted + 3}**" + (f"（{pending} 題待判定）" if pending else ""))
    lines.append(f"| 自動計分小計 | 安全 {planted} + 修正 3 | " + " | ".join(totals) + " |")
    lines += ["", "跨模組理解的 32 分與安全審查的清單外發現需要人工判定，標準在 key/qa_rubric.md 與 key/ANSWER_KEY.md。"]
    (runs_dir / "scorecard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    detail = [{"cli": c, "task": t, **r} for (c, t), r in runs.items()]
    (runs_dir / "scorecard.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines))


def demo():
    key = [{"id": "S1", "file": "a/b.js", "from": 10, "to": 20}]
    assert match_audit([{"file": "./a/b.js", "line": 12}], key) == (["S1"], [])
    assert match_audit([{"file": "a\\b.js", "line": 20}], key)[0] == ["S1"]
    assert match_audit([{"file": "a/b.js", "line": 99}], key)[0] == []
    assert match_audit([{"file": "x.js", "line": 12}, {"file": "a/b.js", "line": "12"}], key)[0] == []
    print("score.py self-check ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
    else:
        main(Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "ctf-runs").expanduser().resolve())
