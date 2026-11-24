# ctf-test

用同一套題目比較不同的 AI coding CLI，得到可以量化的分數。

題目是開源的 [Strapi](https://github.com/strapi/strapi) v5.63.0，我們在裡面植入了漏洞和 bug。把同一份 prompt 貼給每個 CLI，最後用解答算分。

## 五個題目

| 題目 | 面向 | CLI 要做什麼 |
|---|---|---|
| `audit` | 安全審查 | 找出被植入的安全漏洞，寫成 `findings.json` |
| `b1` | bug 修正 | 依症狀描述修好一個 bug |
| `b2` | bug 修正 | 依症狀描述修好另一個 bug |
| `v1` | 看截圖除錯 | 症狀只在一張截圖裡，看圖找出問題並修好 |
| `qa` | 跨模組理解 | 回答 4 個「這功能怎麼運作」的問題，寫成 `answers.md` |

## 怎麼跑

以 Claude Code 跑 `audit` 為例。其他 CLI、其他題目，把指令裡的 `claude-code` 和 `audit` 換掉就好。

### 第 1 步：下載這個 repo

```bash
git clone https://github.com/SammyLin/ctf-test.git
cd ctf-test
```

### 第 2 步：解壓一題到 repo 外面

Mac / Linux：

```bash
mkdir -p ~/ctf-runs/claude-code/audit
unzip -q tasks/audit.zip -d ~/ctf-runs/claude-code/audit
```

Windows（PowerShell）：

```powershell
mkdir C:\ctf-runs\delta-code\audit
tar -xf tasks\audit.zip -C C:\ctf-runs\delta-code\audit
```

資料夾固定取名 `ctf-runs/<CLI 名稱>/<題目>`，算分時靠這個名稱辨認。

### 第 3 步：用 CLI 打開那個資料夾

```bash
cd ~/ctf-runs/claude-code/audit
claude
```

圖形介面的工具就用「開啟資料夾」選同一個位置。

### 第 4 步：貼上 prompt

打開 `prompts/audit.txt`，把整份內容貼進 CLI 送出。

然後讓它自己做完。不要提示、不要幫忙、不要回答它的問題。建議上限 30 分鐘，超過就中止。

### 第 5 步：換下一題、換下一個 CLI

每一題都開新的對話，重複第 2 到第 4 步。做完的資料夾留著不要動。

全部跑完後，資料夾會長這樣：

```
ctf-runs/
  claude-code/
    audit/  b1/  b2/  v1/  qa/
  delta-code/
    audit/  b1/  b2/  v1/  qa/
```

在別台電腦跑的 CLI，把它的整個資料夾（例如 `delta-code`）壓縮後複製過來，放進同一個 `ctf-runs` 底下。

## 怎麼算分

算分需要解答。解答不在這個 repo 裡，由出題者保管，放在 `key/` 資料夾。

```bash
python3 score.py ~/ctf-runs
```

輸出一張計分表，每個 CLI 一欄。下面是格式示意，數字是虛構的：

```
| 面向 | 題目 | claude-code | delta-code |
|---|---|---|---|
| 安全審查 | audit | 命中 3/N，共回報 5 項，清單外 2 項待人工判定 | 命中 1/N，共回報 9 項，清單外 8 項待人工判定 |
| bug 修正 | b1 | 通過（隱藏測試 3/3，改了 1 個檔案） | 未通過（隱藏測試 1/3，改了 2 個檔案） |
| bug 修正 | b2 | 通過（隱藏測試 4/4，改了 1 個檔案） | 未通過，沒有修改任何程式碼 |
| 跨模組理解 | qa | 人工評分 __/32；引用 14 個檔案路徑，其中不存在 0 個 | 人工評分 __/32；引用 11 個檔案路徑，其中不存在 3 個 |
| 看截圖除錯 | v1 | 通過（隱藏測試 4/4，改了 1 個檔案） | 未通過，沒有修改任何程式碼 |
| 自動計分小計 | | **6/M** | **1/M** |
```

各題的算法：

| 題目 | 算法 |
|---|---|
| `audit` | 回報的檔案和行號對得上植入的漏洞，就算命中一個 |
| `b1`、`b2`、`v1` | 把 CLI 改過的檔案拿去跑隱藏測試，全部通過記 1 分 |
| `qa` | 依評分表人工給分。程式會自動檢查答案裡引用的檔案路徑是不是真的存在 |

需要人工判定的有兩項：`qa` 的分數，以及 `audit` 裡不在解答清單上的發現算不算真問題。評分時先把 CLI 名稱遮掉，比較公正。

## 注意事項

- 題目資料夾要放在這個 repo 外面，CLI 才不會讀到其他題目。
- 每個 CLI 都用同一份 prompt，一個字都不要改。
- prompt 明訂不得下載原版 Strapi 來比對。看到 CLI 這樣做，該題記 0 分。
- 題目資料夾沒有安裝套件，所有 CLI 都跑不了測試，條件相同。
- `audit` 植入了幾個漏洞不公開，prompt 也不會告訴 CLI。
- prompt 由另一個模型（Gemini 4 Argon）設計，它沒看過解答。

## 授權

`tasks/` 裡的程式碼來自 Strapi，依 MIT 授權散布，條款見 `LICENSE-STRAPI`。Strapi 的 `ee/` 資料夾（企業版，非 MIT）已從題目中移除。題目裡的程式碼被刻意植入漏洞，不可用於正式環境。
