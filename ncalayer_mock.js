console.log("💉 NCALayer Mock Injected (v10 - STEALTH MODE)");

// 1. МОСТ К PYTHON
window.processNCALayer = async function (jsonDat) {
    try {
        const response = await window.pythonSigner(JSON.stringify(jsonDat));
        return JSON.parse(response);
    } catch (e) {
        console.error("Python signer error:", e);
        return { status: false, code: "500" };
    }
}

// 2. ПЕРЕХВАТ ВХОДА (LOGIN)
// Используем скрытое имя, чтобы сайт не ругался на "SignWorkaround"
window.helpers = window.helpers || {};
window.super_signer = window.super_signer || {};
window.super_signer.form_sign_helper = window.super_signer.form_sign_helper || {};

// Подменяем стандартную функцию подписи XML (для логина, если используется)
window.super_signer.form_sign_helper.sign_raw = async function (callback, type, data) {
    console.log("🔥 LOGIN INTERCEPTED! Подписываем XML...");

    const request = {
        module: "NURSign",
        type: "xml", // Это XML для входа
        data: data
    };

    try {
        const result = await window.processNCALayer(request);

        if (result && result.result) {
            console.log("✅ XML Подписан! Вызываю callback сайта...");
            // Возвращаем результат сайту, как он того ждет
            if (callback && callback.data_signed) {
                callback.data_signed(result.result);
            }
        } else {
            console.error("❌ Ошибка подписи XML:", result);
            if (callback && callback.error) callback.error("Bot Error");
        }
    } catch (e) {
        console.error("❌ Ошибка в sign_raw:", e);
    }
};


// 3. ПЕРЕХВАТ КНОПКИ ФАЙЛА (TENDER)
window.super_signer.form_sign_helper.sign_uploaded_file = async function (btnElement) {
    console.log("🔥 TENDER INTERCEPTED! Качаю файл...");
    const fileUrl = btnElement.getAttribute('data-url');
    const formId = btnElement.getAttribute('data-form-id');

    if (!fileUrl) return;

    try {
        const resp = await fetch(fileUrl);
        const blob = await resp.blob();
        const reader = new FileReader();
        reader.readAsDataURL(blob);

        reader.onloadend = async function () {
            const base64data = reader.result.split(',')[1];
            const request = { module: "NURSign", type: "cms_raw", data: base64data };

            const resultJson = await window.pythonSigner(JSON.stringify(request));
            const result = JSON.parse(resultJson);

            if (result && result.result) {
                const form = document.getElementById(formId);
                if (form) {
                    let input = form.querySelector('input[name="xml"]');
                    if (!input) {
                        input = document.createElement('input');
                        input.type = 'hidden';
                        input.name = 'xml';
                        form.appendChild(input);
                    }
                    input.value = result.result;
                    form.submit();
                }
            }
        }
    } catch (e) { console.error(e); }
};

