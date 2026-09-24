from pathlib import Path

p = Path('public/index.html')
t = p.read_text(encoding='utf-8')

# The helpers were already deployed, but the previous patch incorrectly treated the
# helper definition itself as proof that renderAdminEditor called them.  Make the
# activation explicit and idempotent.
editor_start = t.find('        function renderAdminEditor() {')
editor_end = t.find('        function toLocalInputValue(', editor_start)
if editor_start < 0 or editor_end < 0:
    raise SystemExit('renderAdminEditor markers not found')
editor = t[editor_start:editor_end]

# Activate tabs + convert pricing checkboxes to switches after the question editor
# has rendered.  This is the actual missing call in the deployed source.
needle = "            document.getElementById('btn-save-survey').addEventListener('click', saveSurvey);\n            renderQuestionEditorList();\n        }"
replacement = "            document.getElementById('btn-save-survey').addEventListener('click', saveSurvey);\n            renderQuestionEditorList();\n            setupEditorSectionTabs();\n            enhancePricingSwitches();\n        }"
if '            setupEditorSectionTabs();' not in editor:
    if needle not in t:
        raise SystemExit('editor activation insertion marker not found')
    t = t.replace(needle, replacement, 1)

# Every question-list rerender (opening cards, adding questions, pricing toggle)
# must repaint switch controls as well.
q_start = t.find('        function renderQuestionEditorList() {')
q_end = t.find('        function renderQuestionEditorCard(', q_start)
if q_start < 0 or q_end < 0:
    raise SystemExit('question editor list markers not found')
qblock = t[q_start:q_end]
if 'enhancePricingSwitches();' not in qblock:
    qneedle = "            document.querySelectorAll('.q-just-added').forEach(el => {\n                setTimeout(() => el.classList.remove('q-just-added'), 1400);\n            });\n        }"
    qreplacement = "            document.querySelectorAll('.q-just-added').forEach(el => {\n                setTimeout(() => el.classList.remove('q-just-added'), 1400);\n            });\n            enhancePricingSwitches();\n        }"
    if qneedle not in t:
        raise SystemExit('question rerender switch marker not found')
    t = t.replace(qneedle, qreplacement, 1)

# Make switch UI unmistakable: add OFF/ON text next to the visual track.
# Existing helper is upgraded in-place and remains idempotent.
old = """                track.appendChild(knob);
                input.insertAdjacentElement('afterend', track);
                const paint = () => {
                    track.style.backgroundColor = input.checked ? 'var(--brand-500)' : '#d1d5db';
                    knob.style.left = input.checked ? '1.375rem' : '0.125rem';
                };
                track.addEventListener('click', e => { e.preventDefault(); input.click(); setTimeout(paint, 0); });
                input.addEventListener('change', paint);
                paint();"""
new = """                track.appendChild(knob);
                const stateText = document.createElement('span');
                stateText.className = 'pricing-switch-state text-[11px] font-bold w-7 text-right';
                input.insertAdjacentElement('afterend', track);
                track.insertAdjacentElement('afterend', stateText);
                const paint = () => {
                    track.style.backgroundColor = input.checked ? 'var(--brand-500)' : '#d1d5db';
                    knob.style.left = input.checked ? '1.375rem' : '0.125rem';
                    stateText.textContent = input.checked ? 'ON' : 'OFF';
                    stateText.style.color = input.checked ? 'var(--brand-600)' : '#9ca3af';
                };
                track.addEventListener('click', e => { e.preventDefault(); input.click(); setTimeout(paint, 0); });
                input.addEventListener('change', paint);
                paint();"""
if old in t:
    t = t.replace(old, new, 1)

p.write_text(t, encoding='utf-8')
print('activated editor tabs and pricing switch UI')
