import type { Metadata } from "next";
import { ReactNode } from "react";

import { QueryProvider } from "@/lib/query-provider";

import "../styles/globals.css";


export const metadata: Metadata = {
  title: "Knowledge Hub",
  description: "Internal document knowledge system for grounded answers and cited sources.",
};


export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
