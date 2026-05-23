import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

/**
 * Header Component
 * 
 * Purpose: Renders the top navigation bar containing the app title ("SAGE") 
 * and the theme toggle button.
 * 
 * --- Educational Notes on Dark/Light Mode Implementation ---
 * 
 * 1. How Tailwind's `dark:` class system works:
 *    Tailwind utilizes the `dark:` variant prefix to apply styles conditionally based on the active theme.
 *    By configuring `darkMode: 'class'` in `tailwind.config.js`, we instruct Tailwind to ignore the 
 *    user's OS preference (media query) and instead check for the presence of a specific CSS class 
 *    (default is 'dark') on an ancestor DOM element, typically the root `<html>` element. 
 *    If the 'dark' class is present on `<html>`, any utility class prefixed with `dark:` 
 *    (e.g., `dark:bg-slate-900`) will be applied to the elements.
 * 
 * 2. Manipulating the classList on document.documentElement:
 *    The `document.documentElement` object represents the root element of the document (the `<html>` tag). 
 *    We can globally toggle the 'dark' theme by adding or removing the 'dark' class on this element using 
 *    `document.documentElement.classList.add('dark')` or `.remove('dark')`. 
 *    Because this change happens at the root level, it cascades down the entire DOM tree, instantly 
 *    activating or deactivating all Tailwind `dark:` variants.
 * 
 * 3. Persisting the theme choice using localStorage:
 *    To ensure the user's theme preference remains consistent across page reloads or subsequent visits, 
 *    we persist their choice in the browser's `localStorage` via `localStorage.setItem('theme', value)`. 
 *    When the Header component first mounts, a `useEffect` hook reads `localStorage.getItem('theme')` 
 *    to initialize the local state and apply the corresponding 'dark' class to the DOM immediately.
 */
export default function Header() {
  // Initialize the theme state by checking localStorage or OS preference
  const [isDark, setIsDark] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return savedTheme === 'dark' || (!savedTheme && prefersDark);
  });

  // Apply the theme to the DOM whenever isDark changes
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  /**
   * Toggles the active theme.
   * This function updates the React state, mutates the root DOM element's classList,
   * and saves the new preference to localStorage.
   */
  const toggleTheme = () => {
    setIsDark((prev) => {
      const nextThemeIsDark = !prev;
      
      if (nextThemeIsDark) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
      }
      
      return nextThemeIsDark;
    });
  };

  return (
    <header className="flex justify-between items-center p-6 bg-transparent transition-colors duration-300 relative z-10 w-full max-w-7xl mx-auto">
      {/* App Title */}
      <div className="font-extrabold text-3xl tracking-tight text-slate-900 dark:text-white select-none cursor-pointer">
        SAGE
      </div>
      
      {/* Theme Toggle Button */}
      <button
        onClick={toggleTheme}
        className="p-3 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
        aria-label="Toggle Dark Mode"
        title="Toggle Dark/Light Mode"
      >
        {isDark ? (
          <Sun className="w-5 h-5 text-yellow-500" />
        ) : (
          <Moon className="w-5 h-5" />
        )}
      </button>
    </header>
  );
}
