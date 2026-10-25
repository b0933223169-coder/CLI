# Cool Desktop 介面規格（UI-SPEC）

本文件是 `desktop/`（Electron + React + TypeScript）介面的**格式、定義與排版規則**盤點，
作為後續所有 UI 修改的依據。

- 建立日期：2026-10-25（U2 輪次）
- 本輪**未修改任何程式檔案**，只新增本文件。
- 證據格式：`檔案:行號`，或「指令＋原始輸出」（見附錄 A）。
- 未經 Windows 實機畫面確認的項目一律標 **未驗證**。
- **顏色（色碼、對比度、主題配色）不在本輪範圍，另案處理**；本文只在必要處引用色碼作為定位，
  並在第 7 章列出「顏色另案」清單。

---

## 0. 已確認的設計約束（不可違反）

| 約束 | 證據 |
|---|---|
| 字級滑桿 10–24，預設 13 | `desktop/src/main/services/storage.ts:38`（`fontSize: 13`）；設定頁 `min="10" max="24"`（`App.tsx:3039` 附近，滑桿 aria-label「介面字體大小」） |
| 縮放係數 `--ui-font-scale = fontSize / 13` | `desktop/src/renderer/src/App.tsx:869` |
| 縮放範圍 10/13 ≈ 0.769 → 24/13 ≈ 1.846 | 由上兩條推導 |
| 主題預設 dark | `storage.ts:48` |
| 終端預設開啟、垂直分割、比例 0.68 | `storage.ts:50`（`terminalLayout: 'vertical'`）、`storage.ts:51`（`splitRatio: 0.68`）；`terminalOpen` 預設 true（`App.tsx` 初始化） |
| 分割比例夾在 0.3–0.8 | `App.tsx:1134`（`Math.max(0.3, Math.min(0.8, ratio))`） |
| 視窗 1360×900，最小 1000×680 | `desktop/src/main/index.ts:803-806` |
| `body` 最小 1000×680、`overflow: hidden` | `main.css:11-15` |
| 24 組主題、CLI 報表配色、字族設定維持原機制 | `src/shared/colorThemes.ts`、`src/shared/cliReportColors.ts`、`src/shared/fontSettings.ts`（未改動） |
| 優先級：結構與排版 > 元件 > 字級與間距一致性 > 顏色 | 使用者指定 |

---

## 1. 外殼版面（Shell）

### 1.1 DOM 層級與實際尺寸

```
#root                        height:100vh; width:100vw        main.css:43-46
└─ .app-shell                flex column; 100%×100%            main.css:59-68
   ├─ header.titlebar        height 48px / min-height 48px     main.css:70-78（71-72）
   │    padding: 0 14px 0 18px; -webkit-app-region: drag      main.css:76-77
   ├─ .workbench             flex:1; display:flex              main.css:193-197
   │  ├─ aside.sidebar       flex: 0 0 236px                   main.css:199-213（201）
   │   │    padding: 12px 12px 10px                             main.css:204
   │    │    <1180px → flex-basis: 205px                         main.css:3570-3573（3572）
   │  │    折疊時 → flex-basis: 56px                            main.css:255-259（256）
   │  └─ section.main-column  flex:1; flex-direction:column    main.css:436-443
   │     ├─ .page-topbar     height 43px / min-height 43px     main.css:464-471（468-469）
   │     │    padding: 0 24px; border-bottom 1px               main.css:470-471
   │     ├─ .main-layout     flex:1; display:flex              main.css:445-449
   │     │    .vertical → flex-direction: column                main.css:452-454（預設）
   │     │    .horizontal → flex-direction: row                 main.css:456-458
   │     │    .terminal-hidden .page-content { flex:1 }         main.css:460-462
   │     │    ├─ .page-content  flex: 0 0 var(--split-ratio, 68%)  main.css:519-526（520）
   │     │    │    overflow: auto（唯一的垂直＋水平捲動容器）      main.css:523
   │     │    ├─ .terminal-split-handle  flex: 0 0 5px          main.css:2757-2764（2759）
   │     │    └─ section.terminal-dock  flex:1 1 0              main.css:2738-2746
   │     │         min-height: 160px                            main.css:2743
   │     │         .horizontal → min-width: 260px               main.css:2750-2754（2752）
   │     └─ footer.statusbar  height 23px / min-height 23px     main.css:3469-3479（3473-3474）
   └─ （fixed）.toast / .busy-indicator                          main.css:3500-3515 / 3544-3557
```

`--split-ratio` 由 `App.tsx:1020` 以 inline style 寫入 `.main-layout`
（`{ '--split-ratio': settings.splitRatio * 100% }`）。

### 1.2 捲動容器

**只有 `.page-content` 負責捲動**（`main.css:523` `overflow: auto`，
`scrollbar-width: thin`，`main.css:524-525`）。其他容器：

- `.app-shell { overflow: hidden }`（`main.css:67`）
- `body { overflow: hidden }`（`main.css:14`）
- `.sidebar { overflow: hidden }`（`main.css:207`）
- `.course-list`、`.network-list`、`.report-table` → `overflow: hidden`（`main.css:1472`、`1646`、`1091`）
- `.account-table` → `overflow: visible`（`main.css:1086-1088`）——**這是刻意的**：
  列上的 `.account-login-menu` 是絕對定位浮層（`main.css:1343`），需要溢出容器外顯示。
- `.network-course-progress-log` 自帶 `overflow: auto; max-height: 320px`（`main.css:1651-1655`）
- `.cli-color-menu-list` 自帶 `overflow-y: auto; max-height: 380px`（`main.css:2603-2609`）

### 1.3 內容區可用高度公式

```
workbench 高      = 視窗高 − 48（titlebar）
main-layout 高    = workbench 高 − 43（page-topbar）− 23（statusbar）
                  = 視窗高 − 114
page-content 高   = main-layout 高 × splitRatio
                  − 5（split-handle）
                  − max(0, 160 − dock 應得高度)   ← dock min-height 介入
content-wrap 可用 = page-content 高 − 29（上）− 40（下）
```

**實算（預設 splitRatio 0.68、垂直、預設字級）**

| 視窗 | workbench | main-layout | page-content（0.68） | terminal-dock | content-wrap 可用高 |
|---|---|---|---|---|---|
| 1000×680 | 632 | 566 | 384.9 | 176.1 | **315.9** |
| 1360×900 | 852 | 786 | 534.5 | 246.5 | **465.5** |

**實算（splitRatio 極值）**

| 視窗 | split 0.30 | split 0.50 | split 0.80 |
|---|---|---|---|
| 1000×680 | page 169.8 / dock 391.2 | page 283 / dock 278 | **page 401 / dock 160（實際 70.9% / 28.3%）** |
| 1360×900 | page 235.8 / dock 545.2 | page 393 / dock 388 | **page 621 / dock 160（實際 79.0% / 20.4%）** |

> **重要發現（計算推導，未實機驗證）**：`splitRatio = 0.8` 時
> dock 的 `min-height: 160px`（`main.css:2743`）+ `flex: 0 0 5px` handle（`main.css:2759`）
> 會迫使 `.page-content`（flex-shrink 預設 1）吸收不足量，**實際比例永遠不會低於 160px 的終端**。
> 在 1000×680 開啟狀態下，「80% 終端」實際只會是 160/566 ≈ 28.3%。
> 這不是 bug 就是未定義行為，需在 U 系列決定：**要嘛移除 160px 下限，要嘛把 UI 上的比例上限改為可達值**。

**水平分割（`terminalLayout: 'horizontal'`）**：`page-content` 取的是**寬度**的 `splitRatio`，
dock 的下限是 `min-width: 260px`（`main.css:2752`）。

| 視窗 | 主內容區寬（−sidebar） | split 0.68 | split 0.80 |
|---|---|---|---|
| 1000×680（sidebar 205） | 795 | page 540.6 / dock 249.4→**補到 265** | **page 530（66.7%）/ dock 260（32.7%）** |
| 1360×900（sidebar 236） | 1124 | page 764.3 / dock 354.7 | page 899.2→**約 859** / dock 260 |

### 1.4 內容寬度（content-wrap）

```
content-wrap 寬 = min(100%, 1100px)              main.css:529
padding: 29px 34px 40px                            main.css:530
<1180px → padding-left/right: 24px                 main.css:3575-3576
<1150px → padding-left/right: 20px（被後面的 1180 覆蓋，見 7.2） main.css:3455-3456
```

| 視窗 | sidebar | main-column 寬 | content-wrap 寬 | 內容淨寬（左右 padding） |
|---|---|---|---|---|
| 1000×680 | 205（`main.css:3572`） | 795 | 795 | **747**（24+24） |
| 1360×900 | 236（`main.css:201`） | 1124 | 1100 | **1032**（34+34） |

### 1.5 ASCII 線稿

```
┌──────────────────────────────────────────────────────────────────────┐ 680 / 900
│ .titlebar 48px  [● 本機工作階段 · 帳號]      [終端] [–][□][×]         │
├────────────┬─────────────────────────────────────────────────────────┤
│ .sidebar   │ .page-topbar 43px   cool / 頁面名   [搜尋][?]            │
│ 236px      ├─────────────────────────────────────────────────────────┤
│            │ .main-layout（flex:1）                                  │
│ [品牌鈕]   │ ┌ .page-content  flex:0 0 var(--split-ratio) ─────────┐ │
│  工作台    │ │  .content-wrap  min(100%,1100px)                    │ │
│  帳號(n)   │ │  padding 29 / 34 / 40                               │ │
│  課程      │ │  （唯一捲動容器：overflow:auto）                      │ │
│  報表      │ │                                                      │ │
│  網路      │ └──────────────────────────────────────────────────────┘ │
│  ──────    │ ┌ .terminal-split-handle  5px  ⇕                       │
│  設定      │ ├ .terminal-dock  flex:1 1 0  min-height:160px ────────┤ │
│  [C 帳列] │ │  .terminal-toolbar 32px ＋ .terminal-screen            │ │
├────────────┴─┴───────────────────────────────────────────────────────┤
│ .statusbar 23px   ⟨cmd⟩ cool  ✓ Ready     ⟡ Local data  TS  UTF-8    │
└──────────────────────────────────────────────────────────────────────┘
                （.toast 固定 right:20 bottom:39，main.css:3502-3503）
```

---

## 2. 頁面骨架（Page anatomy）

### 2.1 六個頁面的實際結構

