import { useState } from "react";

const KEY = "sztafeta.howto.collapsed";

export const GOAL =
  "Ćwiczysz czytanie ze zrozumieniem: piszesz historię razem z innymi i z AI, ale żeby dopisać swój kawałek, musisz najpierw zrozumieć, co napisali poprzednicy.";

const STEPS = [
  { title: "Przeczytaj historię", text: "Od początku do końca. Zapamiętaj postacie, miejsca i to, co się wydarzyło." },
  { title: "Dopisz, co było dalej", text: "Nawiąż do tekstu i dodaj własny pomysł. Kilka zdań wystarczy." },
  {
    title: "Sowa sprawdza i odpowiada",
    text: "AI ocenia, czy tekst został zrozumiany, pokazuje zdanie, na którym oparło ocenę, i dopisuje kolejny fragment.",
  },
];

function Steps() {
  return (
    <ol className="mt-3 flex flex-col gap-2">
      {STEPS.map((s, i) => (
        <li key={s.title} className="flex gap-3">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-baton text-sm font-black text-white">
            {i + 1}
          </span>
          <p className="text-sm leading-snug">
            <b>{s.title}.</b> <span className="text-muted">{s.text}</span>
          </p>
        </li>
      ))}
    </ol>
  );
}

/** Cel aplikacji + 3 kroki. `collapsible` — w feedzie można zwinąć (zapamiętane w przeglądarce). */
export default function HowItWorks({ collapsible = false }: { collapsible?: boolean }) {
  const [collapsed, setCollapsed] = useState(() => {
    if (!collapsible) return false;
    try {
      return localStorage.getItem(KEY) === "1";
    } catch {
      return false;
    }
  });
  const toggle = () => {
    setCollapsed((c) => {
      try {
        localStorage.setItem(KEY, c ? "0" : "1");
      } catch {
        /* tryb prywatny */
      }
      return !c;
    });
  };

  return (
    <section className="rounded-3xl bg-card p-4 text-left ring-1 ring-line">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-black">Jak to działa?</h2>
        {collapsible && (
          <button onClick={toggle} className="shrink-0 text-xs font-extrabold text-muted underline">
            {collapsed ? "Pokaż" : "Zwiń"}
          </button>
        )}
      </div>
      {!collapsed && (
        <>
          <p className="mt-1 text-sm font-semibold">{GOAL}</p>
          <Steps />
        </>
      )}
    </section>
  );
}
