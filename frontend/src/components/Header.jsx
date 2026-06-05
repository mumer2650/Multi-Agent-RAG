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
export default function Header({ currentView, onViewChange }) {
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
    <header className="sticky top-0 w-full z-50 backdrop-blur-md bg-white/80 dark:bg-slate-900/80 border-b border-gray-200 dark:border-gray-800 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center w-full">
      {/* App Title */}
      <div className="font-extrabold text-3xl tracking-tight bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 bg-clip-text text-transparent select-none cursor-pointer">
        SAGE
      </div>
      
      <div className="flex items-center gap-6">
        {/* Navigation Group */}
        {onViewChange && (
          <div className="flex gap-4 items-center">
            <button 
              onClick={() => onViewChange('chat')}
              className={`px-4 py-2 rounded-full font-medium transition-colors ${
                currentView === 'chat' 
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md border-none' 
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 bg-transparent'
              }`}
            >
              Chat
            </button>
            <button 
              onClick={() => onViewChange('admin')}
              className={`px-4 py-2 rounded-full font-medium transition-colors ${
                currentView === 'admin' 
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md border-none' 
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 bg-transparent'
              }`}
            >
              Admin Dashboard
            </button>
          </div>
        )}
        
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
      </div>
      </div>
    </header>
  );
}
