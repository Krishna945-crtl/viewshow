import type { Metadata, Viewport } from "next";
import AppShell from "@/components/ui/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "CineVerse 3D",
  description: "Book movie tickets inside an interactive 3D auditorium that takes on each film's atmosphere.",
  applicationName: "CineVerse 3D",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#07070b",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full ambient">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
