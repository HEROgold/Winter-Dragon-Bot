# Winter Dragon Bot Frontend - Issues to Fix

## React Router Issues

1. **Invalid Element Type Error:**
   - Error message: `Error: Element type is invalid: expected a string (for built-in components) or a class/function (for composite components) but got: object. You likely forgot to export your component from the file it's defined in, or you might have mixed up default and named imports.`
   - This suggests we have components that aren't correctly exported or imported
   - Check all feature page components to make sure they're properly defined and exported as default exports

2. **Missing Route Paths:**
   - Error: `Error: No route matches URL "/dashboard"`
   - Error: `Error: No route matches URL "/premium"`
   - Error: `Error: No route matches URL "/commands"`
   - We need to create these routes or update the navigation links to use valid routes

## Tasks to Fix the Issues

1. Create placeholder pages for:
   - `/dashboard`
   - `/premium`
   - `/commands`
   - `/docs`
   - `/faq`
   - `/issues`
   - `/terms`
   - `/privacy`
   - `/cookies`

2. Check all imports and exports in the router configuration:
   - Make sure all feature pages are properly imported in `routes/index.tsx`
   - Verify that all imports match the actual exports (default vs named exports)

3. Review the feature imports in the router to ensure they point to actual files:
   - Verify paths: `/features/moderation`, `/features/auto-mod`, etc.
   - Make sure the file structure matches the imports

4. Add error boundaries and 404 page handling for non-existent routes

5. Make sure all feature page components are created and exported properly:
   - `ModerationFeature`
   - `AutoModFeature`
   - `CustomCommandsFeature`
   - `WelcomeFeature`
   - `LoggingFeature`
   - `FunFeature`
