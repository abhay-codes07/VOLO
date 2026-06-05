export function PageHeader({
  eyebrow,
  title,
  description,
  right,
}: {
  eyebrow: string;
  title: React.ReactNode;
  description: string;
  right?: React.ReactNode;
}) {
  return (
    <section className="relative overflow-hidden">
      <div className="hero-mesh" aria-hidden />
      <div className="hero-noise" aria-hidden />
      <div className="relative max-w-7xl mx-auto px-6 md:px-10 pt-16 pb-12">
        <div className="flex items-end justify-between gap-6 flex-wrap">
          <div className="max-w-3xl">
            <div className="chip mb-5">{eyebrow}</div>
            <h1 className="font-display text-display-lg font-semibold text-text-hi tracking-tighter mb-5">
              {title}
            </h1>
            <p className="text-text-mid text-lg leading-relaxed">{description}</p>
          </div>
          {right ? <div>{right}</div> : null}
        </div>
      </div>
    </section>
  );
}
