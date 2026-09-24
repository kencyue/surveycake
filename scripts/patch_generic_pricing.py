from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# Idempotent patch: enable pricing on single choice, multi choice, image cards and counters.

# Pricing participation helper supports all requested selectable types.
if 'function questionHasPricing(q)' not in text:
    marker = '        function parseTierRules(raw) {'
    helper = '''        function questionHasPricing(q) {\n            if (!q) return false;\n            const supported = q.type === 'counter_group' || q.type === 'choice_single' || q.type === 'choice_multi' || q.type === 'choice_cards';\n            if (!supported) return false;\n            if (q.pricingEnabled === true) return true;\n            const entries = q.type === 'counter_group' ? (q.items || []) : (q.options || []);\n            return q.pricingEnabled !== false && entries.some(entry => {\n                const p = entry.pricing || {};\n                return Number(p.actualUnitPrice || 0) || Number(p.prepayUnitPrice || 0) || String(p.tierRules || '').trim() || String(p.agePriceRules || '').trim();\n            });\n        }\n\n'''
    if marker not in text:
        raise SystemExit('parseTierRules marker not found')
    text = text.replace(marker, helper + marker, 1)
else:
    start = text.find('        function questionHasPricing(q) {')
    end = text.find('        function parseTierRules(raw) {', start)
    if start >= 0 and end > start:
        text = text[:start] + '''        function questionHasPricing(q) {\n            if (!q) return false;\n            const supported = q.type === 'counter_group' || q.type === 'choice_single' || q.type === 'choice_multi' || q.type === 'choice_cards';\n            if (!supported) return false;\n            if (q.pricingEnabled === true) return true;\n            const entries = q.type === 'counter_group' ? (q.items || []) : (q.options || []);\n            return q.pricingEnabled !== false && entries.some(entry => {\n                const p = entry.pricing || {};\n                return Number(p.actualUnitPrice || 0) || Number(p.prepayUnitPrice || 0) || String(p.tierRules || '').trim() || String(p.agePriceRules || '').trim();\n            });\n        }\n\n''' + text[end:]

# Replace the calculator body with a generic choice + counter implementation.
calc_start = text.find('        function calculatePricingSummaryFor(survey, answers) {')
calc_end = text.find('        function calculatePricingSummary()', calc_start)
if calc_start < 0 or calc_end < 0:
    raise SystemExit('pricing calculator markers not found')
calc = r'''        function calculatePricingSummaryFor(survey, answers) {
            const p = getPricingConfig(survey);
            if (!p) return null;
            answers = answers || {};
            const lines = [];
            let actualTotal = 0, prepayTotal = 0, totalPeople = 0, shirts = 0;
            const peopleQid = p.peopleQuestionId || '';
            if (peopleQid) {
                const counts = answers[peopleQid]?.counts || {};
                totalPeople = Object.values(counts).reduce((a,b)=>a+Number(b||0),0);
            }
            (survey.questions || []).filter(questionHasPricing).forEach(q => {
                if (q.type === 'counter_group') {
                    const ans = answers[q.id] || { counts:{}, ages:{} };
                    (q.items || []).forEach(item => {
                        const qty = Number(ans.counts?.[item.id] || 0);
                        if (!qty || !item.pricing) return;
                        const cfg = item.pricing || {};
                        let actual = qty * Number(cfg.actualUnitPrice || 0);
                        const ageRules = parseAgePriceRules(cfg.agePriceRules);
                        if (ageRules.length && item.ageOptions) {
                            const ages = ans.ages?.[item.id] || [];
                            actual = 0;
                            for (let i=0;i<qty;i++) {
                                const age = ageNumber(ages[i]);
                                const rule = ageRules.find(r => age >= r.min && age <= r.max);
                                actual += rule ? rule.price : Number(cfg.actualUnitPrice || 0);
                            }
                        }
                        const tiers = parseTierRules(cfg.tierRules);
                        if (tiers.length) {
                            let unit = Number(cfg.actualUnitPrice || 0);
                            tiers.forEach(t => { if (qty >= t.min) unit = t.price; });
                            actual = qty * unit;
                        }
                        const prepay = qty * Number(cfg.prepayUnitPrice || 0);
                        actualTotal += actual; prepayTotal += prepay;
                        if (actual || prepay) lines.push({ label:`${q.label}－${item.label}`, qty, actual, prepay });
                        if (/隊服|衣服|shirt/i.test(q.label || '')) shirts += qty;
                    });
                    return;
                }
                const ans = answers[q.id] || { selected:[] };
                const selected = Array.isArray(ans.selected) ? ans.selected : [];
                (q.options || []).forEach(opt => {
                    if (!selected.includes(opt.id) || !opt.pricing) return;
                    const cfg = opt.pricing || {};
                    const actual = Number(cfg.actualUnitPrice || 0);
                    const prepay = Number(cfg.prepayUnitPrice || 0);
                    actualTotal += actual; prepayTotal += prepay;
                    if (actual || prepay) lines.push({ label:`${q.label}－${opt.label}`, qty:1, actual, prepay });
                });
            });
            const perPersonActual = totalPeople * Number(p.perPersonActual || 0);
            const perPersonPrepay = totalPeople * Number(p.perPersonPrepay || 0);
            if (perPersonActual || perPersonPrepay) {
                actualTotal += perPersonActual; prepayTotal += perPersonPrepay;
                lines.push({ label:p.perPersonLabel || '每人固定費用', qty:totalPeople, actual:perPersonActual, prepay:perPersonPrepay });
            }
            return { totalPeople, shirts, lines, projectedTotal:actualTotal, prepayTotal };
        }

'''
text = text[:calc_start] + calc + text[calc_end:]

