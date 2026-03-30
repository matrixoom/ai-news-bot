import { BrowserRouter, useRoutes } from "react-router-dom";
import { AppProviders } from "./providers";
import { appRoutes } from "./routes";

function AppRoutes() {
  return useRoutes(appRoutes);
}

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AppProviders>
  );
}
