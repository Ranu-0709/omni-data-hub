"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import ThemeToggle from "./ThemeToggle";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/categories", label: "Categories" },
  { href: "/trends", label: "Trends" },
  { href: "/locations", label: "Locations" },
  { href: "/loyalty", label: "Loyalty" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-[var(--border)] bg-[var(--bg-card)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link href="/" className="text-lg font-bold">
              Omni Data Hub
            </Link>
            <div className="hidden md:flex gap-1">
              {NAV_ITEMS.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={clsx(
                    "px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    pathname === href
                      ? "bg-gray-200 dark:bg-gray-700 text-[var(--text-primary)]"
                      : "text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
                  )}
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
          <ThemeToggle />
        </div>
      </div>
    </nav>
  );
}
