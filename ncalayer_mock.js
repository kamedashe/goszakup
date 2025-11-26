console.log("💉 NCALayer Mock Injected (v25 - SMART JSON PARSER)");

// 1. БЛОКУВАННЯ РЕДИРЕКТІВ
const blockRedirect = (url) => {
    if (url && (url.includes('not_installed') || url.includes('sign_workaround'))) {
        console.warn("🛡️ [MOCK] Redirect BLOCKED:", url);
        return true;
    }
    return false;
};

const originalAssign = window.location.assign;
const originalReplace = window.location.replace;

window.location.assign = function (url) { if (!blockRedirect(url)) originalAssign.call(window.location, url); };
window.location.replace = function (url) { if (!blockRedirect(url)) originalReplace.call(window.location, url); };

try {
    Object.defineProperty(window.location, 'href', {
        set: function (url) { if (!blockRedirect(url)) originalAssign.call(window.location, url); },
        get: function () { return window.document.URL; }
    });
} catch (e) { }

// 2. ГЛОБАЛЬНІ ЗМІННІ
window.ncalayerInstalled = true;
window.isNcalayerInstalled = true;
window.NCALayer = { call: function () { }, init: function () { return true; } };
window.helpers = window.helpers || {};
window.helpers.check_ncalayer = function () { return true; };

// 3. WEBSOCKET MOCK
const originalWebSocket = window.WebSocket;
window.WebSocket = function (url) {
    if (url.includes('13579')) {
        console.log("🔌 [MOCK] WS Connected:", url);

        const wsMock = {
            send: function (data) {
                console.log("📤 [MOCK] Raw Data:", data);

                let isVersionRequest = false;

                // --- РОЗУМНА ПЕРЕВІРКА ---
                try {
                    // Спробуємо розпарсити як JSON
                    const req = JSON.parse(data);
                    if (req.type === 'version' || req.type === 'getVersion' || req.method === 'getVersion') {
                        isVersionRequest = true;
                    }
                } catch (e) {
                    // Якщо це не JSON, використовуємо стару перевірку, але обережно
                    // Перевіряємо, що це НЕ xml
                    if ((data.includes('"type":"version"') || data.includes('getVersion')) && !data.includes('<?xml')) {
                        isVersionRequest = true;
                    }
                }

                if (isVersionRequest) {
                    console.log("⚡ [MOCK] Auto-reply: Version 1.4");
                    setTimeout(() => {
                        if (this.onmessage) this.onmessage({
                            data: JSON.stringify({ "result": { "version": "1.4" }, "errorCode": "NONE" })
                        });
                    }, 10);
                    return;
                }

                // Все інше - в Python!
                if (window.pythonSigner) {
                    console.log("🌉 [MOCK] To Python Bridge...");
                    window.pythonSigner(data).then(r => {
                        console.log("📥 [MOCK] From Python:", r.substring(0, 50) + "...");
                        if (this.onmessage) this.onmessage({ data: r });
                    }).catch(e => {
                        console.error("🔥 [MOCK] Bridge Error:", e);
                    });
                } else {
                    console.error("❌ [MOCK] Python bridge not found!");
                }
            },
            close: function () { },
            readyState: 1,
            addEventListener: function (event, handler) { this['on' + event] = handler; }
        };

        setTimeout(() => { if (wsMock.onopen) wsMock.onopen({ type: 'open' }); }, 10);
        return wsMock;
    }
    return new originalWebSocket(url);
};

// 4. TENDER HIJACK (Про всяк випадок)
window.helpers.sign_workaround = window.helpers.sign_workaround || {};
window.helpers.sign_workaround.form_sign_helper = window.helpers.sign_workaround.form_sign_helper || {};
window.helpers.sign_workaround.form_sign_helper.sign_uploaded_file = async function (btnElement) {
    // Ця функція тепер просто маркер, основну роботу робить Python в tender_fast.py
    console.log("🔥 [MOCK] Button Clicked by Site Logic");
};