import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProviders } from "./providers";
import { AppShell } from "../layouts/app-shell";
import { ModulePlaceholderPage } from "../pages/module-placeholder-page";

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<ModulePlaceholderPage />} />
            <Route path="news" element={<ModulePlaceholderPage />} />
            <Route path="macro" element={<ModulePlaceholderPage />} />
            <Route path="market" element={<ModulePlaceholderPage />} />
            <Route path="events" element={<ModulePlaceholderPage />} />
            <Route path="push" element={<ModulePlaceholderPage />} />
            <Route path="settings" element={<ModulePlaceholderPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProviders>
  );
}
