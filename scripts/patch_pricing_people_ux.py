from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# Global pricing: make per-person multiplication a separate, explicit optional feature.
# This avoids implying that the selected people-source controls other priced questions.

# Add an explicit enable switch around the people-source/per-person section.
old = '''                            <div>
                                <label class="block text-xs font-semibold text-gray-600 mb-1">總人數來源 <span class="font-normal text-gray-400">（選填）</span></label>
                                <p class="text-[11px] leading-relaxed text-gray-400 mb-2">只用來計算下方「每人固定費用 × 總人數」。不會影響其他題目的金額統計；其他題目仍依各自的「納入金額統計」開關計費。</p>
                                <select id="ed-pricing-people-qid" class="w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm bg-white">
                                    <option value="">不使用總人數計算</option>'''
new = '''                            <div class="rounded-xl border border-gray-100 bg-gray-50 p-3 space-y-3">
                                <label class="flex items-center justify-between gap-3 text-sm font-bold text-gray-700">
                                    <span><i class="fas fa-users mr-2" style="color:var(--brand-500)"></i>依總人數計算固定費用 <span class="font-normal text-gray-400">（選填）</span></span>
                                    <input type="checkbox" id="ed-pricing-people-enabled" ${(s.pricing?.peopleEnabled || !!s.pricing?.peopleQuestionId) ? 'checked' : ''}>
                                </label>
                                <p class="text-[11px] leading-relaxed text-gray-400">只有需要「每人固定費用 × 總人數」時才開啟。這個設定完全不影響其他題目的金額統計。</p>
                                <div id="pricing-people-fields" class="${(s.pricing?.peopleEnabled || !!s.pricing?.peopleQuestionId) ? '' : 'hidden'} space-y-3">
                                <div>
                                <label class="block text-xs font-semibold text-gray-600 mb-1">哪一題代表總人數？</label>
                                <select id="ed-pricing-people-qid" class="w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm bg-white">
                                    <option value="">請選擇人數題目</option>'''
if old in text:
    text = text.replace(old, new, 1)

# Close the new wrapper after the fixed-fee label.
old_close = '''                            <label class="block text-xs font-semibold text-gray-500">每人固定費用名稱<input id="ed-pricing-person-label" type="text" class="mt-1 w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm" value="${escapeHtml(s.pricing?.perPersonLabel||'每人固定費用')}" placeholder="例如：D1晚餐＋D2午餐"></label>
                        </div>'''
new_close = '''                            <label class="block text-xs font-semibold text-gray-500">每人固定費用名稱<input id="ed-pricing-person-label" type="text" class="mt-1 w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm" value="${escapeHtml(s.pricing?.perPersonLabel||'每人固定費用')}" placeholder="例如：D1晚餐＋D2午餐"></label>
                                </div>
                                </div>
                        </div>'''
if old_close in text:
    text = text.replace(old_close, new_close, 1)

# Bind the optional switch and clear multiplication when disabled.
bind_marker = '''            const peopleQ = document.getElementById('ed-pricing-people-qid');
            if (peopleQ) peopleQ.addEventListener('change', e => { s.pricing = s.pricing || {}; s.pricing.peopleQuestionId = e.target.value; });'''
bind_new = '''            const peopleEnabled = document.getElementById('ed-pricing-people-enabled');
            if (peopleEnabled) peopleEnabled.addEventListener('change', e => {
                s.pricing = s.pricing || {};
                s.pricing.peopleEnabled = e.target.checked;
                const box = document.getElementById('pricing-people-fields');
                if (box) box.classList.toggle('hidden', !e.target.checked);
                if (!e.target.checked) s.pricing.peopleQuestionId = '';
            });
            const peopleQ = document.getElementById('ed-pricing-people-qid');
            if (peopleQ) peopleQ.addEventListener('change', e => { s.pricing = s.pricing || {}; s.pricing.peopleQuestionId = e.target.value; s.pricing.peopleEnabled = !!e.target.value; });'''
if bind_marker in text:
    text = text.replace(bind_marker, bind_new, 1)

# Calculation only uses total people when this feature is enabled. Legacy records with a peopleQuestionId remain compatible.
text = text.replace("const peopleQid = p.peopleQuestionId || '';", "const peopleQid = (p.peopleEnabled === false) ? '' : (p.peopleQuestionId || '');", 1)

# Improve mobile header if older markup is still present.
text = text.replace(
'''                        <div class="flex items-center justify-between">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用計算設定</h2>
                            <label class="flex items-center gap-2 text-sm font-bold"><input type="checkbox" id="ed-pricing-enabled" ${s.pricing?.enabled ? 'checked' : ''}> 啟用最後金額確認</label>
                        </div>''',
'''                        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用計算設定</h2>
                            <label class="flex items-center justify-between sm:justify-end gap-3 text-sm font-bold rounded-xl bg-gray-50 px-3 py-2"><span>啟用最後金額確認</span><input type="checkbox" id="ed-pricing-enabled" ${s.pricing?.enabled ? 'checked' : ''}></label>
                        </div>''', 1)

path.write_text(text, encoding='utf-8')
print('patched explicit optional per-person pricing switch')
