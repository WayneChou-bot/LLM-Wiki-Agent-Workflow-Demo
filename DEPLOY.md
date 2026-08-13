# 部署到 Vercel(web/ 靜態展示網站)

`web/` 資料夾是一個純靜態網站(單一 `index.html`,零依賴、零後端、零 API key),
專門用來在線上展示這個 LLM Wiki 專案。Streamlit 版(`app.py`)仍然只在本機執行。

## 方法一:Vercel 網頁介面(推薦,約 2 分鐘)

1. 先把 `web/` 資料夾 commit 並 push 到 GitHub repo
   (`WayneChou-bot/LLM-Wiki-Agent-Workflow-Demo`)。
2. 到 <https://vercel.com> 用 GitHub 帳號登入。
3. 點 **Add New… → Project**,選擇這個 repo 按 **Import**。
4. 重要設定:
   - **Framework Preset**:`Other`
   - **Root Directory**:點 Edit,選 `web`
   - Build Command / Output Directory:全部留空(靜態網站不需要 build)
5. 按 **Deploy**。完成後會拿到一個 `*.vercel.app` 網址,之後每次 push 都會自動重新部署。

## 方法二:Vercel CLI

```bash
npm i -g vercel
cd "LLM WiKi_karpathy/web"
vercel          # 第一次會要求登入與確認設定,一路 Enter 即可
vercel --prod   # 部署正式版
```

## 本機預覽

不需要任何工具,直接用瀏覽器打開 `web/index.html` 即可;
或在 `web/` 內跑 `python -m http.server 8000` 後開 <http://localhost:8000>。

## 之後想更新網站內容?

網站內容(wiki 頁面、raw 來源)都內嵌在 `index.html` 的 `FILES` 物件裡。
新 ingest 了頁面之後,把新的 markdown 貼進 `FILES`,push 即自動部署。
(未來也可以寫一個小腳本自動把 `wiki/` 資料夾打包成 JSON 注入。)
