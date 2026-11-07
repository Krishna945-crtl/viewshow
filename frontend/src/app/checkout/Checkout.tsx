"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { DemoBadge, Empty, Spinner } from "@/components/ui/bits";
import { toast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cap, rupees, showDate, showTime } from "@/lib/format";
import type { Booking } from "@/lib/types";
import { useApi } from "@/lib/useApi";

interface Order { order_id: string; amount_paise: number; provider: "mock" | "razorpay"; key_id: string | null; sandbox: boolean; booking_reference: string }
interface PaidResult { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }

declare global {
  interface Window { Razorpay?: new (opts: Record<string, unknown>) => { open: () => void; on: (e: string, cb: (r: unknown) => void) => void } }
}

function loadRazorpay() {
  return new Promise<void>((resolve, reject) => {
    if (window.Razorpay) return resolve();
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Couldn't load Razorpay checkout"));
    document.body.appendChild(s);
  });
}

export default function Checkout() {
  const id = useSearchParams().get("booking");
  const router = useRouter();
  const user = useAuth((s) => s.session?.user);
  const { data: b, error, loading, reload } = useApi<Booking>(id ? `/bookings/${id}` : null);
  const [order, setOrder] = useState<Order | null>(null);
  const [busy, setBusy] = useState(false);
  const [left, setLeft] = useState(0);

  useEffect(() => {
    if (!b) return;
    const t = setInterval(() => setLeft(Math.max(0, Math.floor((new Date(b.expires_at).getTime() - Date.now()) / 1000))), 1000);
    return () => clearInterval(t);
  }, [b]);
  useEffect(() => {
    if (b?.status === "CONFIRMED") router.replace(`/ticket/?booking=${b.id}`);
  }, [b, router]);

  async function verify(paid: PaidResult) {
    try {
      const done = await api<Booking>("/payments/verify", { body: { booking_id: id, ...paid } });
      toast("Payment confirmed — enjoy the show!", "success");
      router.replace(`/ticket/?booking=${done.id}`);
    } catch (e) {
      toast((e as ApiError).message, "error");
      reload();
    }
  }

  async function failed() {
    await api("/payments/failed", { body: { booking_id: id } }).catch(() => {});
    toast("Payment didn't go through. Your seats are still held — try again.", "error");
    setOrder(null);
  }

  async function pay() {
    setBusy(true);
    try {
      const o = await api<Order>("/payments/order", { body: { booking_id: id } });
      if (o.provider === "razorpay") {
        await loadRazorpay();
        const rz = new window.Razorpay!({
          key: o.key_id, order_id: o.order_id, amount: o.amount_paise, currency: "INR", name: "CineVerse 3D",
          description: `Booking ${o.booking_reference}`, prefill: { name: user?.full_name, email: user?.email },
          handler: (r: PaidResult) => verify(r),
          modal: { ondismiss: () => setBusy(false) },
        });
        rz.on("payment.failed", () => failed());
        rz.open();
      } else {
        setOrder(o); // show the sandbox sheet
      }
    } catch (e) {
      toast((e as ApiError).message, "error");
      reload();
    } finally {
      setBusy(false);
    }
  }

  async function mock(outcome: "success" | "failure") {
    if (!order) return;
    setBusy(true);
    const r = await api<PaidResult & { error?: unknown }>("/payments/mock/checkout", { body: { order_id: order.order_id, outcome } });
    if ("error" in r && r.error) await failed();
    else await verify(r);
    setBusy(false);
  }

  if (loading) return <Spinner />;
  if (error || !b) return <Empty title="Booking not found" hint={error?.message} />;
  if (b.status !== "PENDING_PAYMENT" && b.status !== "CONFIRMED") {
    return (
      <Empty title={`This booking is ${b.status.toLowerCase().replace("_", " ")}`} hint="Seats were released. Pick them again to continue.">
        <Link href={`/seats/?show=${b.show.id}`} className="btn btn-primary">Choose seats</Link>
      </Empty>
    );
  }
  const subtotal = b.amount_paise - b.convenience_fee_paise;

  return (
    <div className="mx-auto max-w-lg px-4 py-6">
      <h1 className="text-2xl font-bold">Booking summary</h1>
      <p className="text-sm text-muted mt-1">
        Seats held for <span className={`tabular-nums font-semibold ${left < 60 ? "text-red-300" : "text-text"}`}>{Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}</span>
      </p>
      <section className="glass rounded-3xl p-5 mt-4 space-y-4">
        <div className="flex justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{b.movie.title}</h2>
            <p className="text-xs text-muted">{b.movie.certificate} · {b.show.format} · {b.show.language}</p>
          </div>
          {b.theatre.is_demo && <DemoBadge />}
        </div>
        <div className="text-sm">
          <p>{b.theatre.name}, {b.theatre.city}</p>
          <p className="text-muted">{b.show.auditorium} · {showDate(b.show.starts_at)}, {showTime(b.show.starts_at)}</p>
        </div>
        <ul className="text-sm divide-y divide-line border-y border-line">
          {b.seats.map((s) => (
            <li key={s.id} className="flex justify-between py-2"><span>{s.label} <span className="text-muted text-xs">{cap(s.category)}</span></span><span>{rupees(s.price_paise)}</span></li>
          ))}
        </ul>
        <dl className="text-sm space-y-1">
          <div className="flex justify-between"><dt className="text-muted">Tickets</dt><dd>{rupees(subtotal)}</dd></div>
          <div className="flex justify-between"><dt className="text-muted">Convenience fee</dt><dd>{rupees(b.convenience_fee_paise)}</dd></div>
          <div className="flex justify-between text-base font-bold pt-1"><dt>Total</dt><dd>{rupees(b.amount_paise)}</dd></div>
        </dl>
        <button className="btn btn-primary w-full" onClick={pay} disabled={busy || left === 0}>{busy ? "Opening payment…" : `Pay ${rupees(b.amount_paise)}`}</button>
        <Link href={`/seats/?show=${b.show.id}`} className="block text-center text-sm text-muted">Change seats</Link>
      </section>

      {order && order.provider === "mock" && (
        <div className="fixed inset-0 z-40 bg-black/60 grid place-items-end sm:place-items-center p-3" role="dialog" aria-modal="true" aria-labelledby="sbx">
          <div className="glass rounded-3xl p-6 w-full max-w-sm">
            <p className="text-[10px] uppercase tracking-widest text-amber-300">Sandbox · no real money moves</p>
            <h2 id="sbx" className="text-xl font-bold mt-1">Simulated checkout</h2>
            <p className="text-sm text-muted mt-1">Order {order.order_id}. This stands in for Razorpay test mode; the server verifies the signature exactly like a real payment.</p>
            <div className="mt-5 grid gap-2">
              <button className="btn btn-primary" disabled={busy} onClick={() => mock("success")}>Pay {rupees(order.amount_paise)} (success)</button>
              <button className="btn btn-ghost" disabled={busy} onClick={() => mock("failure")}>Simulate card decline</button>
              <button className="text-sm text-muted mt-1" onClick={() => setOrder(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