| 頁面 | 容器 | 標題區 | 工具列 | 內容區 | 空狀態 | 證據 |
|---|---|---|---|---|---|---|
| 工作台 Home | `.content-wrap` | **`.welcome-line`**（非 PageHeading），eyebrow「YOUR LEARNING WORKSPACE」 | 無（右側僅「重新整理」按鈕在標題列內） | `.stats-grid`(4) → `.hero-card` → `.section-heading` → `.quick-grid`(3) | 無（新使用者仍看到全套統計與 hero） | `App.tsx:1251-1336` |
| 帳號 Accounts | `.content-wrap` | `PageHeading`（無 action） | `.panel.login-panel` 表單本身即工具列 | `.section-heading` → `.account-table` | `.empty-state.compact` | `App.tsx:1482-1568`、`1723` |
| 課程 Courses | `.content-wrap` | `PageHeading`，**action 放的是 `.selection-chip`（狀態晶片）而非按鈕** | `.panel.add-url-panel` 新增表單 | `.section-heading` → `.course-list` | `.empty-state` | `App.tsx:1816-1876`、`2018` |
| 報表 Reports | `.content-wrap` | `PageHeading`，action = 主按鈕 | `.report-toolbar`（欄位＋來源標籤） | `.report-table`（head+rows） | `.empty-state`（在表格內） | `App.tsx:2048-2126` |
| 網路 Network | `.content-wrap` | 詳情檢視與列表檢視**各自 return 一套** `PageHeading` | action = `.network-view-tabs`；列表上方另有 `.network-toolbar` 與 `.network-mode-tabs-wrap` | `.network-list` / `.network-session-detail` | `.empty-state` | `App.tsx:2260`、`2360`、`2610` |
| 設定 Settings | **`.content-wrap.settings-page`**（多一個 class，`padding-bottom:48px` 覆寫） | 分類頁：`.settings-back-button` + 分類卡；分類內頁：`PageHeading` | `.settings-category-tools`（僅分類頁） | `.settings-category-grid` / `.preference-controls` | 無 | `App.tsx:2823`、`main.css:2132-2134` |

### 2.2 共同模式（現況歸納）

實際上 6 頁共用同一條骨架，只有兩處命名分叉：

```
.content-wrap  (min(100%,1100px), padding 29/34/40)      main.css:528-532
 ├─ [A] .page-heading  ← PageHeading 元件，App.tsx:1212-1233
 │      margin: 3px 0 24px                                main.css:560-563
 │      h1 22px/650 + p 11px + 右側 action                main.css:568-578
 │   或 [B] .welcome-line（僅 Home）
 │      margin-bottom: 25px（與 A 的 24 不同）             main.css:534-541
 │      h1 23px/650（與 A 的 22 不同）                     main.css:543-550
 ├─ 工具列：.report-toolbar / .panel(表單) / .network-view-tabs
 │      常見 margin-bottom: 22px（.login-panel 945-947、.add-url-panel 1443-1445）
 │      或 14px（.report-toolbar 1617-1621）
 ├─ 區塊標題：.section-heading  margin: 17px 0 11px        main.css:856-860
 ├─ 內容容器：.account-table / .course-list / .report-table / .network-list
 │      border 1px + radius 7px + background #14171c      main.css:1079-1091、1471-1476、1644-1650
 └─ 註腳：.report-disclaimer（mb 0, mt 11）／.privacy-note（mt 15）
```

### 2.3 標準骨架（提案）

| 區 | 內容 | 對齊／間距（收斂後） | 說明 |
|---|---|---|---|
| 1 標題區 | eyebrow（可省）＋ h1 ＋ 一句說明 ＋ 右側**單一** action | `margin: 0 0 24px`；h1 22×scale；p 11×scale | 全站只用 `PageHeading`，廢除 `welcome-line` |
| 2 工具列（可選） | 篩選／輸入／主要動作 | `margin-bottom: 16px`；單一列，不換行 | 同頁最多一列工具列；多餘的動作降級到列內的選單 |
| 3 區塊標題（可選） | h2 12×scale ＋ 計數晶片 ＋ 一行說明 | `margin: 16px 0 8px` | `.section-heading` 現為 17/11（`main.css:856-860`），收斂到 16/8 |
| 4 內容容器 | `.account-table` 等 | `border 1px; radius 8; overflow` 視情況 | 四個容器統一 radius（現為 7，見 4.2） |
| 5 註腳 | 免責、隱私、提示 | `margin-top: 16px` | 現為 11（`main.css:1631-1635`）與 15（`main.css:1038-1042`），收斂 |
| 6 空狀態 | icon ＋ strong ＋ span | 置中；`min-height: 174px`（compact 110） | 現有 `.empty-state` 已足夠（`main.css:1393-1423`） |

### 2.4 目前偏離標準骨架之處

| # | 偏離 | 位置 | 有功能理由？ |
|---|---|---|---|
| P1 | Home 用 `.welcome-line` 而非 `PageHeading`，h1 23px vs 22px、margin-bottom 25 vs 24 | `App.tsx:1252`、`main.css:534-566` | **否**——差 1px 與 1px 標題字級，屬歷史累積 |
| P2 | Courses 的 PageHeading action 是 `.selection-chip`（唯讀狀態） | `App.tsx:1823-1827` | **半是**——它要表達「目前使用哪個帳號」，但更適合放在工具列或側欄 |
| P3 | Network 有**兩層**工具列（action 內的 view tabs ＋ 外層 mode tabs ＋ network-toolbar） | `App.tsx:2362-2440` | **是**——view（進行中/歷史）與 mode（有頭/無頭/直接）是兩組獨立維度，但目前視覺權重相同，需分主次 |
| P4 | Network 詳情與列表是兩個 return，各自組一套骨架 | `App.tsx:2260` 與 `2360` | **是**——兩種檢視本來就不同；但應共用 `PageHeading` 而非各寫各的 |
| P5 | Accounts 的標題區沒有 action，主要動作藏在 panel 內 | `App.tsx:1483-1487` | **否**——「新增帳號」永遠展開佔版面，即使已有 5 個帳號 |
| P6 | Settings 容器多一個 `.settings-page` 覆寫 padding-bottom 48 | `App.tsx:2823`、`main.css:2132-2134` | **是**——分類卡片網格底部需要呼吸空間，但應併入標準 padding |
| P7 | Home 沒有空狀態：0 帳號 0 課程時仍顯示 4 張統計卡＋hero＋3 張快速卡 | `App.tsx:1263-1336` | **否**——8 個等重區塊對新使用者無資訊（詳見第 9 章 Q1） |

---

## 3. 元件盤點（Component inventory）

> 使用次數為 `grep -o 'className="[^"]*<name>[^"]*"' App.tsx components/*.tsx` 與
> 模板字串 `className={\`…\`}` 的計數（指令見附錄 A-10），模板字串中的動態 class 計入「template」欄。

### 3.1 按鈕（Button）

| 實作 | 定義 | 次數 | 尺寸 |
|---|---|---|---|
| `.button`（基底） | `main.css:569-586` | literal 35 | `min-height: 34px`（574）、`padding: 0 12px`、`radius 6`、`font 11×scale`、`weight 560` |
| `.button.primary` | `main.css:621-628` | 5（＋模板內若干） | 同上，`filter: brightness(1.12)` hover |
| `.button.secondary` | `main.css:632-639` | 8 | 同上，hover 換底＋邊框 |
| `.button.ghost` | `main.css:643-647` | 3 | 同上，透明底 |
| `.button.danger`／`.danger-hover` | `main.css:1387-1391`（danger-hover） | 3＋2 | 只有 hover 樣式，**沒有獨立的 base `.danger` 宣告**（危險底色由 inline 或其他規則提供）→ 屬未完成的變體 |
| `.button.mode-button.{headed,headless,direct}` | `main.css:593-615` | 4 | `weight 650`、三色實底 |
| `.button.small` | `main.css:652-656` | 與 mode-button 搭配 4 次 | `min-height: 29px`、`padding: 0 9px`、`font 10×scale` |
| `.button.help-button` | 無獨立樣式 | 1（`App.tsx:1012`） | **沒有 onClick，是空按鈕**（見 7.5） |
| `.icon-button` | `main.css:160-163` | 11 | 30×28、radius 6（高 28 於 `main.css:162`） |
| `.mini-icon-button` | `main.css:166-169` | 9 | 25×25、radius 5 |
| `.window-control` | `main.css:179-187` | 3 | 10×10 圓點 |
| `.font-size-step` | `main.css:2443-2452` | 2 | `min-width:32px`、`height:28px`（`main.css:2445`）、radius 5 |
| `.settings-back-button` | `main.css:2258-2270` | 1 | `min-height:30px`（`main.css:2262`） |
| `.network-mode-delete` | `main.css:1696-1711` | 3 | 29×29、radius 5 |
| `.network-selection-delete` | `main.css:1783-1791` | 1 | `min-height:29px`（邊框於 `main.css:1785`） |

**判定**：`.icon-button`／`.mini-icon-button`／`.font-size-step`／`.network-mode-delete`
四者本質是同一件事（方形圖示鈕），尺寸 30×28 / 25×25 / 32×28 / 29×29 四個值，
屬**歷史累積**（`.mini-icon-button` 是 `.icon-button` 的縮小版，radius 從 6 變 5 沒有功能理由）。

**判定**：`.button.small`（29px）與 `.network-selection-delete`（29px）、`.settings-back-button`（30px）
都是「小號按鈕」，高度 29/30 之差無功能理由。

### 3.2 標題容器

| 實作 | 定義 | 使用 | 尺寸 |
|---|---|---|---|
| `.page-heading`（PageHeading 元件） | `main.css:560-567`（`margin: 3px 0 24px` 於 562、`h1 22px` 於 565）；元件 `App.tsx:1212-1233` | 5 頁 | `margin: 3px 0 24px`；h1 22px/650；p 11px |
| `.welcome-line` | `main.css:534-558`（h1 與 page-heading 共用規則在 543-549，23px 於 547） | 1（Home） | `margin-bottom: 25px`；h1 23px/650 |
| `.section-heading` | `main.css:856-874`（`margin: 17px 0 11px` 於 860） | 4（Home/Accounts/Courses/…） | `margin: 17px 0 11px`；h2 12px/600；p 9px |
| `.panel-heading` | `main.css:949-967` | 2（login-panel、add-url-panel） | `gap 11`、`mb 15`；h2 12px/620；p 10px |
| `.hero-card` 標題組 | `main.css:769-784`（`h2 17px/620` 於 769） | 1 | h2 17px/620、p 10px |
| `.settings-section-heading` | `main.css:2286-2293` | 分類內頁 | `grid-column: 1/-1` |

**判定**：h2 出現 12px(600)、12px(620)、17px 三種字級／字重，`margin-bottom` 有 11、15、24、25 四個值 →
**歷史累積**，應統一為：h1 22／h2 12／h3 11，mb 24／16／8。

### 3.3 卡片／面板（Card / Panel）

