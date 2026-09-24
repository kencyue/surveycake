from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# 1) Fix progress: pricing confirmation is a real extra step, never 2/1 or 200%.
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

# 2) Replace the pricing engine with a generic schema driven by admin-maintainable data.
start = text.find('        function getPricingConfig(survey) {')
end = text.find('        function pricingSummaryHtml(', start)
if start < 0 or end < 0:
    raise SystemExit('generic pricing helper markers not found')
engine = r'''        function getPricingConfig(survey) {
            survey = survey || {};
            const p = survey.pricing;
            return p && p.enabled ? p : null;
        }

        function parseTierRules(raw) {
            if (!raw) return [];
            if (Array.isArray(raw)) return raw.map(x => ({ min:Number(x.min)||0, price:Number(x.price)||0 })).sort((a,b)=>a.min-b.min);
            return String(raw).split(/[,，]/).map(x => x.trim()).filter(Boolean).map(x => {
                const m = x.match(/(\d+)\s*[:：=]\s*(\d+(?:\.\d+)?)/);
                return m ? { min:Number(m[1]), price:Number(m[2]) } : null;
            }).filter(Boolean).sort((a,b)=>a.min-b.min);
        }

        function parseAgePriceRules(raw) {
            if (!raw) return [];
            return String(raw).split(/[,，]/).map(x => x.trim()).filter(Boolean).map(x => {
                let m = x.match(/(\d+)\s*\+\s*[:：=]\s*(\d+(?:\.\d+)?)/);
                if (m) return { min:Number(m[1]), max:999, price:Number(m[2]) };
                m = x.match(/(\d+)\s*[-~～]\s*(\d+)\s*[:：=]\s*(\d+(?:\.\d+)?)/);
                return m ? { min:Number(m[1]), max:Number(m[2]), price:Number(m[3]) } : null;
            }).filter(Boolean);
        }

        function ageNumber(v) {
            const m = String(v || '').match(/(\d+)/);
            return m ? Number(m[1]) : 0;
        }

        function calculatePricingSummaryFor(survey, answers) {
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
            (survey.questions || []).filter(q => q.type === 'counter_group').forEach(q => {
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
            });
            const perPersonActual = totalPeople * Number(p.perPersonActual || 0);
            const perPersonPrepay = totalPeople * Number(p.perPersonPrepay || 0);
            if (perPersonActual || perPersonPrepay) {
                actualTotal += perPersonActual; prepayTotal += perPersonPrepay;
                lines.push({ label:p.perPersonLabel || '每人固定費用', qty:totalPeople, actual:perPersonActual, prepay:perPersonPrepay });
            }
            return { totalPeople, shirts, lines, projectedTotal:actualTotal, prepayTotal };
        }

        function calculatePricingSummary() { return calculatePricingSummaryFor(state.activeSurvey || {}, state.answers || {}); }

'''
text = text[:start] + engine + text[end:]

# 3) Generic summary HTML: render configured line items, not hard-coded room/ticket/meal/shirt fields.
start = text.find('        function pricingSummaryHtml(')
end = text.find('        function renderPricingSummary()', start)
if start < 0 or end < 0:
    raise SystemExit('pricingSummaryHtml markers not found')
