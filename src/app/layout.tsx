import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Maktab SMS — Boshqaruv Paneli",
  description: "Ko'p maktabli (Multi-tenant) maktab boshqaruv tizimi va avtomatlashtirilgan dars jadvali generatori",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="uz">
      <body className="antialiased bg-[#F3F4F6] text-gray-800">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