| 實作 | 定義 | 尺寸 | 底 |
|---|---|---|---|
| `.panel` | `main.css:938-943` | `padding 17`、radius 8 | `#15181e` |
| `.stat-card` | `main.css:665-674` | `min-height 121`、`padding 14px 15px 12px`、radius 8 | `linear-gradient(145deg,#171a20,#14171c)` |
| `.quick-card` | `main.css:881-893` | `padding 12`、radius 7 | `#15181e` |
| `.hero-card` | `main.css:733-747` | `min-height 209`、`padding 22px 25px`、radius 9 | 雙層漸層＋radial |
| `.settings-category-card` | `main.css:2168-2181` | `min-height 82`、`padding 15`、radius 9 | `#171a20` |
| `.settings-about-card` | `main.css:2228-2237` | `min-height 64`（2233）、`padding 12px 15px` | 無（複用 `.panel`，`grid-column: 1/-1` 於 `main.css:2230`） |
| `.account-table`/`.report-table`/`.course-list`/`.network-list` | `main.css:1079-1091`、`1471-1476`、`1644-1650` | radius 7 | `#14171c` |
| `.network-session-detail` | `main.css:1937-1942` | radius 7 | `#14171c` |

**判定**：`padding` 有 17 / (14,15,12) / 12 / 22,25 / 15 / 12,15 六組；`radius` 有 7/8/9 三種；
底色有 `#15181e`、`#171a20`、`#14171c`、漸層四種 → **歷史累積**（`.panel` 與 `.quick-card` 底色相同但 padding 17 vs 12、radius 8 vs 7，無功能理由）。

### 3.4 表格

| 表 | 容器 | head | row | 欄定義 |
|---|---|---|---|---|
| 帳號 | `.account-table`（`main.css:1086-1088` overflow visible） | `.table-head.account-row`（`App.tsx:1564-1571`） | `.table-row.account-row`（`main.css:1134-1137`，`min-height 74`、`padding 0 13`） | `minmax(145px,1.1fr) minmax(190px,1.6fr) minmax(125px,1fr) minmax(145px,1fr) 112px`＋`gap 10`（`main.css:1120-1124`） |
| 報表 | `.report-table`（`main.css:1077-1079` overflow hidden） | `.table-head.report-row`（`App.tsx:2079`） | `.table-row.report-row`（`main.css:1605-1612`） | `0.9fr 1.15fr 1.15fr 0.9fr 1fr`＋`gap 12`＋`padding 0 15` |
| 網路事件 | `.network-session-events`（`main.css:2025`） | 無 head | `.network-event`（`main.css:2049-2060`，`min-height 39`） | `35px 50px minmax(100px,1fr) 42px minmax(60px,auto) 65px`＋`gap 9`（2051） |
| 課程 | `.course-list`（flex 列） | 無 | `.course-item`（`main.css:1518-1527`，`min-height 59`） | flex + `gap 11` |

`.table-head` 通用：`min-height: 32px`、`padding: 0 13px`、`font 8×scale`、`uppercase`、`letter-spacing .07em`
（`main.css:1094-1104`）。`.table-row` 通用：`min-height: 49px`、`border-bottom 1px`、`font 10×scale`（`main.css:1107-1116`）。

### 3.5 表單欄位

| 實作 | 定義 | 尺寸 |
|---|---|---|
| `.field` | `main.css:999-1006` | `flex column; gap 6`；label `span` 10×scale；`small` 9×scale |
| `.field input/select` | `main.css:1011-1024` | `height: 34px`、`padding 0 10px`、`radius 5`、`font 11×scale` |
| `.add-url-panel textarea` | `main.css:1443-1452` | `min-height 74`、`padding 10`、`radius 5` |
| `.search-box` | `main.css:490-503` | `220×27`、`radius 5`、內含 input `font 10×scale` |
| `.preference-control` | `main.css:2395-2402` | `min-height 33`、`flex; justify-content: space-between`；label 10×scale |
| `.preference-control select` | `main.css:2666-2673`（另一處 `2466-2468` 只是 `max-width: 60%`） | `min-width 130`、`height 28` |
| `.preference-control input[type=color]` | `main.css:2470-2477` | `42×26` |
| `.inline-field`（報表帳號選擇） | `main.css:1594-1596` | `width: min(420px, 65%)` |

**判定**：輸入框高度 34 / 28 / 27 三個值；`.field` 與 `.preference-control` 是兩套 label＋control
排版（垂直 vs 水平）——**這是功能差異（表單 vs 設定列），應保留兩種，但共用控制項尺寸與字級**。

### 3.6 對話框

| 實作 | 定義 | 尺寸 |
|---|---|---|
| `.account-login-backdrop` | `main.css:1267-1275` | `position: fixed; inset: 0; padding 24; z-index 30`、遮罩 `rgb(0 0 0 / 62%)` |
| `.account-login-dialog` | `main.css:1277-1288` | `width: min(420px,100%)`、`padding 22`、`radius 10`、`gap 14`、`box-shadow 0 18px 60px` |
| `.account-login-menu` | `main.css:1343-1351` | `position: absolute`、`min-width 112`、`padding 5`、`radius 6`、item `padding 6px 9px` |
| `.cli-color-menu-list` | `main.css:2603-2613` | `position: absolute`、`max-height 380`（2609）、`radius 6` |
| `.terminal-profile-menu`／`.terminal-context-menu` | `main.css:2856-2863` | `min-width 220/150`、`padding 5`、`radius 6` |

**判定**：5 種浮層各自實作，`radius` 6/6/6/10、內距 5/5、min-width 112/150/220 →
**功能差異（modal vs popover vs menu）存在，但尺寸與圓角應收斂**；對話框是唯一該用 10（收斂為 8 或保持 10）的。

### 3.7 標籤／徽章（Badge / Tag）

| 實作 | 定義 | 尺寸 |
|---|---|---|
| `.status-pill` | `main.css:1206-1221` | `padding 4px 7px`、`radius 20`、`font 9×scale`、內含 5px 指示點 |
| `.network-mode`／`.session-status` | `main.css:1991-2013` | `padding 3px 6px`、`radius 4`、`font 9×scale`、uppercase |
| `.selection-chip` | `main.css:1425-1435` | `padding 7px 9px`、`radius 6`、`font 10×scale` |
| `.heading-count` | `main.css:1067-1074` | `min-width 18`、`height 18`、`radius 5`、`font 9×scale` |
| `.account-selected-label` | `main.css:1190-1198` | `padding 2px 5px`、`radius 4`、`font 8×scale` |
| `.account-selected-*`（帳號選取列） | `main.css:1127-1132` | 4 個 CSS 變數（hover/selected bg/outline/text） |

**判定**：pill(radius 20)、tag(radius 4)、chip(radius 6) 三種形狀各有用途，**可保留三型**；
但 `.selection-chip`（radius 6、padding 7/9）與 `.button.ghost` 視覺近似，易混淆 → 需明確規則（見 3.10）。

### 3.8 提示（Toast）與忙碌指示

| 實作 | 定義 | 尺寸 |
|---|---|---|
| `.toast`（success/error/info） | `main.css:3500-3543` | `position: fixed; right 20; bottom 39; max-width min(440px, 100vw-40); padding 11px 12px; radius 7; z-index 20` |
| `.busy-indicator` | `main.css:3544-3557` | `fixed; right 18; bottom 40; padding 7px 10px; radius 6; z-index 15` |

**判定**：兩者 `bottom` 39/40、`right` 20/18 各差 1-2px，屬**歷史累積**；`.toast` 無進入／離開動畫
（全站只有 `@keyframes spin`，`main.css:3564-3567`）。

### 3.9 分頁／切換（Tabs）

| 實作 | 定義 | 次數 | 語意 |
|---|---|---|---|
| `.network-view-tabs` | `main.css:1663-1683` | 1 | `button.selected` 換底；**無 `role="tablist"`**（`App.tsx:2369-2385`） |
| `.network-mode-tabs`（有頭/無頭/直接） | `main.css:1672-1684`、`1802-1876` | 3 組 | 有計數晶片；**有** `role="tablist"` ＋子項 `role="tab"`＋`aria-selected`（`App.tsx:2399-2410`）✅ |
| `.network-detail-format-tabs` | `main.css:1965-1987` | 1 | `role="tablist"` + `role="tab"` + `aria-selected`（`App.tsx:2313-2333`）✅ |
| `.terminal-tab` | `main.css:2803-2817` | 1 組 | `div role="button" tabIndex=0` ＋鍵盤處理（`TerminalPanel.tsx:365-386`）；內部再嵌一個 close `button` |
| `.settings-category-card`（分類入口） | `main.css:2168-2181` | 7 | `button`，有 hover `translateY(-1px)` |

**判定**：只有 `.network-detail-format-tabs` 做到 ARIA tabs；其餘「看起來像分頁」的東西是
普通按鈕群 → **功能不缺，但語意不一致（歷史累積）**。

### 3.10 最小標準元件集（提案）

| # | 名稱 | 變體 | 尺寸 | 狀態 | 使用規則 |
|---|---|---|---|---|---|
| 1 | `Button` | `primary`｜`secondary`｜`ghost`｜`danger`｜`mode(headed\|headless\|direct)` | `md: min-height 34×scale, padding 0 12`；`sm: 29×scale, padding 0 9` | hover：primary `brightness(1.12)`、secondary 換底、ghost `#ffffff0d`、danger 換紅底；focus：`outline: 2px solid var(--accent); offset 2px`（`main.css:36-40`）；disabled：`border #697384 / bg #394353`（`main.css:585-591`） | 一列只有一個 primary；`mode` 只出現在課程列的開啟動作 |
| 2 | `IconButton` | `default`｜`subtle`（原 mini） | `md: 30×28, r6`；`sm: 25×25, r4`（收斂自 5） | 同 Button 的 hover/focus | **必須**有 `aria-label` 或 `title`；不用於表達狀態 |
| 3 | `Panel` | `plain`｜`with-heading` | `padding 16`（收斂自 17）、`r8`、`border 1px` | focus 依內容 | 一頁最多 1 個 `with-heading`；其餘用 `plain` |
| 4 | `Card`（取代 stat/quick/hero/category） | `stat`｜`action`｜`feature` | 內距統一 `16`；`r8` | action 型可 hover | feature 型全站最多 1 張（目前是 hero） |
| 5 | `Field` | `stacked`（表單）｜`inline`（設定列） | control `height 34×scale / r5 / font 11×scale`；設定列 control `28×scale` | focus 同上 | label 一律 10×scale；hint 9×scale 且只在必要時出現 |
| 6 | `Table` | `accounts`｜`reports`｜`events` | head `min-height 32×scale`、row `min-height 49×scale`（account 74×scale） | row hover 底色；selected 用 `--account-selected-*` | 欄寬規則見第 5 章 |
| 7 | `SectionHeading` | `with-count` | `margin 16px 0 8px` | — | h2 12×scale；說明 9×scale；一行 |
| 8 | `PageHeading` | `action-slot` | `margin 0 0 24px` | — | **全站唯一標題元件**；action slot 只放按鈕，不放狀態晶片（狀態移到工具列） |
| 9 | `EmptyState` | `default`｜`compact` | `min-height 174 / 110` | — | 每個內容容器必備；文案需含「下一步做什麼」 |
| 10 | `Badge` | `pill`（r20）｜`tag`（r4）｜`count`（18×18） | 見 3.7 | — | pill 只表示狀態，tag 只表示類型，count 只表示數量 |
| 11 | `Toast` | `success`｜`error`｜`info` | `right 20 / bottom 39 / r7 / padding 11px 12px` | 自動關閉（現況手動） | 與 `.busy-indicator` 共用同一定位基準 |
| 12 | `Dialog` | `confirm`｜`form` | `width min(420px,100%)`、`padding 22`、`r10` | focus trap（**目前未實作，未驗證**） | 僅帳號登入密碼提示使用 |
| 13 | `Menu` | `popover` | `padding 5`、`r6`、item `padding 6px 9px` | Esc 關閉（`.cli-color-menu` 已有，`App.tsx:208-216`） | 同一專案內全部改用此尺寸 |
| 14 | `Tabs` | `segmented`（有底框）｜`underline`（終端） | segmented `padding 3`、`r6`；underline 無框 | **必須**帶 `role="tablist"/"tab"`＋`aria-selected` | 目前 `.network-mode-tabs`（`App.tsx:2399`）與 `.network-detail-format-tabs`（`App.tsx:2313`）已做到，`.network-view-tabs`（`App.tsx:2369`）需補齊 |

