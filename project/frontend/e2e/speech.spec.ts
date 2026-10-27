import { expect, test, type Page } from "@playwright/test";

const runId = process.env.E2E_RUN_ID ?? String(Date.now());
const account = {
  email: `speech-${runId}@example.com`,
  password: "speech-password-123",
  display_name: "Speech E2E",
};

let accessToken = "";

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  const registered = await request.post("/api/v1/auth/register", { data: account });
  if (!registered.ok()) {
    throw new Error(
      `register failed: ${registered.status()} ${await registered.text()}`,
    );
  }
  accessToken = (await registered.json()).access_token;
});

interface Step {
  at: number;
  resultIndex?: number;
  results: Array<{ text: string; final: boolean }>;
}

async function openApp(page: Page, steps: Step[]) {
  await page.addInitScript(
    ({ token, scriptSteps }) => {
      localStorage.setItem("gorky-auth-token", token);
      localStorage.removeItem("voice-assistant-session-id");
      localStorage.removeItem("gorky-assistant-mode");

      const state = window as unknown as {
        __speechSteps: Step[];
        __speechPlayed?: boolean;
        SpeechRecognition?: unknown;
        webkitSpeechRecognition?: unknown;
      };
      state.__speechSteps = scriptSteps;

      class MockRecognition {
        continuous = false;
        interimResults = false;
        lang = "";
        maxAlternatives = 1;
        onstart: (() => void) | null = null;
        onend: (() => void) | null = null;
        onerror: ((event: { error: string }) => void) | null = null;
        onresult:
          | ((event: {
              resultIndex: number;
              results: Array<{
                isFinal: boolean;
                length: number;
                0: { transcript: string; confidence: number };
              }>;
            }) => void)
          | null = null;
        private timers: number[] = [];

        start() {
          this.onstart?.();
          if (state.__speechPlayed) {
            return;
          }
          state.__speechPlayed = true;
          for (const step of state.__speechSteps) {
            this.timers.push(
              window.setTimeout(() => {
                const results = step.results.map((item) => ({
                  isFinal: item.final,
                  length: 1,
                  0: { transcript: item.text, confidence: 1 },
                }));
                this.onresult?.({
                  resultIndex: step.resultIndex ?? 0,
                  results,
                });
              }, step.at),
            );
          }
        }

        stop() {
          this.timers.forEach((timer) => window.clearTimeout(timer));
          this.timers = [];
          this.onend?.();
        }

        abort() {
          this.stop();
        }
      }

      Object.defineProperty(window, "SpeechRecognition", {
        configurable: true,
        value: MockRecognition,
      });
      Object.defineProperty(window, "webkitSpeechRecognition", {
        configurable: true,
        value: MockRecognition,
      });

      const synth = {
        speak(utterance: SpeechSynthesisUtterance) {
          window.setTimeout(() => {
            utterance.onstart?.(new Event("start") as SpeechSynthesisEvent);
            window.setTimeout(() => {
              utterance.onend?.(new Event("end") as SpeechSynthesisEvent);
            }, 40);
          }, 5);
        },
        cancel() {},
        getVoices() {
          return [];
        },
        addEventListener() {},
        removeEventListener() {},
      };
      Object.defineProperty(window, "speechSynthesis", {
        configurable: true,
        value: synth,
      });
    },
    { token: accessToken, scriptSteps: steps },
  );

  await page.goto("/");
}

async function chooseTextMode(page: Page) {
  await page
    .locator(".mode-picker")
    .getByRole("button", { name: /Текстовый режим/ })
    .click();
}

async function chooseVoiceMode(page: Page) {
  await page
    .locator(".mode-picker")
    .getByRole("button", { name: /Голосовой режим/ })
    .click();
}

const cumulativeFinals: Step[] = [
  { at: 120, results: [{ text: "создай", final: true }] },
  {
    at: 380,
    results: [
      { text: "создай", final: true },
      { text: "создай событие", final: true },
    ],
  },
  {
    at: 640,
    results: [
      { text: "создай", final: true },
      { text: "создай событие", final: true },
      { text: "создай событие на завтра", final: true },
    ],
  },
];

const singleGrowingResult: Step[] = [
  { at: 120, results: [{ text: "создай", final: true }] },
  { at: 380, results: [{ text: "создай событие", final: true }] },
  { at: 640, results: [{ text: "создай событие на завтра", final: true }] },
];

const repeatedSeparateFinals: Step[] = [
  { at: 120, results: [{ text: "создай", final: true }] },
  {
    at: 300,
    results: [
      { text: "создай", final: true },
      { text: "создай", final: true },
    ],
  },
  {
    at: 480,
    results: [
      { text: "создай", final: true },
      { text: "создай", final: true },
      { text: "событие", final: true },
    ],
  },
  {
    at: 660,
    results: [
      { text: "создай", final: true },
      { text: "создай", final: true },
      { text: "событие", final: true },
      { text: "событие", final: true },
      { text: "на", final: true },
    ],
  },
  {
    at: 840,
    results: [
      { text: "создай", final: true },
      { text: "создай", final: true },
      { text: "событие", final: true },
      { text: "событие", final: true },
      { text: "на", final: true },
      { text: "завтра", final: true },
    ],
  },
];

const interimThenFinal: Step[] = [
  { at: 120, results: [{ text: "создай", final: false }] },
  { at: 320, results: [{ text: "создай событие", final: false }] },
  { at: 520, results: [{ text: "создай событие на завтра", final: true }] },
];

for (const [name, steps] of [
  ["cumulative finals", cumulativeFinals],
  ["one growing final result", singleGrowingResult],
  ["repeated separate finals", repeatedSeparateFinals],
  ["interim growth followed by a final", interimThenFinal],
] as const) {
  test(`dictation keeps exactly the spoken phrase: ${name}`, async ({ page }) => {
    await openApp(page, steps);
    await chooseTextMode(page);
    await page.getByRole("button", { name: "Надиктовать сообщение" }).click();

    await expect(page.locator(".composer input")).toHaveValue(
      "создай событие на завтра",
      { timeout: 5_000 },
    );
  });
}

test("voice call sends the whole phrase once after two seconds of silence", async ({
  page,
}) => {
  const requests: string[] = [];
  let requestAt = 0;
  await page.route("**/api/v1/chat", async (route) => {
    const body = route.request().postDataJSON() as { text: string };
    requestAt = Date.now();
    requests.push(body.text);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: "speech-mock-session",
        reply: "Готово.",
        action: { name: "create_event", status: "done", entity_id: "mock" },
        clarification: null,
        audio_url: null,
      }),
    });
  });

  await openApp(page, cumulativeFinals);
  await chooseVoiceMode(page);
  await expect(page.locator(".call")).toBeVisible();
  const openedAt = Date.now();

  await expect.poll(() => requests.length, { timeout: 7_000 }).toBe(1);
  const elapsed = requestAt - openedAt;
  expect(elapsed).toBeGreaterThanOrEqual(2_000);
  expect(elapsed).toBeLessThan(5_000);
  expect(requests).toEqual(["создай событие на завтра"]);
});
