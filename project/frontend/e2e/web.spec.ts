import { expect, test, type Page } from "@playwright/test";

const runId = process.env.E2E_RUN_ID ?? String(Date.now());
const account = {
  email: `e2e-${runId}@example.com`,
  password: "e2e-password-123",
  display_name: "E2E",
};
const runSuffix = runId.slice(-8);

let accessToken = "";

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  const registered = await request.post("/api/v1/auth/register", { data: account });
  if (registered.ok()) {
    accessToken = (await registered.json()).access_token;
    return;
  }

  if (registered.status() !== 409) {
    throw new Error(`register failed: ${registered.status()} ${await registered.text()}`);
  }

  const loggedIn = await request.post("/api/v1/auth/login", {
    data: { email: account.email, password: account.password },
  });
  if (!loggedIn.ok()) {
    throw new Error(`login failed: ${loggedIn.status()} ${await loggedIn.text()}`);
  }
  accessToken = (await loggedIn.json()).access_token;
});

async function chooseTextMode(page: Page) {
  const picker = page.locator(".mode-picker");
  await expect(picker).toBeVisible();
  await picker.getByRole("button", { name: /Текстовый режим/ }).click();
  await expect(picker).toBeHidden();
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript((token) => {
    localStorage.setItem("gorky-auth-token", token);
    localStorage.removeItem("voice-assistant-session-id");
  }, accessToken);
  await page.goto("/");
  await chooseTextMode(page);
});

async function sendChat(page: Page, text: string) {
  const messages = page.locator(".chat__messages .message");
  const before = await messages.count();
  await page.locator(".composer input").fill(text);
  await page.locator('.composer button[type="submit"]').click();
  await expect(messages).toHaveCount(before + 2);
  await expect(messages.last()).toContainText("Готово");
}

test("chat creates a reminder and timeline shows it", async ({ page }) => {
  await sendChat(page, "Напомни завтра в 10 утра позвонить Ивану");

  await page.getByRole("button", { name: "Таймлайн" }).click();
  await expect(
    page.locator(".event-card", { hasText: "позвонить Ивану" }),
  ).toContainText("Напоминание");
});

test("voice mode opens a call without a text composer", async ({ page }) => {
  await expect(page.getByRole("button", { name: "Надиктовать сообщение" })).toBeVisible();

  await page.getByRole("button", { name: /Звонок/ }).click();
  const call = page.locator(".call");
  await expect(call).toBeVisible();
  await expect(call.locator(".call-wave")).toBeVisible();
  await expect(call.locator("input")).toHaveCount(0);
  await expect(call.locator("textarea")).toHaveCount(0);

  await call.getByRole("button", { name: /Завершить/ }).click();
  await expect(call).toBeHidden();
  await expect(page.locator(".mode-switch__item--active")).toHaveText("Текст");
});

test("clarification answer creates a meeting", async ({ page }) => {
  await page.locator(".composer input").fill("Поставь встречу с командой завтра");
  await page.locator('.composer button[type="submit"]').click();

  const clarification = page.locator(".clarification");
  await expect(clarification).toBeVisible();
  await page.locator(".composer input").fill("В 15:00");
  await page.locator('.composer button[type="submit"]').click();
  await expect(clarification).toBeHidden();
  await expect(page.locator(".chat__messages .message").last()).toContainText("Готово");

  await page.getByRole("button", { name: "Таймлайн" }).click();
  const meeting = page.locator(".event-card", { hasText: "встречу с командой" });
  await expect(meeting).toContainText("Встреча");
  await expect(meeting).toContainText("Запланировано");
});

test("timeline creates and completes an event", async ({ page }) => {
  const title = `Купить билеты ${runSuffix}`;

  await page.getByRole("button", { name: "Таймлайн" }).click();
  await page.getByRole("button", { name: "Новое событие" }).click();
  await page.locator('.event-editor input:not([type="datetime-local"])').fill(title);
  await page.locator('.event-editor button[type="submit"]').click();

  const card = page.locator(".event-card", { hasText: title });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Выполнить" }).click();
  await expect(card).toContainText("Выполнено");
});

test("editor converts the selected timezone to UTC", async ({ page }) => {
  const title = `Созвон в Дубае ${runSuffix}`;

  await page.getByRole("button", { name: "Таймлайн" }).click();
  await page.getByRole("button", { name: "Новое событие" }).click();
  await page.locator('.event-editor input:not([type="datetime-local"])').fill(title);
  await page.locator('.event-editor input[type="datetime-local"]').fill("2030-01-01T12:00");
  await page.locator(".event-editor select").nth(1).selectOption("Asia/Dubai");
  await page.locator('.event-editor button[type="submit"]').click();

  const dueAt = await page.evaluate(async (eventTitle) => {
    const token = localStorage.getItem("gorky-auth-token");
    const response = await fetch("/api/v1/events", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const items = (await response.json()) as Array<{ title: string; due_at: string | null }>;
    return items.find((item) => item.title === eventTitle)?.due_at ?? null;
  }, title);

  expect(dueAt).toBe("2030-01-01T12:00:00+04:00");
});

test("search finds a chat-created event", async ({ page }) => {
  await page.getByRole("button", { name: "Поиск" }).click();
  await page.locator(".search-bar input").fill("Ивану");
  await page.locator('.search-bar button[type="submit"]').click();

  await expect(
    page.locator(".event-card", { hasText: "позвонить Ивану" }),
  ).toBeVisible();
});

test("auth screen is shown without a token", async ({ page }) => {
  await page.addInitScript(() => localStorage.removeItem("gorky-auth-token"));
  await page.reload();

  await expect(
    page.getByRole("heading", { name: /Скажи\.\s*Я запомню\./ }),
  ).toBeVisible();
  await expect(page.getByRole("tab", { name: "Регистрация" })).toBeVisible();
});

test("registration through the UI opens the workspace", async ({ page }) => {
  await page.addInitScript(() => localStorage.removeItem("gorky-auth-token"));
  await page.reload();

  await page.getByRole("tab", { name: "Регистрация" }).click();
  await page.getByLabel("Имя").fill("Новый пользователь");
  await page.getByLabel("Email").fill(`ui-${runId}@example.com`);
  await page.getByLabel("Пароль").fill("ui-password-123");
  await page.getByRole("button", { name: /Создать аккаунт/ }).click();
  await chooseTextMode(page);

  await expect(page.getByRole("heading", { name: "Ассистент" })).toBeVisible();
  await expect(page.locator(".topbar__user")).toContainText("Новый пользователь");
});

test.describe("mobile", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("composer stays inside the viewport", async ({ page }) => {
    await expect(page.locator(".composer")).toBeInViewport();
    await expect(page.locator(".composer input")).toBeInViewport();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