---

## 4. 尺度系統（Scales）

### 4.1 現況統計（指令與原始輸出見附錄 A）

**字級**（`grep -o "font-size: [^;]*;" main.css | sort | uniq -c | sort -rn`）

```
50 font-size: calc(9px * var(--ui-font-scale, 1));
26 font-size: calc(10px * var(--ui-font-scale, 1));
11 font-size: calc(8px * var(--ui-font-scale, 1));
11 font-size: calc(11px * var(--ui-font-scale, 1));
 5 font-size: calc(12px * var(--ui-font-scale, 1));
 1 font-size: calc(23px * var(--ui-font-scale, 1));
 1 font-size: calc(22px * var(--ui-font-scale, 1));
 1 font-size: calc(20px * var(--ui-font-scale, 1));
 1 font-size: calc(17px * var(--ui-font-scale, 1));
 1 font-size: calc(16px * var(--ui-font-scale, 1));
 1 font-size: calc(15px * var(--ui-font-scale, 1));
 1 font-size: 13px;                      ← main.css:56，唯一沒乘縮放
```

**圓角**

```
15 × 7px   15 × 5px   11 × 6px   8 × 4px   6 × 8px   4 × 50%
 3 × 9px   1 × 3px    1 × 10px   1 × 20px  1 × 22px  1 × 0
```

**間距**

```
gap: 8px×14, 9px×11, 7px×10, 12px×10, 3px×7, 6px×6, 11px×5, 5px×4,
    4px×4, 2px×4, 10px×4, 13px×2, 24/20/16/14px×1
padding（單值）: 3px×3, 2px×3, 12px×3, 5px×2, 24px×2, 10px×2, 7/6/4/22/17/16/15px×1
margin-top: 3px×4, 8px×3, 5px×3, 10px×3, 6px×2, 15px×2, 14px×2, 4/12/11px×1
margin-bottom: 9px×2, 8px×2, 22px×2, 10px×2, 3/25/24/17/15/14px×1
```

**固定寬／高**

```
width 出現：29px×4, 5px×3, 6/31/30/28/220/18/15px×2，其餘 1
height 出現：29px×7, 28px×6, 30px×5, 32px×4, 5px×3, 48px×3, 36px×3, 34px×3,
            23px×3, 74/6/43/42/31/25/18/15px×2，其餘 1
```

**陰影**（17 種，`grep -o "box-shadow: [^;]*;"`）
`0 0 8px #e5687066`×2、`0 0 8px #b18b4c55`×2、`none`×2，
其餘各 1：`0 8px 32px #0008`、`0 8px 24px rgb(32 42 54 / 18%)`、`0 8px 24px rgb(0 0 0 / 40%)`、
`0 8px 22px #0008`、`0 18px 60px rgb(0 0 0 / 42%)`、`0 10px 28px #0008`、`0 0 8px #62d7a655`、
`0 0 45px #55c8b322`、`0 0 18px #85e3cf`、`0 0 0 1px #0002`、`inset 4px 0 #fff`、
`inset 4px 0 #101318`、`inset 3px 0 var(--account-selected-outline)`、`inset 0 0 0 1px var(--accent)`

**動畫**：`transition` 7 處（`main.css:157, 208, 291, 582, 892, 2180, 2317`），
`@keyframes` 只有 `spin`（`main.css:3564-3567`）。

### 4.2 收斂級距（提案）

#### 字級（**全部乘 `var(--ui-font-scale, 1)`**）

| 級距名 | 值 | 用途 | 對應現況 |
|---|---|---|---|
| `--fs-micro` | 9 | 狀態列、表頭、眉標、註腳、tab 說明 | 8（11 處）→ 9；9（50 處）→ 9 |
| `--fs-caption` | 10 | 次要說明、欄位標籤、統計標籤 | 10（26 處） |
| `--fs-body` | 11 | 內文、按鈕文字、輸入框 | 11（11 處） |
| `--fs-label` | 12 | 導覽項目、小標 h2、設定列標題 | 12（5 處） |
| `--fs-emphasis` | 14 | 強調數字（原 15） | 15 → 14 |
| `--fs-h3` | 17 | hero 標題 | 17 |
| `--fs-stat` | 20 | 統計數值 | 20 |
| `--fs-h1` | 22 | 頁面標題 | 22、23 → 22 |
| （基準） | 16 | `.app-shell` 繼承基準（`main.css:66`） | 維持不變——它是繼承底，改動影響面無法預估 |
| （特例） | `.app-loading` 13px（`main.css:49` 定義、字級於 `main.css:56`） | 改為 `calc(12px * var(--ui-font-scale,1))`，使全站沒有未縮放字級 |

> 收斂效果：12 個不同字級 → **8 個**（8px 絕跡，最小字級從 8 提到 9）。

#### 圓角

| 級距 | 值 | 用途 | 對應現況 |
|---|---|---|---|
| `--r-flat` | 0 | 表格容器、topbar、statusbar、分隔線 | 0 |
| `--r-xs` | 4px | 標籤（tag）、菜單項、小色塊 | 3 → 4、4 → 4 |
| `--r-sm` | 6px | 按鈕、輸入框、tab、浮層選單、icon-button | 5 → 6、6 → 6 |
| `--r-md` | 8px | 卡片、面板、表格容器、對話框 | 7 → 8、8 → 8、9 → 8、10 → 8 |
| `--r-pill` | 999px | 狀態 pill、頭像、圓點 | 20、22 → 999；50% → 50%（指示點） |

> 12 種 → **5 種**。

#### 間距（4 的倍數＋2 的微值）

| 級距 | 值 | 對應現況（`gap`／`padding`／`margin`） |
|---|---|---|
| `--s-0` | 0 | — |
| `--s-micro` | 2px | 2、3 |
| `--s-1` | 4px | 4、5 |
| `--s-2` | 8px | 6、7、8、9、10 |
| `--s-3` | 12px | 11、12、13 |
| `--s-4` | 16px | 14、15、16、17 |
| `--s-5` | 24px | 20、22、24、25 |
| `--s-6` | 32px | 29、34（間距用途） |
| `--s-7` | 40px | 40（`content-wrap` 下內距） |

> **具體到本案的三個修正**：`.content-wrap` 的 `29px 34px 40px` → `24px 32px 40px`；
> `.panel` 的 `17px` → `16px`；`.section-heading` 的 `17px 0 11px` → `16px 0 8px`。

### 4.3 哪些尺寸隨字級縮放、哪些不縮放

**必須縮放（容器內含文字，字級 24 時會溢出）**——改為 `calc(<值>px * var(--ui-font-scale, 1))`：

| 元素 | 現值 | 位置 |
|---|---|---|
| `.button` / `.button.small` 最小高 | 34 / 29 | `main.css:574` / `653` |
| `.field input/select` 高 | 34 | `main.css:1029` |
| `.search-box` 高 | 27 | `main.css:495` |
| `.table-head` 最小高 | 32 | `main.css:1097` |
| `.table-row` 最小高 | 49 | `main.css:1108` |
| `.table-row.account-row` 最小高 | 74 | `main.css:1135` |
| `.course-item` 最小高 | 59 | `main.css:1522` |
| `.network-event` 最小高 | 39 | `main.css:2054` |
| `.network-session-header` 最小高 | 48 | `main.css:1909` |
| `.network-selection-toolbar` 最小高 | 42 | `main.css:1753` |
| `.settings-category-card` 最小高 | 82 | `main.css:2172` |
| `.settings-about-card` 最小高 | 64 | `main.css:2235` |
| `.settings-row` 最小高 | 69 | `main.css:2681` |
| `.cli-report-color-row` 最小高 | 62 | `main.css:2551` |
| `.preference-control` 最小高 | 33 | `main.css:2400` |
| `.settings-category-tools` 最小高 | 32 | `main.css:2147` |
| `.nav-item` 高 | 36 | `main.css:279` |
| `.account-mini` 高 | 34 | `main.css:342`（選擇器 337） |
| `.icon-button` 30×28、`.mini-icon-button` 25×25 | 30/28/25 | `main.css:162` / `168` |
| `.font-size-step` 高 | 28 | `main.css:2445` |
| `.cli-color-menu-trigger` 高 | 30 | `main.css:2594` |
| `.preference-control select` 高 | 28 | `main.css:2667` |
| `.settings-about-card` 最小高 | 64 | `main.css:2233`（選擇器 2228） |
| `.empty-state` 最小高 | 174 / 110 | `main.css:1398` / `1422` |

**不縮放（框架骨架，縮放會改變版面比例與終端可用空間）**：

| 元素 | 值 | 理由 | 位置 |
|---|---|---|---|
| `.titlebar` 高 | 48 | 視窗拖曳列，OS 級 chrome | `main.css:71` |
| `.page-topbar` 高 | 43 | 麵包屑列，屬外殼 | `main.css:468` |
| `.statusbar` 高 | 23 | 狀態列屬外殼；**其字級也應改為不縮放**（現為 `calc(8px*scale)` 於 `main.css:3479`，字級 24 時 8×1.846=14.8px 行高 23.7px > 23px 會溢出）→ 建議固定 9px | `main.css:3473` / `3479` |
| `.sidebar` 寬 | 236 / 205 / 56 | 主內容可用寬度的關鍵 | `main.css:201` / `3572` / `256` |
| `.terminal-dock` 下限 | 160（水平 260） | 終端可操作底線 | `main.css:2743` / `2752` |
| `.terminal-split-handle` | 5 | 拖曳命中區 | `main.css:2759` |
| `.terminal-toolbar` 高 | 32 | 終端 chrome（其文字 9×scale 在字級 24 時 16.6px 行高 26.6px，仍放得下 32px）→ **可維持固定** | `main.css:2789` |
| `.content-wrap` 寬 | `min(100%,1100px)` | 版心 | `main.css:529` |
| `.network-raw-data` 高 | `min(68vh,760px)` | iframe | `main.css:2037`（選擇器 2036） |
| `.network-course-progress-log` 上限 | 320 | 內嵌 log 視窗 | `main.css:1653`（選擇器 1651） |
| `.cli-color-menu-list` 上限 | 380 | 菜單可視上限 | `main.css:2609` |

