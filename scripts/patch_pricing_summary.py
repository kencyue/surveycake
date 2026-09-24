from pathlib import Path

path = Path("public/index.html")
text = path.read_text(encoding="utf-8")

# The pricing helper may already be the new calculatePricingSummary version, or the old renderPricingSummary version.
start = text.find("        function calculatePricingSummary() {")
if start < 0:
    start = text.find("        function renderPricingSummary() {")
end = text.find("        function renderFillPage() {", start)
if start < 0 or end < 0:
    raise SystemExit("pricing/renderFillPage markers not found")

helper = r'''        function getPricingConfig(survey) {
            survey = survey || {};
            let p = survey.pricing;
            if ((!p || !p.enabled) && (survey.questions || []).some(q => q.id === 'attendees') && (survey.questions || []).some(q => q.id === 'rooms')) {
                p = { enabled:true, attendeeQuestionId:'attendees', adultItemId:'adult', childItemId:'child', roomQuestionId:'rooms', twinItemId:'twin', quadItemId:'quad', extraBedItemId:'extra', shirtQuestionId:'shirts' };
            }
            return p && p.enabled ? p : null;
        }

        function calculatePricingSummaryFor(survey, answers) {
            const p = getPricingConfig(survey);
            if (!p) return null;
            answers = answers || {};
            const count = (qid, itemId) => Number(answers[qid]?.counts?.[itemId] || 0);
            const attendeeQ = p.attendeeQuestionId;
            const adults = count(attendeeQ, p.adultItemId);
            const children = count(attendeeQ, p.childItemId);
            const totalPeople = adults + children;
            let child7plus = 0, childUnder7 = 0;
            const childAges = answers[attendeeQ]?.ages?.[p.childItemId] || [];
            childAges.forEach(age => {
                const m = String(age || '').match(/(\d+)/);
                const n = m ? Number(m[1]) : 0;
                if (n >= 7) child7plus++; else childUnder7++;
            });
            childUnder7 += Math.max(0, children - childAges.length);
            const ticketAdultCount = adults + child7plus;
            const twin = count(p.roomQuestionId, p.twinItemId);
            const quad = count(p.roomQuestionId, p.quadItemId);
            const extra = count(p.roomQuestionId, p.extraBedItemId);
            const roomActual = twin * 3500 + quad * 5200 + extra * 800;
            const shirtAns = answers[p.shirtQuestionId]?.counts || {};
            const shirts = Object.values(shirtAns).reduce((a,b) => a + Number(b || 0), 0);
            const shirtTier = shirts >= 50 ? 650 : (shirts >= 20 ? 700 : (shirts >= 15 ? 750 : 700));
            const shirtActual = shirts * shirtTier;
            const ticketsActual = ticketAdultCount * 285 + childUnder7 * 230;
            const mealsActual = totalPeople * 900;
            const prepayTotal = totalPeople * 1000 + shirts * 700;
            const projectedTotal = roomActual + ticketsActual + mealsActual + shirtActual;
            return { adults, children, totalPeople, child7plus, childUnder7, twin, quad, extra, shirts, shirtTier, roomActual, ticketsActual, mealsActual, shirtActual, projectedTotal, prepayTotal };
        }

        function calculatePricingSummary() {
            return calculatePricingSummaryFor(state.activeSurvey || {}, state.answers || {});
        }

        function pricingSummaryHtml(x, compact = false) {
            if (!x) return '';
            const money = n => Number(n || 0).toLocaleString('zh-TW');
            return `<div class="${compact ? 'rounded-xl p-3' : 'bg-white rounded-2xl shadow-sm p-5 mb-6 border-2'}" style="${compact ? 'background-color:var(--brand-50);border:1px solid var(--brand-100)' : 'border-color:var(--brand-200)'}">
                <div class="flex items-center gap-2 mb-3"><i class="fas fa-receipt" style="color:var(--brand-500)"></i><h3 class="font-bold ${compact ? 'text-sm' : 'text-lg'} text-gray-800">最後統計預覽確認</h3></div>
                <div class="space-y-1.5 text-sm text-gray-600">
                    <div class="flex justify-between gap-3"><span>參加人數</span><b class="text-gray-800">${x.totalPeople} 人（大人 ${x.adults}／小孩 ${x.children}）</b></div>
                    <div class="flex justify-between"><span>房間預估</span><b class="text-gray-800">$${money(x.roomActual)}</b></div>
                    <div class="flex justify-between"><span>鐵道自行車</span><b class="text-gray-800">$${money(x.ticketsActual)}</b></div>
                    <div class="flex justify-between"><span>D1 晚餐＋D2 午餐</span><b class="text-gray-800">$${money(x.mealsActual)}</b></div>
                    <div class="flex justify-between gap-3"><span>隊服 ${x.shirts} 件（$${money(x.shirtTier)}/件）</span><b class="text-gray-800">$${money(x.shirtActual)}</b></div>
                    <div class="border-t pt-2 mt-2 flex justify-between"><span>預估活動總額</span><b class="text-gray-800">$${money(x.projectedTotal)}</b></div>
                </div>
                <div class="mt-3 rounded-xl p-3" style="background-color:var(--brand-100)"><div class="flex items-end justify-between gap-3"><span class="font-bold" style="color:var(--brand-700)">預收費用合計</span><span class="${compact ? 'text-xl' : 'text-2xl'} font-extrabold" style="color:var(--brand-600)">$${money(x.prepayTotal)}</span></div></div>
                ${compact ? '' : '<p class="text-xs text-gray-400 mt-3">預收：住宿 $500/人 ＋ 用餐/車票 $500/人 ＋ 隊服 $700/件。實際費用依最終人數、房型與隊服總件數級距結算。</p>'}
            </div>`;
        }

        function renderPricingSummary() { return pricingSummaryHtml(calculatePricingSummary(), false); }
        function renderAdminPricingSummary(summary) { return summary ? pricingSummaryHtml(summary, true) : ''; }

        function buildAdminPricingAggregate(rows) {
            const survey = state.viewingSurveyMeta || {};
            const summaries = rows.map(r => r.pricingSummary || calculatePricingSummaryFor(survey, r.answers || {})).filter(Boolean);
            if (!summaries.length) return '';
            const sum = key => summaries.reduce((a,s) => a + Number(s[key] || 0), 0);
            const money = n => Number(n || 0).toLocaleString('zh-TW');
            return `<div class="mb-4 rounded-2xl p-4 border" style="background-color:var(--brand-50);border-color:var(--brand-200)">
                <div class="font-bold text-gray-800 mb-2"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用統計</div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                    <div class="stat-pill rounded-xl p-2"><div class="font-extrabold" style="color:var(--brand-600)">${sum('totalPeople')}</div><div class="text-xs text-gray-500">總人數</div></div>
                    <div class="stat-pill rounded-xl p-2"><div class="font-extrabold" style="color:var(--brand-600)">${sum('shirts')}</div><div class="text-xs text-gray-500">隊服件數</div></div>
                    <div class="stat-pill rounded-xl p-2"><div class="font-extrabold" style="color:var(--brand-600)">$${money(sum('projectedTotal'))}</div><div class="text-xs text-gray-500">預估總額</div></div>
                    <div class="stat-pill rounded-xl p-2"><div class="font-extrabold" style="color:var(--brand-600)">$${money(sum('prepayTotal'))}</div><div class="text-xs text-gray-500">預收合計</div></div>
                </div>
            </div>`;
        }

'''
text = text[:start] + helper + text[end:]

