import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";
import { FeedsPageClient } from "@/components/Admin/Feeds/FeedsPageClient";

export default async function FeedsPage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect("/auth/signin");
  }

  return <FeedsPageClient />;
}
