import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "./providers";
import { appRoutes } from "./routes";

const initialEntry = `${window.location.pathname}${window.location.search}${window.location.hash}`;
const router = createMemoryRouter(appRoutes, {
  initialEntries: [initialEntry],
});

export function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
