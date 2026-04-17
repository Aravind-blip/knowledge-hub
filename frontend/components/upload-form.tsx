"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";


type UploadState = {
  fileName: string;
  success?: string;
  error?: string;
};

async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/documents", {
    method: "POST",
    body: formData,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? payload.error ?? "Upload failed.");
  }
  return payload;
}


export function UploadForm() {
  const queryClient = useQueryClient();
  const [state, setState] = useState<UploadState | null>(null);
  const mutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: (data) => {
      setState({ fileName: data.original_name, success: "File uploaded and indexed successfully." });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error: Error) => {
      setState((current) => ({
        fileName: current?.fileName ?? "",
        error: error.message,
      }));
    },
  });

  return (
    <div className="panel panel--form">
      <div className="panel__header">
        <div>
          <h2>Upload documents</h2>
          <p>Upload text-based PDF, text, or Markdown documents for the current organization workspace. Image-only files are not processed in this MVP.</p>
        </div>
      </div>
      <label className="upload-dropzone">
        <input
          accept=".pdf,.txt,.md,text/plain,text/markdown,application/pdf"
          className="sr-only"
          type="file"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            setState({ fileName: file.name });
            mutation.mutate(file);
          }}
        />
        <span className="upload-dropzone__title">Choose a file</span>
        <span className="upload-dropzone__description">
          Files up to 15 MB. OCR and image-only documents are out of scope for this MVP.
        </span>
      </label>
      {mutation.isPending ? <div className="callout">Indexing {state?.fileName ?? "document"}...</div> : null}
      {state?.success ? <div className="callout callout--success">{state.success}</div> : null}
      {state?.error ? <div className="callout callout--error">{state.error}</div> : null}
      {!mutation.isPending && !state ? (
        <div className="callout callout--subtle">No files uploaded yet. Select a document to begin indexing for this organization.</div>
      ) : null}
    </div>
  );
}
