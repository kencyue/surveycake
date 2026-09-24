from pathlib import Path

p = Path('public/index.html')
t = p.read_text(encoding='utf-8')

# --- Editor tabs + real switch UI -------------------------------------------------
# Add helpers before renderAdminEditor.
anchor = '        function renderAdminEditor() {'
if 'function setupEditorSectionTabs()' not in t:
    helper = r'''        function setupEditorSectionTabs() {
            const root = DOM.root.querySelector('.animate-fade-in');
            if (!root) return;
            const cards = [...root.children].filter(el => el.classList && el.classList.contains('bg-white'));
            const head = cards.find(el => el.querySelector('#ed-title'));
            const foot = cards.find(el => el.querySelector('#ed-thanks-title'));
            const pricing = cards.find(el => el.querySelector('#ed-pricing-enabled'));
            const questions = cards.find(el => el.querySelector('#question-editor-list'));
            if (!head || !foot || !questions) return;
            head.dataset.editorSection = 'head';
            foot.dataset.editorSection = 'foot';
            if (pricing) pricing.dataset.editorSection = 'foot';
            questions.dataset.editorSection = 'questions';
            const bar = document.createElement('div');
            bar.className = 'editor-section-tabs bg-white rounded-2xl shadow-sm border border-gray-100 p-1 grid grid-cols-3 gap-1 sticky top-2 z-20';
            bar.innerHTML = `
                <button data-tab="head" class="editor-section-tab rounded-xl py-2.5 px-3 text-sm font-bold"><i class="fas fa-heading mr-1"></i>頁首</button>
                <button data-tab="questions" class="editor-section-tab rounded-xl py-2.5 px-3 text-sm font-bold"><i class="fas fa-list-ol mr-1"></i>題目</button>
                <button data-tab="foot" class="editor-section-tab rounded-xl py-2.5 px-3 text-sm font-bold"><i class="fas fa-shoe-prints mr-1"></i>頁尾</button>`;
            root.insertBefore(bar, head);
            const activate = tab => {
                root.querySelectorAll('[data-editor-section]').forEach(el => el.classList.toggle('hidden', el.dataset.editorSection !== tab));
                bar.querySelectorAll('.editor-section-tab').forEach(btn => {
                    const on = btn.dataset.tab === tab;
                    btn.className = `editor-section-tab rounded-xl py-2.5 px-3 text-sm font-bold transition-colors ${on ? 'text-white shadow-sm' : 'text-gray-500 hover:bg-gray-50'}`;
                    btn.style.backgroundColor = on ? 'var(--brand-500)' : '';
                });
                try { sessionStorage.setItem('surveyEditorTab', tab); } catch(e) {}
            };
            bar.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.tab)));
            let initial = 'head';
            try { initial = sessionStorage.getItem('surveyEditorTab') || 'head'; } catch(e) {}
            activate(initial);
        }

        function enhancePricingSwitches() {
            DOM.root.querySelectorAll('input[type="checkbox"][data-field="pricingEnabled"], #ed-pricing-enabled').forEach(input => {
                if (input.dataset.switchReady) return;
                input.dataset.switchReady = '1';
                input.classList.add('sr-only');
                const track = document.createElement('span');
                track.className = 'pricing-switch-track relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full transition-colors';
                const knob = document.createElement('span');
                knob.className = 'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all';
                track.appendChild(knob);
                input.insertAdjacentElement('afterend', track);
                const paint = () => {
                    track.style.backgroundColor = input.checked ? 'var(--brand-500)' : '#d1d5db';
                    knob.style.left = input.checked ? '1.375rem' : '0.125rem';
                };
                track.addEventListener('click', e => { e.preventDefault(); input.click(); setTimeout(paint, 0); });
                input.addEventListener('change', paint);
                paint();
            });
        }

'''
    t = t.replace(anchor, helper + anchor, 1)

# Call tab/switch setup at end of editor render after existing bindings are created.
call_anchor = "            bindAdminThemeToggle();\n            renderQuestionEditorList();"
if call_anchor in t and 'setupEditorSectionTabs();' not in t[t.find('function renderAdminEditor()'):t.find('function renderQuestionEditorList()')]:
    t = t.replace(call_anchor, "            bindAdminThemeToggle();\n            renderQuestionEditorList();\n            setupEditorSectionTabs();\n            enhancePricingSwitches();", 1)

