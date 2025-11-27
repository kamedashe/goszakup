# goszakup/browser.py
import asyncio
import json
import logging
import os
import base64
import re
import html
import shutil
from playwright.async_api import async_playwright, Page
from config import GOV_URL, GOV_PASSWORD, KEY_PATH
from signer import sign_xml_data, sign_cms_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIG ---
TARGET_PRICE = "12129429"

# --- AUTO-DUMPER (ЧЕРНЫЙ ЯЩИК) ---
DUMP_CTR = 0

async def _save_dump(page: Page):
    global DUMP_CTR
    DUMP_CTR += 1
    try:
        if not os.path.exists("debug_dumps"):
            os.makedirs("debug_dumps")
            
        # Формируем имя файла из URL
        clean_url = page.url.split('?')[0].split('#')[0]
        slug = clean_url.replace('https://', '').replace('http://', '').replace('/', '_')
        slug = slug[-40:] if len(slug) > 40 else slug # Обрезаем если длинный
        if not slug: slug = "blank"
        
        filename = f"debug_dumps/{DUMP_CTR:03d}_{slug}.html"
        
        content = await page.content()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        # logger.info(f"📸 [DUMP] Снимок сохранен: {filename}")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось сделать дамп: {e}")

def _attach_dumper(page: Page):
    """Вешает слушатель на страницу"""
    # Срабатывает когда страница полностью загрузилась
    page.on("load", lambda: asyncio.create_task(_save_dump(page)))

# -------------------------------

# --- MOCK JS (ТЕПЕРЬ УМЕЕТ ЗАВЕРШАТЬ CMS ПОДПИСЬ) ---
MOCK_JS = """
console.log("💉 NCALayer: UNIVERSAL MODE + LOGIN + CMS (AUTO-SUBMIT)");
window.ncalayerInstalled = true;
window.isNcalayerInstalled = true;
window.NCALayer = { call: function(){}, init: function(){return true;} };

function injectAndSubmit(signature, isCms) {
    console.log("💉 [JS] Injecting signature (CMS=" + isCms + ")...");
    
    // 1. Для XML (форма priceoffers)
    if (!isCms) {
        let form = document.getElementById('priceoffers') || document.forms[0];
        if (form) {
            form.querySelectorAll('input[type="hidden"]').forEach(inp => {
                if (inp.name.toLowerCase().match(/(xml|sign|cert|hash)/)) {
                    inp.value = signature;
                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        }
        if (!document.getElementById('signature_injected_success')) {
            let div = document.createElement('div');
            div.id = 'signature_injected_success';
            document.body.appendChild(div);
        }
    } 
    
    // 2. Для CMS (Приложения, файлы)
    if (isCms) {
        // Ищем кнопку, которая инициировала подпись (обычно у нее есть data-file-identifier)
        // В helpers.js госзакупок логика такая: helpers.sign_workaround.form_sign_helper.sign_uploaded_file(this)
        // После подписи вызывается .afterGenSignEvent()
        
        let buttons = document.querySelectorAll('.btn-add-signature');
        buttons.forEach(btn => {
            // Если у кнопки есть колбэк - вызываем его
            if (btn.afterGenSignEvent) {
                console.log("🚀 [JS] Вызываю afterGenSignEvent для кнопки...");
                try { btn.afterGenSignEvent(signature); } catch(e) { console.error(e); }
            }
            
            // Или ищем форму рядом и сабмитим её (как запасной вариант)
            let formId = btn.getAttribute('data-form-id');
            if (formId) {
                let form = document.getElementById(formId);
                if (form) {
                    // Вставляем подпись в скрытое поле (если оно есть) или просто сабмитим
                    // Обычно CMS подпись улетает через ajax, но тут форма.
                    // Попробуем найти input[name='signedData'] или просто сабмит
                    console.log("🚀 [JS] Сабмичу форму " + formId);
                    form.submit();
                }
            }
        });
    }
}

const originalWebSocket = window.WebSocket;
window.WebSocket = function(url) {
    if (url.includes('13579')) {
        const wsMock = {
            send: async function(data) {
                const req = JSON.parse(data);
                if (req.type === 'version' || req.method === 'getVersion') {
                    setTimeout(() => this.onmessage({ data: JSON.stringify({ "result": { "version": "1.4" }, "errorCode": "NONE" }) }), 50);
                    return;
                }
                if (window.pythonSigner) {
                    window.pythonSigner(data).then(r => {
                        if (this.onmessage) this.onmessage({ data: r });
                        
                        try {
                            const resp = JSON.parse(r);
                            let sig = resp.result;
                            if (Array.isArray(sig)) sig = sig[0];
                            if (typeof sig === 'object' && sig !== null) sig = Object.values(sig)[0];
                            
                            if (sig && sig.length > 100) {
                                // Определяем тип подписи
                                const isCms = (req.type === 'createCms' || req.method === 'createCms' || req.type === 'cms');
                                injectAndSubmit(sig, isCms);
                            }
                        } catch(e) {}
                    });
                }
            },
            close: function(){},
            readyState: 1,
            addEventListener: function(evt, cb) { this['on'+evt] = cb; }
        };
        setTimeout(() => { if (wsMock.onopen) wsMock.onopen({ type: 'open' }); }, 100);
        return wsMock;
    }
    return new originalWebSocket(url);
};
"""

