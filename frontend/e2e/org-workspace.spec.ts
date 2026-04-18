import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

const PASSWORD = process.env.PLAYWRIGHT_E2E_PASSWORD;
const supportPolicyPath = path.resolve(__dirname, "../../docs/demo-data/support_policy.md");

function uniqueEmail(prefix: string) {
  const runId = Date.now().toString(36);
  return `${prefix}-${runId}@example.com`;
}

async function signUp(page: Page, options: { fullName: string; email: string; password: string; organizationName: string }) {
  await page.goto("/login");
  await page.getByTestId("auth-mode-signup").click();
  await page.getByTestId("signup-full-name").fill(options.fullName);
  await page.getByTestId("signup-organization-name").fill(options.organizationName);
  await page.getByTestId("auth-email").fill(options.email);
  await page.getByTestId("auth-password").fill(options.password);
  await page.getByTestId("auth-submit").click();

  if (page.url().includes("/documents")) {
    return;
  }

  const confirmationMessage = page.getByText("Your workspace account was created. If email confirmation is enabled");
  if (await confirmationMessage.isVisible()) {
    await signIn(page, { email: options.email, password: options.password });
  }
}

async function signIn(page: Page, options: { email: string; password: string }) {
  await page.goto("/login");
  await page.getByTestId("auth-mode-signin").click();
  await page.getByTestId("auth-email").fill(options.email);
  await page.getByTestId("auth-password").fill(options.password);
  await page.getByTestId("auth-submit").click();
  await page.waitForURL("**/documents");
}

async function expectWorkspaceContext(page: Page, organizationName: string, userName: string) {
  await expect(page.getByTestId("workspace-organization")).toContainText(organizationName);
  await expect(page.getByTestId("workspace-user")).toContainText(userName);
}

async function uploadSupportPolicy(page: Page) {
  await page.goto("/documents/upload");
  await page.getByTestId("file-upload-input").setInputFiles(supportPolicyPath);
  await expect(page.getByText("File uploaded and indexed successfully.")).toBeVisible({ timeout: 60_000 });
}

async function expectDocumentVisible(page: Page, fileName: string) {
  await page.goto("/documents");
  await expect(page.getByText(fileName)).toBeVisible({ timeout: 30_000 });
}

async function expectDocumentHidden(page: Page, fileName: string) {
  await page.goto("/documents");
  await expect(page.getByText(fileName)).toHaveCount(0);
}

async function searchAndAssertCitation(page: Page, question: string, fileName: string) {
  await page.goto("/search");
  await page.getByLabel("Search request").fill(question);
  await page.getByRole("button", { name: "Search answers" }).click();
  await page.waitForURL("**/answers/**", { timeout: 60_000 });
  await expect(page.getByText("Sources")).toBeVisible();
  await expect(page.getByText(fileName)).toBeVisible();
}

async function assertEmptySearchWorkspace(page: Page) {
  await page.goto("/search");
  await expect(page.getByText("Documents are required before searching")).toBeVisible();
}

async function signOut(page: Page) {
  await page.getByTestId("sign-out-button").click();
  await page.waitForURL("**/login");
}

test.describe("organization workspace flows", () => {
  test.skip(!PASSWORD, "Set PLAYWRIGHT_E2E_PASSWORD to run organization E2E tests.");

  test("signup, shared organization visibility, isolation, and logout", async ({ browser }) => {
    const runKey = Date.now().toString();
    const sharedOrgCanonical = `C3U ${runKey}`;
    const sharedOrgVariant = ` c3u ${runKey} `;
    const otherOrg = `Northwind ${runKey}`;

    const userOne = {
      fullName: "Avery Operations",
      email: uniqueEmail("avery"),
      password: PASSWORD!,
      organizationName: sharedOrgCanonical,
    };
    const userTwo = {
      fullName: "Jordan Support",
      email: uniqueEmail("jordan"),
      password: PASSWORD!,
      organizationName: sharedOrgVariant,
    };
    const userThree = {
      fullName: "Morgan Finance",
      email: uniqueEmail("morgan"),
      password: PASSWORD!,
      organizationName: otherOrg,
    };

    const contextOne = await browser.newContext();
    const pageOne = await contextOne.newPage();
    await signUp(pageOne, userOne);
    await expectWorkspaceContext(pageOne, sharedOrgCanonical, userOne.fullName);
    await uploadSupportPolicy(pageOne);
    await expectDocumentVisible(pageOne, "support_policy.md");

    const contextTwo = await browser.newContext();
    const pageTwo = await contextTwo.newPage();
    await signUp(pageTwo, userTwo);
    await expectWorkspaceContext(pageTwo, sharedOrgCanonical, userTwo.fullName);
    await expectDocumentVisible(pageTwo, "support_policy.md");
    await searchAndAssertCitation(pageTwo, "What queue handles standard password reset requests?", "support_policy.md");
    await signOut(pageTwo);
    await signIn(pageTwo, { email: userTwo.email, password: userTwo.password });
    await expectDocumentVisible(pageTwo, "support_policy.md");

    const contextThree = await browser.newContext();
    const pageThree = await contextThree.newPage();
    await signUp(pageThree, userThree);
    await expectWorkspaceContext(pageThree, otherOrg, userThree.fullName);
    await expectDocumentHidden(pageThree, "support_policy.md");
    await assertEmptySearchWorkspace(pageThree);

    await Promise.all([contextOne.close(), contextTwo.close(), contextThree.close()]);
  });
});