# Every question-list rerender needs switch enhancement.
q_end = "            initQuestionSortable();\n        }"
if q_end in t:
    t = t.replace(q_end, "            initQuestionSortable();\n            enhancePricingSwitches();\n        }", 1)

# --- Lightweight RBAC -------------------------------------------------------------
# Secondary admin records live in settings.secondaryAdmins with SHA-256 password hash.
# This gates the existing client admin UI; super admin remains the existing adminPassword.
if 'async function sha256Text(' not in t:
    auth_anchor = '        async function promptAdminLogin() {'
    rbac_helpers = r'''        async function sha256Text(value) {
            const data = new TextEncoder().encode(String(value || ''));
            const hash = await crypto.subtle.digest('SHA-256', data);
            return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
        }
        function isSuperAdmin() { return !state.currentAdminRole || state.currentAdminRole === 'super'; }
        function allowedFolderIds() { return isSuperAdmin() ? null : (state.currentAdminFolderIds || []); }
        function adminCanAccessSurvey(s) { const ids = allowedFolderIds(); return ids === null || (!!s.folderId && ids.includes(s.folderId)); }
        function adminCanAccessFolder(id) { const ids = allowedFolderIds(); return ids === null || ids.includes(id); }

        async function createSecondaryAdminFlow() {
            if (!isSuperAdmin()) return;
            const name = await showPrompt('建立次級管理員', '請輸入管理員名稱：', '');
            if (!name) return;
            const password = await showPrompt('設定登入密碼', '請輸入次級管理員密碼：', '');
            if (!password) return;
            if (!state.adminFolders.length) return showMessage('尚無資料夾', '請先建立至少一個資料夾，再建立次級管理員。');
            const folderText = state.adminFolders.map((f,i)=>`${i+1}. ${f.name}`).join('<br>');
            const selected = await showPrompt('授權資料夾', `輸入資料夾編號，可用逗號選多個：<br>${folderText}`, '1');
            if (!selected) return;
            const indexes = String(selected).split(/[,，]/).map(x=>Number(x.trim())-1).filter(i=>i>=0 && i<state.adminFolders.length);
            const folderIds = [...new Set(indexes.map(i=>state.adminFolders[i].id))];
            if (!folderIds.length) return showMessage('未選擇資料夾', '至少要授權一個資料夾。', 'error');
            const admins = Array.isArray(appSettings.secondaryAdmins) ? [...appSettings.secondaryAdmins] : [];
            admins.push({ id:'adm_'+Date.now(), name, passwordHash:await sha256Text(password), folderIds, createdAt:new Date().toISOString() });
            appSettings.secondaryAdmins = admins;
            await setDoc(settingsRef(), { secondaryAdmins: admins }, { merge:true });
            showMessage('建立完成', `已建立次級管理員「${escapeHtml(name)}」。`, 'success');
        }

        async function manageSecondaryAdminsFlow() {
            if (!isSuperAdmin()) return;
            const admins = Array.isArray(appSettings.secondaryAdmins) ? appSettings.secondaryAdmins : [];
            if (!admins.length) return createSecondaryAdminFlow();
            const rows = admins.map((a,i)=>`${i+1}. ${escapeHtml(a.name)}｜${(a.folderIds||[]).map(id=>escapeHtml(state.adminFolders.find(f=>f.id===id)?.name||'已刪除資料夾')).join('、')}`).join('<br>');
            const action = await showPrompt('次級管理員', `${rows}<br><br>輸入「+」新增，或輸入編號刪除該管理員：`, '+');
            if (!action) return;
            if (action.trim() === '+') return createSecondaryAdminFlow();
            const idx = Number(action)-1;
            if (idx < 0 || idx >= admins.length) return showMessage('輸入錯誤','找不到這個管理員。','error');
            if (!await showConfirm('刪除次級管理員', `確定刪除「${escapeHtml(admins[idx].name)}」？`)) return;
            admins.splice(idx,1); appSettings.secondaryAdmins = admins;
            await setDoc(settingsRef(), { secondaryAdmins: admins }, { merge:true });
            showMessage('已刪除','次級管理員已刪除。','success');
        }

'''
    t = t.replace(auth_anchor, rbac_helpers + auth_anchor, 1)

# Replace login decision block: super password first, then secondary password hashes.
old_login = '''            } else if (pw === appSettings.adminPassword) {
                enterAdminDashboard();
            } else {
                showMessage("登入失敗", "密碼錯誤", "error");
            }'''
