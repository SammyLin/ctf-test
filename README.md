# ctf-test

用同一套題目比較不同的 AI coding CLI，得到可以量化的分數。

題目建立在開源的 [Strapi](https://github.com/strapi/strapi) v5.63.0 上。我們在裡面植入了漏洞和 bug，所以任何模型都沒看過答案。把同一份 prompt 丟給每個 CLI，收集它們的產出，再用解答算分。

解答不在這個 repo 裡，由出題者另外保管。

## 題目

| 面向 | 題目 | CLI 要交的產出 | 怎麼算分 |
|---|---|---|---|
| 安全審查 | `audit` | `findings.json` | 自動：植入的漏洞命中幾個 |
| bug 修正 | `b1`、`b2` | 修改後的程式碼 | 自動：隱藏測試全過記 1 分 |
| 看截圖除錯 | `v1` | 修改後的程式碼 | 自動：隱藏測試全過記 1 分 |
| 跨模組理解 | `qa` | `answers.md` | 人工：依評分表給分。自動檢查引用的檔案路徑是否存在 |

`audit` 植入了幾個漏洞不公開，prompt 也不會告訴受測的 CLI。`v1` 的症狀只寫在 `report.png` 這張圖裡，CLI 讀不了圖片就做不出來。

## 流程

對每個要比較的 CLI、每一題，做同樣的三步，最後一起算分。下面以名稱 `cli-a` 為例，名稱可以自己取。

### 1. 建立題目資料夾

```bash
./start.sh cli-a audit          # Windows: .\start.ps1 cli-a audit
```

這會把 `tasks/audit.zip` 解壓到 repo 以外的位置（Mac 是 `~/eval-runs/cli-a/audit`，Windows 是 `C:\eval-runs\cli-a\audit`），開始計時，並把 prompt 複製到剪貼簿。需要 git。

題目資料夾要放在這個 repo 外面，受測的 CLI 才不會讀到其他題目或別的 CLI 的產出。

### 2. 讓 CLI 作答

用該 CLI 打開題目資料夾，開新的對話，貼上 prompt。prompt 在 `prompts/<題目>.short.txt` 或 `.detailed.txt`，要比較的 CLI 必須用同一個版本。

讓它自己做完，不提示、不幫忙。建議每題上限 30 分鐘。

### 3. 收集產出

```bash
./finish.sh cli-a audit         # Windows: .\finish.ps1 cli-a audit
```

產出會存到 `results/cli-a/audit/`：

| 檔案 | 內容 |
|---|---|
| `findings.json` | audit 的答案 |
| `answers.md` | qa 的答案 |
| `changes.patch` | CLI 改了哪些程式碼（`git diff`） |
| `seconds` | 花了幾秒 |
| `notes.txt` | 你寫的備註，例如報錯、卡住、讀不了圖片 |

不想用腳本也可以，自己把上面的檔案放進 `results/<cli>/<題目>/` 就行。

### 4. 算分

所有 CLI 都跑完後，把 `results/` 交給持有解答的人。對方把解答放在 `key/`，執行：

```bash
python3 score.py
```

輸出 `results/scorecard.md`，每個 CLI 一欄、每個面向一列，最後一列是自動計分的小計。下面是格式示意，數字是虛構的：

```
| 面向 | 題目 | cli-a | cli-b |
|---|---|---|---|
| 安全審查 | audit | 命中 3/N，共回報 5 項，清單外 2 項待人工判定，12 分 4 秒 | 命中 1/N，共回報 9 項… |
| bug 修正 | b1 | 通過（隱藏測試 3/3），4 分 10 秒 | 未通過（隱藏測試 1/3），9 分 2 秒 |
| 跨模組理解 | qa | 人工評分 __/32；引用 14 個檔案路徑，其中不存在 0 個 | 人工評分 __/32；引用 11 個，其中不存在 3 個 |
| 自動計分小計 | | **6/M** | **2/M** |
```

需要人工判定的有兩項：`qa` 的分數，以及 `audit` 清單以外的發現是真問題還是誤報。評分時先把 CLI 名稱遮掉再評，比較公正。

## 資料夾

| 路徑 | 內容 |
|---|---|
| `tasks/` | 5 題的程式碼，各一個 zip |
| `prompts/` | 每題兩個版本的 prompt：`short`、`detailed` |
| `start.*`、`finish.*` | 建立題目資料夾、收集產出 |
| `score.py` | 計分程式，只用 Python 標準函式庫，需要解答才能執行 |

## 公平性

- 題目資料夾沒有 git 歷史，檔案時間一致，會直接指出答案的既有測試已經移除。
- 題目資料夾沒有安裝套件，所有 CLI 都跑不了測試，條件相同。
- prompt 明訂不得下載原版 Strapi 來比對。發現受測 CLI 這樣做，該題記 0 分。
- prompt 由另一個模型（Gemini 4 Argon）設計，它沒看過解答。
- 解答、隱藏測試、植入腳本都不在這個 repo 裡。

## 授權

`tasks/` 裡的程式碼來自 Strapi，依 MIT 授權散布，條款見 `LICENSE-STRAPI`。Strapi 的 `ee/` 資料夾（企業版，非 MIT）已從題目中移除。題目裡的程式碼被刻意植入漏洞，不可用於正式環境。
