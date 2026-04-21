import { redirect } from "next/navigation";

// Home page stub — the academic Home design is in a later ticket.
// For now, route authenticated users to Reports (the only built page).
export default function RootRedirect() {
  redirect("/reports");
}