> **未驗證**：以上「必須縮放」清單是依 `min-height`/`height` 與內含字級的算術推導，
> 尚未在字級 24 實測每一列的溢出量。

---

## 5. 表格與長內容規則

### 5.1 現況（附證據）

| 表 | 欄定義 | 位置 | 問題 |
|---|---|---|---|
| 帳號 | `minmax(145px,1.1fr) minmax(190px,1.6fr) minmax(125px,1fr) minmax(145px,1fr) 112px`，`gap 10`，row `padding 0 13px` | `main.css:1120-1124`、`1135-1136` | **固定最小寬合計 757 + 26 padding + 2 border = 785px**；1000×680 時內容淨寬只有 747px → 溢出約 38px（推導，未實機驗證） |
| 報表 | `0.9fr 1.15fr 1.15fr 0.9fr 1fr`，`gap 12`，`padding 0 15px` | `main.css:1605-1612` | 全彈性，不會溢出；但欄寬隨視窗漂移，數字欄不對齊 |
| 網路事件 | `35px 50px minmax(100px,1fr) 42px minmax(60px,auto) 65px`，`gap 9` | `main.css:2049-2054`；<1150px 改為 5 欄 `main.css:3465-3467` | **子元素是條件渲染**（`App.tsx:2641-2644`：`status`、`message` 可缺），欄數固定但孩子數 4–7 → 缺欄時後面欄位往前補，**不同列的欄位不對齊** |
| 課程 | flex，`gap 11`，`min-height 59` | `main.css:1518-1527` | 無固定寬，靠 `course-meta` 的 `min-width:0` 與 ellipsis（`main.css:1564-1572`） |

### 5.2 欄位分類規則（提案）

| 類型 | 欄位 | 規則 |
|---|---|---|
| **固定**（不可擠壓） | 動作列（112px）、狀態碼（42/65px）、勾選框（15px）、序號（35px/20px） | `width: <值>` 或 `auto`；**不使用 `fr`** |
| **彈性且可截斷**（文字主體） | 帳號名、Email、課程 URL、事件 URL、訊息 | `minmax(0, <n>fr)` ＋ `min-width: 0` ＋ `overflow:hidden; text-overflow:ellipsis; white-space:nowrap` |
| **彈性不可截斷**（數值） | 學習時間、月份、狀態文字 | `minmax(<min>px, auto)`；必要時整欄可橫向捲動 |

### 5.3 截斷／換行／捲動規則

1. **截斷**：單行文字一律 ellipsis。已正確的：`.table-muted`（`main.css:1199-1206`）、
   `.event-url`（`main.css:2080-2085`）、`.event-message`（`main.css:2094-2098`）、
   `.account-mini-name`（`main.css:374-377`）、`.course-meta span`（`main.css:1564-1572`）。
   `title` 屬性提供完整值（`App.tsx:2639` 的 event-url、課程 URL 列）。
2. **換行**：只有三類——cookie 狀態說明（`.cookie-status small`，`overflow-wrap: anywhere`，`main.css:1263`）、
   長免責文字（`.report-disclaimer`）、pre 型內容（`.network-details pre`）。
3. **水平捲動層級**：**表格自身不開橫向捲軸**（目前 `page-content` 承擔全部 x/y 捲動）。
   新規則：橫向捲動放在**內容容器**（`.account-table` 等）一層，`overflow-x: auto`，
   讓 `.page-content` 只負責頁面垂直捲動。
   > **阻礙**：`.account-table` 必須 `overflow: visible` 才能顯示 `.account-login-menu` 絕對定位浮層
   > （`main.css:1086-1088`、`1343`）。改為 `overflow-x: auto` 會裁切菜單。
   > **最小解法**：菜單改為 `position: fixed` 並用 JS 對齊觸發鈕，或在表格容器外渲染。
   > 此改動屬行為變更，**留到 U5（帳號頁）處理，本輪不動**。
4. **數值對齊**：時間欄 `text-align: right` 或等寬字（`.event-url` 已用 Cascadia Code，`main.css:2058`）。

### 5.4 字級 24 的保障

| 手段 | 說明 |
|---|---|
| 文字欄一律 `minmax(0, nfr)` | 可無限壓縮，絕不撐破容器 |
| 固定欄不乘縮放 | 112px 動作列若乘 1.846 會變 207px，反而更擠；固定欄維持 px |
| 內距與行高乘縮放 | `padding: 0 13px` → `0 calc(13px * var(--ui-font-scale,1))`；列高如 4.3 表 |
| 帳號表最小寬的具體改法 | `minmax(0,1.1fr) minmax(0,1.6fr) minmax(0,1fr) minmax(0,1fr) auto`（移除 145/190/125/145 的 px 下限），必要時以 `padding` 補呼吸感 |
| 驗收條件 | 字級 24 ＋ 1000×680 ＋ 三種分割比例下：**沒有 `scrollWidth > clientWidth` 的非可捲動元素、沒有相鄰區塊 bounding box 相交** |

---

## 6. 響應與壓力測試矩陣

### 6.1 維度

| 維度 | 取值 | 說明 |
|---|---|---|
| 字級 `fontSize` | 10、13、18、24 | 對應 `--ui-font-scale` 0.769 / 1.0 / 1.385 / 1.846 |
| 終端比例 `splitRatio` | 0.30、0.50、0.80 | UI 允許範圍的下限／預設附近／上限（`App.tsx:1134`） |
| 分割方向 | vertical（預設）、horizontal | `storage.ts:50` |
| 視窗 | 1000×680、1360×900 | `index.ts:803-806` |
| 主題方向 | dark（預設）、light | `storage.ts:48`、`main.css:2952+` |
| 頁面 | home、accounts、courses、reports、network、settings | `App.tsx:996-1120` |

**全矩陣 = 4×3×2×2×2×6 = 576 組**（不切實際）。採分層抽樣：

### 6.2 核心驗收集（24 組，必測）

| # | 字級 | 比例 | 方向 | 視窗 | 主題 | 頁面 | 關注點 |
|---|---|---|---|---|---|---|---|
| 1 | 13 | 0.68 | v | 1000×680 | dark | home | 基準 |
| 2 | 13 | 0.68 | v | 1000×680 | light | home | 淺色對比（另案） |
| 3 | 10 | 0.30 | v | 1000×680 | dark | accounts | 極小字＋極小內容區 |
| 4 | **24** | **0.30** | v | **1000×680** | dark | **accounts** | **最高風險**：內容高僅 ~101px ＋ 帳號表 785px > 747px |
| 5 | 24 | 0.68 | v | 1000×680 | dark | accounts | 列高 74×1.846 ≈ 137px，一屏只放得下 2 列 |
| 6 | 24 | 0.80 | v | 1000×680 | dark | accounts | dock 下限 160 介入後 page 僅 401px |
| 7 | 24 | 0.68 | v | 1000×680 | light | accounts | 淺色＋最大字 |
| 8 | 24 | 0.68 | **h** | 1000×680 | dark | accounts | 水平分割下內容淨寬 795−48=747 |
| 9 | 24 | 0.80 | **h** | 1000×680 | dark | courses | dock min-width 260 搶寬 |
| 10 | 10 | 0.68 | v | 1000×680 | dark | courses | 最小字＋課程 URL 截斷 |
| 11 | 24 | 0.68 | v | 1000×680 | dark | courses | 分組列＋「開啟全部」按鈕群擠壓 |
| 12 | 24 | 0.68 | v | 1000×680 | dark | reports | 5 欄數值欄 |
| 13 | 13 | 0.68 | v | 1000×680 | light | reports | — |
| 14 | 24 | 0.30 | v | 1000×680 | dark | reports | 內容區 101px |
| 15 | 24 | 0.68 | v | 1000×680 | dark | network | 6 欄條件欄位不對齊 |
| 16 | 24 | 0.68 | v | 1000×680 | light | network | <1150px 的 5 欄覆寫（`main.css:3465`） |
| 17 | 24 | 0.68 | **h** | 1000×680 | dark | network | 寬度不足 |
| 18 | 24 | 0.68 | v | 1000×680 | dark | settings | 2 欄設定格＋滑桿 |
| 19 | 24 | 0.68 | v | 1000×680 | light | settings | 分類卡拖曳 |
| 20 | 13 | 0.50 | v | 1360×900 | dark | settings | 分類內頁 `preference-controls` 2 欄 |
| 21 | 24 | 0.68 | v | 1360×900 | dark | settings | `color-theme-grid` 4 欄卡片 |
| 22 | 24 | 0.68 | v | 1360×900 | dark | reports | 大視窗＋最大字 |
| 23 | 10 | 0.68 | v | 1360×900 | light | home | — |
| 24 | 24 | 0.80 | v | 1360×900 | dark | home | hero + 4 統計卡 |

### 6.3 「破版」判定標準（可自動化）

| 代號 | 判定 | 實作方式 |
|---|---|---|
| **X-overflow** | 元素 `scrollWidth > clientWidth` 且其 `overflow-x` 不是 `auto/scroll` | 對 `.content-wrap > *` 與每個 `.table-row > *` 掃描 |
| **Y-clip** | 元素 `scrollHeight > clientHeight` 且 `overflow-y: hidden` 且內含文字節點 | 對固定高度容器掃描 |
| **overlap** | 兩個相鄰區塊的 `getBoundingClientRect()` 相交（排除刻意 `position: fixed/absolute`） | 對 `.content-wrap` 的直接子元素兩兩檢查 |
| **truncate-bad** | 文字被裁切但 `text-overflow !== 'ellipsis'` | 檢查 computed style |
| **unfocusable** | 對每個可聚焦元素執行 `el.focus()`，其 `getBoundingClientRect()` 超出視窗 | 鍵盤可達性 |
| **covered** | 點擊 `el` 中心的 `document.elementFromPoint` 不是 `el` 或其子孫 | 被浮層遮住 |
| **scroll-both** | `.page-content` 同時 `scrollWidth>clientWidth` 且 `scrollHeight>clientHeight`（表示表格溢出污染了頁面捲動） | — |

**判定時機**：每個組合載入頁面 → 依序觸發空狀態／有資料兩種資料狀態 → 檢查上述 7 條。

### 6.4 最高風險組合（優先）

