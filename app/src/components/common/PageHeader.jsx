// Replaces the old title→eyebrow→hero pattern (36–48px bold + uppercase
// tracking label) repeated on every page. Operators already know which
// screen they're on; the title doesn't need to compete for attention with
// the content below it.
function PageHeader({ title, description, meta, children }) {
  return (
    <div className="flex flex-col justify-between gap-3 border-b border-[#DDE4DF] pb-4 lg:flex-row lg:items-end">
      <div>
        <h1 className="text-lg font-medium text-[#17211D] md:text-xl">
          {title}
        </h1>

        {description && (
          <p className="mt-1.5 max-w-2xl text-sm leading-6 text-[#626D67]">
            {description}
          </p>
        )}

        {children && <div className="mt-2">{children}</div>}
      </div>

      {meta && <div className="text-left lg:text-right">{meta}</div>}
    </div>
  );
}

export default PageHeader;
