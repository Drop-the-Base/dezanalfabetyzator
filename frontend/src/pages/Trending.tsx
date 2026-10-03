import { Mascot, TabBar, TopBar } from "../components/ui";

/** Zakładka „Na topie” — trendujące historie (#31). */
export default function Trending() {
  return (
    <>
      <TopBar />
      <TabBar />
      <main className="mx-auto max-w-xl px-4 pb-10 pt-4">
        <section className="flex items-center gap-3 rounded-3xl bg-ai-soft p-4">
          <Mascot size={52} />
          <p className="text-sm font-semibold text-ai">Tu będą historie, które najbardziej się podobają. Już wkrótce!</p>
        </section>
      </main>
    </>
  );
}
