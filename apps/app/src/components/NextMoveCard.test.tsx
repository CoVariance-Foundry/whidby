// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import NextMoveCard from "./NextMoveCard";

afterEach(cleanup);

describe("NextMoveCard", () => {
  it("renders a linked Continue CTA", () => {
    render(
      <NextMoveCard
        href="/explore?city=New%20York&service=garage%20door%20repair"
        title="Browse similar markets"
        subtitle="Compare adjacent opportunities."
        primary
      />,
    );

    const link = screen.getByRole("link", { name: /browse similar markets/i });
    expect(link).toHaveAttribute(
      "href",
      "/explore?city=New%20York&service=garage%20door%20repair",
    );
    expect(screen.getByText("Continue")).toBeInTheDocument();
  });
});
