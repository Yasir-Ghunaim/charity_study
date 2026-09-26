import Link from "next/link";
export default function NotFound() {
  return (
    <main className="mx-auto max-w-xl px-5 py-24 text-center">
      <div className="text-[26px] font-bold">الصفحة غير موجودة · Page not found</div>
      <Link href="/" className="mt-4 inline-block text-brand-600 hover:underline">←</Link>
    </main>
  );
}