# Choice editor: add pricing switch and per-option actual/prepay prices.
choice_old = '''            } else if (q.type.startsWith('choice')) {
                typeSpecificHtml = `
                    <div class="flex flex-wrap gap-4 text-sm">
                        <label class="flex items-center gap-1.5"><input type="checkbox" class="q-field" data-idx="${idx}" data-field="allowCustom" data-bool="1" ${q.allowCustom ? 'checked' : ''}> 允許其他自填</label>
                    </div>'''
choice_new = '''            } else if (q.type.startsWith('choice')) {
                typeSpecificHtml = `
                    <div class="space-y-3">
                        <label class="flex items-center justify-between gap-3 rounded-xl border p-3 text-sm font-bold ${questionHasPricing(q) ? 'border-[var(--brand-200)] bg-[var(--brand-50)]' : 'border-gray-200 bg-gray-50'}">
                            <span><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>納入金額統計</span>
                            <input type="checkbox" class="q-field" data-idx="${idx}" data-field="pricingEnabled" data-bool="1" ${questionHasPricing(q) ? 'checked' : ''}>
                        </label>
                        <p class="text-[11px] text-gray-400">開啟後，所選選項的實際單價／預收單價會列入最後金額確認與後台費用統計。</p>
                    </div>
                    <div class="flex flex-wrap gap-4 text-sm">
                        <label class="flex items-center gap-1.5"><input type="checkbox" class="q-field" data-idx="${idx}" data-field="allowCustom" data-bool="1" ${q.allowCustom ? 'checked' : ''}> 允許其他自填</label>
                    </div>'''
if choice_old in text:
    text = text.replace(choice_old, choice_new, 1)

# Add price controls to each choice option after its label row.
choice_label_row = '''                                </div>
                                ${q.type === 'choice_cards' ? `'''
choice_price = '''                                </div>
                                <div class="option-pricing-panel ${questionHasPricing(q) ? '' : 'hidden'} rounded-lg p-2" style="background-color:var(--brand-50);border:1px solid var(--brand-100)">
                                    <div class="text-[11px] font-bold mb-2" style="color:var(--brand-700)"><i class="fas fa-dollar-sign mr-1"></i>費用設定</div>
                                    <div class="grid grid-cols-2 gap-2">
                                        <label class="text-[11px] text-gray-500">實際單價<input type="number" min="0" class="opt-price-field w-full border border-gray-200 rounded-lg py-1 px-1.5 mt-1" data-idx="${idx}" data-oi="${oi}" data-price-field="actualUnitPrice" value="${Number(opt.pricing?.actualUnitPrice||0)}"></label>
                                        <label class="text-[11px] text-gray-500">預收單價<input type="number" min="0" class="opt-price-field w-full border border-gray-200 rounded-lg py-1 px-1.5 mt-1" data-idx="${idx}" data-oi="${oi}" data-price-field="prepayUnitPrice" value="${Number(opt.pricing?.prepayUnitPrice||0)}"></label>
                                    </div>
                                </div>
                                ${q.type === 'choice_cards' ? `'''
