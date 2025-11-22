console.log("💉 NCALayer Mock Injected (v3 - TOTAL CONTROL)");

// --- 1. MOCK WEB SOCKET (Ты это уже видел) ---
const originalWebSocket = window.WebSocket;
window.WebSocket = function (url) {
    if (url.includes('127.0.0.1:13579') || url.includes('localhost:13579')) {
        console.log("🔒 WS Перехвачен:", url);
        const mockWS = {
            readyState: 1,
            send: function (data) {
                console.log("📤 WS Send:", data);
                // Шлем в Python
                if (window.pythonSigner) {
                    window.pythonSigner(data).then(resp => {
                        console.log("📥 WS Recv:", resp);
                        if (mockWS.onmessage) mockWS.onmessage({ data: resp });
                    });
                }
            },
            close: () => { },
            addEventListener: function (ev, cb) {
                if (ev === 'open') this.onopen = cb;
                if (ev === 'message') this.onmessage = cb;
            }
        };
        setTimeout(() => { if (mockWS.onopen) mockWS.onopen({ type: 'open' }); }, 10);
        return mockWS;
    }
    return new originalWebSocket(url);
};

// --- 2. MOCK HTTP FETCH (ДЛЯ РЕЗЕРВНОЙ ПРОВЕРКИ) ---
const originalFetch = window.fetch;
window.fetch = async function (input, init) {
    const url = input.toString();
    if (url.includes('127.0.0.1:13579') || url.includes('localhost:13579')) {
        console.log("🛡️ FETCH Перехвачен:", url);

        // Эмулируем ответ сервера NCALayer
        const fakeResponse = {
            result: { version: "1.4" },
            errorCode: "NONE"
        };

        return new Response(JSON.stringify(fakeResponse), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    }
    return originalFetch(input, init);
};

// --- 3. MOCK XMLHTTPRequest (ДЛЯ СТАРЫХ СКРИПТОВ) ---
const originalXHR = window.XMLHttpRequest;
window.XMLHttpRequest = function () {
    const xhr = new originalXHR();
    const originalOpen = xhr.open;

    xhr.open = function (method, url) {
        if (url.toString().includes('127.0.0.1:13579') || url.toString().includes('localhost:13579')) {
            console.log("🛡️ XHR Перехвачен:", url);

            // Подменяем отправку
            xhr.send = function () {
                const fakeResponse = JSON.stringify({
                    result: { version: "1.4" },
                    errorCode: "NONE"
                });

                // Эмулируем задержку сети и ответ
                setTimeout(() => {
                    Object.defineProperty(xhr, 'responseText', { value: fakeResponse });
                    Object.defineProperty(xhr, 'status', { value: 200 });
                    Object.defineProperty(xhr, 'readyState', { value: 4 });
                    if (xhr.onreadystatechange) xhr.onreadystatechange();
                    if (xhr.onload) xhr.onload();
                }, 50);
            };
            return;
        }
        return originalOpen.apply(this, arguments);
    };
    return xhr;
};

// --- 4. НАСИЛЬНО ГОВОРИМ САЙТУ, ЧТО ВСЁ ОК ---
window.helpers = window.helpers || {};
window.helpers.check_ncalayer = function () { return true; }; // Заглушка функции проверки

// 5. БЛОКИРОВКА РЕДИРЕКТА НА ОШИБКУ ЧЕРЕЗ JS
// Если сайт вызовет window.location.href = "...", мы это проигнорируем, если там "not_installed"
const originalSet = Object.getOwnPropertyDescriptor(window.Location.prototype, 'href').set;
Object.defineProperty(window.location, 'href', {
    set: function (val) {
        if (val.toString().includes('not_installed')) {
            console.log("🚫 BLOCKED REDIRECT TO ERROR PAGE:", val);
            return; // Игнорируем!
        }
        originalSet.call(this, val);
    }
});

// 6. ПЕРЕХВАТ ЗАГРУЗКИ КАРТИНОК (IMAGE PING)
// Сайт может проверять наличие слоя, пытаясь загрузить иконку с локалхоста
const originalImage = window.Image;
window.Image = function (width, height) {
    const img = new originalImage(width, height);

    Object.defineProperty(img, 'src', {
        set: function (url) {
            if (url && (url.includes('127.0.0.1:13579') || url.includes('localhost:13579'))) {
                console.log("🖼️ IMAGE PING Перехвачен:", url);
                // Эмулируем успешную загрузку через 10мс
                setTimeout(() => {
                    if (img.onload) img.onload();
                }, 10);
                return;
            }
            this.setAttribute('src', url);
        },
        get: function () { return this.getAttribute('src'); }
    });
    return img;
};