1. **字級 24 ＋ split 0.30 ＋ 1000×680 ＋ accounts**：內容淨高 ≈ `566×0.30 − 5 − 69 ≈ 96px`，
   帳號表最小高 74×1.846 ≈ 137px → 表頭＋第一列即溢出。
2. **字級 24 ＋ 1000×680 ＋ accounts（任一比例）**：欄位最小寬 785 > 747 → 橫向溢出。
3. **split 0.80 ＋ 1000×680**：dock `min-height 160` 讓實際比例與 UI 顯示不符（1.3 節）。
4. **light ＋ ≤1150px ＋ network**：`main.css:3465` 把 6 欄改成 5 欄，與條件渲染欄位交互作用。
5. **horizontal ＋ 1000px ＋ 任一页**：內容淨寬只剩 747px，所有表格都要重新算欄寬。

---

## 7. 現況問題清單（只記錄，不修）

### 7.1 重複定義的選擇器（`grep -oE '^[.#][^{]+\{' main.css | sort | uniq -c`，≥2）

```
2 .terminal-context-menu          2 .statusbar            2 .status-branch
2 .settings-note                  2 .report-table         2 .profile-avatar
2 .preference-control select      2 .page-heading h1      2 .page-heading
2 .network-mode.direct            2 .mini-icon-button     2 .course-open-actions
2 .color-theme-card.selected      2 .cli-report-color-list
2 .app-shell[data-theme='light'] .terminal-toolbar
2 .app-shell[data-theme='light'] .network-session-header
2 .app-shell[data-theme='light']  2 .app-shell[data-theme='dark'] .settings-category-card
2 .app-shell                      2 .add-url-panel textarea
2 .account-login-dialog p
```

（`.app-shell` 與 `.page-heading` 的第二筆是**合法的分段定義**：`.app-shell` 第二次是
`main.css:1127` 宣告 4 個 account 變數；`.page-heading` 第二次是 `main.css:560`
覆寫 `margin` 與 `align-items`。其餘屬重複。）

### 7.2 永遠不會生效的 media query

| 位置 | 條件 | 生效？ | 證據 |
|---|---|---|---|
| `main.css:3142` | `max-width: 900px` | **否** | `body { min-width: 1000px }`（`main.css:12`）＋ `BrowserWindow.minWidth: 1000`（`index.ts:805`） |
| `main.css:3148` | `max-width: 680px` | **否** | 同上 |
| `main.css:3412` | `max-width: 760px` | **否** | 同上 |
| `main.css:3453` | `max-width: 1150px` | **是**（1000–1150） | 設 `content-wrap` 左右 padding 20（`3455-3456`）、`.network-event` 改 5 欄（`3465-3467`） |
| `main.css:3570` | `max-width: 1180px` | **是**（1000–1180） | sidebar 205（`3572`）、`content-wrap` padding 24（`3575-3576`）、`stats-grid` 改 2 欄（`3578-3580`） |

> **附帶發現**：1150 的 `padding: 20px`（`3455`）在 ≤1150 區間被後面的 1180 規則
> `padding: 24px`（`3575`）覆蓋（同樣 specificity、檔案位置在後）→ **20px 那兩行實際永遠無效**。

### 7.3 疑似未使用的 class（**可能由字串組合動態產生，不可僅憑搜尋刪除**）

| class | TSX 命中 | CSS 位置 |
|---|---|---|
| `.login-finish-row` | 0 | `main.css:1050-1054`（還出現在 94 的選擇器群組 `main.css:96`） |
| `.browser-open-status` | 0 | `main.css:1055-1065` |
| `.preference-group-title` | 0 | `main.css:2377-2385`（＋淺色覆寫 `main.css:3424-3427`） |
| `.settings-value` | 0 | `main.css:2716-2719` |

> 指令：`for c in …; do grep -c "$c" App.tsx components/*.tsx; done` → 全部 0。
> 這 4 個可能來自已刪除的舊版面，也可能是 `className={\`...\`}` 動態組字，
> **U 系列拆檔時再逐一確認，不可直接刪**。

### 7.4 重複的 `:root` 與 `body` 宣告

| 宣告 | 位置 1 | 位置 2 | 效果 |
|---|---|---|---|
| `:root` | `base.css:1-24`（`--ev-*` 18 個變數） | `base.css:26-32`（`--color-*`）、`main.css:3-9`（font-family/color/background） | 三個 `:root`，`main.css` 後載入（`main.css:1 ` `@import './base.css'`）→ base 的 `font-family` 定義被覆蓋 |
| `body` | `base.css:46-67`（`min-height:100vh`、字族含 Inter/-apple-system、`line-height:1.6`） | `main.css:11-16`（`min-width:1000px`、`overflow:hidden`、`user-select:none`） | 合併生效，但字族以 `main.css:4` 的 `:root` 為準 → base 的字族清單實際無效 |
| `--ev-*` 18 個變數 | `base.css:1-24` | 全專案搜尋僅在 base.css 內被引用 | **疑似整包死碼**（未在 TSX 動態引用；`--ev-button-alt-*` 只在 base.css 自身使用） |

### 7.5 可及性缺口

| # | 問題 | 位置 |
|---|---|---|
| A1 | `prefers-reduced-motion` **0 筆** | `grep -rn "prefers-reduced-motion" .` → 0 |
| A2 | `<div role="button">` 終端分頁：有 `tabIndex` 與 Enter/Space 處理（合格），但**內部再嵌一個 `button`（關閉鈕）** → 嵌套互動元素，Tab 順序與螢幕閱讀器語意混亂 | `TerminalPanel.tsx:365-386` |
| A3 | `<kbd>⌘ K</kbd>` 顯示在搜尋框，但**全專案無任何 KeyK／快捷鍵處理**（`grep -rn "KeyK"` → 0），且 Windows 應為 `Ctrl K` | `App.tsx:1009` |
| A4 | 「說明」按鈕**沒有 onClick**，是死按鈕 | `App.tsx:1012-1014` |
| A5 | 側欄 `.profile-row` 的 `MoreHorizontal` 圖示無按鈕語意（純裝飾） | `App.tsx:982-990` |
| A6 | 三個「看起來像分頁」的群組中，`.network-mode-tabs`（`App.tsx:2399-2410`）與 `.network-detail-format-tabs`（`App.tsx:2313-2333`）有 `role="tablist"`；`.network-view-tabs`（`App.tsx:2369-2385`）沒有 | 語意不一致 |
| A7 | `.settings-category-card` 支援拖曳排序（`cursor: grab`，`main.css:2157`），**鍵盤替代路徑未驗證** | `App.tsx:2706` 起 |
| A8 | `.button:disabled` 用 `opacity: 1` ＋ 低對比底色表達，焦點樣式與 disabled 的互動未驗證 | `main.css:585-591` |
| A9 | `.cli-color-menu-option:focus-visible` 用 `outline: 2px solid #111`（`main.css:2647`，深色外框），與全域 `var(--accent)` 焦點外框不一致 | `main.css:2647` vs `main.css:36-40` |

### 7.6 不隨字級縮放的尺寸（清單見 4.3）

重點三個：
- `.statusbar` 字級 `calc(8px * scale)` 在固定 23px 高的列內（`main.css:3473`、`3479`）→ 字級 24 時行高溢出。
- `.app-loading { font-size: 13px }` 未乘縮放（`main.css:56`）。
- `.account-row` 欄位最小寬合計 785px 與視窗無關（`main.css:1120-1124`）→ 1000px 視窗必溢出。

### 7.7 冗餘或系統用語文案（只記錄）

| 文案 | 位置 | 問題 |
|---|---|---|
| `Ready` | `App.tsx:1173` | 使用者語言是中文；「Ready」對使用者無意義 |
| `Local data` | `App.tsx:1178` | 系統用語 |
| `TypeScript` | `App.tsx:1180` | **實作語言，與使用者任務無關**，佔永久狀態列 |
| `UTF-8` | `App.tsx:1181` | 編碼，使用者不會操作 |
| `⌘ K` | `App.tsx:1009` | 無實作對應（7.5 A3）＋非 Windows 鍵位 |
| `cool / 頁面名` 麵包屑 | `App.tsx:995-999` | 「cool」是內部代號 |
| `help-button`（`title="說明"`） | `App.tsx:1012-1014` | 無功能（7.5 A4） |
| `早期測試版本：v0.0.1，感謝白老鼠協助測試` | `App.tsx:3359` | 內部用語 |

### 7.8 顏色另案（本輪不處理，僅登記）

- 385 個唯一 hex、584 次出現（U1 統計）。
- 5 組文字低於 WCAG AA 4.5:1（U1 統計，深色預設）。
- `main.css:2952` 起的 `.app-shell[data-theme='light']` 深色覆寫區（約 460 行）。
- 24 組主題 × 7 色（`src/shared/colorThemes.ts`）與 CLI 報表配色（`src/shared/cliReportColors.ts`）。

---

## 8. 遷移計畫

> 原則：**每一步只動一層，每步結束外觀與行為都可驗證**；顏色最後處理。

### 8.1 CSS 遷移（main.css 535 個規則區塊 → 元件／尺度）

| 步 | 內容 | 會動到的檔案 | 驗證方式 |
|---|---|---|---|
| **S0** | 新增 `assets/tokens.css`：只放 8 個語意變數＋尺度級距，**值＝現況值**；`main.css:1` 後 `@import './tokens.css'` | 新增 `tokens.css`；改 `main.css`（1 行） | `npm run typecheck`、`npm test`；逐頁截圖比對（應像素等同） |
| **S1** | 換掉 `.app-shell`～`.main-layout` 區段（`main.css:59-532`）的寫死值 → 變數（**值相同**） | `main.css` | 截圖比對（外殼不應有任何變化） |
| **S2** | 換掉元件區（`main.css:569-1100`：button/panel/field/table-head） | `main.css` | 同上 |
| **S3** | 換掉列表區（`main.css:1101-2130`：account/course/report/network） | `main.css` | 同上 |
| **S4** | 換掉設定區（`main.css:2131-2730`） | `main.css` | 同上 |
| **S5** | 換掉終端區（`main.css:2731-2950`） | `main.css` | 同上 |
| **S6** | **尺度收斂（外觀會變）**，四個小步各自獨立 commit：字級 8→9 → 圓角 → 間距 → 固定高度乘縮放 | `main.css` | 每小步跑 6.2 的核心 24 組 |
| **S7** | 深色覆寫區（`main.css:2952-3410`）逐段改為由 token 推導，刪除已推導的行 | `main.css` | 深／淺兩方向逐頁比對 |
| **S8** | 刪除死碼：3 個失效 media query、`.app-loading` 未縮放字級、`base.css` 的 `--ev-*`（**需先確認無動態引用**） | `main.css`、`base.css` | typecheck＋test＋截圖 |

