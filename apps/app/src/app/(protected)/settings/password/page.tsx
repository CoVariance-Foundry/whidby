import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import PasswordResetForm from "./PasswordResetForm";

export const dynamic = "force-dynamic";

export default function PasswordSettingsPage() {
  return (
    <div className="app">
      <Sidebar active="settings" />
      <div className="main">
        <Topbar crumbs={["Settings", "Password"]} />
        <main className="page" style={{ maxWidth: 840, margin: "0 auto", width: "100%" }}>
          <PasswordResetForm />
        </main>
      </div>
    </div>
  );
}
