import { expect, test, type Page } from "@playwright/test";

const demoUser = `e2e-${process.env.E2E_RUN_ID ?? Date.now()}`;
const runSuffix = demoUser.slice(-8);

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await page.addInitScript((user) => {
    localStorage.setItem("voice-assistant-demo-user", user);
    localStorage.removeItem("voice-assistant-session-id");
  }, demoUser);
  await page.goto("/");
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

test("clarification answer creates a meeting", async ({ page }) => {
  await page.locator(".composer input").fill("Поставь встречу с командой завтра");
  await page.locator('.composer button[type="submit"]').click();

  const clarification = page.locator(".clarification");
  await expect(clarification).toBeVisible();
  await page.locator(".clarification__form input").fill("В 15:00");
  await page.locator('.clarification__form button[type="submit"]').click();
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
    const user = localStorage.getItem("voice-assistant-demo-user") ?? "demo";
    const response = await fetch("/api/v1/events", {
      headers: { "X-Demo-User": user },
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
