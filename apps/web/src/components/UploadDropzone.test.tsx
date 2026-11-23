import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DocumentOut, UploadOutcome } from "@/api/client";
import { renderWithIntl } from "@/test/renderWithIntl";
import { UploadDropzone } from "./UploadDropzone";

const anyDoc = {} as DocumentOut;

function file(name: string, size: number): File {
  return new File([new Uint8Array(size)], name, { type: "application/pdf" });
}

async function choose(files: File[]) {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
  await userEvent.upload(input, files);
}

describe("UploadDropzone", () => {
  it("rejects a file over the limit without uploading it", async () => {
    const upload = vi.fn<(f: File) => Promise<UploadOutcome>>();
    renderWithIntl(<UploadDropzone maxBytes={100} upload={upload} onUploaded={vi.fn()} />, "en");
    await choose([file("big.pdf", 101)]);
    expect(await screen.findByText("big.pdf: The file is too large.")).toBeInTheDocument();
    expect(upload).not.toHaveBeenCalled();
  });

  it("uploads valid files and reports added and duplicate results", async () => {
    const upload = vi
      .fn<(f: File) => Promise<UploadOutcome>>()
      .mockResolvedValueOnce({ kind: "added", document: anyDoc })
      .mockResolvedValueOnce({ kind: "duplicate", document: anyDoc });
    const onUploaded = vi.fn();
    renderWithIntl(<UploadDropzone maxBytes={1000} upload={upload} onUploaded={onUploaded} />, "en");
    await choose([file("a.pdf", 10), file("b.pdf", 10)]);
    expect(await screen.findByText("a.pdf was added.")).toBeInTheDocument();
    expect(await screen.findByText("b.pdf was already in your inbox.")).toBeInTheDocument();
    expect(upload).toHaveBeenCalledTimes(2);
    expect(onUploaded).toHaveBeenCalledOnce();
  });

  it("shows the server's error code as a translated message", async () => {
    const upload = vi
      .fn<(f: File) => Promise<UploadOutcome>>()
      .mockResolvedValue({ kind: "error", code: "upload.unsupported_type" });
    renderWithIntl(<UploadDropzone maxBytes={1000} upload={upload} onUploaded={vi.fn()} />, "de");
    await choose([file("x.pdf", 10)]);
    expect(
      await screen.findByText(
        "x.pdf: Dieser Dateityp wird nicht unterstützt. Bitte verwende PDF, XML, PNG oder JPEG.",
      ),
    ).toBeInTheDocument();
  });

  it("never shows a raw error code for unknown errors", async () => {
    const upload = vi
      .fn<(f: File) => Promise<UploadOutcome>>()
      .mockResolvedValue({ kind: "error", code: "something.new" });
    renderWithIntl(<UploadDropzone maxBytes={1000} upload={upload} onUploaded={vi.fn()} />, "en");
    await choose([file("x.pdf", 10)]);
    expect(
      await screen.findByText("x.pdf: Something went wrong. Please try again."),
    ).toBeInTheDocument();
  });
});
