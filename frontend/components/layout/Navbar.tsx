"use client";

import { useState, useEffect } from "react";
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
  const [open, setOpen] = useState(false);

  // Auto-close mobile menu on route change
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <nav className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--bg-card)] backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* Top Bar */}
        <div className="flex items-center justify-between h-16">

          {/* Left */}
          <div className="flex items-center gap-6">
            <Link href="/" className="text-lg font-bold whitespace-nowrap">
              Omni Data Hub
            </Link>

            {/* Desktop Menu */}
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

          {/* Right */}
          <div className="flex items-center gap-2">

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Mobile Menu Button */}
            <button
              onClick={() => setOpen(!open)}
              className="md:hidden p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <svg
                className="w-6 h-6 text-[var(--text-primary)]"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                {open ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>

          </div>
        </div>

        {/* Mobile Menu */}
        <div
          className={clsx(
            "md:hidden overflow-hidden transition-all duration-300",
            open ? "max-h-96 pb-4" : "max-h-0"
          )}
        >
          <div className="flex flex-col gap-1 pt-2">
            {NAV_ITEMS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "px-3 py-2 rounded-md text-base font-medium transition-colors",
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

      </div>
    </nav>
  );
}