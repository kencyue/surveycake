from pathlib import Path

path = Path('public/index.html')
text = path.read_text(encoding='utf-8')

# Clarify that this selector is only the source for per-person calculations,
# not a switch controlling which questions participate in pricing.
text = text.replace(
'''                        <div class="flex items-center justify-between">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用計算設定</h2>
                            <label class="flex items-center gap-2 text-sm font-bold"><input type="checkbox" id="ed-pricing-enabled" ${s.pricing?.enabled ? 'checked' : ''}> 啟用最後金額確認</label>
                        </div>''',
'''                        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <h2 class="font-bold text-gray-800"><i class="fas fa-calculator mr-2" style="color:var(--brand-500)"></i>費用計算設定</h2>
                            <label class="flex items-center justify-between sm:justify-end gap-3 text-sm font-bold w-full sm:w-auto"><span>啟用最後金額確認</span><input type="checkbox" id="ed-pricing-enabled" ${s.pricing?.enabled ? 'checked' : ''}></label>
                        </div>''', 1)
text = text.replace(
'''                                <label class="block text-xs font-semibold text-gray-500 mb-1">參加人數來源</label>''',
'''                                <label class="block text-sm font-bold text-gray-700 mb-1">總人數來源 <span class="text-xs font-normal text-gray-400">（選填）</span></label>
                                <p class="text-xs text-gray-400 mb-2">只用來計算「每人固定費用」與顯示參加總人數；不會影響其他題目的金額統計。其他題目是否計費，以各題的「納入金額統計」開關為準。</p>''', 1)
text = text.replace('<option value="">不統計總人數</option>', '<option value="">不使用總人數</option>', 1)

path.write_text(text, encoding='utf-8')
print('patched pricing people-source copy and mobile layout')
