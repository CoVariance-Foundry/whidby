import { redirect } from "next/navigation";
import { isRedirectError } from "next/dist/client/components/redirect-error";
import Footer from "@/components/Footer";
import Navbar, { type NavbarUser } from "@/components/Navbar";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { loadAccountSummary } from "@/lib/account/summary";
import { createClient } from "@/lib/supabase/server";

function deriveInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  return (parts[0] ?? "U").slice(0, 2).toUpperCase();
}

export default async function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const adminUrl = process.env.NEXT_PUBLIC_ADMIN_URL ?? "http://localhost:3001";
  let navbarUser: NavbarUser | null = null;

  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      redirect("/login");
    }

    const displayName =
      user.user_metadata?.full_name ??
      user.user_metadata?.name ??
      user.email ??
      "User";
    const email = user.email ?? displayName;

    navbarUser = {
      email,
      displayName,
      initials: deriveInitials(displayName),
      planLabel: "Free",
      scansUsed: 0,
      scansLimit: 0,
      adminUrl,
      isAdmin: false,
      freshReportQuotaExempt: false,
    };

    try {
      const { entitlement } = await resolveEntitlementContext(supabase);
      const summary = await loadAccountSummary({ supabase, user, entitlement });
      navbarUser = {
        ...navbarUser,
        email: summary.email,
        planLabel: summary.plan_label,
        scansUsed: summary.fresh_reports_used,
        scansLimit: summary.monthly_report_limit,
        isAdmin: entitlement.member_role === "admin",
        freshReportQuotaExempt: entitlement.fresh_report_quota_exempt,
      };
    } catch (error) {
      if (isRedirectError(error)) throw error;
      navbarUser = {
        ...navbarUser,
        planLabel: "Free",
        scansUsed: 0,
        scansLimit: 0,
        isAdmin: false,
        freshReportQuotaExempt: false,
      };
    }
  } catch (error) {
    if (isRedirectError(error)) throw error;
    redirect("/login");
  }

  if (!navbarUser) {
    redirect("/login");
  }

  return (
    <div className="app density-roomy">
      <Navbar user={navbarUser} />
      <div className="app-main">{children}</div>
      <Footer />
    </div>
  );
}
