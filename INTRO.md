# LLM Wiki Agent Workflow Demo

最近在研究 Karpathy 提到的 LLM Wiki 概念，所以做了一個小型 demo，想展示 AI Agent 不只是回答問題，而是可以幫我們維護一個會累積、會自己交織的知識庫。

這個 demo 的核心流程是：

`Inputs 原始資料 → Agents 不同 AI 視角 → Knowledge 知識頁 → Concepts 跨來源合成 → Map 關聯圖 → Ask 問知識庫 → Maintain 健康檢查`

## 這個 Demo 在做什麼？

一般聊天機器人的回答常常留在對話紀錄裡，用完就散掉。

這個 demo 想展示另一種工作流：把文章、筆記、會議紀錄、網頁等原始資料交給不同 AI Agent，讓它們整理成**可長期維護、可查詢、可累積**的 Markdown 知識庫——而且每多餵一份新資料，既有頁面之間的交叉連結會自動更新。

## 目前支援的 Agent 視角

- **Programming Agent**：整理技術架構、API 整合、開發模式
- **UI Design Agent**：整理介面流程、互動設計、使用者體驗
- **Project Manager Agent**：整理 roadmap、任務拆解、風險與決策
- **Personal Knowledge Agent**：整理學習筆記、反思、個人知識管理方法

同一份資料可以被不同 Agent 用不同角度閱讀，產生不同用途的知識頁。

## Demo 功能

- **Inputs**：貼純文字、選擇既有資料、或直接貼 URL 自動抓取網頁
- **Agents**：選擇 AI 視角，將資料轉成知識頁（可一次跑全部 4 個視角）
- **Knowledge**：按 source 分組瀏覽，同一份資料的多視角擺在一起，視角用顏色區分
- **Concepts**：輸入概念名稱（例如「ingest」、「workflow」），自動把跨多個 source 的相關段落合成一頁
- **Map**：以節點圖展示 raw source、agent、knowledge page、concept page 之間的關聯
- **Ask**：根據已整理的 wiki 提問，支援中英混合查詢
- **Maintain**：唯讀健康檢視 + 明確動作鈕（重建 index / 記錄 lint），含 orphan 頁面偵測

目前已串接 Gemini API，可以讓 Agent 真正讀取 raw source、寫出 wiki page、並在寫的時候主動跨頁面交叉連結。所有產出都是 Markdown 檔案，整個 `wiki/` 資料夾可以直接用 Obsidian 打開、繼續編輯。

## 一句話總結

這個 demo 想展示的是：AI Agent 不只是聊天工具，而是可以把散落資料整理成一個**會長大、會自己編織關聯**的知識系統。
