import { NavLink } from "react-router-dom";
import { primaryNavItems, secondaryNavItems } from "../shared/config/nav-items";
import { cn } from "../shared/lib/cn";
import type { NavItem } from "../shared/config/nav-items";

function NavSection({ items }: { items: NavItem[] }) {
  return (
    <div className="space-y-1">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          aria-label={item.title}
          className={({ isActive }) =>
            cn(
              "block rounded-xl px-3 py-2 text-sm transition",
              isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )
          }
        >
          <div className="font-medium">{item.title}</div>
          <div aria-hidden="true" className="mt-1 text-xs opacity-75">
            {item.description}
          </div>
        </NavLink>
      ))}
    </div>
  );
}

export function SidebarNav() {
  return (
    <nav aria-label="Primary" className="flex h-full flex-col justify-between">
      <div>
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Research Desk</p>
          <h1 className="mt-2 text-xl font-semibold text-slate-950">AI News Bot</h1>
          <p className="mt-3 text-sm text-slate-600">Loading workspace...</p>
        </div>
        <NavSection items={primaryNavItems} />
      </div>
      <NavSection items={secondaryNavItems} />
    </nav>
  );
}
