"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Bookings, Errors } from "@/components/admin/Bookings";
import Movies from "@/components/admin/Movies";
import Overview from "@/components/admin/Overview";
import Shows from "@/components/admin/Shows";
import Themes from "@/components/admin/Themes";
import Venues from "@/components/admin/Venues";
import ThemeApplier from "@/components/ui/ThemeApplier";
import { Spinner } from "@/components/ui/bits";
import { useAuth } from "@/lib/auth";

const TABS = { overview: Overview, movies: Movies, themes: Themes, venues: Venues, shows: Shows, bookings: Bookings, errors: Errors };

export default function Admin() {
  const { session, ready } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<keyof typeof TABS>("overview");
  useEffect(() => {
    if (ready && !session?.user.is_admin) router.replace("/login/?next=/admin/");
  }, [ready, session, router]);
  if (!session?.user.is_admin) return <Spinner />;
  const View = TABS[tab];
  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <ThemeApplier theme={null} />
      <h1 className="text-2xl font-bold">Admin</h1>
      <nav className="mt-3 flex gap-2 overflow-x-auto no-scrollbar pb-1" role="tablist">
        {(Object.keys(TABS) as (keyof typeof TABS)[]).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={`chip capitalize ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t}</button>
        ))}
      </nav>
      <div className="mt-5"><View /></div>
    </div>
  );
}
