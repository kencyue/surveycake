from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# Optional custom survey slug. Firestore document IDs remain immutable; existing surveys keep working.

# 1. Resolver helpers before getUrlSurveyId.
marker = '''        function getUrlSurveyId() {
            const params = new URLSearchParams(window.location.search);
            return params.get('s');
        }
'''
replacement = r'''        function getUrlSurveyId() {
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
            // Backward compatibility: old random document-ID links always remain valid.
            const direct = await getDoc(surveyDocRef(key));
            if (direct.exists()) return key;
            // Custom slug is an alias only; it never replaces the immutable document ID.
            const snap = await getDocs(surveysCol());
            let found = null;
            snap.forEach(d => { if (!found && normalizeSurveySlug(d.data()?.slug) === normalizeSurveySlug(key)) found = d.id; });
            return found;
        }
'''
if 'async function resolveSurveyId(key)' not in text:
    if marker not in text: raise SystemExit('getUrlSurveyId marker not found')
    text = text.replace(marker, replacement, 1)

# 2. Resolve either immutable ID or slug on entry.
old = '''        async function enterSurveyById(id) {
            state.mode = 'loading';
            render();
            try {
                const snap = await getDoc(surveyDocRef(id));
                if (!snap.exists()) {
                    await showMessage('找不到問卷', '這份問卷不存在，或已被刪除。');
                    return enterPicker();
                }
                const survey = { id: snap.id, ...snap.data() };
                state.activeSurvey = survey;
                state.activeSurveyId = id;'''
new = '''        async function enterSurveyById(id) {
            state.mode = 'loading';
            render();
            try {
                const resolvedId = await resolveSurveyId(id);
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
                state.activeSurveyId = resolvedId;'''
if old in text:
    text = text.replace(old, new, 1)

# Picker uses custom URL when present.
text = text.replace("params.set('s', openOnes[0].id);", "params.set('s', surveyPublicKey(openOnes[0]));")
text = text.replace("params.set('s', btn.dataset.id);", "const picked = state.surveysPublic.find(x => x.id === btn.dataset.id); params.set('s', surveyPublicKey(picked || {id:btn.dataset.id}));")

# 3. Add optional slug input to header settings after title.
title_block = '''                            <div>
                                <label class="block text-sm font-semibold text-gray-600 mb-1">問卷標題</label>
                                <input id="ed-title" type="text" class="w-full border-2 border-gray-200 rounded-xl py-2.5 px-3 focus:outline-none" value="${escapeHtml(s.title)}">
                            </div>'''
slug_block = title_block + r'''
                            <div>
                                <label class="block text-sm font-semibold text-gray-600 mb-1">自訂網址 ID <span class="font-normal text-gray-400">（選填）</span></label>
                                <div class="flex items-center border-2 border-gray-200 rounded-xl overflow-hidden bg-white focus-within:border-[var(--brand-300)]">
                                    <span class="hidden sm:block text-xs text-gray-400 bg-gray-50 px-3 py-2.5 border-r border-gray-200">?s=</span>
                                    <input id="ed-slug" type="text" maxlength="60" class="flex-grow min-w-0 py-2.5 px-3 focus:outline-none text-sm" value="${escapeHtml(s.slug || '')}" placeholder="留白＝系統亂數，例如 family-trip-2026">
                                </div>
                                <div id="ed-slug-status" class="text-xs mt-1.5 text-gray-400">英文小寫、數字、-、_；留白時維持系統亂數網址。既有亂數網址永遠有效。</div>
                            </div>'''
if 'id="ed-slug"' not in text:
    if title_block not in text: raise SystemExit('title editor marker not found')
    text = text.replace(title_block, slug_block, 1)

# 4. Bind slug UI and normalize locally.
bind_title = "            document.getElementById('ed-title').addEventListener('input', e => s.title = e.target.value);\n"
slug_bind = bind_title + r'''            const slugInput = document.getElementById('ed-slug');
            const slugStatus = document.getElementById('ed-slug-status');
            if (slugInput) {
                slugInput.addEventListener('input', () => {
                    const raw = slugInput.value;
                    const normalized = normalizeSurveySlug(raw);
                    s.slug = normalized;
                    if (!raw.trim()) {
                        slugStatus.textContent = '未設定：將使用系統亂數 ID，既有網址不受影響。';
                        slugStatus.className = 'text-xs mt-1.5 text-gray-400';
                    } else if (!normalized || RESERVED_SURVEY_SLUGS.has(normalized)) {
                        slugStatus.textContent = '此網址 ID 無效或屬於系統保留字。';
                        slugStatus.className = 'text-xs mt-1.5 text-red-500';
                    } else {
                        slugStatus.textContent = `預覽：?s=${normalized}（儲存時會再次檢查是否重複）`;
                        slugStatus.className = 'text-xs mt-1.5 text-green-600';
                    }
                });
                slugInput.addEventListener('blur', () => { slugInput.value = normalizeSurveySlug(slugInput.value); s.slug = slugInput.value; });
            }
'''
if "const slugInput = document.getElementById('ed-slug');" not in text:
    if bind_title not in text: raise SystemExit('title bind marker not found')
    text = text.replace(bind_title, slug_bind, 1)

# 5. Collision check on save: slug vs all slugs AND document IDs.
save_old = '''        async function saveSurvey() {
            const s = state.editingSurvey;
            if (!s.title.trim()) { showMessage('尚未填寫', '請輸入問卷標題'); return; }
            const cleanQuestions = JSON.parse(JSON.stringify(s.questions)).map(q => { delete q._open; delete q._justAdded; return q; });
            const payload = { ...s, questions: cleanQuestions };
            delete payload.id;
            try {'''
save_new = '''        async function saveSurvey() {
            const s = state.editingSurvey;
            if (!s.title.trim()) { showMessage('尚未填寫', '請輸入問卷標題'); return; }
            s.slug = normalizeSurveySlug(s.slug || '');
            if (s.slug && RESERVED_SURVEY_SLUGS.has(s.slug)) { showMessage('網址 ID 不可使用', '這個網址 ID 是系統保留字，請換一個。'); return; }
            if (s.slug) {
                try {
                    const snap = await getDocs(surveysCol());
                    let conflict = null;
                    snap.forEach(d => {
                        if (d.id === state.editingSurveyId) return;
                        const data = d.data() || {};
                        if (d.id.toLowerCase() === s.slug || normalizeSurveySlug(data.slug) === s.slug) conflict = d.id;
                    });
                    if (conflict) { showMessage('網址 ID 已被使用', `「${s.slug}」已被其他問卷使用，請換一個。`); return; }
                } catch (e) { console.error('slug collision check failed', e); showMessage('檢查失敗', '目前無法確認網址 ID 是否重複，為避免衝突暫不儲存。', 'error'); return; }
            }
            const cleanQuestions = JSON.parse(JSON.stringify(s.questions)).map(q => { delete q._open; delete q._justAdded; return q; });
            const payload = { ...s, slug: s.slug || '', questions: cleanQuestions };
            delete payload.id;
            try {'''
if save_old in text:
    text = text.replace(save_old, save_new, 1)

# 6. Dashboard links prefer slug, fallback to immutable random ID.
text = text.replace("const link = `${window.location.origin}${window.location.pathname}?s=${s.id}`;", "const link = surveyPublicLink(s);")

path.write_text(text, encoding='utf-8')
print('patched optional collision-safe survey slug')