if 'class="opt-price-field' not in text:
    if choice_label_row not in text:
        raise SystemExit('choice option insertion marker not found')
    text = text.replace(choice_label_row, choice_price, 1)

# Counter editor: add the same explicit switch and hide item price panels until enabled.
counter_old = '''            } else if (q.type === 'counter_group') {
                typeSpecificHtml = `
                    <div class="space-y-2">
                        <div class="text-xs font-semibold text-gray-500">計數項目：</div>'''
counter_new = '''            } else if (q.type === 'counter_group') {
                typeSpecificHtml = `
                    <div class="space-y-3">
                        <label class="flex items-center justify-between gap-3 rounded-xl border p-3 text-sm font-bold ${questionHasPricing(q) ? 'border-[var(--brand-200)] bg-[var(--brand-50)]' : 'border-gray-200 bg-gray-50'}">
                            <span><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>納入金額統計</span>
                            <input type="checkbox" class="q-field" data-idx="${idx}" data-field="pricingEnabled" data-bool="1" ${questionHasPricing(q) ? 'checked' : ''}>
                        </label>
                        <p class="text-[11px] text-gray-400">開啟後，此題各項目的單價／預收／級距／年齡票價會列入最後金額確認與後台費用統計。</p>
                        <div class="text-xs font-semibold text-gray-500">計數項目：</div>'''
if counter_old in text:
    text = text.replace(counter_old, counter_new, 1)

counter_panel_old = '''                                <div class="rounded-lg p-2 space-y-2" style="background-color:var(--brand-50);border:1px solid var(--brand-100)">
                                    <div class="text-[11px] font-bold" style="color:var(--brand-700)"><i class="fas fa-dollar-sign mr-1"></i>費用設定（選填）</div>'''
counter_panel_new = '''                                <div class="item-pricing-panel ${questionHasPricing(q) ? '' : 'hidden'} rounded-lg p-2 space-y-2" style="background-color:var(--brand-50);border:1px solid var(--brand-100)">
                                    <div class="text-[11px] font-bold" style="color:var(--brand-700)"><i class="fas fa-dollar-sign mr-1"></i>費用設定</div>'''
if counter_panel_old in text:
    text = text.replace(counter_panel_old, counter_panel_new, 1)

# Question toggle rerenders immediately.
handler_old = """                    if (field === 'allowCustom') { q.allowCustom = el.checked; renderQuestionEditorList(); return; }
                    if (el.dataset.bool) q[field] = el.checked; else q[field] = el.value;"""
handler_new = """                    if (field === 'allowCustom') { q.allowCustom = el.checked; renderQuestionEditorList(); return; }
                    if (field === 'pricingEnabled') { q.pricingEnabled = el.checked; renderQuestionEditorList(); return; }
                    if (el.dataset.bool) q[field] = el.checked; else q[field] = el.value;"""
if handler_old in text:
    text = text.replace(handler_old, handler_new, 1)

# Choice option price handlers.
opt_handler_anchor = "            document.querySelectorAll('.del-opt-btn').forEach(b => b.addEventListener('click', () => {"
if "document.querySelectorAll('.opt-price-field')" not in text:
    opt_handler = r'''            document.querySelectorAll('.opt-price-field').forEach(el => {
                el.addEventListener('input', () => {
                    const idx = Number(el.dataset.idx), oi = Number(el.dataset.oi), field = el.dataset.priceField;
                    const opt = s.questions[idx].options[oi];
                    opt.pricing = opt.pricing || {};
                    opt.pricing[field] = Number(el.value) || 0;
                });
            });
'''
    if opt_handler_anchor not in text:
        raise SystemExit('option handler marker not found')
    text = text.replace(opt_handler_anchor, opt_handler + opt_handler_anchor, 1)

# Help text reflects all supported types.
text = text.replace('啟用後，填答者送出前會多一頁「最後統計預覽確認」。各計數項目的單價可在下方題目內維護。', '啟用後，填答者送出前會多一頁「最後統計預覽確認」。單選／多選／多選圖卡／人數統計皆可個別開啟「納入金額統計」並維護價格。')
text = text.replace('再於需要計價的「人數統計」題目勾選「納入金額統計」，即可維護各項目的單價。', '單選／多選／多選圖卡／人數統計皆可個別開啟「納入金額統計」並維護價格。')

path.write_text(text, encoding='utf-8')
print('patched pricing for choice_single/choice_multi/choice_cards/counter_group')
