from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# Idempotent UI/schema patch layered on the already-deployed generic pricing implementation.
# The deploy workflow writes public/index.html back to main, so every operation is guarded.

# Fix progress for installations that still have the original progress calculation.
old = """                const total = state.pages.length;
                const percent = total > 0 ? Math.round(((state.currentPageIndex + 1) / total) * 100) : 0;
                DOM.progressBar.style.width = `${percent}%`;
                DOM.progressText.textContent = `進度: ${percent}% (第 ${state.currentPageIndex + 1}/${total} 頁)`;"""
new = """                const hasPricingReview = !!getPricingConfig(state.activeSurvey || {});
                const total = state.pages.length + (hasPricingReview ? 1 : 0);
                const current = Math.min(state.currentPageIndex + 1, total);
                const percent = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
                DOM.progressBar.style.width = `${percent}%`;
                DOM.progressText.textContent = `進度: ${percent}% (第 ${current}/${total} 頁)`;"""
if old in text:
    text = text.replace(old, new, 1)

# Add a helper that makes pricing participation explicit while preserving legacy injected data.
if 'function questionHasPricing(q)' not in text:
    marker = '        function parseTierRules(raw) {'
    helper = '''        function questionHasPricing(q) {\n            if (!q || q.type !== 'counter_group') return false;\n            if (q.pricingEnabled === true) return true;\n            return q.pricingEnabled !== false && (q.items || []).some(item => {\n                const p = item.pricing || {};\n                return Number(p.actualUnitPrice || 0) || Number(p.prepayUnitPrice || 0) || String(p.tierRules || '').trim() || String(p.agePriceRules || '').trim();\n            });\n        }\n\n'''
    if marker not in text:
        raise SystemExit('parseTierRules marker not found')
    text = text.replace(marker, helper + marker, 1)

# Only explicitly-enabled/legacy-priced counter questions contribute to calculation.
text = text.replace("(survey.questions || []).filter(q => q.type === 'counter_group').forEach(q => {", "(survey.questions || []).filter(questionHasPricing).forEach(q => {", 1)

# Add explicit question-level toggle before counter items.
counter_marker = '''            } else if (q.type === 'counter_group') {
                typeSpecificHtml = `
                    <div class="space-y-2">
                        <div class="text-xs font-semibold text-gray-500">計數項目：</div>'''
if 'data-field="pricingEnabled"' not in text:
    replacement = '''            } else if (q.type === 'counter_group') {
                typeSpecificHtml = `
                    <div class="space-y-3">
                        <label class="flex items-center justify-between gap-3 rounded-xl border p-3 text-sm font-bold ${questionHasPricing(q) ? 'border-[var(--brand-200)] bg-[var(--brand-50)]' : 'border-gray-200 bg-gray-50'}">
                            <span><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>納入金額統計</span>
                            <input type="checkbox" class="q-field" data-idx="${idx}" data-field="pricingEnabled" data-bool="1" ${questionHasPricing(q) ? 'checked' : ''}>
                        </label>
                        <p class="text-[11px] text-gray-400">開啟後，此題各項目的單價／預收／級距／年齡票價才會列入前台最後確認與後台費用統計。</p>
                        <div class="text-xs font-semibold text-gray-500">計數項目：</div>'''
    if counter_marker not in text:
        raise SystemExit('counter editor marker not found')
    text = text.replace(counter_marker, replacement, 1)

# Existing item pricing panel: hide it until the question is marked as a pricing question.
old_panel = '''                                <div class="rounded-lg p-2 space-y-2" style="background-color:var(--brand-50);border:1px solid var(--brand-100)">
                                    <div class="text-[11px] font-bold" style="color:var(--brand-700)"><i class="fas fa-dollar-sign mr-1"></i>費用設定（選填）</div>'''
new_panel = '''                                <div class="item-pricing-panel ${questionHasPricing(q) ? '' : 'hidden'} rounded-lg p-2 space-y-2" style="background-color:var(--brand-50);border:1px solid var(--brand-100)">
                                    <div class="text-[11px] font-bold" style="color:var(--brand-700)"><i class="fas fa-dollar-sign mr-1"></i>費用設定</div>'''
if old_panel in text:
    text = text.replace(old_panel, new_panel, 1)

# If a previous run already renamed the heading but did not add conditional visibility, fix it.
old_panel2 = '''                                <div class="rounded-lg p-2 space-y-2" style="background-color:var(--brand-50);border:1px solid var(--brand-100)">
                                    <div class="text-[11px] font-bold" style="color:var(--brand-700)"><i class="fas fa-dollar-sign mr-1"></i>費用設定</div>'''
if old_panel2 in text:
    text = text.replace(old_panel2, new_panel, 1)

# Rerender immediately when the pricing participation toggle changes.
old_handler = """                    if (field === 'allowCustom') { q.allowCustom = el.checked; renderQuestionEditorList(); return; }
                    if (el.dataset.bool) q[field] = el.checked; else q[field] = el.value;"""
new_handler = """                    if (field === 'allowCustom') { q.allowCustom = el.checked; renderQuestionEditorList(); return; }
                    if (field === 'pricingEnabled') { q.pricingEnabled = el.checked; renderQuestionEditorList(); return; }
                    if (el.dataset.bool) q[field] = el.checked; else q[field] = el.value;"""
if old_handler in text:
    text = text.replace(old_handler, new_handler, 1)

# Clarify the survey-level help text.
text = text.replace('啟用後，填答者送出前會多一頁「最後統計預覽確認」。各計數項目的單價可在下方題目內維護。', '啟用後，填答者送出前會多一頁「最後統計預覽確認」。再於需要計價的「人數統計」題目勾選「納入金額統計」，即可維護各項目的單價。')

path.write_text(text, encoding='utf-8')
print('patched explicit per-question pricing controls')
