import { chromium } from 'playwright';
import fs from 'fs';
import readline from 'readline';

const SESSION_FILE = 'instagram_session.json';

async function saveSession() {
    console.log('🚀 Instagram session saqlash dasturi ishga tushdi...');

    // Browser ochish (headless=false - ko'rinishi uchun)
    const browser = await chromium.launch({
        headless: false,
        args: ['--start-maximized']
    });

    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();

    console.log('📱 Instagram ochilmoqda...');
    await page.goto('https://www.instagram.com/', { waitUntil: 'networkidle' });

    console.log('\n✋ KUTISH REJIMI:');
    console.log('1️⃣  Instagram ga manual login qiling');
    console.log('2️⃣  Login tugagandan keyin "Eslab qolish" ni tanlang');
    console.log('3️⃣  Bosh sahifaga o\'tganingizda bu terminalga qaytib ENTER bosing');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    // Enter tugmasini kutish
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    await new Promise((resolve) => {
        rl.question('\n⌨️  Tayyor bo\'lsangiz ENTER bosing: ', () => {
            rl.close();
            resolve();
        });
    });

    console.log('\n💾 Session saqlanmoqda...');

    // Session ma'lumotlarini saqlash
    const sessionData = await context.storageState();
    fs.writeFileSync(SESSION_FILE, JSON.stringify(sessionData, null, 2));

    console.log(`✅ Session muvaffaqiyatli saqlandi: ${SESSION_FILE}`);
    console.log(`📊 Cookies soni: ${sessionData.cookies.length}`);

    await browser.close();
    console.log('👋 Browser yopildi. Dastur tugadi!');
}

// Xatoliklarni ushlash
saveSession().catch((error) => {
    console.error('❌ Xatolik yuz berdi:', error.message);
    process.exit(1);
});
