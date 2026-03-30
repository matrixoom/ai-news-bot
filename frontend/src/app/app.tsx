import { createBrowserRouter, createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "./providers";
import { appRoutes } from "./routes";

const router =
  import.meta.env.MODE === "test"
    ? createMemoryRouter(appRoutes, {
        initialEntries: ["/dashboard"],
      })
    : createBrowserRouter(appRoutes);

export function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
