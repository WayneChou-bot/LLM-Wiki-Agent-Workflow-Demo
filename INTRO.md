# LLM Wiki Agent Workflow Demo

最近看到 Andrej Karpathy 提到的 LLM Wiki 概念，覺得很適合拿來實作一個小 demo。

這個 demo 想展示的**不是一般聊天機器人，也不是單純 RAG 搜尋**，而是一種新的知識工作流：
讓 AI Agent 把原始資料整理成可以長期維護、查詢、累積的 Markdown Wiki。


## Demo 核心概念

整個系統分成三層：

- **`raw/`**：原始資料，作為 source of truth，不直接修改
- **`wiki/`**：AI Agent 整理後的 Markdown 知識頁，會自動交叉連結
- **`AGENTS.md`**：定義不同 Agent 如何讀資料、整理資料、維護知識庫

使用流程：

1. 把原始資料放進 `raw/`（貼文字、選既有檔、或貼 URL 自動抓）
2. 選一個 Agent 角色
3. 讓 Agent ingest 那份資料，產生結構化 wiki 頁面
4. 用 Concept 把跨多份來源的同一個主題合成一頁
5. 對整個 wiki 提問
6. 把有價值的回答回寫成 synthesis page


## 目前支援的 Agent

我先做了 4 種常見工作情境：

- **Programming Agent**：整理技術架構、API 整合、開發模式
- **UI Design Agent**：整理介面流程、互動設計、使用者體驗
- **Project Manager Agent**：整理 roadmap、任務拆解、風險與決策
- **Personal Knowledge Agent**：整理學習筆記、反思、個人知識管理方法

同一份資料可以被不同 Agent 用不同角度整理，**產生不同用途的 wiki page**——這是在 Karpathy 原始 idea 之外加的「多視角實驗」。

## Demo 介面

目前用 Streamlit 做成本地網頁 demo，8 個分頁對應不同動作：

- **Showcase**：開場，講清楚整套系統在做什麼
- **Inputs**：放材料的地方——貼文字 / 選既有 / 貼 URL 自動抓，**這一步不會動 AI**
- **Agents**：選材料 + 選視角，讓 AI Agent 寫一頁知識
- **Knowledge**：按 source 分組瀏覽，同一份資料的多個視角擠在一起，視角用顏色區分
- **Concepts**：輸入概念名稱（例如「ingest」、「workflow」），AI 把跨多份 source 的相關段落合成一頁
- **Map**：以節點圖展示 raw → agent → wiki page → concept 之間的關聯
- **Ask**：根據整個 wiki 提問，支援中英混合查詢，有價值的回答可存成 synthesis
- **Maintain**：唯讀健康檢視 + 顯式動作鈕（重建 index / 記錄 lint），含 orphan 頁面偵測

## 為什麼要有 Map（節點圖）

參考 Karpathy LLM Wiki 的概念，重點不是產生單篇摘要，而是**讓知識逐步形成網路**。

Map 展示的是：

- 哪些 raw source 被 ingest
- 哪些 Agent 產生了哪些 wiki page
- wiki page 之間如何互相連結（每次 ingest 系統會自動更新兄弟頁面的 cross-reference）
- Concept 頁面如何把跨主題的散點縫合起來
- Synthesis 頁面如何把有價值的問答回寫到 wiki

也就是說：**知識不是只存在聊天紀錄裡，而是會累積成一個可維護、可走動、可長大的 Markdown 知識系統**。


## 一句話總結

AI Agent 不是這個 demo 的主角——**「會自己長大、會自己編織關聯的 Markdown 知識庫」才是**。Agent 是寫手，wiki 是成果。