summary = r'''        function pricingSummaryHtml(x, compact = false) {
            if (!x) return '';
            const money = n => Number(n || 0).toLocaleString('zh-TW');
            const lineHtml = (x.lines || []).map(line => `<div class="flex justify-between gap-3"><span>${escapeHtml(line.label)} × ${line.qty}</span><b class="text-gray-800">${line.actual ? '$'+money(line.actual) : (line.prepay ? '預收 $'+money(line.prepay) : '$0')}</b></div>`).join('');
            return `<div class="${compact ? 'rounded-xl p-3' : 'bg-white rounded-2xl shadow-sm p-5 mb-6 border-2'}" style="${compact ? 'background-color:var(--brand-50);border:1px solid var(--brand-100)' : 'border-color:var(--brand-200)'}">
                <div class="flex items-center gap-2 mb-3"><i class="fas fa-receipt" style="color:var(--brand-500)"></i><h3 class="font-bold ${compact ? 'text-sm' : 'text-lg'} text-gray-800">最後統計預覽確認</h3></div>
                <div class="space-y-1.5 text-sm text-gray-600">
                    ${x.totalPeople ? `<div class="flex justify-between"><span>參加人數</span><b class="text-gray-800">${x.totalPeople} 人</b></div>` : ''}
                    ${lineHtml}
                    <div class="border-t pt-2 mt-2 flex justify-between"><span>預估活動總額</span><b class="text-gray-800">$${money(x.projectedTotal)}</b></div>
                </div>
                <div class="mt-3 rounded-xl p-3" style="background-color:var(--brand-100)"><div class="flex items-end justify-between gap-3"><span class="font-bold" style="color:var(--brand-700)">預收費用合計</span><span class="${compact ? 'text-xl' : 'text-2xl'} font-extrabold" style="color:var(--brand-600)">$${money(x.prepayTotal)}</span></div></div>
                ${compact ? '' : '<p class="text-xs text-gray-400 mt-3">金額依問卷後台的費用計算設定即時計算，送出前請再次確認。</p>'}
            </div>`;
        }

'''
text = text[:start] + summary + text[end:]

# 4) Admin survey-level pricing editor.
anchor = '''                    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                        <div class="flex items-center justify-between mb-4">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-list-ol mr-2" style="color:var(--brand-500)"></i>題目</h2>'''
if 'id="ed-pricing-enabled"' not in text and anchor in text:
    panel = r'''                    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
                        <div class="flex items-center justify-between">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用計算設定</h2>
                            <label class="flex items-center gap-2 text-sm font-bold"><input type="checkbox" id="ed-pricing-enabled" ${s.pricing?.enabled ? 'checked' : ''}> 啟用最後金額確認</label>
                        </div>
                        <p class="text-xs text-gray-400">啟用後，填答者送出前會多一頁「最後統計預覽確認」。各計數項目的單價可在下方題目內維護。</p>
                        <div id="pricing-global-fields" class="${s.pricing?.enabled ? '' : 'hidden'} space-y-3">
                            <div>
                                <label class="block text-xs font-semibold text-gray-500 mb-1">參加人數來源</label>
                                <select id="ed-pricing-people-qid" class="w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm bg-white">
                                    <option value="">不統計總人數</option>
                                    ${(s.questions || []).filter(q=>q.type==='counter_group').map(q=>`<option value="${q.id}" ${(s.pricing?.peopleQuestionId||'')===q.id?'selected':''}>${escapeHtml(q.label)}</option>`).join('')}
                                </select>
                            </div>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <label class="text-xs font-semibold text-gray-500">每人固定實際費用<input id="ed-pricing-person-actual" type="number" min="0" class="mt-1 w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm" value="${Number(s.pricing?.perPersonActual||0)}"></label>
                                <label class="text-xs font-semibold text-gray-500">每人固定預收費用<input id="ed-pricing-person-prepay" type="number" min="0" class="mt-1 w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm" value="${Number(s.pricing?.perPersonPrepay||0)}"></label>
                            </div>
                            <label class="block text-xs font-semibold text-gray-500">每人固定費用名稱<input id="ed-pricing-person-label" type="text" class="mt-1 w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm" value="${escapeHtml(s.pricing?.perPersonLabel||'每人固定費用')}" placeholder="例如：D1晚餐＋D2午餐"></label>
                        </div>
                    </div>

'''
    text = text.replace(anchor, panel + anchor, 1)

# Bind global pricing fields.
bind_anchor = "            document.getElementById('btn-save-survey').addEventListener('click', saveSurvey);\n"
if "ed-pricing-enabled').addEventListener" not in text and bind_anchor in text:
    binds = r'''            const pricingEnabled = document.getElementById('ed-pricing-enabled');
            if (pricingEnabled) pricingEnabled.addEventListener('change', e => {
                s.pricing = s.pricing || {};
                s.pricing.enabled = e.target.checked;
                document.getElementById('pricing-global-fields').classList.toggle('hidden', !e.target.checked);
            });
            const peopleQ = document.getElementById('ed-pricing-people-qid');
            if (peopleQ) peopleQ.addEventListener('change', e => { s.pricing = s.pricing || {}; s.pricing.peopleQuestionId = e.target.value; });
            const pa = document.getElementById('ed-pricing-person-actual');
            if (pa) pa.addEventListener('input', e => { s.pricing = s.pricing || {}; s.pricing.perPersonActual = Number(e.target.value)||0; });
            const pp = document.getElementById('ed-pricing-person-prepay');
            if (pp) pp.addEventListener('input', e => { s.pricing = s.pricing || {}; s.pricing.perPersonPrepay = Number(e.target.value)||0; });
            const pl = document.getElementById('ed-pricing-person-label');
            if (pl) pl.addEventListener('input', e => { s.pricing = s.pricing || {}; s.pricing.perPersonLabel = e.target.value; });
'''
    text = text.replace(bind_anchor, binds + bind_anchor, 1)

