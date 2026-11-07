const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export const rupees = (paise: number) => inr.format(Math.round(paise / 100));

export const showTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" });

export const showDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });

export const dayChip = (ymd: string) => {
  const d = new Date(ymd + "T12:00:00+05:30");
  return {
    wd: d.toLocaleDateString("en-IN", { weekday: "short", timeZone: "Asia/Kolkata" }),
    day: d.toLocaleDateString("en-IN", { day: "numeric", timeZone: "Asia/Kolkata" }),
    mon: d.toLocaleDateString("en-IN", { month: "short", timeZone: "Asia/Kolkata" }),
  };
};

export const runtime = (m: number) => `${Math.floor(m / 60)}h ${m % 60}m`;

export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
