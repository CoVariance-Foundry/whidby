import PasswordResetForm from "./PasswordResetForm";

export const dynamic = "force-dynamic";

export default function PasswordSettingsPage() {
  return (
    <main className="page" style={{ maxWidth: 840, margin: "0 auto", width: "100%" }}>
      <PasswordResetForm />
    </main>
  );
}
