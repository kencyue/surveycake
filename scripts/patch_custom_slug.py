from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# Optional custom survey slug. Immutable Firestore IDs and old links remain valid.

if 'async function resolveSurveyId(key)' not in text:
    marker = """        function getUrlSurveyId() {
            const params = new URLSearchParams(window.location.search);
            return params.get('s');
        }
"""
    helper = r'''        function getUrlSurveyId() {
            const params = new URLSearchParams(window.location.search);
            return params.get('s');
        }

        function normalizeSurveySlug(value) {
            return String(value || '').trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9_-]/g, '').replace(/-+/g, '-').replace(/^[-_]+|[-_]+$/g, '');
        }
        const RESERVED_SURVEY_SLUGS = new Set(['admin','login','logout','inject','api','survey','surveys','settings','responses','response','new','edit','null','undefined']);
        function surveyPublicKey(s) { return (s && s.slug) ? s.slug : (s && s.id ? s.id : ''); }
        function surveyPublicLink(s) { return `${window.location.origin}${window.location.pathname}?s=${encodeURIComponent(surveyPublicKey(s))}`; }
        async function resolveSurveyId(key) {
            if (!key) return null;
            const direct = await getDoc(surveyDocRef(key));
            if (direct.exists()) return key;
            const snap = await getDocs(surveysCol());
            let found = null;
            snap.forEach(d => { if (!found && normalizeSurveySlug(d.data()?.slug) === normalizeSurveySlug(key)) found = d.id; });
            return found;
        }
'''
    if marker not in text: raise SystemExit('getUrlSurveyId marker not found')
    text = text.replace(marker, helper, 1)

# Public entry accepts either old document ID or custom slug.
old = """                const snap = await getDoc(surveyDocRef(id));
                if (!snap.exists()) {
                    await showMessage('找不到問卷', '這份問卷不存在，或已被刪除。');
                    return enterPicker();
                }
                const survey = { id: snap.id, ...snap.data() };
                state.activeSurvey = survey;
                state.activeSurveyId = id;"""
new = """                const resolvedId = await resolveSurveyId(id);
                if (!resolvedId) {
                    await showMessage('找不到問卷', '這份問卷不存在，或已被刪除。');
                    return enterPicker();
                }
                const snap = await getDoc(surveyDocRef(resolvedId));
                if (!snap.exists()) {
                    await showMessage('找不到問卷', '這份問卷不存在，或已被刪除。');
                    return enterPicker();
                }
                const survey = { id: snap.id, ...snap.data() };
                state.activeSurvey = survey;
                state.activeSurveyId = resolvedId;"""
if old in text: text = text.replace(old, new, 1)

text = text.replace("params.set('s', openOnes[0].id);", "params.set('s', surveyPublicKey(openOnes[0]));")
text = text.replace("const link = `${window.location.origin}${window.location.pathname}?s=${s.id}`;", "const link = surveyPublicLink(s);")

# Current editor markup uses font-bold/focus:border brand classes.
if 'id="ed-slug"' not in text:
    title = '''                        <div>
                            <label class="block text-sm font-bold text-gray-700 mb-1">問卷標題</label>
                            <input id="ed-title" type="text" class="w-full border-2 border-gray-200 rounded-xl py-2.5 px-3 focus:outline-none focus:border-[var(--brand-500)]" value="${escapeHtml(s.title)}">
                        </div>'''
    slug = title + r'''
                        <div>
                            <label class="block text-sm font-bold text-gray-700 mb-1">自訂網址 ID <span class="font-normal text-gray-400">（選填）</span></label>
                            <div class="flex items-center border-2 border-gray-200 rounded-xl overflow-hidden bg-white focus-within:border-[var(--brand-500)]">
                                <span class="hidden sm:block text-xs text-gray-400 bg-gray-50 px-3 py-2.5 border-r border-gray-200">?s=</span>
                                <input id="ed-slug" type="text" maxlength="60" class="flex-grow min-w-0 py-2.5 px-3 focus:outline-none text-sm" value="${escapeHtml(s.slug || '')}" placeholder="留白＝系統亂數，例如 family-trip-2026">
                            </div>
                            <div id="ed-slug-status" class="text-xs mt-1.5 text-gray-400">英文小寫、數字、-、_；留白使用系統亂數網址。原本的亂數網址仍永久有效。</div>
                        </div>'''
    if title not in text: raise SystemExit('current title editor marker not found')
    text = text.replace(title, slug, 1)

bind = "            document.getElementById('ed-title').addEventListener('input', e => s.title = e.target.value);\n"
if "const slugInput = document.getElementById('ed-slug');" not in text:
    code = bind + r'''            const slugInput = document.getElementById('ed-slug');
            const slugStatus = document.getElementById('ed-slug-status');
            if (slugInput) {
                slugInput.addEventListener('input', () => {
                    const normalized = normalizeSurveySlug(slugInput.value);
                    s.slug = normalized;
                    if (!slugInput.value.trim()) {
                        slugStatus.textContent = '未設定：使用系統亂數 ID，既有網址不受影響。';
                        slugStatus.className = 'text-xs mt-1.5 text-gray-400';
                    } else if (!normalized || RESERVED_SURVEY_SLUGS.has(normalized)) {
                        slugStatus.textContent = '此網址 ID 無效或屬於系統保留字。';
                        slugStatus.className = 'text-xs mt-1.5 text-red-500';
                    } else {
                        slugStatus.textContent = `預覽：?s=${normalized}（儲存時檢查重複）`;
                        slugStatus.className = 'text-xs mt-1.5 text-green-600';
                    }
                });
                slugInput.addEventListener('blur', () => { slugInput.value = normalizeSurveySlug(slugInput.value); s.slug = slugInput.value; });
            }
'''
    if bind not in text: raise SystemExit('title bind marker not found')
    text = text.replace(bind, code, 1)

# Save-time collision protection.
if "RESERVED_SURVEY_SLUGS.has(s.slug)" not in text:
    marker = """            if (!s.title.trim()) { showMessage('尚未填寫', '請輸入問卷標題'); return; }
            const cleanQuestions = JSON.parse(JSON.stringify(s.questions)).map(q => { delete q._open; delete q._justAdded; return q; });"""
    code = """            if (!s.title.trim()) { showMessage('尚未填寫', '請輸入問卷標題'); return; }
            s.slug = normalizeSurveySlug(s.slug || '');
            if (s.slug && RESERVED_SURVEY_SLUGS.has(s.slug)) { showMessage('網址 ID 不可使用', '這個網址 ID 是系統保留字，請換一個。'); return; }
            if (s.slug) {
                try {
                    const slugSnap = await getDocs(surveysCol());
                    let conflict = false;
                    slugSnap.forEach(d => {
                        if (d.id === state.editingSurveyId) return;
                        const data = d.data() || {};
                        if (d.id.toLowerCase() === s.slug || normalizeSurveySlug(data.slug) === s.slug) conflict = true;
                    });
                    if (conflict) { showMessage('網址 ID 已被使用', `「${s.slug}」已被其他問卷使用，請換一個。`); return; }
                } catch (e) {
                    console.error('slug collision check failed', e);
                    showMessage('檢查失敗', '目前無法確認網址 ID 是否重複，為避免衝突暫不儲存。', 'error');
                    return;
                }
            }
            const cleanQuestions = JSON.parse(JSON.stringify(s.questions)).map(q => { delete q._open; delete q._justAdded; return q; });"""
    if marker not in text: raise SystemExit('save marker not found')
    text = text.replace(marker, code, 1)

path.write_text(text, encoding='utf-8')
print('patched custom slug against current editor markup')
