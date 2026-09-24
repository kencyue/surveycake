from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# Make the global pricing control self-explanatory and mobile friendly.
text = text.replace(
'''                        <div class="flex items-center justify-between">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用計算設定</h2>
                            <label class="flex items-center gap-2 text-sm font-bold"><input type="checkbox" id="ed-pricing-enabled" ${s.pricing?.enabled ? 'checked' : ''}> 啟用最後金額確認</label>
                        </div>''',
'''                        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用計算設定</h2>
                            <label class="flex items-center justify-between sm:justify-end gap-3 text-sm font-bold rounded-xl bg-gray-50 px-3 py-2"><span>啟用最後金額確認</span><input type="checkbox" id="ed-pricing-enabled" ${s.pricing?.enabled ? 'checked' : ''}></label>
                        </div>''', 1)

text = text.replace(
'''                                <label class="block text-xs font-semibold text-gray-500 mb-1">參加人數來源</label>
                                <select id="ed-pricing-people-qid" class="w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm bg-white">
                                    <option value="">不統計總人數</option>''',
'''                                <label class="block text-xs font-semibold text-gray-600 mb-1">總人數來源 <span class="font-normal text-gray-400">（選填）</span></label>
                                <p class="text-[11px] leading-relaxed text-gray-400 mb-2">只用來計算下方「每人固定費用 × 總人數」。不會影響其他題目的金額統計；其他題目仍依各自的「納入金額統計」開關計費。</p>
                                <select id="ed-pricing-people-qid" class="w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm bg-white">
                                    <option value="">不使用總人數計算</option>''', 1)

text = text.replace(
'''                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <label class="text-xs font-semibold text-gray-500">每人固定實際費用''',
'''                            <div class="rounded-xl border border-gray-100 bg-gray-50 p-3">
                                <div class="text-xs font-bold text-gray-600 mb-1">每人固定費用 <span class="font-normal text-gray-400">（選填）</span></div>
                                <p class="text-[11px] leading-relaxed text-gray-400 mb-3">只有設定金額時才需要選「總人數來源」。例如餐費每人 $900，可用「參加人數」自動乘算。</p>
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <label class="text-xs font-semibold text-gray-500">每人固定實際費用''', 1)

text = text.replace(
'''                                <label class="text-xs font-semibold text-gray-500">每人固定預收費用<input id="ed-pricing-person-prepay" type="number" min="0" class="mt-1 w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm" value="${Number(s.pricing?.perPersonPrepay||0)}"></label>
                            </div>
                            <label class="block text-xs font-semibold text-gray-500">每人固定費用名稱''',
'''                                <label class="text-xs font-semibold text-gray-500">每人固定預收費用<input id="ed-pricing-person-prepay" type="number" min="0" class="mt-1 w-full border-2 border-gray-200 rounded-xl py-2 px-3 text-sm" value="${Number(s.pricing?.perPersonPrepay||0)}"></label>
                                </div>
                            </div>
                            <label class="block text-xs font-semibold text-gray-500">每人固定費用名稱''', 1)

path.write_text(text, encoding='utf-8')
print('patched pricing people-source UX and mobile layout')