**S1–S5 的驗證要點**：因為「值相同」，可用 `npm run build` 後比對產出 CSS，
或逐頁 `pixelmatch` 截圖；只要有任何像素差異就代表變數換算有誤。

### 8.2 App.tsx 拆分方案（純搬移，外觀與行為完全不變）

現況：`App.tsx` 3406 行 / 126KB，其中 `App()` 佔 435–1210，六個頁面元件佔 1235–3406。

| 新檔案 | 內容（現況行號） | props 來源 |
|---|---|---|
| `src/pages/HomePage.tsx` | 1235–1351 | 現有 6 個 props（`App.tsx:1236-1244`）**不改** |
| `src/pages/AccountsPage.tsx` | 1399–1772 | 現有 20+ props（`App.tsx:1400-1447`）不改 |
| `src/pages/CoursesPage.tsx` | 1774–2027 | `App.tsx:1775-1805` 不改 |
| `src/pages/ReportsPage.tsx` | 2029–2128 | `App.tsx:2030-2046` 不改 |
| `src/pages/NetworkPage.tsx` | 2130–2629 | 不改 |
| `src/pages/SettingsPage.tsx` | 2697–3406 | `settings`、`onChange` 不改 |
| `src/components/PageHeading.tsx` | 1212–1233 | 不改 |
| `src/components/StatCard.tsx` | 1353–1374 | 不改 |
| `src/components/QuickAction.tsx` | 1376–1397 | 不改 |
| `src/components/NetworkEventRow.tsx` | 2631–2695 | 不改 |
| `src/components/CliColorMenu.tsx` | 179–293 | 不改 |
| `src/components/CliReportColorEditor.tsx` | 295–391 | 不改 |
| `src/App.tsx`（保留） | 1–178、435–1210、3407–3406 | 全部狀態與 IPC |

**共用元件放** `src/components/`，頁面放 `src/pages/`，兩者皆由 `App.tsx` 匯入。

**狀態與 props 傳遞**：維持現況的「狀態全部住在 `App()`，頁面是受控元件」模式
（`App.tsx:435` 起的 `useState` 群）。**不引入任何狀態管理工具**。

**不能動的邏輯（搬移時逐行保持原樣）**：

| 邏輯 | 位置 |
|---|---|
| settings 讀寫與 IPC（`saveSettings`／`loadSettings`） | `App.tsx` 內 settings 相關 hook |
| 主題與 CSS 變數注入（`--ui-font-scale` 等 9 個變數） | `App.tsx:849-870`（`--ui-font-scale` 於 869） |
| 帳號／cookie／課程／報表的 IPC 呼叫 | `App.tsx` 內 `refresh`、`beginLogin`、`fetchReport` 等 |
| 終端分割 pointer 拖曳（0.3–0.8 夾制、rAF 節流、事件註冊解除） | `App.tsx:1110-1150`（夾制於 1134） |
| 側欄 hover 模式（`clientX <= 12`／`> sidebarRight`） | `App.tsx:910-923` |
| 鍵盤／focus 處理（`.cli-color-menu` 的 Esc、方向鍵） | `App.tsx:202-232` |
| `NetworkEventRow` 的條件渲染（status/message/details） | `App.tsx:2641-2690` |
| 終端 session 生命週期與 xterm 掛載 | `TerminalPanel.tsx:200-300` |

**驗證**：`npm run typecheck`、`npm test`（64 個 node:test 應全綠）、
`git diff --stat` 只應顯示「刪除行 ≈ 新增行」的搬移特徵。

### 8.3 建議順序（含前後關係）

```
S0 → S1..S5（token 化，外觀不變）
   → M1（App.tsx 拆檔，外觀不變）      ← 可與 S1..S5 平行，但建議先 CSS 後 TSX
   → S6（尺度收斂，外觀小變）→ 6.2 矩陣
   → 每頁重做（U4 起，一輪一頁）
   → 顏色另案（token 推導、對比度、light 覆寫）
   → S8（刪死碼）
```

---

## 9. 待決定的問題

### Q1. 工作台首頁是否重排？（8 個等重區塊，其中 `.hero-card` 的 `hero-art` 是純裝飾）

| | 維持現狀 | 精簡 |
|---|---|---|
| 內容 | 4 統計卡＋hero（含 300px 裝飾圖）＋3 快速卡 | 一行數字（4 個統計 inline）＋1 張「接著做」卡＋2 個快速動作；移除 `hero-art`（`App.tsx:1311-1320`、`main.css:787-864`） |
| 改動檔案 | 無 | `App.tsx` 的 `HomePage`（1235–1351）＋ `main.css` 的 `.hero-*`／`.stat-*` 區段 |
| 字級 24 ＋ 1000×680 的結果 | 8 區塊需滾動約 3 屏 | 約 1.5 屏 |
| 視覺風險 | 低（不變） | 中（需重新決定唯一重點） |
| 工作量 | 0 | 約半天（含矩陣驗證） |

**我的建議：精簡**。理由：現況 8 個等重區塊沒有視覺入口，且 `hero-art` 佔 300px 寬的裝飾
在最小視窗下會與文字爭空間（`main.css:3581-3584` 在 <1180px 時已降到 `opacity: 0.75`）。
但**先做 S0–S5 與拆檔，再動首頁**，避免同一輪混兩種變更。

### Q2. 終端比例上限 0.8 是否要連同 `min-height: 160px` 一起調整？

- 現況：UI 允許 0.8，但 1000×680 下實際只能到 71%（1.3 節）。
- **建議**：保留 160px 下限（終端太小就不能用），改為把 `splitRatio` 的 UI 上限改為
  「可達值」或在拖曳時用實際高度計算比例，讓滑桿/數值與畫面一致。
- 影響：`App.tsx:1134` 一行（或 +dock 高度推算）＋ `storage.ts` 的校驗（`storage.ts:370-372`）。

### Q3. 帳號表的浮層選單要不要改 `position: fixed`，讓內容容器能開橫向捲動？

- 現況：`.account-table { overflow: visible }`（`main.css:1086`）是為了讓 `.account-login-menu` 顯示；
  代價是 1000px 視窗下整頁出現橫向捲軸。
- **建議**：改 `position: fixed` ＋ 以觸發鈕的 `getBoundingClientRect()` 對齊，
  這樣表格可以 `overflow-x: auto`、5 個欄位可以拿掉 785px 的最小寬下限。
- 影響：`App.tsx` 帳號列選單渲染位置＋`main.css:1343-1351`；屬行為變更，需手測。

### Q4. 狀態列（`.statusbar`）要保留哪些項目？

- 現況 5 項：`cool`、`Ready`、`Local data`、`TypeScript`、`UTF-8`（`App.tsx:1167-1184`）。
- **建議**：只保留 2 項——目前帳號／目前分頁＋「本機儲存」，
  移除 `TypeScript`、`UTF-8`、`Ready`（使用者無法操作也無法據此行動）；
  同時把狀態列字級改為不縮放（4.3）。
- 這是**文案變更**，本輪未動，需你點頭。

### Q5. 疑似未使用的 4 個 class（`.login-finish-row`、`.browser-open-status`、`.preference-group-title`、`.settings-value`）何時清理？

- **建議**：放到拆檔（M1）之後——那時 className 會集中到頁面檔，逐一搜尋動態組字更可靠。
  本輪只登記（7.3），不刪。

---

## 附錄 A：本輪統計指令與原始輸出（V1）

> 執行目錄：`CLI-main/desktop/src/renderer/src/assets`（CSS）與 `.../src`（TSX）。

### A-1 字級與圓角

```
$ grep -o "font-size: [^;]*;" main.css | sort | uniq -c | sort -rn
     50 font-size: calc(9px * var(--ui-font-scale, 1));
     26 font-size: calc(10px * var(--ui-font-scale, 1));
     11 font-size: calc(8px * var(--ui-font-scale, 1));
     11 font-size: calc(11px * var(--ui-font-scale, 1));
      5 font-size: calc(12px * var(--ui-font-scale, 1));
      1 font-size: calc(23px * var(--ui-font-scale, 1));
      1 font-size: calc(22px * var(--ui-font-scale, 1));
      1 font-size: calc(20px * var(--ui-font-scale, 1));
      1 font-size: calc(17px * var(--ui-font-scale, 1));
      1 font-size: calc(16px * var(--ui-font-scale, 1));
      1 font-size: calc(15px * var(--ui-font-scale, 1));
      1 font-size: 13px;

$ grep -o "border-radius: [^;]*;" main.css | sort | uniq -c | sort -rn
     15 border-radius: 7px;
     15 border-radius: 5px;
     11 border-radius: 6px;
      8 border-radius: 4px;
      6 border-radius: 8px;
      4 border-radius: 50%;
      3 border-radius: 9px;
      1 border-radius: 3px;
      1 border-radius: 22px;
      1 border-radius: 20px;
      1 border-radius: 10px;
      1 border-radius: 0;
```

### A-2 固定寬高與欄定義

```
$ grep -o "width: [0-9]*px" main.css | sort | uniq -c | sort -rn
      4 width: 29px     3 width: 5px      2 width: 6px      2 width: 31px
      2 width: 30px     2 width: 28px     2 width: 220px    2 width: 18px
      2 width: 15px     1 width: 90px     1 width: 900px    1 width: 8px
      1 width: 7px      1 width: 760px    1 width: 70px     1 width: 680px
      1 width: 4px      1 width: 42px     1 width: 38px     1 width: 36px
      1 width: 360px    1 width: 34px     1 width: 32px     1 width: 300px
      1 width: 260px    1 width: 25px     1 width: 245px    1 width: 23px
      1 width: 20px     1 width: 1px      1 width: 190px    1 width: 170px
      1 width: 16px     1 width: 150px    1 width: 145px    1 width: 135px
      1 width: 130px    1 width: 1180px   1 width: 1150px   1 width: 112px
      1 width: 110px    1 width: 10px     1 width: 1000px

$ grep -o "height: [0-9]*px" main.css | sort | uniq -c | sort -rn
      7 height: 29px    6 height: 28px    5 height: 30px    4 height: 32px
      3 height: 5px     3 height: 48px    3 height: 36px    3 height: 34px
      3 height: 23px    2 height: 74px    2 height: 6px     2 height: 43px
      2 height: 42px    2 height: 31px    2 height: 25px    2 height: 18px
      2 height: 15px    1 height: 8px     1 height: 82px    1 height: 7px
      1 height: 70px    1 height: 69px    1 height: 680px   1 height: 64px
      1 height: 62px    1 height: 59px    1 height: 4px     1 height: 49px
      1 height: 39px    1 height: 38px    1 height: 380px   1 height: 33px
      1 height: 320px   1 height: 27px    1 height: 26px    1 height: 240px
      1 height: 22px    1 height: 209px   1 height: 190px   1 height: 174px
      1 height: 160px   1 height: 135px   1 height: 121px   1 height: 110px
      1 height: 10px

$ grep -n "grid-template-columns" main.css
660:  grid-template-columns: repeat(4, minmax(0, 1fr));
877:  grid-template-columns: repeat(3, minmax(0, 1fr));
988:  grid-template-columns: repeat(3, minmax(0, 1fr));
1120:  grid-template-columns:
1230:  grid-template-columns: 7px minmax(0, 1fr);
1607:  grid-template-columns: 0.9fr 1.15fr 1.15fr 0.9fr 1fr;
2051:  grid-template-columns: 35px 50px minmax(100px, 1fr) 42px minmax(60px, auto) 65px;
2138:  grid-template-columns: repeat(2, minmax(0, 1fr));
2280:  grid-template-columns: repeat(2, minmax(0, 1fr));
2300:  grid-template-columns: repeat(4, minmax(0, 1fr));
2535:  grid-template-columns: minmax(0, 1fr);
3144:    grid-template-columns: repeat(3, minmax(0, 1fr));
3150:    grid-template-columns: 1fr;
3154:    grid-template-columns: repeat(2, minmax(0, 1fr));
3158:    grid-template-columns: 1fr;
3465:    grid-template-columns: 35px 50px minmax(80px, 1fr) 42px 65px;
3579:    grid-template-columns: repeat(2, minmax(0, 1fr));
```

