const nf = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
export const money = (n: number) => nf.format(Math.round(n));
export const pct = (n: number) => `${Math.round(n)}%`;
export const dateAr = (iso: string) =>
  new Intl.DateTimeFormat("ar-SA-u-ca-gregory-nu-latn", { year: "numeric", month: "short", day: "numeric" }).format(new Date(iso));
export const KIND_AR: Record<string, string> = { sadaqah: "صدقة", zakat: "زكاة", waqf: "وقف" };
