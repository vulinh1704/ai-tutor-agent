import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Onboarding } from "@/components/onboarding";
import { renderWithProviders } from "@/test/render";
import type { LearnerProfile } from "@/lib/types";

async function next(user: ReturnType<typeof userEvent.setup>, name = /Next|Tiếp tục/) {
  await user.click(await screen.findByRole("button", { name }));
}

describe("Onboarding", () => {
  it("builds a learner profile step by step", async () => {
    const onComplete = vi.fn<(profile: LearnerProfile) => Promise<void>>().mockResolvedValue();
    const user = userEvent.setup();
    renderWithProviders(<Onboarding onComplete={onComplete} />);

    // Welcome: switching to Vietnamese switches the whole UI.
    expect(screen.getByText("Step 1 of 8")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Tiếng Việt" }));
    expect(await screen.findByText("Bước 1/8")).toBeInTheDocument();
    await next(user);

    // A name is required before moving on.
    const name = await screen.findByLabelText("Mình nên gọi bạn là gì?");
    expect(screen.getByRole("button", { name: /Tiếp tục/ })).toBeDisabled();
    await user.type(name, "Linh");
    await next(user);

    await user.click(await screen.findByRole("radio", { name: "Lớp 9" }));
    await next(user);
    await user.click(await screen.findByRole("button", { name: "Toán" }));
    await next(user);
    await user.click(await screen.findByRole("button", { name: "Làm tốt bài kiểm tra sắp tới" }));
    await next(user);
    await user.click(await screen.findByRole("radio", { name: /Ngắn gọn/ }));
    await user.click(screen.getByRole("radio", { name: /Hướng dẫn từng bước/ }));
    await next(user);
    await user.click(await screen.findByRole("radio", { name: "violet" }));
    await next(user);

    expect(await screen.findByText("Xong rồi, Linh!")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bắt đầu thôi!" }));

    expect(onComplete).toHaveBeenCalledTimes(1);
    const profile = onComplete.mock.calls[0][0];
    expect(profile).toMatchObject({
      display_name: "Linh",
      level: "lớp 9",
      subjects: ["math"],
      goal: "Làm tốt bài kiểm tra sắp tới",
      preferences: { language: "vi", tone: "direct", scaffolding: "more" },
      appearance: { accent: "violet" },
    });
  });

  it("lets the learner go back", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Onboarding onComplete={async () => undefined} />);
    expect(screen.getByRole("button", { name: /Back/ })).toBeDisabled();
    await next(user);
    expect(await screen.findByText("Step 2 of 8")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Back/ }));
    expect(await screen.findByText("Step 1 of 8")).toBeInTheDocument();
  });
});