// 4. СЕТЕВЫЕ ЗАГЛУШКИ (WebSocket Mock with Events)
const originalWebSocket = window.WebSocket;
window.WebSocket = function (url) {
    // Перехватываем только локальный NCALayer
    if (url.includes('127.0.0.1:13579') || url.includes('localhost:13579')) {
        console.log("🔌 WebSocket Intercepted:", url);
        let heartbeatInterval = null;
        let retryTimeout = null;
        const RETRY_DELAY = 1000; // 1 second
        const HEARTBEAT_INTERVAL = 30000; // 30 seconds

        const wsMock = {
            send: function (data) {
                console.log("📤 WS Send:", data);
                if (window.pythonSigner) {
                    window.pythonSigner(data).then(r => {
                        console.log("📥 WS Recv:", r);
                        if (this.onmessage) this.onmessage({ data: r });
                    }).catch(e => {
                        console.error("Python signer error during WS send:", e);
                        // Optionally trigger onerror or onclose here if pythonSigner fails critically
                    });
                }
            },
            close: function () {
                console.log("🔌 WS Close (Mock)");
                this.readyState = 3; // CLOSED
                clearInterval(heartbeatInterval);
                clearTimeout(retryTimeout);
                if (this.onclose) this.onclose({ type: 'close' });
            },
            readyState: 0, // CONNECTING
            onopen: null,
            onmessage: null,
            onerror: null,
            onclose: null
        };

        const connect = () => {
            clearTimeout(retryTimeout);
            wsMock.readyState = 0; // CONNECTING
            console.log("🔌 WS Attempting to connect (Mock)...");

            // Simulate connection success after a short delay
            setTimeout(() => {
                wsMock.readyState = 1; // OPEN
                console.log("✅ WS Connected (Mock)");
                if (wsMock.onopen) wsMock.onopen({ type: 'open' });

                // Start heartbeat
                clearInterval(heartbeatInterval);
                heartbeatInterval = setInterval(() => {
                    if (wsMock.readyState === 1) {
                        console.log("❤️ WS Heartbeat (Mock)");
                        // Send a dummy message to keep the connection alive
                        // NCALayer often expects a specific ping/pong or just any message
                        wsMock.send(JSON.stringify({ "module": "heartbeat", "data": "ping" }));
                    } else {
                        clearInterval(heartbeatInterval);
                    }
                }, HEARTBEAT_INTERVAL);

            }, 50); // Initial connection delay
        };

        // Handle mock closure/error to trigger reconnect
        Object.defineProperty(wsMock, 'onclose', {
            set: function (handler) {
                this._onclose = (event) => {
                    console.log("🔌 WS Mock onclose triggered. Retrying...", event);
                    handler && handler(event);
                    if (wsMock.readyState !== 3) { // Only retry if not explicitly closed by user
                        retryTimeout = setTimeout(connect, RETRY_DELAY);
                    }
                };
            },
            get: function () { return this._onclose; }
        });

        Object.defineProperty(wsMock, 'onerror', {
            set: function (handler) {
                this._onerror = (event) => {
                    console.error("❌ WS Mock onerror triggered. Retrying...", event);
                    handler && handler(event);
                    if (wsMock.readyState !== 3) { // Only retry if not explicitly closed by user
                        retryTimeout = setTimeout(connect, RETRY_DELAY);
                    }
                };
            },
            get: function () { return this._onerror; }
        });

        // Initial connection attempt
        connect();

        return wsMock;
    }
    return new originalWebSocket(url);
};

window.helpers.check_ncalayer = function () {
    console.log("🕵️ Site checked check_ncalayer -> TRUE");
    return true;
};

// 5. ЖЕЛЕЗНЫЙ КАПКАН НА РЕДИРЕКТ (Client-Side Trap)
(function () {
    console.log("🛡️ Installing Redirect Trap...");

    const blockPatterns = ['not_installed', 'sign_workaround'];

    function shouldBlock(url) {
        if (!url) return false;
        return blockPatterns.some(p => url.includes(p));
    }

    // Перехват location.assign
    const originalAssign = window.location.assign;
    window.location.assign = function (url) {
        if (shouldBlock(url)) {
            console.warn("🛡️ BLOCKED location.assign to:", url);
            return;
        }
        originalAssign.call(window.location, url);
    };

    // Перехват location.replace
    const originalReplace = window.location.replace;
    window.location.replace = function (url) {
        if (shouldBlock(url)) {
            console.warn("🛡️ BLOCKED location.replace to:", url);
            return;
        }
        originalReplace.call(window.location, url);
    };

    // Перехват установки location.href
    // (Сложно перехватить прямой сеттер, но попробуем через defineProperty если возможно,
    // но браузеры часто запрещают это для location. Оставим assign/replace как основные).

    // 6. MOCK NCALayer Object (CRITICAL)
    // Сайт может проверять наличие этого объекта перед тем как вообще пытаться соединиться
    if (!window.NCALayer) {
        window.NCALayer = {
            call: function () { console.log("📞 NCALayer.call invoked"); },
            init: function () { console.log("📞 NCALayer.init invoked"); return true; }
        };
    }

})();