new_login = '''            } else if (pw === appSettings.adminPassword) {
                state.currentAdminRole = 'super'; state.currentAdminName = '總管理員'; state.currentAdminFolderIds = [];
                enterAdminDashboard();
            } else {
                const hash = await sha256Text(pw);
                const matched = (appSettings.secondaryAdmins || []).find(a => a.passwordHash === hash);
                if (matched) {
                    state.currentAdminRole = 'folder'; state.currentAdminName = matched.name || '次級管理員'; state.currentAdminFolderIds = matched.folderIds || [];
                    enterAdminDashboard();
                } else showMessage("登入失敗", "密碼錯誤", "error");
            }'''
if old_login in t:
    t = t.replace(old_login, new_login, 1)

# First-time super admin role.
first = '                        enterAdminDashboard();\n                    } catch (e)'
if first in t:
    t = t.replace(first, "                        state.currentAdminRole = 'super'; state.currentAdminName = '總管理員'; state.currentAdminFolderIds = [];\n                        enterAdminDashboard();\n                    } catch (e)", 1)

# Filter snapshots before putting data into state for folder admins.
old_surveys = '                state.adminSurveys = list;'
if old_surveys in t:
    t = t.replace(old_surveys, '                state.adminSurveys = isSuperAdmin() ? list : list.filter(adminCanAccessSurvey);', 1)
old_folders = '                state.adminFolders = list;'
if old_folders in t:
    t = t.replace(old_folders, '                state.adminFolders = isSuperAdmin() ? list : list.filter(f => adminCanAccessFolder(f.id));', 1)

# Dashboard: role badge + super-only admin management button.
dash_buttons = '''                            ${adminThemeToggleHtml()}
                            <button id="btn-new-survey"'''
if dash_buttons in t:
    t = t.replace(dash_buttons, '''                            ${adminThemeToggleHtml()}
                            <span class="hidden sm:inline text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-500">${escapeHtml(state.currentAdminName || '總管理員')}</span>
                            ${isSuperAdmin() ? '<button id="btn-manage-admins" class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg font-medium"><i class="fas fa-user-shield mr-1"></i>管理員</button>' : ''}
                            <button id="btn-new-survey"''', 1)

# Bind management button; new survey for folder admin is forced into current/first allowed folder.
bind_new = '''            document.getElementById('btn-new-survey').addEventListener('click', () => {
                state.editingSurvey = newSurvey();
                if (state.currentFolderId) state.editingSurvey.folderId = state.currentFolderId;'''
if bind_new in t:
    t = t.replace(bind_new, '''            const manageAdminsBtn = document.getElementById('btn-manage-admins');
            if (manageAdminsBtn) manageAdminsBtn.addEventListener('click', manageSecondaryAdminsFlow);
            document.getElementById('btn-new-survey').addEventListener('click', () => {
                state.editingSurvey = newSurvey();
                if (state.currentFolderId) state.editingSurvey.folderId = state.currentFolderId;
                else if (!isSuperAdmin()) state.editingSurvey.folderId = state.adminFolders[0]?.id || null;''', 1)

# Folder mutation controls only for super admin.
t = t.replace("                document.getElementById('btn-add-folder').addEventListener('click', createFolderFlow);", "                const addFolderBtn = document.getElementById('btn-add-folder'); if (addFolderBtn) { if (isSuperAdmin()) addFolderBtn.addEventListener('click', createFolderFlow); else addFolderBtn.remove(); }", 1)
t = t.replace("                            <div class=\"flex gap-1\">\n                                <button class=\"folder-rename-btn", "                            <div class=\"flex gap-1 ${isSuperAdmin() ? '' : 'hidden'}\">\n                                <button class=\"folder-rename-btn", 1)

# Editor folder selector for folder admins only contains their allowed folders already; prohibit unclassified option.
t = t.replace('''                                <option value="">未分類</option>
                                ${state.adminFolders.map''', '''                                ${isSuperAdmin() ? '<option value="">未分類</option>' : ''}
                                ${state.adminFolders.map''', 1)

# Exit clears role.
exit_anchor = "            state.isAdminMode = false;"
if exit_anchor in t:
    t = t.replace(exit_anchor, "            state.isAdminMode = false;\n            state.currentAdminRole = null; state.currentAdminName = null; state.currentAdminFolderIds = [];", 1)

p.write_text(t, encoding='utf-8')
print('patched admin editor tabs, pricing switches, and folder-scoped admin roles')
