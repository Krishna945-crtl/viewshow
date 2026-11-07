"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { usePrefs } from "@/lib/prefs";
import { Toaster } from "./toast";

const NAV = [
  { href: "/home/", label: "Movies", icon: "M4 6h16M4 12h16M4 18h10" },
  { href: "/lab/", label: "Theme Lab", icon: "M12 3v3m0 12v3m9-9h-3M6 12H3m14.5-6.5-2 2m-9 9-2 2m13 0-2-2m-9-9-2-2" },
  { href: "/profile/", label: "Tickets", icon: "M4 7h16v3a2 2 0 0 0 0 4v3H4v-3a2 2 0 0 0 0-4z" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const init = useAuth((s) => s.init);
  const hydrate = usePrefs((s) => s.hydrate);
  const user = useAuth((s) => s.session?.user);
  const path = usePathname();

  useEffect(() => {
    init();
    hydrate();
  }, [init, hydrate]);

  const bare = path === "/" || path.startsWith("/seats");
  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 z-50 btn btn-primary">
        Skip to content
      </a>
      {!bare && (
        <header className="sticky top-0 z-30 glass border-x-0 border-t-0" style={{ paddingTop: "env(safe-area-inset-top)" }}>
          <div className="mx-auto max-w-6xl px-4 h-14 flex items-center gap-4">
            <Link href="/home/" className="font-bold tracking-tight text-lg flex items-center gap-2" aria-label="CineVerse 3D home">
              <span className="inline-block size-6 rounded-md bg-primary shadow-[0_0_20px_var(--cv-primary)]" aria-hidden />
              CineVerse<span className="text-accent">3D</span>
            </Link>
            <nav className="hidden sm:flex gap-1 ml-4" aria-label="Main">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className={`chip ${path.startsWith(n.href.slice(0, -1)) ? "active" : ""}`}>
                  {n.label}
                </Link>
              ))}
              {user?.is_admin && (
                <Link href="/admin/" className={`chip ${path.startsWith("/admin") ? "active" : ""}`}>Admin</Link>
              )}
            </nav>
            <div className="ml-auto flex items-center gap-2">
              {user ? (
                <Link href="/profile/" className="flex items-center gap-2 text-sm" aria-label="Your profile">
                  <span className="size-8 rounded-full bg-secondary grid place-items-center font-semibold border border-line">
                    {user.full_name.charAt(0).toUpperCase()}
                  </span>
                </Link>
              ) : (
                <Link href="/login/" className="btn btn-ghost !py-1.5 !min-h-9 text-sm">Sign in</Link>
              )}
            </div>
          </div>
        </header>
      )}
      <main id="main" className={bare ? "" : "pb-24 sm:pb-8"}>{children}</main>
      {!bare && (
        <nav className="sm:hidden fixed bottom-0 inset-x-0 z-30 glass border-x-0 border-b-0 grid grid-cols-3"
             style={{ paddingBottom: "env(safe-area-inset-bottom)" }} aria-label="Bottom">
          {NAV.map((n) => {
            const on = path.startsWith(n.href.slice(0, -1));
            return (
              <Link key={n.href} href={n.href} className={`flex flex-col items-center gap-1 py-2.5 text-[11px] ${on ? "text-accent" : "text-muted"}`}>
                <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
                  <path d={n.icon} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {n.label}
              </Link>
            );
          })}
        </nav>
      )}
      <Toaster />
    </>
  );
}
