// Walks through the app like a new user and saves phone-size screenshots (M4 visual check).
//
// Usage: ASTRO_USER=… ASTRO_PASSWORD=… [ASTRO_LANG=de] [ASTRO_BROWSER=webkit|chromium] [BASE_URL=http://localhost]
//        node scripts/screenshots.mjs
// The user must exist and not be onboarded yet (created with `astrocat create-user`).

import { mkdirSync } from "node:fs";
import { chromium, devices, webkit } from "playwright";

const base = process.env.BASE_URL ?? "http://localhost";
const user = process.env.ASTRO_USER;
const password = process.env.ASTRO_PASSWORD;
const lang = process.env.ASTRO_LANG ?? "de";
const browserName = process.env.ASTRO_BROWSER ?? "webkit";
if (!user || !password) throw new Error("set ASTRO_USER and ASTRO_PASSWORD");

const LANGUAGE_LABEL = { en: "English", es: "Español", de: "Deutsch" };
const device = browserName === "webkit" ? devices["iPhone 15"] : devices["Pixel 7"];
const out = `screenshots/${browserName}-${lang}`;
mkdirSync(out, { recursive: true });

const browser = await (browserName === "webkit" ? webkit : chromium).launch();
const context = await browser.newContext({ ...device, locale: lang, timezoneId: "Europe/Berlin", colorScheme: "dark" });
const page = await context.newPage();
page.on("pageerror", (err) => console.error("page error:", err.message));
page.on("console", (msg) => msg.type() === "error" && console.error("console:", msg.text()));

let n = 0;
async function shot(name, fullPage = false) {
  n += 1;
  const file = `${out}/${String(n).padStart(2, "0")}-${name}.png`;
  await page.waitForTimeout(500); // let fade-in animations finish
  await page.screenshot({ path: file, fullPage });
  console.log("saved", file);
}

// Login
await page.goto(base);
await page.locator('input[name="username"]').waitFor();
await shot("login");
await page.fill('input[name="username"]', user);
await page.fill('input[name="password"]', "wrong password");
await page.locator('button[type="submit"]').click();
await page.locator('[role="alert"]').waitFor();
await shot("login-error");
await page.fill('input[name="password"]', password);
await page.locator('button[type="submit"]').click();

// Onboarding step 1: name, language, form of address
await page.locator(".progress").waitFor();
await page.getByRole("button", { name: LANGUAGE_LABEL[lang] }).click();
await page.locator('input[type="text"]').first().fill(lang === "es" ? "Lucía" : lang === "de" ? "Anna" : "Sam");
await page.locator(".radio-cards button").first().click(); // feminine forms
await shot("onboarding-1", true);
await page.locator(".button.primary").click();

// Step 2: birth date and time
await page.locator('input[type="date"]').waitFor();
await page.fill('input[type="date"]', "1991-04-17");
await page.fill('input[type="time"]', "08:20");
await shot("onboarding-2");
await page.locator(".button.primary").click();

// Step 3: birth place search, timezone
await page.locator('input[type="search"]').waitFor();
await page.fill('input[type="search"]', lang === "es" ? "sevil" : "münch");
await page.locator(".results button").first().waitFor();
await shot("onboarding-3-search");
await page.locator(".results button").first().click();
await shot("onboarding-3-chosen", true);
await page.locator(".button.primary").click();

// Today: loading state first (generation takes a while), then the reading
await page.locator('[role="status"], .headline').first().waitFor();
if (await page.locator('[role="status"]').count()) await shot("today-loading");
await page.locator(".headline").waitFor({ timeout: 120_000 });
await shot("today-top");
await page.locator("details.why summary").click();
await shot("today-full", true);

// Settings
await page.locator(".icon-button").last().click();
await page.locator("form").first().waitFor();
await shot("settings", true);

await browser.close();