# 5) Per-counter-item pricing fields in the existing item editor.
item_anchor = '''                                <input type="text" class="item-field w-full border border-gray-200 rounded-lg py-1.5 px-2 text-xs" data-idx="${idx}" data-ii="${ii}" data-field="sublabel" value="${escapeHtml(item.sublabel || '')}" placeholder="附註，如：12歲以上">'''
if 'data-price-field="actualUnitPrice"' not in text and item_anchor in text:
    item_pricing = r'''
                                <div class="rounded-lg p-2 space-y-2" style="background-color:var(--brand-50);border:1px solid var(--brand-100)">
                                    <div class="text-[11px] font-bold" style="color:var(--brand-700)"><i class="fas fa-dollar-sign mr-1"></i>費用設定（選填）</div>
                                    <div class="grid grid-cols-2 gap-2">
                                        <label class="text-[11px] text-gray-500">實際單價<input type="number" min="0" class="item-price-field w-full border border-gray-200 rounded-lg py-1 px-1.5 mt-1" data-idx="${idx}" data-ii="${ii}" data-price-field="actualUnitPrice" value="${Number(item.pricing?.actualUnitPrice||0)}"></label>
                                        <label class="text-[11px] text-gray-500">預收單價<input type="number" min="0" class="item-price-field w-full border border-gray-200 rounded-lg py-1 px-1.5 mt-1" data-idx="${idx}" data-ii="${ii}" data-price-field="prepayUnitPrice" value="${Number(item.pricing?.prepayUnitPrice||0)}"></label>
                                    </div>
                                    <label class="block text-[11px] text-gray-500">數量級距單價<input type="text" class="item-price-field w-full border border-gray-200 rounded-lg py-1 px-1.5 mt-1" data-idx="${idx}" data-ii="${ii}" data-price-field="tierRules" value="${escapeHtml(item.pricing?.tierRules||'')}" placeholder="例如 15:750,20:700,50:650"></label>
                                    ${item.ageOptions ? `<label class="block text-[11px] text-gray-500">年齡票價<input type="text" class="item-price-field w-full border border-gray-200 rounded-lg py-1 px-1.5 mt-1" data-idx="${idx}" data-ii="${ii}" data-price-field="agePriceRules" value="${escapeHtml(item.pricing?.agePriceRules||'')}" placeholder="例如 0-6:230,7+:285"></label>` : ''}
                                </div>'''
    text = text.replace(item_anchor, item_anchor + item_pricing, 1)

handler_anchor = "            document.querySelectorAll('.del-item-btn').forEach(b => b.addEventListener('click', () => {\n"
if "querySelectorAll('.item-price-field')" not in text and handler_anchor in text:
    price_handler = r'''            document.querySelectorAll('.item-price-field').forEach(el => {
                el.addEventListener('input', () => {
                    const idx = Number(el.dataset.idx), ii = Number(el.dataset.ii), field = el.dataset.priceField;
                    const item = s.questions[idx].items[ii];
                    item.pricing = item.pricing || {};
                    item.pricing[field] = (field === 'actualUnitPrice' || field === 'prepayUnitPrice') ? (Number(el.value)||0) : el.value;
                });
            });
'''
    text = text.replace(handler_anchor, price_handler + handler_anchor, 1)

# Remove duplicate pricing card accidentally introduced by previous patch.
dup = "                            ${renderAdminPricingSummary(row.pricingSummary)}\n"
text = text.replace(dup, '', 1)

path.write_text(text, encoding='utf-8')
print('patched generic maintainable pricing + progress')