def replace_price_in_xml(xml_content, new_price):
    if not xml_content or not isinstance(xml_content, str): return xml_content
    patterns = [r'(<ns2:Price>)(.*?)(</ns2:Price>)', r'(<Price>)(.*?)(</Price>)', r'(<price>)(.*?)(</price>)', r'(price=")(.*?)(")']
    modified_xml = xml_content
    replaced = False
    for pat in patterns:
        if re.search(pat, modified_xml):
            modified_xml = re.sub(pat, fr'\g<1>{new_price}\g<3>', modified_xml)
            replaced = True
    if replaced: logger.info(f"💰 [XML] Цена заменена на {new_price} внутри XML!")
    return modified_xml

async def process_signing_item(item):
    if not item: return None
    clean_item = item
    if isinstance(clean_item, str):
        clean_item = html.unescape(clean_item)
        if "&lt;" in clean_item: clean_item = html.unescape(clean_item)
    if isinstance(clean_item, str) and len(clean_item) > 200 and "<" in clean_item:
        clean_item = replace_price_in_xml(clean_item, TARGET_PRICE)
    
    try:
        s = await sign_xml_data(clean_item)
        if s: return s
    except: pass
    
    try:
        b64_data = clean_item
        if isinstance(clean_item, str) and "<" in clean_item:
            b64_data = base64.b64encode(clean_item.encode('utf-8')).decode()
        return await sign_cms_data(b64_data)
    except: return None

async def init_browser(headless=False):
    global DUMP_CTR
    DUMP_CTR = 0 # Сброс счетчика при старте
    # Очистка папки дампов
    if os.path.exists("debug_dumps"):
        try: shutil.rmtree("debug_dumps")
        except: pass
    
    logger.info("🚀 Запуск браузера...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=headless, 
        args=["--start-maximized", "--ignore-certificate-errors", "--disable-blink-features=AutomationControlled"]
    )
    context = await browser.new_context(no_viewport=True, ignore_https_errors=True)
    if os.path.exists("auth.json"):
        try: context = await browser.new_context(storage_state="auth.json", no_viewport=True, ignore_https_errors=True)
        except: pass

    # --- МАГИЯ ДАМПОВ ---
    # 1. Вешаем дампер на любую НОВУЮ страницу, которая родится в этом контексте
    context.on("page", _attach_dumper)
    
    # Защита от редиректов и HTTP Mock
    await context.route("**/*sign_workaround*", lambda route: route.fulfill(status=204))
    await context.route("**/*not_installed*", lambda route: route.fulfill(status=204))
    
    async def mock_ncalayer_http(route):
        await route.fulfill(
            status=200,
            headers={"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
            body='{"result":{"version":"1.3"},"errorCode":"NONE"}'
        )
    await context.route("*://127.0.0.1:13579/*", mock_ncalayer_http)

    async def handle_binding(source, msg_json):
        try:
            req = json.loads(msg_json)
            method = req.get("method")
            req_type = req.get("type")
            response = {"errorCode": "NONE", "result": True}

            if method == "browseKeyStore":
                response["result"] = os.path.abspath(KEY_PATH)
                return json.dumps(response)
            elif method in ["getKeys", "loadKeyStore"]:
                response["result"] = "AUTHENTICATION|CERTIFICATE|PEM"
                return json.dumps(response)
            elif req_type in ["version", "getVersion"]:
                response["result"] = {"version": "1.4"}
            elif req_type in ["xml", "multitext", "signXml"]:
                raw_data = req.get("data") or req.get("args", [None, None, None])[2]
                items = raw_data if isinstance(raw_data, list) else [raw_data]
                signatures = []
                logger.info(f"📝 [BRIDGE] На подпись: {len(items)} шт.")

                for item in items:
                    if isinstance(item, dict):
                        signed_dict = {}
                        for k, v in item.items():
                            signed_val = await process_signing_item(v)
                            if signed_val: signed_dict[k] = signed_val
                        signatures.append(signed_dict)
                    else:
                        signed_val = await process_signing_item(item)
                        if signed_val: signatures.append(signed_val)
                
                if signatures:
                    response.update({"result": signatures if req_type == "multitext" else signatures[0], "code": "200"})
                else:
                    response["errorCode"] = "WRONG_PASSWORD"
            return json.dumps(response)
        except Exception as e:
            logger.error(f"🔥 BRIDGE: {e}")
            return json.dumps({"errorCode": "INTERNAL_ERROR"})

    await context.expose_binding("pythonSigner", handle_binding)
    await context.add_init_script(MOCK_JS)
    
    # Создаем первую страницу и ВРУЧНУЮ вешаем дампер (т.к. событие 'page' может не успеть)
    page = await context.new_page()
    _attach_dumper(page)

    return playwright, browser, context, page

async def perform_login(page, context):
    # ... (твой старый логин, без изменений)
    try: await page.wait_for_load_state("domcontentloaded", timeout=10000)
    except: pass
    if "/user/login" not in page.url:
        try: await page.goto(GOV_URL, wait_until="domcontentloaded", timeout=30000)
        except: pass
    try:
        await page.evaluate("if(window.selectP12File) selectP12File(); else document.getElementById('selectP12File').click();")
        await asyncio.sleep(1)
    except:
        try: await page.click("#selectP12File", force=True)
        except: pass
    try:
        pwd = page.locator("input[type='password']")
        await pwd.wait_for(state="visible", timeout=15000)
        chk = page.locator("input[type='checkbox']").first
        if await chk.count() > 0 and await chk.is_visible(): await chk.check(force=True)
        await pwd.fill(GOV_PASSWORD)
        await pwd.press("Enter")
        await page.wait_for_url("**/cabinet/**", timeout=40000)
        logger.info("🎉 [LOGIN] УСПЕХ!")
        await context.storage_state(path="auth.json")
        return True
    except: return False