### A-3 間距

```
$ grep -o "gap: [0-9]*px;" main.css | sort | uniq -c | sort -rn
     14 gap: 8px;   11 gap: 9px;   10 gap: 7px;   10 gap: 12px;
      7 gap: 3px;    6 gap: 6px;    5 gap: 11px;   4 gap: 5px;
      4 gap: 4px;    4 gap: 2px;    4 gap: 10px;   2 gap: 13px;
      1 gap: 24px;   1 gap: 20px;   1 gap: 16px;   1 gap: 14px;

$ grep -o "padding: [0-9]*px;" main.css | sort | uniq -c | sort -rn
      3 padding: 3px;   3 padding: 2px;   3 padding: 12px;
      2 padding: 5px;   2 padding: 24px;  2 padding: 10px;
      1 padding: 7px;   1 padding: 6px;   1 padding: 4px;
      1 padding: 22px;  1 padding: 17px;  1 padding: 16px;  1 padding: 15px;

$ grep -o "margin[a-z-]*: [0-9]*px;" main.css | sort | uniq -c | sort -rn
      4 margin-top: 3px;      3 margin-top: 8px;      3 margin-top: 5px;
      3 margin-top: 10px;     2 margin-top: 6px;      2 margin-top: 15px;
      2 margin-top: 14px;     2 margin-bottom: 9px;   2 margin-bottom: 8px;
      2 margin-bottom: 22px;  2 margin-bottom: 10px;  1 margin-top: 4px;
      1 margin-top: 12px;     1 margin-top: 11px;     1 margin-left: 5px;
      1 margin-bottom: 3px;   1 margin-bottom: 25px;  1 margin-bottom: 24px;
      1 margin-bottom: 17px;  1 margin-bottom: 15px;  1 margin-bottom: 14px;
```

### A-4 陰影、動畫、media query

```
$ grep -o "box-shadow: [^;]*;" main.css | sort | uniq -c | sort -rn
      2 box-shadow: none;
      2 box-shadow: 0 0 8px #e5687066;
      2 box-shadow: 0 0 8px #b18b4c55;
      1 box-shadow: inset 4px 0 #fff;
      1 box-shadow: inset 4px 0 #101318;
      1 box-shadow: inset 3px 0 var(--account-selected-outline);
      1 box-shadow: inset 0 0 0 1px var(--accent, #62d7c0);
      1 box-shadow: 0 8px 32px #0008;
      1 box-shadow: 0 8px 24px rgb(32 42 54 / 18%);
      1 box-shadow: 0 8px 24px rgb(0 0 0 / 40%);
      1 box-shadow: 0 8px 22px #0008;
      1 box-shadow: 0 18px 60px rgb(0 0 0 / 42%);
      1 box-shadow: 0 10px 28px #0008;
      1 box-shadow: 0 0 8px #62d7a655;
      1 box-shadow: 0 0 45px #55c8b322;
      1 box-shadow: 0 0 18px #85e3cf;
      1 box-shadow: 0 0 0 1px #0002;

$ grep -n "transition:" main.css
157:  transition: 120ms ease;      208:  transition:      291:  transition: 120ms ease;
582:  transition: 120ms ease;      892:  transition: 120ms ease;
2180:  transition:                 2317:  transition:

$ grep -n "@media" main.css
3142:@media (max-width: 900px) {
3148:@media (max-width: 680px) {
3412:@media (max-width: 760px) {
3453:@media (max-width: 1150px) {
3570:@media (max-width: 1180px) {
```

### A-5 重複選擇器

```
$ grep -oE '^[.#][^{]+\{' main.css | sed 's/ {$//' | sort | uniq -c | sort -rn | awk '$1>=2'
      2 .terminal-context-menu
      2 .statusbar
      2 .status-branch
      2 .settings-note
      2 .report-table
      2 .profile-avatar
      2 .preference-control select
      2 .page-heading h1
      2 .page-heading
      2 .network-mode.direct
      2 .mini-icon-button
      2 .course-open-actions
      2 .color-theme-card.selected
      2 .cli-report-color-list
      2 .app-shell[data-theme='light'] .terminal-toolbar
      2 .app-shell[data-theme='light'] .network-session-header
      2 .app-shell[data-theme='light']
      2 .app-shell[data-theme='dark'] .settings-category-card
      2 .app-shell
      2 .add-url-panel textarea
      2 .account-login-dialog p
```

### A-6 檔案規模

```
$ wc -l main.css base.css
  3585 main.css
    67 base.css
  3652 total

$ grep -c "{" main.css
535
```

### A-7 可及性搜尋

```
$ grep -rn "prefers-reduced-motion" . | wc -l
0

$ grep -rn "KeyK" src/ | wc -l
0
```

### A-8 疑似未使用 class

```
$ for c in login-finish-row browser-open-status preference-group-title settings-value; do
    grep -c "$c" App.tsx components/*.tsx | awk -F: '{s+=$2} END {print s}'; done
0
0
0
0
```

### A-9 元件 class 使用次數

```
$ for c in ...; do grep -o "className=\"…<c>…\"" …; done   （結果見第 3 章各表）
  按鈕 literal=35   panel=18   table-head=2   empty-state=4   icon-button=11
  mini-icon-button=9   field=7   section-heading=4   page-heading=1
  content-wrap=7   preference-control=28   settings-row=5   nav-item=1(+1 模板)
```

### A-10 關鍵行號（用於第 3 章與 V3 抽查）

```
$ python3 對 main.css 逐行 re.match() 找選擇器起始行 → 輸出見本次對話
.app-shell 59/1127  .titlebar 70  .workbench 193  .sidebar 199  .main-column 436
.main-layout 445  .page-topbar 464  .page-content 519  .content-wrap 528
.button 569  .button.small 652  .stats-grid 658  .stat-card 665  .hero-card 733
.section-heading 856  .quick-grid 875  .quick-card 881  .panel 938  .field 999
.table-head 1094  .table-row 1107  .account-row 1118  .empty-state 1393
.selection-chip 1425  .course-item 1518  .report-row 1605  .network-list 1644
.network-event 2049  .settings-category-grid 2136  .settings-category-card 2168
.preference-controls 2278  .color-theme-card 2305  .preference-control 2395
.cli-report-color-row 2544  .cli-color-menu 2583  .settings-row 2677
.terminal-dock 2738  .terminal-split-handle 2757  .terminal-toolbar 2785
.statusbar 217/3469  .toast 3500  .busy-indicator 3544
.account-login-dialog 1277  .account-login-backdrop 1267
.login-form 986  .search-box 490  .nav-item 277  .icon-button 160
.status-pill 1206  .cookie-status 1228  .settings-category-grid 2136
body 11  @media 3142/3148/3412/3453/3570
```

---

## 附錄 B：未驗證項目（V4）

**文件內所有標記為「未驗證」的結論：**

1. 1.3 節「splitRatio 0.8 時實際比例退化為 70.9% / 28.3%」——純 flex 計算推導，**未在實機拖曳驗證**。
2. 1.4 節「1000×680 下內容淨寬 747px」——純盒模型推導，**未實測 `getBoundingClientRect`**。
3. 5.1 節「帳號表 785px > 747px 造成橫向溢出」——算術推導，**未實機開啟帳號頁確認出現橫向捲軸**。
4. 4.3 節「必須縮放」清單——依 min-height 與字級行高推導，**未在字級 24 逐列實測溢出量**。
5. 6.4 節所有風險組合的「會破版」判斷——**未執行**（本輪未啟動應用程式）。
6. 7.2 節「`main.css:3455` 的 padding:20 永遠被 3575 覆蓋」——依 CSS 層疊順序推導，**未實機量測 computed padding**。
7. 7.3 節 4 個 class「未被使用」——只做了靜態搜尋，**未排除動態字串組合**。
8. 7.5 A7「設定分類拖曳的鍵盤替代路徑」——**未驗證**。
9. 7.5 A8「disabled 按鈕的焦點與可讀性」——**未驗證**。
10. 7.5 A2「終端分頁嵌套互動元素對螢幕閱讀器的實際影響」——**未驗證**。
11. 3.6 節「Dialog 焦點陷阱」——**未驗證**（`.account-login-dialog` 是否攔 Tab 未確認）。
12. 4.1 節統計只涵蓋 `main.css`，**未含 `TerminalPanel.tsx` 內的 inline style 與 `App.tsx` 的 style 屬性**。

**需要在 Windows 實機確認的畫面（建議順序）：**

1. 首次啟動預設畫面（dark、字級 13、split 0.68、1360×900）——工作台頁。
2. 同上但視窗縮到 1000×680——觀察 sidebar 是否變 205、內容是否出現橫向捲軸。
3. `設定 > 外觀` 把字級拉到 24，回到帳號頁——**確認欄位是否重疊或出現橫向捲軸**（風險 1、2）。
4. `設定 > 工作區` 把終端比例拖到 0.8 與 0.3，視窗在 1000×680——**量測實際比例**（風險 3）。
5. 切到 `horizontal` 分割重複第 3、4 步。
6. 切淺色主題，走訪 6 頁（對比度另案，但先確認結構不破）。
7. 網路紀錄頁：載入一次有頭工作階段，確認 `<1150px` 時 5 欄覆寫下各欄是否對齊。
8. 設定分類：用鍵盤 Tab 到分類卡，嘗試用鍵盤重排序（驗證 7.5 A7）。
9. 帳號頁列選單：在 1000px 寬下打開「重新登入」浮層，確認是否被裁切。
10. 開啟終端、切換分頁，用 Tab 走訪 `.terminal-tab` 與其關閉鈕（驗證 7.5 A2）。
