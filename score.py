"""Score every CLI's outputs against the answer key and write a scorecard.

usage: python3 score.py [results_dir]          (default: ./results)
       python3 score.py demo                   (self-check)

results/<cli>/<task>/ holds what that CLI produced:
  audit -> findings.json
  qa    -> answers.md
  b1, b2, v1 -> changes.patch   (git diff of the fix)
  optional: seconds (elapsed time), notes.txt

Scoring needs the answer key in ./key, which is not published with this repo. audit and qa are
scored straight from the output files. The three fix tasks are scored by hidden tests, which
also need the installed task variants in ./work.
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
FACETS = [("安全審查", ["audit"]), ("bug 修正", ["b1", "b2"]), ("跨模組理解", ["qa"]), ("看截圖除錯", ["v1"])]

def sh(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
    return p.stdout + p.stderr


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


def score_audit(rdir):
    key = json.loads((KEY / "audit_key.json").read_text())
    try:
        findings = json.loads((rdir / "findings.json").read_text(encoding="utf-8-sig"))
        assert isinstance(findings, list)
    except Exception as e:  # missing or malformed output scores zero
        return {"points": 0, "text": f"命中 0/{len(key)}，findings.json 無法使用（{type(e).__name__}）"}
    hit, other = match_audit([f for f in findings if isinstance(f, dict)], key)
    return {"points": len(hit), "hit": hit, "other": other,
            "text": f"命中 {len(hit)}/{len(key)}（{'、'.join(hit) or '無'}），共回報 {len(findings)} 項，清單外 {len(other)} 項待人工判定"}


def score_qa(rdir):
    f = rdir / "answers.md"
    if not f.exists():
        return {"points": None, "text": "沒有 answers.md"}
    names = set(zipfile.ZipFile(HERE / "tasks" / "qa.zip").namelist())
    cited = sorted(set(re.findall(r"packages/[\w@./-]+\.\w+", f.read_text(errors="replace"))))
    fake = [p for p in cited if p not in names]
    return {"points": None, "fabricated": fake,
            "text": f"人工評分 __/32；引用 {len(cited)} 個檔案路徑，其中不存在 {len(fake)} 個"}


def score_fix(task, rdir):
    var, patch = WORK / "variants" / task, rdir / "changes.patch"
    if not patch.exists() or not patch.stat().st_size:
        return {"points": 0, "text": "未通過，沒有修改（changes.patch 是空的）"}
    if not var.is_dir():
        return {"points": None, "text": "待判定：對照解答人工判定，或先建置 ./work 再算分"}
    pkg, tdir, tfile, runner = json.loads((KEY / "hidden" / "tests.json").read_text())[task]
    try:  # apply to the installed variant in place, test, then restore it
        p = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch.resolve())], cwd=var, capture_output=True, text=True)
        if p.returncode:
            return {"points": 0, "text": "未通過，修改無法套用（需人工檢查）"}
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
    return {"points": int(ok), "text": f"{'通過' if ok else '未通過'}（隱藏測試 {passed}/{total}{weak}）"}


def score_run(task, rdir):
    r = score_audit(rdir) if task == "audit" else score_qa(rdir) if task == "qa" else score_fix(task, rdir)
    if (rdir / "seconds").exists():
        s = int((rdir / "seconds").read_text().strip())
        r["text"] += f"，{s // 60} 分 {s % 60} 秒"
    if (rdir / "notes.txt").exists():
        r["notes"] = (rdir / "notes.txt").read_text(errors="replace").strip()
    return r


def main(results):
    if not (KEY / "audit_key.json").exists():
        sys.exit("key/ not found. Scoring needs the answer key, which is kept out of the public repo.")
    planted = len(json.loads((KEY / "audit_key.json").read_text()))
    clis = sorted(d.name for d in results.iterdir() if d.is_dir())
    runs = {}
    for cli in clis:
        for task in ("audit", "b1", "b2", "qa", "v1"):
            if (results / cli / task).is_dir():
                print(f"scoring {cli}/{task} ...", file=sys.stderr)
                runs[(cli, task)] = score_run(task, results / cli / task)
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
    notes = [f"- {c}/{t}：{r['notes']}" for (c, t), r in runs.items() if r.get("notes")]
    if notes:
        lines += ["", "## 執行時的備註", *notes]
    lines += ["", "跨模組理解的 32 分與安全審查的清單外發現需要人工判定，標準在 key/qa_rubric.md 與 key/ANSWER_KEY.md。"]
    (results / "scorecard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    detail = [{"cli": c, "task": t, **r} for (c, t), r in runs.items()]
    (results / "scorecard.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
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
        main(Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "results").resolve())
