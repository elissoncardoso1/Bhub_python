import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";
import { ArticlesPageClient } from "@/components/Admin/Articles/ArticlesPageClient";

export default async function ArticlesPage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect("/auth/signin");
  }

  return <ArticlesPageClient />;
}