# Dedicated confirmation page: the last answer page now goes to a visible pricing review page before submit.
fill_start = text.find("        function renderFillPage() {")
fill_end = text.find("        function validatePage(", fill_start)
if fill_start < 0 or fill_end < 0:
    raise SystemExit("renderFillPage block not found")
new_fill = r'''        function renderFillPage() {
            const isPricingReview = state.currentPageIndex === state.pages.length;
            const hasPricing = !!getPricingConfig(state.activeSurvey || {});
            if (isPricingReview && hasPricing) {
                DOM.root.innerHTML = `
                    <div class="w-full animate-slide-up">
                        ${renderPricingSummary()}
                        <button id="btn-page-next" class="w-full text-white font-bold py-4 px-8 rounded-2xl shadow-md transition-transform transform active:scale-95 text-lg flex items-center justify-center relative overflow-hidden" style="background-color:var(--brand-500)">
                            <span id="submit-text">確認送出</span>
                            <div id="submit-loader" class="hidden absolute inset-0 flex items-center justify-center" style="background-color:var(--brand-600)"><i class="fas fa-spinner fa-spin text-2xl"></i></div>
                        </button>
                    </div>`;
                document.getElementById('btn-page-next').addEventListener('click', async () => {
                    if (!isSurveyOpenNow(state.activeSurvey)) return showMessage('問卷已截止', '問卷調查已截止，無法送出，感謝您的參與！', 'error');
                    document.getElementById('submit-text').classList.add('invisible');
                    document.getElementById('submit-loader').classList.remove('hidden');
                    const ok = await submitResponse();
                    if (ok) { state.mode = 'thanks'; render(); window.scrollTo(0, 0); }
                    else { document.getElementById('submit-text').classList.remove('invisible'); document.getElementById('submit-loader').classList.add('hidden'); }
                });
                return;
            }

            const pageQuestions = state.pages[state.currentPageIndex] || [];
            const isLastQuestionPage = state.currentPageIndex === state.pages.length - 1;
            const submitHere = isLastQuestionPage && !hasPricing;
            DOM.root.innerHTML = `
                <div class="w-full animate-slide-up">
                    <div id="question-list"></div>
                    <button id="btn-page-next" class="w-full text-white font-bold py-4 px-8 rounded-2xl shadow-md transition-transform transform active:scale-95 text-lg flex items-center justify-center relative overflow-hidden" style="background-color:var(--brand-500)">
                        <span id="submit-text">${submitHere ? '確認送出' : (isLastQuestionPage ? '查看最後統計與金額' : '下一步')}</span>
                        <div id="submit-loader" class="hidden absolute inset-0 flex items-center justify-center" style="background-color:var(--brand-600)"><i class="fas fa-spinner fa-spin text-2xl"></i></div>
                        ${submitHere ? '' : '<i class="fas fa-arrow-right ml-2"></i>'}
                    </button>
                </div>`;
            renderCurrentQuestions(pageQuestions);
            document.getElementById('btn-page-next').addEventListener('click', async () => {
                if (!isSurveyOpenNow(state.activeSurvey)) return showMessage('問卷已截止', '問卷調查已截止，無法再繼續填寫，感謝您的參與！', 'error');
                if (!validatePage(pageQuestions)) return;
                if (!submitHere) { state.currentPageIndex++; render(); window.scrollTo(0, 0); return; }
                document.getElementById('submit-text').classList.add('invisible');
                document.getElementById('submit-loader').classList.remove('hidden');
                const ok = await submitResponse();
                if (ok) { state.mode = 'thanks'; render(); window.scrollTo(0, 0); }
                else { document.getElementById('submit-text').classList.remove('invisible'); document.getElementById('submit-loader').classList.add('hidden'); }
            });
        }

'''
text = text[:fill_start] + new_fill + text[fill_end:]

