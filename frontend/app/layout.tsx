import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/providers";
import { Shell } from "@/components/shell";
import "./globals.css";
export const metadata: Metadata = {
  title: "MiniChalk — Feature computation console",
  description:
    "Explore, compute, and trace real-time features in an independent educational engine.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${GeistSans.variable} ${GeistMono.variable}`}>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <Providers>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
