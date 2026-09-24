from pathlib import Path

path = Path("public/index.html")
text = path.read_text(encoding="utf-8")
marker = "function renderPricingSummary()"
if marker in text:
    print("pricing summary already present")
    raise SystemExit(0)

needle = "        function renderFillPage() {\n"
if needle not in text:
    raise SystemExit("renderFillPage marker not found")

helper = r'''        function renderPricingSummary() {
            const p = state.activeSurvey && state.activeSurvey.pricing;
            if (!p || !p.enabled) return '';
            const answers = state.answers || {};
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
            // Adults are always charged at the 7+ ticket rate. Children without an age default to under-7.
            childUnder7 += Math.max(0, children - childAges.length);
            const ticketAdultCount = adults + child7plus;

            const roomQ = p.roomQuestionId;
            const twin = count(roomQ, p.twinItemId);
            const quad = count(roomQ, p.quadItemId);
            const extra = count(roomQ, p.extraBedItemId);
            const roomActual = twin * 3500 + quad * 5200 + extra * 800;

            const shirtQ = p.shirtQuestionId;
            const shirtAns = answers[shirtQ]?.counts || {};
            const shirts = Object.values(shirtAns).reduce((a, b) => a + Number(b || 0), 0);
            const shirtTier = shirts >= 50 ? 650 : (shirts >= 20 ? 700 : (shirts >= 15 ? 750 : 700));
            const shirtActual = shirts * shirtTier;
            const shirtPrepay = shirts * 700;

            const ticketsActual = ticketAdultCount * 285 + childUnder7 * 230;
            const mealsActual = totalPeople * 900;
            const roomPrepay = totalPeople * 500;
            const mealTicketPrepay = totalPeople * 500;
            const prepayTotal = roomPrepay + mealTicketPrepay + shirtPrepay;
            const projectedTotal = roomActual + ticketsActual + mealsActual + shirtActual;
            const money = n => Number(n || 0).toLocaleString('zh-TW');

            return `<div class="bg-white rounded-2xl shadow-sm p-5 mb-6 border-2" style="border-color:var(--brand-200)">
                <div class="flex items-center gap-2 mb-4"><i class="fas fa-receipt" style="color:var(--brand-500)"></i><h3 class="font-bold text-lg text-gray-800">最後統計預覽確認</h3></div>
                <div class="space-y-2 text-sm text-gray-600">
                    <div class="flex justify-between"><span>參加人數</span><b class="text-gray-800">${totalPeople} 人（大人 ${adults}／小孩 ${children}）</b></div>
                    <div class="flex justify-between"><span>房間預估</span><b class="text-gray-800">$${money(roomActual)}</b></div>
                    <div class="flex justify-between"><span>鐵道自行車</span><b class="text-gray-800">$${money(ticketsActual)}</b></div>
                    <div class="flex justify-between"><span>D1 晚餐＋D2 午餐</span><b class="text-gray-800">$${money(mealsActual)}</b></div>
                    <div class="flex justify-between"><span>隊服 ${shirts} 件（目前級距 $${money(shirtTier)}/件）</span><b class="text-gray-800">$${money(shirtActual)}</b></div>
                    <div class="border-t pt-2 mt-2 flex justify-between"><span>預估活動總額</span><b class="text-gray-800">$${money(projectedTotal)}</b></div>
                </div>
                <div class="mt-4 rounded-xl p-4" style="background-color:var(--brand-50)">
                    <div class="text-xs mb-1" style="color:var(--brand-700)">預收：住宿 $500/人 ＋ 用餐/車票 $500/人 ＋ 隊服 $700/件</div>
                    <div class="flex items-end justify-between"><span class="font-bold" style="color:var(--brand-700)">預收費用合計</span><span class="text-2xl font-extrabold" style="color:var(--brand-600)">$${money(prepayTotal)}</span></div>
                </div>
                <p class="text-xs text-gray-400 mt-3">實際費用依最終人數、房型與隊服總件數級距結算；此處先依目前填寫內容試算。</p>
            </div>`;
        }

'''
text = text.replace(needle, helper + needle, 1)

old = '''                <div class="w-full animate-slide-up">
                    <div id="question-list"></div>
                    <button id="btn-page-next"'''
new = '''                <div class="w-full animate-slide-up">
                    <div id="question-list"></div>
                    ${isLast ? renderPricingSummary() : ''}
                    <button id="btn-page-next"'''
if old not in text:
    raise SystemExit("fill page template marker not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched configurable pricing summary")