# Save the calculation snapshot for new responses.
old = '''                await addDoc(responsesCol(state.activeSurveyId), {
                    answers: state.answers,
                    timestamp: new Date().toISOString(),
                    userId: currentUser.uid
                });'''
new = '''                await addDoc(responsesCol(state.activeSurveyId), {
                    answers: state.answers,
                    pricingSummary: calculatePricingSummary(),
                    timestamp: new Date().toISOString(),
                    userId: currentUser.uid
                });'''
if old in text:
    text = text.replace(old, new, 1)

# Admin aggregate: calculate old responses on the fly too, so money statistics are visible immediately.
old = "            statsContainer.innerHTML = '';\n"
if old in text:
    text = text.replace(old, "            statsContainer.innerHTML = buildAdminPricingAggregate(rows);\n", 1)

# Expanded admin response: use stored snapshot, otherwise calculate legacy rows from their answers.
needle = "                            ${(s.questions || []).map(q => renderAnswerDetail(q, row.answers ? row.answers[q.id] : undefined)).join('')}\n"
if needle in text and 'calculatePricingSummaryFor(s, row.answers || {})' not in text:
    text = text.replace(needle, needle + "                            ${renderAdminPricingSummary(row.pricingSummary || calculatePricingSummaryFor(s, row.answers || {}))}\n", 1)

# Export money columns for both new and legacy responses.
pos = text.find('        function getExportRows() {')
if pos >= 0:
    endpos = text.find('        function downloadFile(', pos)
    block = text[pos:endpos]
    old_line = "                if (row.pricingSummary) { out['預估活動總額'] = row.pricingSummary.projectedTotal || 0; out['預收費用合計'] = row.pricingSummary.prepayTotal || 0; }\n"
    new_line = "                const pricing = row.pricingSummary || calculatePricingSummaryFor(s, row.answers || {}); if (pricing) { out['預估活動總額'] = pricing.projectedTotal || 0; out['預收費用合計'] = pricing.prepayTotal || 0; }\n"
    if old_line in block:
        block = block.replace(old_line, new_line, 1)
    elif "'預收費用合計'" not in block:
        block = block.replace("                return out;\n", new_line + "                return out;\n", 1)
    text = text[:pos] + block + text[endpos:]

path.write_text(text, encoding="utf-8")
print("patched dedicated pricing review + legacy admin calculation")
