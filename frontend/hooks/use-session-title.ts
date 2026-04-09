"use client";

import { useMemo } from "react";

import type { SessionResponse } from "@/types";


export function useSessionTitle(session?: SessionResponse) {
  return useMemo(() => session?.title ?? "Search workspace", [session]);
}

