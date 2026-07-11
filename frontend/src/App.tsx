import { AppProviders } from "@/app/providers/AppProviders";
import { AppRouter } from "@/app/router";

export function App() {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
}
