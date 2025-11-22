console.log("💉 NCALayer Mock Injected (v8 - SNIPER XML)");

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

// 2. СУПЕР-ФУНКЦИЯ ПОДПИСИ (SNIPER EDITION)
window.SUPER_SIGN = async function (fileUrl, formId) {
    console.log("🚀 SUPER_SIGN: Цель захвачена", fileUrl);

    try {
        // Скачиваем
        const resp = await fetch(fileUrl);
        const blob = await resp.blob();

        // Конвертируем
        const reader = new FileReader();
        reader.readAsDataURL(blob);

        reader.onloadend = async function () {
            const base64data = reader.result.split(',')[1];

            // Подписываем
            const request = {
                module: "NURSign",
                type: "cms_raw",
                data: base64data
            };

            const responseJson = await window.pythonSigner(JSON.stringify(request));
            const result = JSON.parse(responseJson);

            // Отправляем
            if (result && result.result) {
                console.log("✅ Подпись есть. Ищу форму:", formId);
                const form = document.getElementById(formId);

                if (form) {
                    // --- СНАЙПЕРСКИЙ ВЫСТРЕЛ ---
                    // Ищем поле 'xml'
                    let input = form.querySelector('input[name="xml"]');

                    // Если его нет - создаем
                    if (!input) {
                        input = document.createElement('input');
                        input.type = 'hidden';
                        input.name = 'xml'; // <--- ТОЛЬКО ЭТО ИМЯ
                        form.appendChild(input);
                    }

                    // Вставляем подпись
                    input.value = result.result;

                    console.log("🚀 ОТПРАВКА: поле 'xml' заполнено.");
                    form.submit();
                } else {
                    console.error("❌ Форма не найдена:", formId);
                }
            }
        }
    } catch (e) {
        console.error("❌ Ошибка:", e);
    }
};

// 3. СЕТЕВЫЕ ЗАГЛУШКИ
const originalWebSocket = window.WebSocket;
window.WebSocket = function (url) {
    if (url.includes('127.0.0.1:13579') || url.includes('localhost:13579')) {
        const mockWS = {
            readyState: 1,
            send: function (data) {
                if (window.pythonSigner) {
                    window.pythonSigner(data).then(resp => {
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

const originalFetch = window.fetch;
window.fetch = async function (input, init) {
    const url = input.toString();
    if (url.includes('127.0.0.1:13579')) {
        return new Response(JSON.stringify({ result: { version: "1.4" }, errorCode: "NONE" }), { status: 200 });
    }
    return originalFetch(input, init);
};

const originalImage = window.Image;
window.Image = function (width, height) {
    const img = new originalImage(width, height);
    Object.defineProperty(img, 'src', {
        set: function (url) {
            if (url && url.includes('127.0.0.1:13579')) {
                setTimeout(() => { if (img.onload) img.onload(); }, 10);
                return;
            }
            this.setAttribute('src', url);
        },
        get: function () { return this.getAttribute('src'); }
    });
    return img;
};

window.helpers = window.helpers || {};
window.helpers.check_ncalayer = function () { return true; };

// Блокировка редиректа JS
const originalSet = Object.getOwnPropertyDescriptor(window.Location.prototype, 'href').set;
Object.defineProperty(window.location, 'href', {
    set: function (val) {
        if (val.toString().includes('not_installed')) return;
        originalSet.call(this, val);
    }
});