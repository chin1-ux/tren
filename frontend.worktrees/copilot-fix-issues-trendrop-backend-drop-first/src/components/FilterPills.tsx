import { trendCategories } from "@/lib/trend-categories";
import { cn } from "@/lib/utils";

interface Props {
  active: string;
  onChange: (cat: string) => void;
}

export function FilterPills({ active, onChange }: Props) {
  return (
    <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
      {trendCategories.map((cat) => {
        const isActive = active === cat;
        return (
          <button
            key={cat}
            onClick={() => onChange(cat)}
            className={cn(
              "shrink-0 rounded-full border px-4 py-1.5 text-sm font-medium transition-all",
              isActive
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            {cat}
          </button>
        );
      })}
    </div>
  );
}
