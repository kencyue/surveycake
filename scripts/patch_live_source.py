from pathlib import Path

path = Path("public/index.html")
text = path.read_text(encoding="utf-8")

marker = "// Always refresh the survey before starting so an already-open public page cannot use stale questions."
old = """            const btnStart = document.getElementById('btn-start');
            if (btnStart) btnStart.addEventListener('click', () => {
                state.mode = 'fill'; state.currentPageIndex = 0; render(); window.scrollTo(0, 0);
            });"""
new = """            const btnStart = document.getElementById('btn-start');
            if (btnStart) btnStart.addEventListener('click', async () => {
                // Always refresh the survey before starting so an already-open public page cannot use stale questions.
                btnStart.disabled = true;
                try {
                    const snap = await getDoc(surveyDocRef(state.activeSurveyId));
                    if (!snap.exists()) {
                        await showMessage('找不到問卷', '這份問卷不存在，或已被刪除。');
                        btnStart.disabled = false;
                        return;
                    }
                    const latestSurvey = { id: snap.id, ...snap.data() };
                    state.activeSurvey = latestSurvey;
                    applyTheme(latestSurvey.theme || 'orange');
                    DOM.footerLine1.textContent = latestSurvey.title || '問卷調查';
                    state.pages = computePages(latestSurvey.questions || []);
                    state.answers = {};
                } catch (e) {
                    console.error(e);
                    await showMessage('讀取失敗', '無法取得最新問卷內容，請檢查網路後再試一次。', 'error');
                    btnStart.disabled = false;
                    return;
                }
                state.mode = 'fill';
                state.currentPageIndex = 0;
                render();
                window.scrollTo(0, 0);
            });"""

if marker in text:
    print("stale-survey fix already present")
elif old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("patched stale-survey start flow")
else:
    raise SystemExit("Expected btn-start block was not found; refusing to patch an unknown live source.")
